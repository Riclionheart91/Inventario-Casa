"""Endpoint dei miei codici (PERS + 9 cifre; i vecchi EAN-13 2999… restano validi). Vedi codici.py."""
from datetime import datetime

from .codici import MieiCodici, e_mio, e_pers
from .service import ApiError, bco, nbc


def codici_usati(inv) -> set:
    """Ogni codice che compare gia nel foglio (prodotti, movimenti, bozze, proposte, alias), senza zeri iniziali."""
    usati = set()
    for foglio in ("prodotti", "movimenti", "bozze", "ai_prodotti"):
        for r in inv._opz(foglio):
            k = nbc(r.get("Barcode"))
            if k:
                usati.add(k)
    for r in inv._opz("alias"):
        for c in ("Alias", "Principale"):
            k = nbc(r.get(c))
            if k:
                usati.add(k)
    return usati


def registra(app, ctx) -> None:
    from fastapi import Header, HTTPException
    from pydantic import BaseModel

    mc = MieiCodici()

    class Nuovo(BaseModel):
        nome: str = ""

    class Nome(BaseModel):
        codice: str
        nome: str = ""

    class Collega(BaseModel):
        codice: str       # il mio codice
        principale: str   # il codice del prodotto (comprato o gia nel catalogo) che deve valere lo stesso

    @app.get("/api/codici")
    def codici_elenco(x_code: str = Header(None)):
        ctx.check(x_code)
        inv = ctx.inv()
        alias = inv.alias()
        out = []
        for v in mc.elenco():
            k = nbc(v["codice"])
            p = inv.prodotto(v["codice"])
            out.append(dict(v, prodotto=(p or {}).get("prodotto", ""), nel_catalogo=p is not None,
                            alias_di=alias.get(k, ""), usato=p is not None or k in alias))
        return out

    @app.post("/api/codici/nuovo")
    def codici_nuovo(m: Nuovo, x_code: str = Header(None)):
        ctx.check(x_code)
        try:
            v = mc.nuovo(m.nome, codici_usati(ctx.inv()))
        except ValueError as e:
            raise HTTPException(409, str(e))
        return v

    @app.post("/api/codici/nome")
    def codici_nome(m: Nome, x_code: str = Header(None)):
        ctx.check(x_code)
        if not e_mio(m.codice) or not mc.rinomina(m.codice, m.nome):
            raise HTTPException(404, "Codice non trovato")
        return {"ok": True}

    @app.post("/api/codici/elimina")
    def codici_elimina(m: Nome, x_code: str = Header(None)):
        """Toglie il codice dall'elenco (mai riusato). Se c'e un prodotto con questo codice non si puo: prima va tolto o unito."""
        ctx.check(x_code)
        if not e_mio(m.codice):
            raise HTTPException(404, "Codice non trovato")
        if ctx.inv().prodotto(m.codice) is not None:
            raise HTTPException(409, "Questo codice è usato da un prodotto: collegalo a un altro prodotto o eliminalo prima dal catalogo.")
        if not mc.elimina(m.codice):
            raise HTTPException(404, "Codice non trovato")
        return {"ok": True}

    @app.delete("/api/prodotto/{barcode}")
    def prodotto_elimina(barcode: str, x_code: str = Header(None)):
        """Elimina un prodotto dal catalogo con i suoi movimenti. Se era un mio codice, sparisce anche dall'elenco (e non verra mai riusato)."""
        ctx.check(x_code)
        ctx.writable()
        try:
            r = ctx.inv().elimina_prodotto(barcode)
        except ApiError as e:
            raise HTTPException(getattr(e, "status", 400), str(e))
        if e_mio(barcode):
            mc.elimina(nbc(barcode) if e_pers(barcode) else barcode)
            mc.elimina(str(barcode).strip().upper())
        return r

    @app.post("/api/codici/collega")
    def codici_collega(m: Collega, x_code: str = Header(None)):
        """Il mio codice diventa un alias di un prodotto che esiste gia: scansionandolo si apre quel prodotto."""
        ctx.check(x_code)
        ctx.writable()
        inv = ctx.inv()
        mio, prin = nbc(m.codice), nbc(m.principale)
        if not e_mio(mio) or mio not in {nbc(v["codice"]) for v in mc.elenco()}:
            raise HTTPException(404, "Non è uno dei tuoi codici")
        if not prin or prin == mio:
            raise HTTPException(400, "Codice del prodotto non valido")
        prin = inv.risolvi(prin)
        if inv.prodotto(prin) is None:
            raise HTTPException(404, "Quel prodotto non è nel catalogo")
        if inv.prodotto(mio) is not None:                      # il mio codice ha gia un prodotto: si uniscono (movimenti inclusi)
            try:
                return inv.unisci_prodotti(mio, prin)
            except ApiError as e:
                raise HTTPException(e.status if hasattr(e, "status") else 400, str(e))
        inv.store.crea_foglio("alias", ["Alias", "Principale", "Creato", "Nome"])
        inv.store.append_row("alias", {"Alias": bco(mio), "Principale": bco(prin), "Creato": datetime.now().strftime("%d/%m/%Y"),
                                       "Nome": next((v["nome"] for v in mc.elenco() if nbc(v["codice"]) == mio), "")})
        inv._drop("alias")
        return {"ok": True, "principale": bco(prin), "alias": bco(mio)}
