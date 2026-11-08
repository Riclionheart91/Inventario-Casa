"""Livello HTTP sottile (FastAPI). Non testato qui: PyPI non raggiungibile nell'ambiente di sviluppo."""
import hmac
import logging
import os
from pathlib import Path

import threading
import time

from starlette.concurrency import run_in_threadpool
from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .service import ApiError, Inventory
from . import ai, aiuso, analisi, lookup, pagina, regole_auto, ricerca
from .accesso import Accesso, _Mw
from .store import make_store

app = FastAPI(title="Inventario Casa", docs_url=None, redoc_url=None)
app.add_middleware(GZipMiddleware, minimum_size=1000)


def _tieni_fresco():
    """Rilegge i fogli ogni 20 secondi in background: cosi Stock e Prodotti rispondono dalla memoria."""
    while True:
        try:
            inv().refresh()
        except Exception:   # rete o quota di Google: si riprova al giro dopo
            pass
        time.sleep(20)


_arr = None


def _chiavi_ricerca():
    return {k: _env(k) for k in ("BRAVE_SEARCH_KEY", "SERPER_KEY", "TAVILY_KEY") if _env(k)}


def _web_dati(bc, solo_con_immagine=False):
    """Ricerca web: prima l'app cerca sul web (senza AI) e passa i risultati a Gemini da leggere; se non trova niente prova lo strumento di ricerca di Gemini.
    Nome, marca, confezione e, se una pagina che riporta davvero il codice ce l'ha, l'immagine."""
    if not _env("GEMINI_API_KEY"):
        return None
    testo, urls = ricerca.contesto([str(bc), "%s codice a barre prodotto" % bc], bc, _chiavi_ricerca())
    r = ai.cerca_web(bc, _env("GEMINI_API_KEY"), _env("GEMINI_MODELLO"), _env("GEMINI_MODELLO_RISERVA"), contesto=testo) if testo else None
    if not r:
        r = ai.cerca_web(bc, _env("GEMINI_API_KEY"), _env("GEMINI_MODELLO"), _env("GEMINI_MODELLO_RISERVA"))
    if not r:
        return None
    img = ""
    for u in list(r.get("urls", [])) + urls:
        img = pagina.immagine_da_pagina(u, bc)
        if img:
            break
    if not img and (solo_con_immagine or not r.get("nome")):
        return None
    return {"nome": r["nome"], "marca": r["marca"], "confezione": r["confezione"], "immagine": img}


def _web(bc):
    return _web_dati(bc, True)


_rev = None
_ult_rev = [0.0]


def rev():
    global _rev
    if _rev is None:
        from .revisione import Revisione
        def sugg(nome, marca, conf, cats, tipi):
            if not _env("GEMINI_API_KEY"):
                return None
            return ai.suggerisci(nome, marca, conf, cats, tipi, _env("GEMINI_API_KEY"), _env("GEMINI_MODELLO"), _env("GEMINI_MODELLO_RISERVA"))
        def ctrl(prodotti, cats):
            if not _env("GEMINI_API_KEY"):
                return None
            return ai.controlla_categorie(prodotti, cats, _env("GEMINI_API_KEY"), _env("GEMINI_MODELLO"), _env("GEMINI_MODELLO_RISERVA"))
        def gen(prodotti, tipi):
            if not _env("GEMINI_API_KEY"):
                return None
            return ai.tipi_generici(prodotti, tipi, _env("GEMINI_API_KEY"), _env("GEMINI_MODELLO"), _env("GEMINI_MODELLO_RISERVA"))
        _rev = Revisione(inv(), sugg, controlla=ctrl, generalizza=gen, arricchisci=lambda: threading.Thread(target=lambda: arr().esegui(int(_env("ARRICCHIMENTO_MAX") or 60), ignora_prove=True), daemon=True).start())
    return _rev


