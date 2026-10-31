"""Revisione a tappeto del catalogo: ogni sei mesi (o a richiesta) cerca incongruenze e le mette in «Da fare».
Non scrive sul foglio: salva le voci in un file di stato; il foglio cambia solo quando una voce viene approvata."""
import hashlib
import json
import os
import re
import tempfile
import threading
import unicodedata
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from .service import SH_AIT, SH_MOV, SH_PROD, SH_CAT, nbc, data_it, _num

GIORNI = 182          # circa sei mesi
MAX_AI = 20           # prodotti senza tipo per i quali si chiede un suggerimento all'AI, a ogni revisione
MAX_ELENCO = 15
FERMI_GIORNI = 365


def _chiave(t: str) -> str:
    s = unicodedata.normalize("NFD", str(t or "").lower())
    s = "".join(c for c in s if c.isalnum())
    return s[:-1] if len(s) > 4 and s[-1] in "ieoa" else s


class Revisione:
    def __init__(self, inv, suggerisci: Optional[Callable] = None, arricchisci: Optional[Callable] = None, percorso: str = "",
                 oggi: Callable = datetime.now):
        self.inv, self.suggerisci, self.arricchisci, self.oggi = inv, suggerisci, arricchisci, oggi
        self.percorso = percorso or os.path.join(os.environ.get("DATA_DIR") or ("/data" if os.path.isdir("/data") else tempfile.gettempdir()),
                                                 "revisione.json")
        self._lock = threading.Lock()

    # --- stato su file ---------------------------------------------------
    def _leggi(self) -> dict:
        try:
            with open(self.percorso, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    def _salva(self, d: dict) -> None:
        try:
            tmp = self.percorso + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False)
            os.replace(tmp, self.percorso)
        except Exception:
            pass

    def stato(self) -> dict:
        d = self._leggi()
        aperte = [v for v in d.get("voci", []) if v.get("stato") == "APERTA"]
        return {"ultima": d.get("ultima", ""), "aperte": len(aperte), "in_corso": self._lock.locked(), "dovuta": self.dovuta(),
                "riepilogo": d.get("riepilogo", "")}

    def dovuta(self) -> bool:
        u = self._leggi().get("ultima", "")
        try:
            return self.oggi().date() - datetime.strptime(u, "%Y-%m-%d").date() >= timedelta(days=GIORNI)
        except Exception:
            return True   # mai fatta

    def voci_aperte(self) -> List[dict]:
        out = []
        for v in self._leggi().get("voci", []):
            if v.get("stato") == "APERTA":
                out.append({"id": v["id"], "gruppo": "Revisione", "genere": "R", "titolo": v["titolo"], "prima": v.get("prima", ""),
                            "dopo": v.get("dopo", ""), "motivo": v.get("motivo", ""), "sicurezza": None, "info": not v.get("azione"),
                            "etichetta": v.get("etichetta", ""), "campi": {}})
        return out

    # --- analisi -----------------------------------------------------------
    def _voce(self, tipo: str, chiave: str, titolo: str, dopo: str = "", motivo: str = "", prima: str = "", azione: Optional[dict] = None,
              etichetta: str = "") -> dict:
        i = "R_" + hashlib.sha1((tipo + "|" + chiave).encode("utf-8")).hexdigest()[:10]
        return {"id": i, "titolo": titolo, "prima": prima, "dopo": dopo, "motivo": motivo, "azione": azione, "etichetta": etichetta, "stato": "APERTA"}

    def _elenco(self, xs: List[str]) -> str:
        xs = [x for x in xs if x]
        return ", ".join(xs[:MAX_ELENCO]) + (" … (+%d)" % (len(xs) - MAX_ELENCO) if len(xs) > MAX_ELENCO else "")

    def analizza(self) -> List[dict]:
        inv = self.inv
        prodotti = inv._dicts(SH_PROD, True)
        tipi_righe = inv._dicts(SH_AIT, True)
        movimenti = inv._dicts(SH_MOV, True)
        voci: List[dict] = []
        ha_tipo = "Tipo" in inv._rows(SH_PROD, True)[0]
        # prodotti per tipo
        per_tipo: Dict[str, List[dict]] = {}
        senza_tipo, visti, doppi, non_validi = [], {}, [], []
        for p in prodotti:
            k = nbc(p.get("Barcode"))
            nome = str(p.get("Prodotto", "") or "").strip() or "(senza nome)"
            raw = re.sub(r"\D", "", str(p.get("Barcode", "")))
            if not k or len(k) < 6:
                non_validi.append("%s (%s)" % (nome, str(p.get("Barcode", "")) or "vuoto"))
                continue
            if k in visti:
                doppi.append("%s / %s (%s)" % (visti[k], nome, k))
            visti[k] = nome
            t = str(p.get("Tipo", "") or "").strip()
            if t:
                per_tipo.setdefault(t.casefold(), []).append(p)
            else:
                senza_tipo.append((k, nome, str(p.get("Marca", "") or "")))
        # 1) prodotti senza tipo: l'AI ne suggerisce uno
        if senza_tipo and ha_tipo:
            fatti = 0
            cats, tipi = inv.categorie(), inv.tipi()
            for k, nome, marca in senza_tipo:
                if not self.suggerisci or fatti >= MAX_AI:
                    break
                fatti += 1
                try:
                    s = self.suggerisci(nome, marca, "", cats, tipi)
                except Exception:
                    s = None
                if s and s.get("tipo"):
                    voci.append(self._voce("tipo", k, "Tipo mancante: %s" % nome, dopo="Tipo %s" % s["tipo"], prima="Nessun tipo",
                                           motivo="proposto dall'AI" + (" (tipo nuovo, scorta 0)" if s.get("tipo_nuovo") else ""),
                                           azione={"t": "tipo", "bc": k, "tipo": s["tipo"]}, etichetta="Imposta il tipo"))
            resto = len(senza_tipo) - sum(1 for v in voci if v["id"].startswith("R_") and v["azione"] and v["azione"].get("t") == "tipo")
            if resto > 0:
                voci.append(self._voce("tipo_info", "n", "%d prodotti senza tipo" % resto,
                                       motivo="Aprili dalla scheda e scegli il tipo dal menu, oppure lancia di nuovo la revisione: " +
                                       self._elenco([n for _, n, _ in senza_tipo])))
        # 2) tipi quasi uguali da unire
        attivi = [str(t.get("Tipo", "") or "").strip() for t in tipi_righe
                  if str(t.get("Tipo", "") or "").strip() and str(t.get("Stato", "")).upper() != "RIFIUTATO"]
        gruppi: Dict[str, List[str]] = {}
        for t in attivi:
            gruppi.setdefault(_chiave(t), []).append(t)
        for key, ts in gruppi.items():
            ts = sorted(set(ts), key=lambda x: (-len(per_tipo.get(x.casefold(), [])), x))
            for altro in ts[1:]:
                voci.append(self._voce("unisci", altro + ">" + ts[0], "Tipi simili: %s e %s" % (altro, ts[0]), prima=altro, dopo="Unisci in %s" % ts[0],
                                       motivo="%d prodotti passerebbero a «%s»." % (len(per_tipo.get(altro.casefold(), [])), ts[0]),
                                       azione={"t": "unisci", "da": altro, "a": ts[0]}, etichetta="Unisci"))
        # 3) tipi approvati senza prodotti
        for t in tipi_righe:
            nome = str(t.get("Tipo", "") or "").strip()
            if ha_tipo and nome and str(t.get("Stato", "")).upper() == "APPROVATO" and not per_tipo.get(nome.casefold()):
                voci.append(self._voce("vuoto", nome, "Tipo senza prodotti: %s" % nome, dopo="Rifiuta il tipo",
                                       motivo="Nessun prodotto lo usa. Se serve di nuovo, lo ricrea l'AI o lo scegli dal menu.",
                                       azione={"t": "rifiuta_tipo", "tipo": nome}, etichetta="Rifiuta il tipo"))
        # 4) scorte minime a zero
        zero = [str(t.get("Tipo", "")) for t in tipi_righe if str(t.get("Stato", "")).upper() == "APPROVATO"
                and _num(t.get("Scorta_min", t.get("Scorta min", 0))) == 0 and per_tipo.get(str(t.get("Tipo", "")).strip().casefold())]
        if zero:
            voci.append(self._voce("scorta0", "n", "%d tipi con scorta minima 0" % len(zero),
                                   motivo="Non entrano mai nella spesa. Imposta la scorta dalla scheda di un prodotto del tipo: " + self._elenco(zero)))
        # 5) dati mancanti
        nimg = sum(1 for p in prodotti if nbc(p.get("Barcode")) and not str(p.get("Immagine", "") or "").strip())
        nmar = sum(1 for p in prodotti if nbc(p.get("Barcode")) and not str(p.get("Marca", "") or "").strip())
        ncon = sum(1 for p in prodotti if nbc(p.get("Barcode")) and not str(p.get("Confezione", "") or "").strip())
        if nimg or nmar or ncon:
            voci.append(self._voce("incompleti", "n", "Dati mancanti: %d senza immagine · %d senza marca · %d senza confezione" % (nimg, nmar, ncon),
                                   motivo="L'arricchimento cerca online i campi vuoti (non tocca quelli già compilati).",
                                   azione={"t": "arricchisci"} if self.arricchisci else None, etichetta="Avvia l'arricchimento"))
        # 6) sottocategorie senza prodotti
        usate = {(str(p.get("Categoria", "") or "").strip().casefold(), str(p.get("Sottocategoria", "") or "").strip().casefold()) for p in prodotti}
        vuote = ["%s › %s" % (c["categoria"], s) for c in inv.categorie() for s in c["sottocategorie"]
                 if (c["categoria"].casefold(), s.casefold()) not in usate]
        if vuote:
            voci.append(self._voce("sotto_vuote", "n", "%d sottocategorie senza prodotti" % len(vuote),
                                   motivo="Da togliere dal foglio «categorie» se non servono più: " + self._elenco(vuote)))
        # 7) codici a barre
        if non_validi:
            voci.append(self._voce("codici", "nv", "%d codici a barre non validi" % len(non_validi), motivo=self._elenco(non_validi)))
        if doppi:
            voci.append(self._voce("doppi", "d", "%d codici a barre doppi" % len(doppi), motivo=self._elenco(doppi)))
        # 8) giacenze strane e prodotti fermi
        anomale = ["%s: %s a %s" % (e["nome"] or e["barcode"], e["qta"], e["luogo"]) for e in inv._stock(zeri=True) if e["qta"] < 0 or e["qta"] >= 100]
        if anomale:
            voci.append(self._voce("giacenze", "g", "%d giacenze anomale (negative o da 100 in su)" % len(anomale), motivo=self._elenco(anomale)))
        ultimo: Dict[str, datetime] = {}
        for m in movimenti:
            k = nbc(m.get("Barcode"))
            try:
                d = datetime.strptime(data_it(m.get("Data", "")), "%d/%m/%Y")
            except Exception:
                continue
            if k and (k not in ultimo or d > ultimo[k]):
                ultimo[k] = d
        limite = self.oggi().replace(tzinfo=None) - timedelta(days=FERMI_GIORNI)
        fermi = []
        for e in inv.stock():
            d = ultimo.get(nbc(e["barcode"]))
            if d and d < limite and e["qta"] > 0:
                fermi.append("%s (da %d mesi)" % (e["nome"] or e["barcode"], max(1, (self.oggi().replace(tzinfo=None) - d).days // 30)))
        if fermi:
            voci.append(self._voce("fermi", "f", "%d prodotti fermi da oltre un anno" % len(fermi),
                                   motivo="Ancora in giacenza ma senza movimenti: scaduti o già finiti? " + self._elenco(fermi)))
        return voci

    def esegui(self) -> dict:
        if not self._lock.acquire(blocking=False):
            return {"errore": "gia in corso"}
        try:
            voci = self.analizza()
            azioni = sum(1 for v in voci if v.get("azione"))
            riep = "%d voci: %d con correzione proposta, %d solo da leggere" % (len(voci), azioni, len(voci) - azioni)
            self._salva({"ultima": self.oggi().strftime("%Y-%m-%d"), "voci": voci, "riepilogo": riep})
            return {"ok": True, "voci": len(voci), "riepilogo": riep}
        finally:
            self._lock.release()

    # --- decisioni -----------------------------------------------------------
    def decidi(self, id_: str, azione: str, campi: Optional[dict] = None) -> dict:
        d = self._leggi()
        v = next((x for x in d.get("voci", []) if x.get("id") == id_), None)
        if v is None:
            return {"errore": "Voce non trovata", "stato": 404}
        if v.get("stato") != "APERTA":
            return {"errore": "Voce già chiusa", "stato": 409}
        azione = str(azione).upper()
        if azione == "APPROVA" and v.get("azione"):
            a = v["azione"]
            t = a.get("t")
            if t == "tipo":
                self.inv.imposta_tipo(a["bc"], a["tipo"])
            elif t == "unisci":
                self.inv.unisci_tipo(a["da"], a["a"])
            elif t == "rifiuta_tipo":
                self.inv.rifiuta_tipo(a["tipo"])
            elif t == "arricchisci" and self.arricchisci:
                self.arricchisci()
            v["stato"] = "FATTA"
        else:
            v["stato"] = "IGNORATA"
        self._salva(d)
        return {"ok": True, "stato": v["stato"]}
