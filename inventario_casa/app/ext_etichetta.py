"""Endpoint dell'etichetta per la stampante termica: QR del codice a barre + nome + posizione (vedi etichetta.py)."""
import base64
import re

from .codici import MieiCodici, e_mio
from .etichetta import ICONE, etichetta_png
from .service import nbc

TESTA = 96        # punti della testina (rotolo 12 mm a 203 DPI)
LUNGHEZZA = 280   # punti stampabili lungo l'etichetta da 40 mm


def posizione(giacenze) -> str:
    """I luoghi dove c'e il prodotto, senza ripetizioni (al massimo due, poi «…»)."""
    luoghi = []
    for g in giacenze or []:
        if (g.get("qta") or 0) > 0 and g.get("luogo") and g["luogo"] not in luoghi:
            luoghi.append(g["luogo"])
    return ", ".join(luoghi[:2]) + ("…" if len(luoghi) > 2 else "")


def manda_a_stampante(png: bytes, url: str, token: str, timeout: float = 70.0) -> None:
    """Spedisce l'etichetta al servizio «Stampa Etichette» (rete locale). Solleva RuntimeError con un messaggio leggibile."""
    import json
    import urllib.error
    import urllib.request
    req = urllib.request.Request(url.rstrip("/") + "/stampa", data=png, method="POST",
                                 headers={"X-Token": token, "Content-Type": "image/png"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read()
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read()).get("errore", "")
        except Exception:
            msg = ""
        raise RuntimeError(msg or "Il servizio di stampa ha risposto con l'errore %s" % e.code)
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError("Il servizio di stampa non è raggiungibile (%s): controlla che «Stampa Etichette» sia avviato e l'indirizzo nelle opzioni." % getattr(e, "reason", e))


def registra(app, ctx) -> None:
    import os
    from fastapi import Header, HTTPException

    mc = MieiCodici()

    def componi(barcode, posiz=1, data="", tipo_data="scad", lotto="", codice=0, icona=""):
        """(png, cifre, nome, posizione) dell'etichetta di un prodotto o di un mio codice."""
        if not e_mio(barcode):
            raise HTTPException(403, "L'etichetta si crea solo per i tuoi codici personali (quelli che iniziano con 2999).")
        sch = ctx.inv().scheda(barcode)
        nome_mio = next((v["nome"] for v in mc.elenco() if nbc(v["codice"]) == nbc(barcode)), None) if e_mio(barcode) else None
        if not sch and nome_mio is None:
            raise HTTPException(404, "Prodotto non trovato")
        sch = sch or {"barcode": barcode, "nome": nome_mio, "giacenze": []}   # un mio codice non ancora usato ha solo il nome dato alla creazione
        cifre = re.sub(r"\D", "", str(sch["barcode"]))
        if not 1 <= len(cifre) <= 41:
            raise HTTPException(400, "Codice non adatto a un QR")
        pos = posizione(sch.get("giacenze")) if posiz else ""
        data_txt = ""
        if data:
            import datetime
            try:
                d = datetime.date.fromisoformat(data)
            except ValueError:
                raise HTTPException(400, "Data non valida")
            data_txt = ("Prod. " if tipo_data == "prod" else "Scad. ") + d.strftime("%d/%m/%y")
        if icona and icona not in ICONE:
            raise HTTPException(400, "Icona sconosciuta")
        try:
            png = etichetta_png(cifre, sch.get("nome") or cifre, pos, TESTA, LUNGHEZZA, data_txt, lotto.strip()[:12], bool(codice), icona)
        except ImportError:
            raise HTTPException(503, "Manca la libreria di disegno (Pillow) nell'add-on: aggiornalo all'ultima versione.")
        return png, cifre, sch.get("nome") or "", pos

    def stampante():
        return os.environ.get("STAMPANTE_URL", "").strip(), os.environ.get("STAMPANTE_TOKEN", "")

    @app.get("/api/etichetta/{barcode}")
    def etichetta(barcode: str, posiz: int = 1, data: str = "", tipo_data: str = "scad", lotto: str = "", codice: int = 0,
                  icona: str = "", x_code: str = Header(None)):
        """L'etichetta del prodotto come PNG (in base64): da salvare/condividere o da mandare alla stampante."""
        ctx.check(x_code)
        png, cifre, nome, pos = componi(barcode, posiz, data, tipo_data, lotto, codice, icona)
        url, tok = stampante()
        return {"png": base64.b64encode(png).decode("ascii"), "barcode": cifre, "nome": nome,
                "posizione": pos, "testa": TESTA, "lunghezza": LUNGHEZZA, "stampante": bool(url and tok)}

    @app.post("/api/stampa/{barcode}")
    def stampa(barcode: str, posiz: int = 1, data: str = "", tipo_data: str = "scad", lotto: str = "", codice: int = 0,
               icona: str = "", x_code: str = Header(None)):
        """Stampa l'etichetta sulla X1 tramite il servizio «Stampa Etichette» di Home Assistant."""
        ctx.check(x_code)
        url, tok = stampante()
        if not (url and tok):
            raise HTTPException(503, "Stampante non configurata: imposta stampante_url e stampante_token nelle opzioni dell'add-on.")
        png, _cifre, _nome, _pos = componi(barcode, posiz, data, tipo_data, lotto, codice, icona)
        try:
            manda_a_stampante(png, url, tok)
        except RuntimeError as e:
            raise HTTPException(502, str(e))
        return {"ok": True}
