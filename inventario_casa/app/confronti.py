"""Prodotti che su Open Food Facts (o sui progetti fratelli) ci sono gia: confronto con il tuo foglio, a schede di approvazione.
Per ogni campo che differisce o che manca da una parte, proponi tu cosa fare: usare il valore di Open Food Facts nel tuo foglio, mandare il tuo a Open Food Facts
(solo dove lì e vuoto: non si sovrascrive mai niente di loro) oppure lasciare com'e. Niente si scrive finche non applichi."""
import difflib
import json
import os
import re
import tempfile
import threading
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional

from .off import FOTO_OK, NUTRI, PROGETTI, Off, valido_per_off
from .service import ApiError, nbc

ETICHETTE = {"nome": "Nome", "marca": "Marca", "confezione": "Confezione", "ingredienti": "Ingredienti", "nutrizione": "Valori nutrizionali (per 100 g)", "immagine": "Foto"}
CAMPI_OFF = "product_name,product_name_it,generic_name_it,brands,quantity,ingredients_text_it,ingredients_text,nutriments,image_front_url"
PREFISSO_ING = "🧪 Ingredienti:"


def _n(s) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def _simili(a: str, b: str, soglia: float = 0.85) -> bool:
    return _n(a) == _n(b) or difflib.SequenceMatcher(None, _n(a), _n(b)).ratio() >= soglia


def testo_nutrizione(nu: dict) -> str:
    """Valori per 100 g come testo breve, nello stesso formato del foglio."""
    parti = []
    for chiave, icona, unita in (("energia_kcal", "🔥", "kcal"), ("grassi", "🫙", "g grassi"), ("zuccheri", "🍬", "g zuccheri"), ("sale", "🧂", "g sale")):
        v = str(nu.get(chiave) or "").strip()
        if v:
            parti.append("%s %s %s" % (icona, v, unita))
    return "  |  ".join(parti)


def da_off(prod: dict) -> dict:
    """Prodotto Open*Facts -> campi confrontabili (testo)."""
    nu = prod.get("nutriments") or {}

    def num(k):
        try:
            v = float(nu.get(k))
            return ("%g" % round(v, 2))
        except (TypeError, ValueError):
            return ""
    n = {"energia_kcal": num("energy-kcal_100g"), "grassi": num("fat_100g"), "saturi": num("saturated-fat_100g"), "carboidrati": num("carbohydrates_100g"),
         "zuccheri": num("sugars_100g"), "fibre": num("fiber_100g"), "proteine": num("proteins_100g"), "sale": num("salt_100g")}
    return {"nome": str(prod.get("product_name_it") or prod.get("product_name") or prod.get("generic_name_it") or "").strip(),
            "marca": str(prod.get("brands") or "").split(",")[0].strip(), "confezione": str(prod.get("quantity") or "").strip(),
            "ingredienti": str(prod.get("ingredients_text_it") or prod.get("ingredients_text") or "").strip(),
            "nutrizione": testo_nutrizione(n), "n": n, "immagine": str(prod.get("image_front_url") or "").strip()}