def arr():
    global _arr
    if _arr is None:
        from .arricchimento import Arricchitore
        chiave = lambda: _env("GEMINI_API_KEY")
        def web(bc):
            r = _web(bc)
            return r and dict(r, fonte="Web", dettagli="", composizione="", nutrizione="", punteggi="")
        def extra(bc, nome, marca, conf):   # punteggi e riciclo che nessun archivio ha: li cerca l'AI con Google
            if not chiave():
                return None
            testo, _ = ricerca.contesto(["%s %s %s nutri-score nova eco-score" % (nome, marca, conf), str(bc)], bc, _chiavi_ricerca())
            r = ai.integra_scheda(bc, nome, marca, conf, chiave(), _env("GEMINI_MODELLO"), _env("GEMINI_MODELLO_RISERVA"), contesto=testo) if testo else None
            return r or ai.integra_scheda(bc, nome, marca, conf, chiave(), _env("GEMINI_MODELLO"), _env("GEMINI_MODELLO_RISERVA"))
        _arr = Arricchitore(inv(), lambda bc: lookup.cerca(bc, chiavi=chiavi()),
                            lambda testi: ai.traduci(testi, chiave(), _env("GEMINI_MODELLO"), _env("GEMINI_MODELLO_RISERVA")), web=web, extra=extra)
    return _arr


_avv = None


def avv():
    global _avv
    if _avv is None:
        from datetime import datetime
        from .avvisi import Avvisi
        try:
            from zoneinfo import ZoneInfo
            fuso = ZoneInfo("Europe/Rome")
        except Exception:
            fuso = None
        _avv = Avvisi(inv(), oggi=lambda: datetime.now(fuso) if fuso else datetime.now())
    return _avv


@app.post("/api/foglio/riordina")
def foglio_riordina(x_code: str = Header(None)):
    """Riordina il foglio Google per l'app (nasconde fogli e colonne di AppSheet, ordina, filtri, formati). Non cancella nulla."""
    check(x_code)
    writable()
    from . import foglio
    try:
        r = foglio.applica(inv().store)
    except Exception as e:
        raise HTTPException(502, "Riordino non riuscito: %s" % e)
    inv()._cache.clear(); inv()._memo.clear()   # le colonne hanno cambiato posto: si rilegge tutto
    return r


@app.get("/api/avvisi")
def avvisi_stato(x_code: str = Header(None)):
    check(x_code)
    return dict(avv().stato(), servizio=_env("SCADENZA_NOTIFICA"), giorni=_giorni_scadenza(), ora=_env("SCADENZA_ORA") or "08:00")


@app.post("/api/avvisi/prova")
def avvisi_prova(x_code: str = Header(None)):
    """Invia subito una notifica di prova (anche se non c'e nulla in scadenza)."""
    check(x_code)
    if not _env("SCADENZA_NOTIFICA"):
        raise HTTPException(400, "Scegli il servizio notify nelle opzioni dell'app (scadenza_notifica).")
    try:
        return avv().esegui(_env("SCADENZA_NOTIFICA"), _giorni_scadenza(), url=_env("SECURE_URL") or "", forza=True)
    except Exception as e:
        raise HTTPException(502, "Notifica non inviata: %s" % e)


def _notturno():
    """Attivita programmata: ogni notte (all'ora scelta nelle opzioni) cerca i dati mancanti e traduce in italiano. Solo se acceso e non in sola lettura."""
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        fuso = ZoneInfo("Europe/Rome")
    except Exception:
        fuso = None
    while True:
        try:
            if os.environ.get("ARRICCHIMENTO", "false").lower() == "true" and not READ_ONLY:
                ora = (_env("ARRICCHIMENTO_ORA") or "03:00")
                adesso = datetime.now(fuso) if fuso else datetime.now()
                if adesso.strftime("%H:%M") >= ora and arr().da_fare_oggi():
                    arr().oggi = (lambda: datetime.now(fuso) if fuso else datetime.now())
                    arr().esegui(int(_env("ARRICCHIMENTO_MAX") or 60))
        except Exception:
            logging.getLogger("inventario").exception("arricchimento notturno")
        try:   # avviso giornaliero delle scadenze: una notifica di Home Assistant dopo l'ora scelta (non scrive sul foglio)
            if _env("SCADENZA_NOTIFICA"):
                avv().esegui(_env("SCADENZA_NOTIFICA"), _giorni_scadenza(), _env("SCADENZA_ORA") or "08:00", _env("SECURE_URL") or "")
        except Exception:
            logging.getLogger("inventario").exception("avviso scadenze")
        try:   # revisione a tappeto ogni sei mesi: non scrive sul foglio, quindi parte anche in sola lettura
            if rev().dovuta() and time.time() - _ult_rev[0] > 3600:   # al piu un tentativo all'ora
                _ult_rev[0] = time.time()
                rev().esegui()
        except Exception:
            logging.getLogger("inventario").exception("revisione semestrale")
        time.sleep(60)


