"""Livello HTTP sottile (FastAPI). Non testato qui: PyPI non raggiungibile nell'ambiente di sviluppo."""
import hmac
import os
from pathlib import Path

import threading
import time

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .service import ApiError, Inventory
from . import ai, lookup
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


@app.on_event("startup")
def _avvio():
    threading.Thread(target=_tieni_fresco, daemon=True).start()
_inv = None
SHARED = os.environ.get("SHARED_CODE", "")
READ_ONLY = os.environ.get("READ_ONLY", "true").lower() != "false"
# Chiavi dalle opzioni dell'app (variabili d'ambiente): restano sul server, non vanno mai al frontend ne nei log.
CHIAVI_PROVIDER = ("BARCODELOOKUP_KEY", "UPCDATABASE_KEY", "GOUPC_TOKEN", "SPOONACULAR_KEY", "NUTRITIONIX_APP_ID", "NUTRITIONIX_APP_KEY",
                   "EDAMAM_APP_ID", "EDAMAM_APP_KEY", "ICECAT_SHOP", "ICECAT_API_TOKEN", "GS1_API_URL", "GS1_API_KEY")


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
    """Codice opzionale (seconda barriera). Il login resta quello di Home Assistant (ingress)."""
    if SHARED and not hmac.compare_digest(code or "", SHARED):
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


class Dec(BaseModel):
    azione: str


@app.get("/api/config")
def config():
    return {"url_sicuro": os.environ.get("SECURE_URL", "").strip(), "sola_lettura": READ_ONLY, "ai": bool(_env("GEMINI_API_KEY"))}


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
    r = lookup.cerca(barcode, chiavi=chiavi())
    return dict(r, found=True) if r else {"found": False}


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
    return dict(s, ai=True) if s else {"ai": False, "motivo": "risposta"}


@app.get("/api/tipi")
def tipi(x_code: str = Header(None)):
    check(x_code)
    return inv().tipi()


@app.post("/api/prodotto")
def crea_prodotto(m: NuovoProd, x_code: str = Header(None)):
    check(x_code)
    writable()
    return inv().crea_prodotto(m.barcode, m.nome, m.marca, m.confezione, m.immagine, m.categoria, m.sottocategoria,
                               m.tipo, m.dettagli, m.composizione, m.nutrizione, m.punteggi, m.fonte)


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
    return inv().decidi(id_, d.azione)


@app.post("/api/foto")
async def foto(barcode: str = Form(...), file: UploadFile = File(...), x_code: str = Header(None)):
    check(x_code)
    writable()
    return inv().foto(barcode, await file.read(), file.content_type or "")


STATIC = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
