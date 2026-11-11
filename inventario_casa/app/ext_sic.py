"""Registro degli accessi (chi apre l'app, da quale dispositivo). Si salva in /data/accessi.json.
Niente cookie, codici o corpi delle richieste: solo ora, via, indirizzo, dispositivo abbreviato e (da ingress) il nome dell'utente di Home Assistant."""
import hashlib
import json
import os
import re
import tempfile
import threading
import time
from datetime import datetime
from typing import Callable, Optional

from . import accesso

ORA = 3600
SILENZIO_INIZIALE = 24 * 3600     # nelle prime 24 ore dal primo avvio i dispositivi si segnano senza avvisare
MAX_EVENTI = 200
MAX_ERRORI = 100


def dispositivo_breve(ua: str) -> str:
    u = str(ua or "")
    if not u:
        return "Dispositivo sconosciuto"
    if "HomeAssistant" in u or "Home Assistant" in u:
        base = "App Home Assistant"
        dev = "iPhone" if "iPhone" in u or "iOS" in u else "iPad" if "iPad" in u else "Android" if "Android" in u else ""
        return (dev + " · " + base) if dev else base
    dev = ("iPhone" if "iPhone" in u else "iPad" if "iPad" in u else "Android" if "Android" in u else "Mac" if "Macintosh" in u or "Mac OS X" in u
           else "Windows" if "Windows" in u else "Linux" if "Linux" in u else "Altro")
    br = ("Edge" if re.search(r"Edg(e|A|iOS)?/", u) else "Firefox" if re.search(r"Firefox|FxiOS", u) else "Chrome" if re.search(r"Chrome|CriOS", u)
          else "Safari" if "Safari" in u else "Browser")
    return "%s · %s" % (dev, br)


def impronta(ip: str, ua: str) -> str:
    return hashlib.sha256(("%s|%s" % (ip, ua)).encode("utf-8", "replace")).hexdigest()[:16]


class Registro:
    def __init__(self, percorso: Optional[str] = None, giorni: Callable[[], int] = lambda: 90, avvisa: Optional[Callable[[dict], None]] = None,
                 orologio: Callable[[], float] = time.time):
        base = os.environ.get("DATA_DIR") or ("/data" if os.path.isdir("/data") else tempfile.gettempdir())
        self.percorso = percorso or os.path.join(base, "accessi.json")
        self.giorni, self.avvisa, self.ora = giorni, avvisa, orologio
        self._lock = threading.RLock()
        self._mem: Optional[dict] = None     # il registro sta in memoria: il middleware non legge il disco a ogni richiesta

    def _carica(self) -> dict:
        if self._mem is None:
            try:
                with open(self.percorso, encoding="utf-8") as f:
                    d = json.load(f)
                self._mem = d if isinstance(d, dict) else {}
            except Exception:
                self._mem = {}
        return self._mem

    def _salva(self, d: dict) -> None:
        self._mem = d
        try:
            os.makedirs(os.path.dirname(self.percorso), exist_ok=True)
            tmp = self.percorso + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False)
            os.replace(tmp, self.percorso)
        except OSError:
            pass

    def _pota(self, d: dict) -> None:
        limite = self.ora() - max(1, int(self.giorni())) * 86400
        d["dispositivi"] = {k: v for k, v in d.get("dispositivi", {}).items() if v.get("ultimo", 0) >= limite}
        d["eventi"] = [e for e in d.get("eventi", []) if e.get("t", 0) >= limite][-MAX_EVENTI:]
        d["errori"] = [e for e in d.get("errori", []) if e.get("t", 0) >= limite][-MAX_ERRORI:]

    def evento(self, ev: dict) -> None:
        """Punto d'ingresso chiamato dal middleware. Non solleva mai."""
        try:
            self._evento(ev)
        except Exception:
            pass

    def _evento(self, ev: dict) -> None:
        t = self.ora()
        ip, ua, via, tipo = str(ev.get("ip", ""))[:45], str(ev.get("ua", "")), str(ev.get("via", "")), str(ev.get("tipo", "visita"))
        with self._lock:
            d = self._carica()
            d.setdefault("avvio", t)
            if tipo in ("errato", "blocco"):
                d.setdefault("errori", []).append({"t": t, "tipo": tipo, "ip": ip, "via": via})
                self._pota(d); self._salva(d)
                return
            fp = impronta(ip, ua)
            dis = d.setdefault("dispositivi", {})
            x = dis.get(fp)
            nuovo = x is None
            utente = str(ev.get("utente", ""))
            if x is not None and t - x.get("ultimo", 0) < ORA and (not utente or utente == x.get("utente")):
                return        # al massimo una voce per dispositivo e per ora
            if nuovo:
                x = dis[fp] = {"primo": t, "n": 0, "avvisato": False}
            x.update(ultimo=t, via=via, ip=ip, nome=dispositivo_breve(ua), utente=utente or x.get("utente", ""))
            x["n"] = x.get("n", 0) + 1
            d.setdefault("eventi", []).append({"t": t, "fp": fp, "via": via, "ip": ip})
            avvisare = nuovo and (t - d["avvio"]) > SILENZIO_INIZIALE
            if nuovo and not avvisare:
                x["avvisato"] = True
            self._pota(d); self._salva(d)
        if avvisare and self.avvisa:
            x["avvisato"] = True
            threading.Thread(target=self.avvisa, args=(dict(x),), daemon=True).start()

    def elenco(self) -> dict:
        with self._lock:
            d = self._carica()
        self._pota(d)
        dev = sorted(({"id": k, "nome": v.get("nome", ""), "utente": v.get("utente", ""), "via": v.get("via", ""), "ip": v.get("ip", ""), "primo": v.get("primo", 0),
                       "ultimo": v.get("ultimo", 0), "n": v.get("n", 0)} for k, v in d.get("dispositivi", {}).items()), key=lambda x: -x["ultimo"])
        return {"adesso": self.ora(), "dispositivi": dev, "errori": list(reversed(d.get("errori", [])))[:30], "da": d.get("avvio", 0)}

    def svuota(self) -> None:
        with self._lock:
            d = self._carica()
            self._salva({"avvio": d.get("avvio", self.ora())})


def registra(app, ctx) -> None:
    def notifica(x: dict) -> None:
        if not ctx.impostazioni().get("accessi_avviso"):
            return
        servizio = ctx.env("SCADENZA_NOTIFICA")
        if not servizio:
            return
        try:
            from .avvisi import invia_ha
            invia_ha(servizio, "Inventario: dispositivo nuovo", "%s ha aperto l'app (%s%s)." % (x.get("nome", "Un dispositivo"), "da Home Assistant" if x.get("via") == "ingress" else "accesso diretto",
                                                                                              (", utente " + x["utente"]) if x.get("utente") else ""))
        except Exception:
            pass

    reg = Registro(giorni=lambda: ctx.impostazioni().get("accessi_giorni"), avvisa=notifica)
    accesso.HOOK[0] = reg.evento

    # gli endpoint veri hanno bisogno dell'intestazione x-code: si definiscono con Header
    from fastapi import Header

    @app.get("/api/accessi", include_in_schema=False)
    def _acc_elenco(x_code: str = Header(None)):
        ctx.check(x_code)
        return reg.elenco()

    @app.post("/api/accessi/svuota")
    def _acc_svuota(x_code: str = Header(None)):
        ctx.check(x_code)
        reg.svuota()
        return {"ok": True}
