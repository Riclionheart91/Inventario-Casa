"""Livello HTTP sottile (FastAPI). Non testato qui: PyPI non raggiungibile nell'ambiente di sviluppo."""
import hmac
import logging
import os
from pathlib import Path

import threading
import time

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .service import ApiError, Inventory
from . import ai, lookup
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


def arr():
    global _arr
    if _arr is None:
        from .arricchimento import Arricchitore
        chiave = lambda: _env("GEMINI_API_KEY")
        _arr = Arricchitore(inv(), lambda bc: lookup.cerca(bc, chiavi=chiavi()),
                            lambda testi: ai.traduci(testi, chiave(), _env("GEMINI_MODELLO"), _env("GEMINI_MODELLO_RISERVA")))
    return _arr


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
        time.sleep(60)


@app.on_event("startup")
def _avvio():
    threading.Thread(target=_tieni_fresco, daemon=True).start()
    threading.Thread(target=_notturno, daemon=True).start()
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


def chiavi():
    return {k: _env(k) for k in CHIAVI_PROVIDER if _env(k)}


def inv() -> Inventory:
    global _inv
    if _inv is None:
        _inv = Inventory(make_store(), ttl=90)   # le richieste rispondono dalla memoria; il ciclo sotto la tiene fresca
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


class Dec(BaseModel):
    azione: str
    campi: dict = {}


class CampiBozza(BaseModel):
    campi: dict = {}


@app.get("/api/arricchimento")
def arricchimento_stato(x_code: str = Header(None)):
    check(x_code)
    return dict(arr().stato(), attivo=os.environ.get("ARRICCHIMENTO", "false").lower() == "true", sola_lettura=READ_ONLY)


@app.post("/api/arricchimento/avvia")
def arricchimento_avvia(x_code: str = Header(None)):
    """Lancia subito un giro (stesso lavoro della notte)."""
    check(x_code)
    writable()
    threading.Thread(target=lambda: arr().esegui(int(_env("ARRICCHIMENTO_MAX") or 60)), daemon=True).start()
    return {"ok": True, "avviato": True}


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
                          m.destinazione, m.categoria, m.categoria_new)


@app.get("/api/approvazioni")
def approvazioni(x_code: str = Header(None)):
    check(x_code)
    return inv().approvazioni()


@app.post("/api/approvazioni/{id_}")
def decidi(id_: str, d: Dec, x_code: str = Header(None)):
    check(x_code)
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
    return inv().foto(barcode, await file.read(), file.content_type or "")


STATIC = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
