"""Come si compila la scheda di un codice nuovo: prima la ricerca sul web per codice a barre, la foto solo se serve."""
from typing import Callable, Optional


CAMPI_CLASSE = ("categoria", "sottocategoria", "tipo", "tipo_nuovo", "proposta")


def analizza(web: Callable[[], Optional[dict]], suggerisci: Callable[[str, str, str], Optional[dict]],
             da_foto: Callable[[], Optional[dict]], immagine: str = "") -> Optional[dict]:
    """web() -> {nome, marca, confezione, immagine?} cercati per codice; suggerisci(nome, marca, conf) -> categoria/tipo; da_foto() -> lettura della foto.
    Se il web da il nome si usano quei dati (la foto serve solo a completare la categoria, se manca); altrimenti si legge la foto."""
    try:
        w = web()
    except Exception:
        w = None
    a: Optional[dict] = None
    if w and str(w.get("nome") or "").strip():
        s = suggerisci(w["nome"], w.get("marca", ""), w.get("confezione", "")) or {}
        a = dict(s, nome=w["nome"], marca=w.get("marca", ""), confezione=w.get("confezione", ""), fonte="Web (ricerca per codice)")
        if not ((a.get("categoria") and a.get("sottocategoria")) or a.get("proposta")):
            f = da_foto()
            for k in CAMPI_CLASSE:
                if f and f.get(k) and not a.get(k):
                    a[k] = f[k]
    else:
        a = da_foto()
    img = (w or {}).get("immagine") or (a or {}).get("immagine") or immagine
    if img:
        a = dict(a or {}, immagine=img)
    return a or None
