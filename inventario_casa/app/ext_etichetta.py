"""Endpoint dell'etichetta per la stampante termica: QR del codice a barre + nome + posizione (vedi etichetta.py)."""
import base64
import re

from .etichetta import etichetta_png

TESTA = 96        # punti della testina (rotolo 12 mm a 203 DPI)
LUNGHEZZA = 280   # punti stampabili lungo l'etichetta da 40 mm


def posizione(giacenze) -> str:
    """I luoghi dove c'e il prodotto, senza ripetizioni (al massimo due, poi «…»)."""
    luoghi = []
    for g in giacenze or []:
        if (g.get("qta") or 0) > 0 and g.get("luogo") and g["luogo"] not in luoghi:
            luoghi.append(g["luogo"])
    return ", ".join(luoghi[:2]) + ("…" if len(luoghi) > 2 else "")


def registra(app, ctx) -> None:
    from fastapi import Header, HTTPException

    @app.get("/api/etichetta/{barcode}")
    def etichetta(barcode: str, x_code: str = Header(None)):
        """L'etichetta del prodotto come PNG (in base64): da salvare/condividere o da mandare alla stampante."""
        ctx.check(x_code)
        sch = ctx.inv().scheda(barcode)
        if not sch:
            raise HTTPException(404, "Prodotto non trovato")
        cifre = re.sub(r"\D", "", str(sch["barcode"]))
        if not 1 <= len(cifre) <= 41:
            raise HTTPException(400, "Codice non adatto a un QR")
        pos = posizione(sch.get("giacenze"))
        try:
            png = etichetta_png(cifre, sch.get("nome") or cifre, pos, TESTA, LUNGHEZZA)
        except ImportError:
            raise HTTPException(503, "Manca la libreria di disegno (Pillow) nell'add-on: aggiornalo all'ultima versione.")
        return {"png": base64.b64encode(png).decode("ascii"), "barcode": cifre, "nome": sch.get("nome") or "",
                "posizione": pos, "testa": TESTA, "lunghezza": LUNGHEZZA}