@app.on_event("startup")
def _avvio():
    threading.Thread(target=_tieni_fresco, daemon=True).start()
    threading.Thread(target=_notturno, daemon=True).start()
    if os.environ.get("ARRICCHIMENTO_AVVIO", "false").lower() == "true" and not READ_ONLY:   # una tantum: cerca subito i dati mancanti (anche con l'AI su Google)
        threading.Thread(target=lambda: arr().esegui(int(_env("ARRICCHIMENTO_MAX") or 60), 3000.0), daemon=True).start()
    if os.environ.get("TRADUZIONE_AVVIO", "false").lower() == "true" and not READ_ONLY:   # una tantum: traduce in italiano i testi esistenti
        threading.Thread(target=lambda: arr().esegui(0, 3000.0, True), daemon=True).start()
_inv = None
SHARED = os.environ.get("SHARED_CODE", "")
ACCESSO = Accesso(lambda: SHARED)
app.add_middleware(_Mw, acc=ACCESSO)
READ_ONLY = os.environ.get("READ_ONLY", "true").lower() != "false"
# Chiavi dalle opzioni dell'app (variabili d'ambiente): restano sul server, non vanno mai al frontend ne nei log.
CHIAVI_PROVIDER = ("BARCODELOOKUP_KEY", "UPCDATABASE_KEY", "GOUPC_TOKEN", "SPOONACULAR_KEY", "NUTRITIONIX_APP_ID", "NUTRITIONIX_APP_KEY",
                   "EDAMAM_APP_ID", "EDAMAM_APP_KEY", "ICECAT_SHOP", "ICECAT_API_TOKEN", "GS1_API_URL", "GS1_API_KEY", "GOOGLE_BOOKS_KEY", "OPENFDA_KEY")


def _env(k):
    v = os.environ.get(k, "").strip()
    return "" if v.lower() == "null" else v


def _giorni_scadenza() -> int:
    try:
        return max(0, min(90, int(_env("SCADENZA_GIORNI") or 7)))
    except ValueError:
        return 7


def chiavi():
    return {k: _env(k) for k in CHIAVI_PROVIDER if _env(k)}


def inv() -> Inventory:
    global _inv
    if _inv is None:
        _inv = Inventory(make_store(), ttl=90)   # le richieste rispondono dalla memoria; il ciclo sotto la tiene fresca
        aiuso.ATTIVO = True                       # conteggio e memoria delle risposte AI solo nell'app (non nei test)
        ai.regole_provider = _inv.regole          # le regole della casa entrano nelle richieste all'AI
    return _inv


def check(code):
    """Il frontend non invia x-code: il gate vero e il middleware di accesso (ingress HA oppure sessione sulla porta diretta).
    Qui si rifiuta solo un header x-code presente ma errato."""
    if SHARED and code is not None and not hmac.compare_digest(code, SHARED):
        raise HTTPException(401, "Codice mancante o errato")


def writable():
    if READ_ONLY:
        raise HTTPException(403, "Modalita sola lettura attiva")


@app.exception_handler(ApiError)
async def _api_error(_, e: ApiError):
    return JSONResponse({"errore": e.msg}, status_code=e.status)


