"""Avviso giornaliero dei prodotti in scadenza: una notifica al giorno tramite Home Assistant (servizio notify scelto nelle opzioni)."""
import json
import os
import urllib.request
from datetime import datetime
from typing import Callable, List, Optional


def invia_ha(servizio: str, titolo: str, messaggio: str, url: str = "") -> None:
    """Chiama il servizio notify di Home Assistant tramite il Supervisor (serve homeassistant_api nell'add-on)."""
    tok = os.environ.get("SUPERVISOR_TOKEN", "")
    if not tok or not servizio:
        raise RuntimeError("Notifiche non disponibili: manca il servizio notify nelle opzioni o il token di Home Assistant.")
    servizio = servizio.replace("notify.", "", 1).strip()
    dati = {"title": titolo, "message": messaggio}
    if url:
        dati["data"] = {"url": url, "clickAction": url}
    req = urllib.request.Request("http://supervisor/core/api/services/notify/" + servizio, data=json.dumps(dati).encode("utf-8"),
                                 headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        r.read()


def testo(voci: List[dict]) -> (str, str):
    """Titolo e messaggio brevi: prima gli scaduti, poi quelli in scadenza."""
    sc = [v for v in voci if v["giorni"] < 0]
    ins = [v for v in voci if v["giorni"] >= 0]

    def quando(v):
        g = v["giorni"]
        return "scaduto" if g < 0 else "oggi" if g == 0 else "domani" if g == 1 else "tra %d giorni" % g
    parti = []
    if sc:
        parti.append("%d scadut%s" % (len(sc), "o" if len(sc) == 1 else "i"))
    if ins:
        parti.append("%d in scadenza" % len(ins))
    titolo = "Inventario: " + " e ".join(parti)
    righe = ["%s (%s%s)" % (v["nome"], quando(v), ", %d pz" % v["qta"] if v["qta"] != 1 else "") for v in voci[:6]]
    if len(voci) > 6:
        righe.append("… e altri %d" % (len(voci) - 6))
    return titolo, "; ".join(righe)


class Avvisi:
    def __init__(self, inv, invia: Callable = invia_ha, percorso: str = "/data/avvisi.json", oggi: Callable = datetime.now):
        self.inv, self.invia, self.percorso, self.oggi = inv, invia, percorso, oggi

    def _leggi(self) -> dict:
        try:
            with open(self.percorso, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    def _salva(self, d: dict) -> None:
        try:
            with open(self.percorso, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False)
        except Exception:
            pass

    def stato(self) -> dict:
        return self._leggi()

    def esegui(self, servizio: str, giorni: int = 7, ora: str = "08:00", url: str = "", forza: bool = False) -> dict:
        """Una notifica al giorno, dopo l'ora scelta, solo se c'e qualcosa da dire. `forza` = prova (ignora ora e giorno)."""
        adesso = self.oggi()
        oggi = adesso.strftime("%Y-%m-%d")
        d = self._leggi()
        if not forza and (adesso.strftime("%H:%M") < ora or d.get("ultimo") == oggi):
            return {"inviata": False, "motivo": "non e il momento"}
        voci = self.inv.scadenze(giorni, adesso.date())
        if not voci:
            if forza:
                self.invia(servizio, "Inventario: scadenze", "Nessun prodotto in scadenza nei prossimi %d giorni." % giorni, url)
                return {"inviata": True, "voci": 0}
            d["ultimo"] = oggi
            self._salva(d)
            return {"inviata": False, "motivo": "niente in scadenza"}
        titolo, msg = testo(voci)
        self.invia(servizio, titolo, msg, url)
        if not forza:
            d.update({"ultimo": oggi, "voci": len(voci)})
            self._salva(d)
        return {"inviata": True, "voci": len(voci)}