class Confronti:
    def __init__(self, off: Off, inv, percorso: str = "", pausa: float = 0.8):
        base = os.environ.get("DATA_DIR") or ("/data" if os.path.isdir("/data") else tempfile.gettempdir())
        self.off, self.inv, self.pausa = off, inv, pausa
        self.percorso = percorso or os.path.join(base, "off_confronti.json")
        self._lock = threading.RLock()
        self._in_corso = False

    # --- stato -----------------------------------------------------------
    def _carica(self) -> dict:
        try:
            with open(self.percorso, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    def _salva(self, d: dict) -> None:
        try:
            os.makedirs(os.path.dirname(self.percorso), exist_ok=True)
            tmp = self.percorso + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False)
            os.replace(tmp, self.percorso)
        except Exception:
            pass

    def _imposta(self, bc: str, stato: str, voci: Optional[list] = None, prog: str = "") -> None:
        with self._lock:
            d = self._carica()
            d.setdefault("schede", {})[bc] = {"stato": stato, "voci": voci or [], "progetto": prog, "quando": datetime.now().isoformat(timespec="seconds")}
            self._salva(d)

    def in_corso(self) -> bool:
        return self._in_corso

    # --- confronto -------------------------------------------------------
    def _nostri(self, p: dict) -> dict:
        """I valori che abbiamo noi: foglio + dati completati dalla ricerca/AI + foto in attesa."""
        c = self.off.campi(p)
        ing = c.get("ingredienti") or p.get("composizione", "").replace(PREFISSO_ING, "").strip()
        n = {k: c.get("n_" + k, "") for k, _, _ in NUTRI}
        return {"nome": p.get("nome", ""), "marca": c.get("marca") or p.get("marca", ""), "confezione": c.get("confezione") or p.get("confezione", ""),
                "ingredienti": ing, "nutrizione_foglio": p.get("nutrizione", ""), "n": n, "nutrizione": testo_nutrizione(n) or p.get("nutrizione", ""),
                "immagine": p.get("immagine", ""), "foto": self.off.foto_file(p["barcode"]) is not None}

    def voci(self, p: dict, o: dict) -> List[dict]:
        """Differenze fra il foglio (e i dati che abbiamo raccolto) e Open Food Facts, campo per campo."""
        n = self._nostri(p)
        out = []

        def voce(campo, nostro, off, azioni, sugg):
            out.append({"campo": campo, "etichetta": ETICHETTE[campo], "nostro": nostro, "off": off, "azioni": azioni, "suggerita": sugg})
        for campo in ("nome", "marca", "confezione", "ingredienti"):
            a, b = n[campo].strip(), o[campo].strip()
            if a and b:
                if not _simili(a, b):
                    voce(campo, a, b, ["foglio", "nessuna"], "nessuna")
            elif b and not a:
                voce(campo, "", b, ["foglio", "nessuna"], "foglio")
            elif a and not b and campo != "nome":
                voce(campo, a, "", ["off", "nessuna"], "off")
        # valori nutrizionali: da Open Food Facts al foglio se il foglio non li ha; dal nostro a Open Food Facts se li mancano e abbiamo almeno 4 valori
        n_nostri = sum(1 for v in n["n"].values() if v)
        n_off = sum(1 for v in o["n"].values() if v)
        if o["nutrizione"] and not n["nutrizione_foglio"]:
            voce("nutrizione", n["nutrizione"], o["nutrizione"], ["foglio", "nessuna"], "foglio")
        elif n_nostri >= 4 and n_off < 4:
            voce("nutrizione", n["nutrizione"], o["nutrizione"], ["off", "nessuna"], "off")
        # foto: la tua a Open Food Facts se lì manca; l'immagine di Open Food Facts al foglio se il foglio non ne ha
        if not o["immagine"] and n["foto"]:
            voce("immagine", "la tua foto", "", ["off", "nessuna"], "off")
        elif o["immagine"] and not n["immagine"]:
            voce("immagine", "", o["immagine"], ["foglio", "nessuna"], "foglio")
        return out

    def _scarica(self, prog: str, cod: str) -> Optional[dict]:
        try:
            codice, j = self.off.http("GET", "%s/api/v2/product/%s.json?fields=%s" % (PROGETTI[prog][1], cod, CAMPI_OFF), agent=self.off.agent, timeout=20.0)
        except Exception:
            return None
        if isinstance(j, dict) and j.get("status") == 1 and isinstance(j.get("product"), dict):
            return da_off(j["product"])
        return None

    def scansiona(self, massimo: int = 40, max_ai: int = 15) -> int:
        """Confronta i prodotti gia su Open*Facts mai esaminati. Per chi ha lacune su Open Food Facts completa prima i dati nostri (ricerca per codice + AI)."""
        with self._lock:
            if self._in_corso:
                return 0
            self._in_corso = True
        try:
            visti = self._carica().get("schede", {})
            stati = self.off._carica().get("prodotti", {})
            cat = {p["barcode"]: p for p in self.off._catalogo()}
            n = ai = 0
            for bc, s in stati.items():
                if n >= massimo:
                    break
                if s.get("stato") != "presente" or bc in visti or bc not in cat:
                    continue
                p, prog = cat[bc], (s.get("progetto") if s.get("progetto") in PROGETTI else "food")
                o = self._scarica(prog, valido_per_off(bc))
                time.sleep(self.pausa)
                if o is None:
                    continue
                v = self.voci(p, o)
                lacune = not o["ingredienti"] or not o["marca"] or not o["confezione"] or sum(1 for x in o["n"].values() if x) < 4
                gia = self.off._dati_tutti().get(bc, {})
                if lacune and not gia.get("tentato") and ai < max_ai and self.off.arricchisci:
                    ai += 1
                    self.off.arricchisci_uno(bc)
                    v = self.voci(p, o)
                self._imposta(bc, "aperto" if v else "chiuso", v, prog)
                n += 1
            return n
        finally:
            self._in_corso = False

    # --- schede da approvare ----------------------------------------------
    def elenco(self) -> List[dict]:
        cat = {p["barcode"]: p for p in self.off._catalogo()}
        out = []
        for bc, s in self._carica().get("schede", {}).items():
            if s.get("stato") == "aperto" and s.get("voci") and bc in cat:
                out.append({"barcode": bc, "nome": cat[bc]["nome"], "voci": s["voci"], "progetto_nome": PROGETTI.get(s.get("progetto"), PROGETTI["food"])[0]})
        return sorted(out, key=lambda x: x["nome"].lower())

    def ignora(self, barcode) -> None:
        k = nbc(barcode)
        s = self._carica().get("schede", {}).get(k)
        self._imposta(k, "ignorato", s.get("voci") if s else [], (s or {}).get("progetto", ""))

    def applica(self, barcode, scelte: Dict[str, str]) -> List[dict]:
        """Esegue le scelte dell'utente. Ritorna l'esito per campo. La scheda si chiude quando non resta niente da decidere."""
        k = nbc(barcode)
        s = self._carica().get("schede", {}).get(k)
        p = next((x for x in self.off._catalogo() if x["barcode"] == k), None)
        if not s or not p:
            raise ApiError(404, "Scheda non trovata")
        voci = {v["campo"]: v for v in s["voci"]}
        prog = s.get("progetto") if s.get("progetto") in PROGETTI else "food"
        esiti, foglio, verso_off = [], {}, {}
        for campo, az in (scelte or {}).items():
            v = voci.get(campo)
            if not v or az not in v["azioni"]:
                continue
            if az == "foglio":
                foglio[campo] = v["off"]
            elif az == "off":
                verso_off[campo] = v["nostro"]
        if foglio:
            try:
                self.inv.aggiorna_da_off(k, foglio)
                esiti += [{"campo": c, "ok": True, "messaggio": "Aggiornato il tuo foglio."} for c in foglio]
            except Exception as e:
                esiti += [{"campo": c, "ok": False, "messaggio": "Foglio non aggiornato: %s" % str(e)[:80]} for c in foglio]
        if verso_off:
            esiti += self._invia_a_off(p, prog, verso_off)
        fatti = {e["campo"] for e in esiti if e["ok"]}
        scelti_nessuna = {c for c, a in (scelte or {}).items() if a == "nessuna"}
        restano = [v for v in s["voci"] if v["campo"] not in fatti and v["campo"] not in scelti_nessuna]
        self._imposta(k, "aperto" if restano else "chiuso", restano, s.get("progetto", ""))
        return esiti

    def _invia_a_off(self, p: dict, prog: str, campi: Dict[str, str]) -> List[dict]:
        """Manda a Open*Facts SOLO i campi scelti (che li' sono vuoti): niente di loro viene sovrascritto."""
        if not self.off.configurato():
            return [{"campo": c, "ok": False, "messaggio": "Servono utente e password di Open Food Facts nelle opzioni."} for c in campi]
        cod, base = valido_per_off(p["barcode"]), PROGETTI[prog][1]
        auth = {"user_id": self.off.utente, "password": self.off.password}
        c = self.off.campi(p)
        post = dict(auth, code=cod, lc="it", cc="it", app_name="InventarioCasa", app_version="1", comment="Completato da Inventario Casa (solo campi vuoti)")
        for campo in campi:
            if campo == "marca":
                post["brands"] = c["marca"] or campi[campo]
            elif campo == "confezione":
                post["quantity"] = c["confezione"] or campi[campo]
            elif campo == "ingredienti":
                post["ingredients_text"] = c["ingredienti"] or campi[campo]
            elif campo == "nutrizione" and any(c["n_" + n[0]] for n in NUTRI):
                post["nutrition_data_per"] = "100g"
                for nome, off_n, unita in NUTRI:
                    if c["n_" + nome]:
                        post["nutriment_" + off_n] = c["n_" + nome].replace(",", ".")
                        post["nutriment_%s_unit" % off_n] = unita
        esiti = []
        testuali = [x for x in campi if x != "immagine"]
        if testuali:
            try:
                codice, j = self.off.http("POST", base + "/cgi/product_jqm2.pl", post, agent=self.off.agent, timeout=40.0)
                ok = isinstance(j, dict) and j.get("status") == 1
                esiti += [{"campo": x, "ok": ok, "messaggio": "Inviato a Open Food Facts." if ok else "Rifiutato: %s" % str((j or {}).get("status_verbose") if isinstance(j, dict) else "HTTP %s" % codice)[:80]} for x in testuali]
            except Exception as e:
                esiti += [{"campo": x, "ok": False, "messaggio": "Non riuscito: %s" % str(e).replace(self.off.password, "***")[:80]} for x in testuali]
        if "immagine" in campi:
            esiti.append(self._foto(p, prog, cod, base, auth))
        return esiti

    def _foto(self, p: dict, prog: str, cod: str, base: str, auth: dict) -> dict:
        f = self.off.foto_file(p["barcode"])
        if not f:
            return {"campo": "immagine", "ok": False, "messaggio": "Non ho la tua foto."}
        try:
            with open(f[0], "rb") as fh:
                dati = fh.read()
            codice, j = self.off.http("POST", base + "/cgi/product_image_upload.pl", dict(auth, code=cod, imagefield="front"),
                                      ("imgupload_front", "foto." + FOTO_OK[f[1]], dati, f[1]), agent=self.off.agent, timeout=90.0)
            ok = isinstance(j, dict) and j.get("status") == "status ok"
            if ok:
                self.off.togli_foto(p["barcode"], "fronte")
            return {"campo": "immagine", "ok": ok, "messaggio": "Foto caricata." if ok else "Foto non partita."}
        except Exception as e:
            return {"campo": "immagine", "ok": False, "messaggio": "Foto non partita: %s" % str(e)[:60]}
