"""Foto della data di scadenza sulla confezione: l'AI la legge e propone la data. Non scrive nulla: la data va nel campo e la conferma l'utente salvando."""
from . import ai

MAX_BYTE = 8 * 1024 * 1024
MIME_OK = ("image/jpeg", "image/png", "image/webp", "image/heic", "image/heif")


def registra(app, ctx) -> None:
    from fastapi import File, Header, HTTPException, UploadFile

    @app.post("/api/scadenza/foto")
    async def scadenza_foto(file: UploadFile = File(...), x_code: str = Header(None)):
        ctx.check(x_code)
        if not ctx.env("GEMINI_API_KEY"):
            raise HTTPException(503, "Manca la chiave Gemini nelle opzioni dell'app: scrivi la data a mano.")
        mime = (file.content_type or "").lower()
        if mime not in MIME_OK:
            raise HTTPException(400, "Serve una foto (JPEG, PNG o WebP).")
        dati = await file.read(MAX_BYTE + 1)
        if not dati or len(dati) > MAX_BYTE:
            raise HTTPException(400, "Foto vuota o troppo grande (massimo 8 MB).")
        r = ai.leggi_scadenza(dati, mime, ctx.env("GEMINI_API_KEY"), ctx.env("GEMINI_MODELLO"), ctx.env("GEMINI_MODELLO_RISERVA"))
        if r is None:
            raise HTTPException(502, "L'AI non ha risposto%s." % (" (%s)" % ai.ULTIMO_ERRORE[0] if ai.ULTIMO_ERRORE[0] else ""))
        return r
