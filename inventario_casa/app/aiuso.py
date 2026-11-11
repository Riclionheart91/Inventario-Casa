"""Conteggio delle chiamate all'AI e memoria delle risposte.
- Uso: per giorno e per compito, quante richieste, quante sono andate male, quanto ci hanno messo, quante risposte sono arrivate dalla memoria;
  e come hai trattato le proposte (approvate, corrette, rifiutate). Serve a capire se l'AI funziona davvero.
- Memoria: la stessa richiesta (stesso prodotto, stesse regole) non richiama Gemini per 30 giorni.
Tutto resta in /data (file piccoli); niente chiavi, niente testi dei prodotti nel conteggio. Si attiva solo nell'app (ATTIVO), non nei test."""
import functools
import hashlib
import inspect
import json
import os
import tempfile
import threading
import time
from datetime import datetime
from typing import Callable, Optional

ATTIVO = False
GIORNI_STORICO = 60
VALIDITA_MEMORIA = 30 * 86400
VALIDITA_VUOTA = 7 * 86400      # «nessun risultato» da Gemini: per una settimana non si richiede la stessa cosa
MAX_MEMORIA = 1500
_lock = threading.RLock()


def _cartella() -> str:
    return os.environ.get("DATA_DIR") or ("/data" if os.path.isdir("/data") else tempfile.gettempdir())