@app.exception_handler(Exception)
async def _errore_generico(_, e: Exception):
    """Errori imprevisti (rete, Google): si registrano e si mostra il motivo breve invece di un muto 'Errore 500'."""
    logging.getLogger("inventario").exception("errore non gestito")
    return JSONResponse({"errore": "Errore del foglio Google, riprova: %s" % (str(e) or type(e).__name__)[:120]}, status_code=500)


class Mov(BaseModel):
    barcode: str
    tipo: str
    location: str
    quantita: float = 1
    prodotto: str = ""
    foto: str = ""
    destinazione: str = ""
    categoria: str = ""
    categoria_new: str = ""
    scadenza: str = ""


class ModProd(BaseModel):
    sottocategoria: str


class NuovoProd(BaseModel):
    barcode: str
    nome: str
    marca: str = ""
    confezione: str = ""
    immagine: str = ""
    categoria: str = ""
    sottocategoria: str = ""
    tipo: str = ""
    dettagli: str = ""
    composizione: str = ""
    nutrizione: str = ""
    punteggi: str = ""
    fonte: str = "App"
    location: str = ""
    quantita: float = 1


class ScortaIn(BaseModel):
    tipo: str
    scorta: float


class Dec(BaseModel):
    azione: str
    campi: dict = {}


class CampiBozza(BaseModel):
    campi: dict = {}


@app.post("/api/tipi/scorta")
def imposta_scorta(m: ScortaIn, x_code: str = Header(None)):
    check(x_code)
    writable()
    return inv().imposta_scorta(m.tipo, m.scorta)


@app.get("/api/arricchimento")
def arricchimento_stato(x_code: str = Header(None)):
    check(x_code)
    return dict(arr().stato(), attivo=os.environ.get("ARRICCHIMENTO", "false").lower() == "true", sola_lettura=READ_ONLY)


@app.post("/api/arricchimento/avvia")
def arricchimento_avvia(x_code: str = Header(None)):
    """Lancia subito un giro (stesso lavoro della notte)."""
    check(x_code)
    writable()
    threading.Thread(target=lambda: arr().esegui(int(_env("ARRICCHIMENTO_MAX") or 60), ignora_prove=True), daemon=True).start()
    return {"ok": True, "avviato": True}


def _voce_ok(t: str):
    tok = _env("VOCE_TOKEN")
    if not tok:
        raise HTTPException(403, "Risposte a voce spente: imposta voce_token nelle opzioni dell'app.")
    if not t or not hmac.compare_digest(str(t), tok):
        raise HTTPException(401, "Token errato")


@app.get("/voce/manca")
def voce_manca(t: str = ""):
    """Frase pronta per Google Home / Assist: cosa manca in casa."""
    _voce_ok(t)
    return {"testo": inv().voce_manca()}


@app.get("/voce/cerca")
def voce_cerca(q: str = "", t: str = ""):
    """Frase pronta: ho questo prodotto e dove?"""
    _voce_ok(t)
    return {"testo": inv().voce_cerca(q[:80])}


@app.get("/api/config")
def config(request: Request):
    return {"diretto": ACCESSO.e_diretto(request.scope), "url_sicuro": os.environ.get("SECURE_URL", "").strip(), "sola_lettura": READ_ONLY, "ai": bool(_env("GEMINI_API_KEY")),
            "shortcut_spesa": (os.environ.get("SHORTCUT_SPESA", "Spesa AppSheet") or "Spesa AppSheet").strip()}


@app.get("/api/stock")
def stock(x_code: str = Header(None)):
    check(x_code)
    return inv().stock()


@app.get("/api/prodotto/{barcode}")
def prodotto(barcode: str, x_code: str = Header(None)):
    check(x_code)
    p = inv().prodotto(barcode)
    if p is None:
        return {"found": False}   # codice nuovo: non e un errore
    return dict(p, found=True)


