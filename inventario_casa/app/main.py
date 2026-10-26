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


class Dec(BaseModel):
    azione: str


@app.get("/api/config")
def config():
    return {"url_sicuro": os.environ.get("SECURE_URL", "").strip(), "sola_lettura": READ_ONLY}


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