def _leggi(nome: str) -> dict:
    try:
        with open(os.path.join(_cartella(), nome), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _scrivi(nome: str, dati: dict) -> None:
    try:
        p = os.path.join(_cartella(), nome)
        with open(p + ".tmp", "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False)
        os.replace(p + ".tmp", p)
    except Exception:
        pass   # il conteggio e un di piu: non deve mai bloccare l'app


def _oggi() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def registra_chiamata(compito: str, ok: bool, ms: float, da_memoria: bool = False, errore: str = "", vuota: bool = False) -> None:
    if not ATTIVO:
        return
    with _lock:
        d = _leggi("ai_uso.json")
        g = d.setdefault("giorni", {}).setdefault(_oggi(), {}).setdefault(compito, {"richieste": 0, "errori": 0, "ms": 0, "memoria": 0, "vuote": 0})
        g["richieste"] += 1
        if da_memoria:
            g["memoria"] += 1
        else:
            g["ms"] += int(ms)
            if not ok and vuota:
                g["vuote"] = g.get("vuote", 0) + 1      # Gemini ha risposto ma non ha trovato niente: non e un guasto
            elif not ok:
                g["errori"] += 1
                if errore:
                    d.setdefault("ultimo_errore", {})[compito] = {"quando": datetime.now().strftime("%d/%m %H:%M"), "testo": errore[:160]}
        for k in sorted(d["giorni"])[:-GIORNI_STORICO]:
            del d["giorni"][k]
        _scrivi("ai_uso.json", d)


def esito(genere: str, azione: str, corretta: bool = False) -> None:
    """Come e stata trattata una proposta: genere P/T/C/R; azione APPROVA/RIFIUTA; corretta = approvata ma cambiata a mano."""
    if not ATTIVO:
        return
    with _lock:
        d = _leggi("ai_uso.json")
        e = d.setdefault("esiti", {}).setdefault(genere, {"approvate": 0, "corrette": 0, "rifiutate": 0})
        e["rifiutate" if azione == "RIFIUTA" else ("corrette" if corretta else "approvate")] += 1
        _scrivi("ai_uso.json", d)


def riepilogo(giorni: int = 7) -> dict:
    d = _leggi("ai_uso.json")
    gs = sorted(d.get("giorni", {}))[-giorni:]
    tot = {}
    for g in gs:
        for c, v in d["giorni"][g].items():
            t = tot.setdefault(c, {"richieste": 0, "errori": 0, "ms": 0, "memoria": 0, "vuote": 0})
            for k in t:
                t[k] += v.get(k, 0)
    compiti = []
    for c, t in sorted(tot.items(), key=lambda x: -x[1]["richieste"]):
        veri = t["richieste"] - t["memoria"]
        compiti.append({"compito": c, "richieste": t["richieste"], "dalla_memoria": t["memoria"], "errori": t["errori"], "vuote": t["vuote"], "ms_medi": int(t["ms"] / veri) if veri else 0})
    oggi = d.get("giorni", {}).get(_oggi(), {})
    try:
        from .impostazioni import imp
        _v = imp().tutte()
    except Exception:
        _v = {}
    return {"sospesa": bool(_v.get("ai_sospesa")), "limite": int(_v.get("ai_limite") or 0), "giorni": giorni, "compiti": compiti, "oggi": sum(v["richieste"] - v["memoria"] for v in oggi.values()),
            "esiti": d.get("esiti", {}), "memoria": len(_leggi("ai_memoria.json")), "ultimo_errore": d.get("ultimo_errore", {})}


def _chiave(compito: str, args: dict, extra: str) -> str:
    return hashlib.sha1((compito + "|" + extra + "|" + json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)).encode("utf-8")).hexdigest()


def _valido(r) -> bool:
    if r is None or r == {}:
        return False
    if isinstance(r, list):   # una lista vuota e una risposta valida (es. «nessun prodotto da spostare»)
        return all(x is not None for x in r)
    return True


def chiamate_oggi() -> int:
    """Chiamate vere a Gemini fatte oggi (quelle dalla memoria non contano)."""
    oggi = _leggi("ai_uso.json").get("giorni", {}).get(_oggi(), {})
    return sum(max(0, v.get("richieste", 0) - v.get("memoria", 0)) for v in oggi.values())


def freno() -> str:
    """Motivo per cui in questo momento l'AI non va chiamata (sospesa dalle Impostazioni o limite giornaliero raggiunto), oppure ''."""
    if not ATTIVO:
        return ""
    try:
        from .impostazioni import imp
        v = imp().tutte()
    except Exception:
        return ""
    if v.get("ai_sospesa"):
        return "AI sospesa dalle impostazioni"
    lim = int(v.get("ai_limite") or 0)
    if lim > 0 and chiamate_oggi() >= lim:
        return "limite giornaliero raggiunto (%d chiamate)" % lim
    return ""


def extra_errore() -> str:
    """Motivo dell'ultimo fallimento di Gemini (senza chiave), se il modulo ai lo sa."""
    try:
        from . import ai
        return str(ai.ULTIMO_ERRORE[0] or "")
    except Exception:
        return ""


def registra(compito: str, memoria: bool = False, extra: Optional[Callable[[], str]] = None):
    """Decoratore delle funzioni che chiamano Gemini: conta, e (se memoria) riusa le risposte recenti."""
    def deco(f):
        sig = inspect.signature(f)

        @functools.wraps(f)
        def w(*a, **k):
            if not ATTIVO or "post" in k:
                return f(*a, **k)
            chiave = None
            if memoria:
                b = sig.bind(*a, **k); b.apply_defaults()
                args = {n: v for n, v in b.arguments.items() if n not in ("chiave", "modello", "riserva", "post")}
                chiave = _chiave(compito, args, extra() if extra else "")
                with _lock:
                    hit = _leggi("ai_memoria.json").get(chiave)
                if hit and time.time() - hit["t"] < (VALIDITA_VUOTA if hit.get("vuota") else VALIDITA_MEMORIA):
                    registra_chiamata(compito, True, 0, True)
                    return hit["v"]
            motivo = freno()
            if motivo:   # niente chiamata e niente errore nelle statistiche; la memoria resta intatta
                try:
                    from . import ai
                    ai.ULTIMO_ERRORE[0] = motivo
                except Exception:
                    pass
                return None
            t0 = time.time()
            r = f(*a, **k)
            ok = _valido(r)
            err = extra_errore() if not ok else ""
            vuota = (not ok) and not err
            registra_chiamata(compito, ok, (time.time() - t0) * 1000, errore=err, vuota=vuota)
            if memoria and (ok or vuota):
                with _lock:
                    m = _leggi("ai_memoria.json")
                    m[chiave] = {"t": time.time(), "v": r}
                    if vuota:
                        m[chiave]["vuota"] = 1
                    if len(m) > MAX_MEMORIA:
                        for kk in sorted(m, key=lambda x: m[x]["t"])[:len(m) - MAX_MEMORIA]:
                            del m[kk]
                    _scrivi("ai_memoria.json", m)
            return r
        return w
    return deco


def svuota_memoria() -> int:
    with _lock:
        n = len(_leggi("ai_memoria.json"))
        _scrivi("ai_memoria.json", {})
        return n