@app.get("/api/cerca/{barcode}")
def cerca(barcode: str, x_code: str = Header(None)):
    """Cerca il codice sui database aperti. Non scrive nulla: la proposta si conferma dalla schermata."""
    check(x_code)
    t0 = time.time()
    r = lookup.cerca(barcode, chiavi=chiavi())
    if r:
        return dict(r, found=True)
    errs = sorted({"%s (%s)" % (h, msg) for t, h, msg in list(lookup.ERRORI) if t >= t0})
    if errs:
        logging.getLogger("inventario").warning("ricerca %s: %s", barcode, "; ".join(errs))
    return {"found": False, "errori": errs[:6]}


class ChiediAi(BaseModel):
    nome: str
    marca: str = ""
    confezione: str = ""


@app.post("/api/suggerisci")
def suggerisci(m: ChiediAi, x_code: str = Header(None)):
    """Suggerimento AI di categoria, sottocategoria e tipo. Non scrive nulla; senza chiave o se Gemini non risponde: ai=False."""
    check(x_code)
    if not _env("GEMINI_API_KEY"):
        return {"ai": False, "motivo": "chiave"}
    s = ai.suggerisci(m.nome, m.marca, m.confezione, inv().categorie(), inv().tipi(), _env("GEMINI_API_KEY"),
                      _env("GEMINI_MODELLO"), _env("GEMINI_MODELLO_RISERVA"))
    if s and s.get("proposta") and not READ_ONLY:
        p = s["proposta"]
        inv().proponi_categoria(p["categoria"], p["sottocategoria"], m.nome, p.get("categoria_nuova", False))
    return dict(s, ai=True) if s else {"ai": False, "motivo": "risposta", "dettaglio": ai.ULTIMO_ERRORE[0]}


@app.get("/api/tipi")
def tipi(x_code: str = Header(None)):
    check(x_code)
    return inv().tipi()


@app.post("/api/prodotto")
def crea_prodotto(m: NuovoProd, x_code: str = Header(None)):
    check(x_code)
    writable()
    return inv().crea_prodotto(m.barcode, m.nome, m.marca, m.confezione, m.immagine, m.categoria, m.sottocategoria,
                               m.tipo, m.dettagli, m.composizione, m.nutrizione, m.punteggi, m.fonte, m.location, m.quantita)


@app.get("/api/categorie")
def categorie(x_code: str = Header(None)):
    check(x_code)
    return inv().categorie()


class ModTipo(BaseModel):
    tipo: str


class ModDati(BaseModel):
    nome: str
    marca: str = ""
    confezione: str = ""


@app.patch("/api/prodotto/{barcode}/dati")
def modifica_dati(barcode: str, m: ModDati, x_code: str = Header(None)):
    check(x_code)
    writable()
    return inv().modifica_dati(barcode, m.nome, m.marca, m.confezione)


@app.patch("/api/prodotto/{barcode}/tipo")
def modifica_tipo(barcode: str, m: ModTipo, x_code: str = Header(None)):
    check(x_code)
    writable()
    return inv().imposta_tipo(barcode, m.tipo)


@app.patch("/api/prodotto/{barcode}")
def modifica_prodotto(barcode: str, m: ModProd, x_code: str = Header(None)):
    check(x_code)
    writable()
    return inv().modifica_prodotto(barcode, m.sottocategoria)


@app.get("/api/prodotti")
def prodotti(x_code: str = Header(None)):
    check(x_code)
    return inv().elenco_prodotti()


@app.get("/api/scheda/{barcode}")
def scheda(barcode: str, x_code: str = Header(None)):
    check(x_code)
    p = inv().scheda(barcode)
    if p is None:
        raise HTTPException(404, "Codice sconosciuto")
    return p


@app.post("/api/movimento")
def movimento(m: Mov, x_code: str = Header(None)):
    check(x_code)
    writable()
    return inv().movimento(m.barcode, m.tipo, m.location, m.quantita, m.prodotto, m.foto,
                          m.destinazione, m.categoria, m.categoria_new, scadenza=m.scadenza)


@app.get("/api/scadenze")
def scadenze(x_code: str = Header(None)):
    check(x_code)
    return inv().scadenze(_giorni_scadenza())


@app.get("/api/ai/uso")
def ai_uso(x_code: str = Header(None)):
    check(x_code)
    return aiuso.riepilogo(7)


