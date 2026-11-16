"""Prodotti fatti in casa (codici PERS): chat con l'AI per ricavare informazioni indicative e salvarle nella scheda a mano."""
from typing import List, Optional

from . import ai
from .codici import e_mio


def registra(app, ctx) -> None:
    from fastapi import Header, HTTPException
    from pydantic import BaseModel

    class Messaggio(BaseModel):
        ruolo: str
        testo: str

    class Chat(BaseModel):
        barcode: str
        messaggi: List[Messaggio]

    class Info(BaseModel):
        composizione: Optional[str] = None
        nutrizione: Optional[str] = None
        dettagli: Optional[str] = None

    def solo_mio(barcode):
        if not e_mio(barcode):
            raise HTTPException(403, "Disponibile solo per i tuoi codici personali (PERS…).")

    @app.get("/api/ai/casa/{barcode}")
    def prompt_iniziale(barcode: str, x_code: str = Header(None)):
        """Il primo messaggio della chat, gia scritto con i dati della scheda: l'utente lo rilegge e preme Invia."""
        ctx.check(x_code)
        solo_mio(barcode)
        sch = ctx.inv().scheda(barcode)
        if not sch:
            raise HTTPException(404, "Prodotto non trovato: salva prima la scheda.")
        return {"prompt": ai.prompt_casa(sch), "ai": bool(ctx.env("GEMINI_API_KEY"))}

    @app.post("/api/ai/casa")
    def chat(m: Chat, x_code: str = Header(None)):
        """Un turno di chat. Non scrive nulla: se la risposta ha il blocco JSON, lo restituisce in `scheda` e il salvataggio lo decide l'utente."""
        ctx.check(x_code)
        solo_mio(m.barcode)
        if not ctx.env("GEMINI_API_KEY"):
            raise HTTPException(503, "Manca la chiave Gemini nelle opzioni dell'app.")
        msgs = [{"ruolo": x.ruolo, "testo": x.testo[:6000]} for x in m.messaggi][-20:]
        if not msgs or msgs[-1]["ruolo"] != "utente":
            raise HTTPException(400, "Manca il messaggio da inviare.")
        t = ai.chat_casa(msgs, ctx.env("GEMINI_API_KEY"), ctx.env("GEMINI_MODELLO"), ctx.env("GEMINI_MODELLO_RISERVA"))
        if not t:
            raise HTTPException(502, "L'AI non ha risposto%s." % (" (%s)" % ai.ULTIMO_ERRORE[0] if ai.ULTIMO_ERRORE[0] else ""))
        return {"testo": t, "scheda": ai.scheda_da_risposta(t)}

    @app.patch("/api/prodotto/{barcode}/info")
    def salva_info(barcode: str, m: Info, x_code: str = Header(None)):
        """Ingredienti, valori per 100 g e note di un mio prodotto (a mano o dalle stime dell'AI)."""
        ctx.check(x_code)
        ctx.writable()
        solo_mio(barcode)
        return ctx.inv().imposta_info(barcode, m.composizione, m.nutrizione, m.dettagli)
