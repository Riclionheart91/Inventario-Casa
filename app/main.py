"""Livello HTTP sottile (FastAPI). Non testato qui: PyPI non raggiungibile nell'ambiente di sviluppo."""
import hmac
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .service import ApiError, Inventory
from .store import make_store

app = FastAPI(title="Inventario Casa", docs_url=None, redoc_url=None)
_inv = None
SHARED = os.environ.get("SHARED_CODE", "")


def inv() -> Inventory:
    global _inv
    if _inv is None:
        _inv = Inventory(make_store())
    return _inv


def check(code):
    """Codice opzionale (seconda barriera). Il login resta quello di Home Assistant (ingress)."""
    if SHARED and not hmac.compare_digest(code or "", SHARED):
        raise HTTPException(401, "Codice mancante o errato")


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


class Dec(BaseModel):
    azione: str


@app.get("/api/stock")
def stock(x_code: str = Header(None)):
    check(x_code)
    return inv().stock()


@app.get("/api/prodotto/{barcode}")
def prodotto(barcode: str, x_code: str = Header(None)):
    check(x_code)
    p = inv().prodotto(barcode)
    if p is None:
        raise HTTPException(404, "Codice sconosciuto")
    return p


@app.post("/api/movimento")
def movimento(m: Mov, x_code: str = Header(None)):
    check(x_code)
    return inv().movimento(m.barcode, m.tipo, m.location, m.quantita, m.prodotto, m.foto)


@app.get("/api/approvazioni")
def approvazioni(x_code: str = Header(None)):
    check(x_code)
    return inv().approvazioni()


@app.post("/api/approvazioni/{id_}")
def decidi(id_: str, d: Dec, x_code: str = Header(None)):
    check(x_code)
    return inv().decidi(id_, d.azione)


@app.post("/api/foto")
async def foto(barcode: str = Form(...), file: UploadFile = File(...), x_code: str = Header(None)):
    check(x_code)
    return inv().foto(barcode, await file.read(), file.content_type or "")


WEB = Path(__file__).resolve().parent.parent / "web"


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")