@app.post("/api/ai/modelli")
async def ai_modelli(x_code: str = Header(None)):
    check(x_code)
    return await run_in_threadpool(ai.verifica_modelli, _env("GEMINI_API_KEY"))


@app.post("/api/ricerca/prova")
async def ricerca_prova(x_code: str = Header(None)):
    """Prova la ricerca web dell'app (senza AI) con una domanda di esempio: dice quale fonte usa e cosa trova."""
    check(x_code)
    def f():
        ch = _chiavi_ricerca()
        r = ricerca.cerca("Barilla spaghetti n.5 500 g", ch)
        return {"fonte": ricerca.fonte(ch), "risultati": len(r), "primo": (r[0]["titolo"] + " — " + r[0]["url"]) if r else "", "errore": "" if r else (ricerca.ULTIMO_ERRORE[0] or "nessun risultato")}
    return await run_in_threadpool(f)


@app.post("/api/ai/memoria/svuota")
def ai_memoria_svuota(x_code: str = Header(None)):
    check(x_code)
    writable()
    return {"svuotate": aiuso.svuota_memoria()}


class Regola(BaseModel):
    testo: str
    chiave: str = ""


@app.get("/api/regole")
def regole_elenco(x_code: str = Header(None)):
    check(x_code)
    return inv().regole()


@app.post("/api/regole")
def regole_aggiungi(r: Regola, x_code: str = Header(None)):
    check(x_code)
    writable()
    out = inv().aggiungi_regola(r.testo)
    regole_auto.segna(r.chiave)
    return out


@app.post("/api/regole/suggerisci")
def regole_suggerisci(x_code: str = Header(None)):
    """Regole desunte dai dati (catalogo e correzioni passate), riscritte da Gemini in modo chiaro. Non scrive niente."""
    check(x_code)
    c = inv().candidate_regole()
    if c and _env("GEMINI_API_KEY"):
        frasi = ai.riscrivi_regole([x["bozza"] for x in c], _env("GEMINI_API_KEY"), _env("GEMINI_MODELLO"), _env("GEMINI_MODELLO_RISERVA"))
        for x, f in zip(c, frasi):
            x["testo"] = regole_auto.chiara(f, x)
    for x in c:
        x.setdefault("testo", x["bozza"])
        x.pop("obbligatori", None)
    return c


@app.post("/api/regole/scarta")
def regole_scarta(r: Regola, x_code: str = Header(None)):
    check(x_code)
    regole_auto.segna(r.chiave)
    return {"ok": True}


@app.post("/api/regole/elimina")
def regole_elimina(r: Regola, x_code: str = Header(None)):
    check(x_code)
    writable()
    return inv().elimina_regola(r.testo)


@app.get("/api/approvazioni")
def approvazioni(x_code: str = Header(None)):
    check(x_code)
    return inv().approvazioni() + rev().voci_aperte()


@app.get("/api/revisione")
def revisione_stato(x_code: str = Header(None)):
    check(x_code)
    return dict(rev().stato(), sola_lettura=READ_ONLY)


@app.post("/api/revisione/avvia")
def revisione_avvia(x_code: str = Header(None)):
    """La revisione non scrive sul foglio (solo le voci che approvi): si puo lanciare anche in sola lettura."""
    check(x_code)
    threading.Thread(target=lambda: rev().esegui(), daemon=True).start()
    return {"ok": True, "avviato": True}


@app.post("/api/approvazioni/{id_}")
def decidi(id_: str, d: Dec, x_code: str = Header(None)):
    check(x_code)
    if id_.startswith("R_"):
        if d.azione.upper() == "APPROVA":
            writable()
        r = rev().decidi(id_, d.azione, d.campi)
        if r.get("errore"):
            raise HTTPException(r.get("stato", 400), r["errore"])
        return r
    writable()
    return inv().decidi(id_, d.azione, d.campi)


@app.get("/api/spesa")
def spesa(x_code: str = Header(None)):
    check(x_code)
    return inv().spesa()


