"""Regole della casa desunte dai dati: dove tieni davvero i prodotti di un tipo (dal catalogo) e dove correggi di solito l'AI (dal registro log_ai).
Propone soltanto: ogni regola entra nel foglio dopo la tua approvazione. Quelle gia approvate o scartate non tornano."""
import json
import os
import tempfile
from collections import Counter, defaultdict
from typing import Dict, List, Optional

from . import ai

MIN_PRODOTTI = 3       # quanti prodotti di un tipo servono per parlare di abitudine
MIN_COERENZA = 0.8     # quota di quei prodotti che sta nello stesso posto
MIN_CORREZIONI = 2     # volte che hai corretto allo stesso modo
MAX_PROPOSTE = 12


def _file() -> str:
    return os.path.join(os.environ.get("DATA_DIR") or ("/data" if os.path.isdir("/data") else tempfile.gettempdir()), "regole_gestite.json")


def gestite() -> set:
    try:
        with open(_file(), encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def segna(chiave: str) -> None:
    if not chiave:
        return
    g = gestite(); g.add(str(chiave)[:120])
    try:
        with open(_file(), "w", encoding="utf-8") as f:
            json.dump(sorted(g), f, ensure_ascii=False)
    except Exception:
        pass


def _s(x) -> str:
    return str(x or "").strip()


def _desc(p: dict) -> str:
    return " · ".join(x for x in (_s(p.get("Prodotto")) or "(senza nome)", _s(p.get("Marca"))) if x)


def candidate(prodotti: List[dict], log: List[dict], esistenti: List[str], escluse: Optional[set] = None) -> List[dict]:
    """[{chiave, bozza, obbligatori, prodotti, n, tot}] ordinate per forza dell'evidenza."""
    escluse = escluse if escluse is not None else gestite()
    ex = " ".join(ai._n(r) for r in esistenti)
    out: List[dict] = []
    # 1) abitudini: dove stanno i prodotti di uno stesso tipo
    per_tipo: Dict[str, List[dict]] = defaultdict(list)
    for p in prodotti:
        if _s(p.get("Tipo")) and _s(p.get("Categoria")):
            per_tipo[_s(p.get("Tipo"))].append(p)
    for tipo, ps in per_tipo.items():
        chiave = "tipo|" + ai._n(tipo)
        if len(ps) < MIN_PRODOTTI or chiave in escluse or ai._n(tipo) in ex:
            continue
        cat, nc = Counter(_s(p["Categoria"]) for p in ps).most_common(1)[0]
        if nc / len(ps) < MIN_COERENZA:
            continue
        dentro = [p for p in ps if _s(p["Categoria"]) == cat]
        sub, ns = Counter(_s(p.get("Sottocategoria")) for p in dentro if _s(p.get("Sottocategoria"))).most_common(1)[0] if any(_s(p.get("Sottocategoria")) for p in dentro) else ("", 0)
        if sub and ns / len(ps) >= MIN_COERENZA:
            bozza, obbl, k = "I prodotti di tipo «%s» vanno in %s › %s." % (tipo, cat, sub), [tipo, cat, sub], ns
        else:
            bozza, obbl, k = "I prodotti di tipo «%s» vanno in %s." % (tipo, cat), [tipo, cat], nc
        out.append({"chiave": chiave, "bozza": bozza, "obbligatori": obbl, "prodotti": [_desc(p) for p in ps[:5]], "n": k, "tot": len(ps), "peso": len(ps) * (k / len(ps))})
    # 2) correzioni ripetute: da una categoria a un'altra, approvate da te
    nomi = {ai.nbc_(p.get("Barcode")): p for p in prodotti}
    gr: Dict[tuple, List[dict]] = defaultdict(list)
    for x in log:
        if _s(x.get("Campo")) != "Categoria" or _s(x.get("Fonte")).upper() != "APPROVATO":
            continue
        a, b = _s(x.get("Prima")), _s(x.get("Dopo"))
        if a and b and ai._n(a) != ai._n(b):
            gr[(ai._n(a), ai._n(b))].append(x)
    for (_, _), xs in gr.items():
        a, b = _s(xs[0].get("Prima")), _s(xs[0].get("Dopo"))
        chiave = "corr|%s>%s" % (ai._n(a), ai._n(b))
        if len(xs) < MIN_CORREZIONI or chiave in escluse or (ai._n(a) in ex and ai._n(b) in ex):
            continue
        ps = [nomi[ai.nbc_(x.get("Barcode"))] for x in xs if ai.nbc_(x.get("Barcode")) in nomi]
        esempi = [_s(p.get("Prodotto")) for p in ps if _s(p.get("Prodotto"))][:4]
        bozza = "Prodotti come %s vanno in %s, non in %s." % (", ".join(esempi), b, a) if esempi else "I prodotti che l'AI mette in %s spesso vanno in %s." % (a, b)
        out.append({"chiave": chiave, "bozza": bozza, "obbligatori": [b, a], "prodotti": [_desc(p) for p in ps[:5]], "n": len(xs), "tot": len(xs), "peso": len(xs) * 8})
    out.sort(key=lambda c: -c["peso"])
    for c in out:
        c.pop("peso", None)
    return out[:MAX_PROPOSTE]


def chiara(frase, c: dict) -> str:
    """La frase riscritta vale solo se resta breve e cita ancora tipo e categorie della bozza: altrimenti si tiene la bozza."""
    f = " ".join(str(frase or "").split())
    if 10 <= len(f) <= 200 and all(ai._n(o) in ai._n(f) for o in c["obbligatori"]):
        return f
    return c["bozza"]
