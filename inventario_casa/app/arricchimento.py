"""Arricchimento notturno dei prodotti e traduzione in italiano: porting di startNightlyFullEnrich / aiTraduciProvaRun.
Regole (le stesse del motore Apps Script e quelle decise con l'utente):
- si riempiono SOLO i campi vuoti: mai sovrascrivere quello che c'e gia;
- se la ricerca non trova nulla il prodotto non cambia (ne dati, ne stato, ne data): se ne ricorda solo l'app, in un file suo;
- i testi lunghi (dettagli, composizione, free-from, smaltimento) vengono resi in italiano solo se non lo sono gia.
Nessuna scrittura se l'app e in sola lettura."""
import hashlib
import json
import os
import tempfile
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from .service import SH_PROD, nbc

CAMPI = (("Prodotto", "nome"), ("Marca", "marca"), ("Confezione", "confezione"), ("Immagine", "immagine"),
         ("Dettagli prodotto", "dettagli"), ("Composizione", "composizione"), ("Nutrizione (100g)", "nutrizione"), ("Punteggi", "punteggi"))
CAMPI_TRAD = ("Dettagli prodotto", "Composizione", "Free-from", "Smaltimento/riciclo")
RIPROVA_GIORNI = 30      # un codice non trovato si riprova dopo un mese
LOTTO_TRAD = 10


def _h(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:16]


class Arricchitore:
    def __init__(self, inv, cerca: Callable, traduci: Callable, percorso: str = "", oggi: Callable = datetime.now, web: Optional[Callable] = None):
        self.inv, self.cerca, self.traduci, self.oggi, self.web = inv, cerca, traduci, oggi, web
        self.percorso = percorso or os.path.join(os.environ.get("DATA_DIR") or ("/data" if os.path.isdir("/data") else tempfile.gettempdir()),
                                                 "arricchimento.json")
        self._lock = threading.Lock()

    # stato su file (resta tra un riavvio e l'altro)
    def _leggi(self) -> dict:
        try:
            with open(self.percorso, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    def _salva(self, d: dict):
        try:
            tmp = self.percorso + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False)
            os.replace(tmp, self.percorso)
        except Exception:
            pass

    def stato(self) -> dict:
        d = self._leggi()
        return {"ultimo": d.get("ultimo", ""), "rapporto": d.get("rapporto", {})}

    def da_fare_oggi(self) -> bool:
        return self._leggi().get("ultimo", "") != self.oggi().strftime("%Y-%m-%d")

    def esegui(self, massimo: int = 60, budget_s: float = 1500.0, traduci_testi: bool = True) -> dict:
        """Un giro: cerca i dati dei prodotti incompleti e traduce i testi non italiani. Ritorna il rapporto."""
        if not self._lock.acquire(blocking=False):
            return {"errore": "gia in corso"}
        try:
            t0 = time.time()
            st = self._leggi()
            rap = {"cercati": 0, "completati": 0, "non_trovati": 0, "campi_scritti": 0, "tradotti": 0, "traduzioni_fallite": 0}
            prove: Dict[str, str] = st.get("prove", {})
            adesso = self.oggi()
            limite = (adesso - timedelta(days=RIPROVA_GIORNI)).strftime("%Y-%m-%d")
            h, rows = self.inv._rows(SH_PROD, True)
            if "Barcode" not in h:
                return {"errore": "foglio prodotti senza colonna Barcode"}
            ix = {n: i for i, n in enumerate(h)}
            cella = lambda r, n: str(r[ix[n]]).strip() if n in ix and len(r) > ix[n] and r[ix[n]] is not None else ""
            ups = []
            candidati = []
            for i, r in enumerate(rows):
                bc = nbc(r[ix["Barcode"]]) if len(r) > ix["Barcode"] else ""
                if not bc or prove.get(bc, "") > limite:
                    continue
                vuoti = [n for n in ("Marca", "Confezione", "Immagine") if n in ix and not cella(r, n)]
                incompleto = bool(vuoti) or not cella(r, "API Status").startswith("✅")
                if incompleto:
                    candidati.append((0 if not cella(r, "API Status") else 1, i, bc))
            candidati.sort()
            for _, i, bc in candidati[:massimo]:
                if time.time() - t0 > budget_s:
                    break
                r = rows[i]
                rap["cercati"] += 1
                try:
                    info = self.cerca(bc)
                except Exception:
                    info = None
                if not info and self.web:   # nessun archivio lo conosce: ricerca su Google con l'AI (solo se la pagina riporta il codice)
                    try:
                        info = self.web(bc)
                    except Exception:
                        info = None
                    if info:
                        rap["da_web"] = rap.get("da_web", 0) + 1
                prove[bc] = adesso.strftime("%Y-%m-%d")
                if not info:
                    rap["non_trovati"] += 1     # nessuna scrittura: il prodotto resta com'e
                    continue
                nuovi = [(n, str(info.get(k) or "").strip()) for n, k in CAMPI if n in ix and not cella(r, n) and str(info.get(k) or "").strip()]
                if not nuovi:
                    continue
                for n, v in nuovi:
                    ups.append((i + 2, n, v))
                if "API Status" in ix and not cella(r, "API Status").startswith("✅"):
                    stato = "🔶 Web (AI)" if info.get("fonte") == "Web" else "✅ App (%s)" % (info.get("fonte") or "ricerca")
                    ups.append((i + 2, "API Status", stato))
                if "Aggiornato il" in ix:
                    ups.append((i + 2, "Aggiornato il", adesso.strftime("%d/%m/%Y")))
                rap["completati"] += 1
                rap["campi_scritti"] += len(nuovi)
            if ups:
                self.inv.store.update_cells(SH_PROD, ups)
                self.inv._drop(SH_PROD)
            if traduci_testi:
                self._traduci(st, rap, t0, budget_s)
            st["prove"] = prove
            st["ultimo"] = adesso.strftime("%Y-%m-%d")
            rap["quando"] = adesso.strftime("%d/%m/%Y %H:%M")
            st["rapporto"] = rap
            self._salva(st)
            return rap
        finally:
            self._lock.release()

    def _traduci(self, st: dict, rap: dict, t0: float, budget_s: float):
        visti = set(st.get("tradotti", []))
        h, rows = self.inv._rows(SH_PROD, True)
        ix = {n: i for i, n in enumerate(h)}
        lavori = []   # (riga sheet, colonna, testo)
        for i, r in enumerate(rows):
            for n in CAMPI_TRAD:
                if n in ix and len(r) > ix[n] and str(r[ix[n]] or "").strip():
                    t = str(r[ix[n]])
                    if _h(t) not in visti:
                        lavori.append((i + 2, n, t))
        ups = []
        for k in range(0, len(lavori), LOTTO_TRAD):
            if time.time() - t0 > budget_s:
                break
            lotto = lavori[k:k + LOTTO_TRAD]
            try:
                res = self.traduci([t for _, _, t in lotto])
            except Exception:
                res = [None] * len(lotto)
            for (riga, n, t), it in zip(lotto, res):
                if it is None:
                    rap["traduzioni_fallite"] += 1
                    continue
                visti.add(_h(t))
                if it.strip() != t.strip():
                    ups.append((riga, n, it))
                    visti.add(_h(it))
                    rap["tradotti"] += 1
        if ups:
            self.inv.store.update_cells(SH_PROD, ups)
            self.inv._drop(SH_PROD)
        st["tradotti"] = sorted(visti)[-20000:]