@app.get("/api/bozze")
def bozze(x_code: str = Header(None)):
    check(x_code)
    return inv().bozze()


@app.post("/api/bozze/{id_}/salva")
def bozza_salva(id_: str, d: CampiBozza, x_code: str = Header(None)):
    check(x_code)
    writable()
    return inv().bozza_salva(id_, d.campi)


@app.post("/api/bozze/{id_}/conferma")
def bozza_conferma(id_: str, d: CampiBozza, x_code: str = Header(None)):
    check(x_code)
    writable()
    return inv().bozza_conferma(id_, d.campi)


@app.post("/api/bozze/{id_}/scarta")
def bozza_scarta(id_: str, x_code: str = Header(None)):
    check(x_code)
    writable()
    return inv().bozza_scarta(id_)


@app.post("/api/foto")
async def foto(barcode: str = Form(...), file: UploadFile = File(...), x_code: str = Header(None)):
    check(x_code)
    writable()
    dati, mime = await file.read(), file.content_type or ""
    out = dict(inv().foto(barcode, dati, mime), id="AI")   # id: segnaposto per le versioni vecchie della pagina rimaste in cache
    if _env("GEMINI_API_KEY"):   # la foto va solo a Gemini, non si salva da nessuna parte
        # risponde subito: l'AI e la ricerca web girano in background e completano la bozza quando finiscono (il salvataggio non aspetta)
        threading.Thread(target=_analizza_foto, args=(barcode, dati, mime), daemon=True).start()
    return out


class FotoUrl(BaseModel):
    barcode: str
    url: str


@app.post("/api/foto_url")
def foto_url(m: FotoUrl, x_code: str = Header(None)):
    """Il database ha trovato il codice ma non il nome: la sua foto va all'AI al posto di quella scattata (stessa analisi, in background)."""
    check(x_code)
    writable()
    inv().foto(m.barcode, b"x", "image/jpeg")   # solo il controllo del codice
    if _env("GEMINI_API_KEY"):
        threading.Thread(target=_analizza_foto_url, args=(m.barcode, m.url), daemon=True).start()
    return {"ok": True, "url": "", "id": "AI"}


def _analizza_foto_url(barcode: str, url: str) -> None:
    def foto():
        try:
            dati, mime = lookup.scarica_immagine(url)
        except Exception:
            return None
        if not dati or not mime:
            return None
        return ai.foto_prodotto(dati, mime, inv().categorie(), inv().tipi(), _env("GEMINI_API_KEY"), _env("GEMINI_MODELLO"), _env("GEMINI_MODELLO_RISERVA"))
    _analizza(barcode, foto, url)


def _analizza_foto(barcode: str, dati: bytes, mime: str) -> None:
    _analizza(barcode, lambda: ai.foto_prodotto(dati, mime, inv().categorie(), inv().tipi(), _env("GEMINI_API_KEY"), _env("GEMINI_MODELLO"), _env("GEMINI_MODELLO_RISERVA")))


def _analizza(barcode: str, da_foto, immagine: str = "") -> None:
    """In background: prima la ricerca per codice a barre sul web; la foto si legge solo se il web non da il nome (o per completare la categoria)."""
    try:
        cod = lookup.codice_da_cercare(barcode)
        a = analisi.analizza(lambda: _web_dati(cod) if cod else None,
                             lambda n, m, c: ai.suggerisci(n, m, c, inv().categorie(), inv().tipi(), _env("GEMINI_API_KEY"), _env("GEMINI_MODELLO"), _env("GEMINI_MODELLO_RISERVA")),
                             da_foto, immagine)
        if a and a.get("proposta") and not READ_ONLY:
            p = a["proposta"]
            inv().proponi_categoria(p["categoria"], p["sottocategoria"], a.get("nome", ""), p.get("categoria_nuova", False))
        inv().applica_analisi(barcode, a or None)
    except Exception:
        logging.getLogger("inventario").exception("analisi foto %s", barcode)
        try:
            inv().applica_analisi(barcode, None)
        except Exception:
            pass
