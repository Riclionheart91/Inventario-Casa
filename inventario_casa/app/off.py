"""Invio dei prodotti a Open Food Facts e ai progetti fratelli (cibo per animali, prodotti per la casa, cosmetici).

- controlla(): cerca ogni codice del catalogo sui progetti; quelli che non ci sono finiscono nell'elenco «da inviare».
- invia(): per i prodotti spuntati manda nome, marca, confezione e la tua foto (se c'e). Utente e password restano sul server e vanno solo ai siti Open*Facts.
- ignora(): «non proporre più»: il codice non torna mai nell'elenco.
Lo stato sta in /data/off_stato.json, le foto in /data/foto_off/ (si cancellano appena il prodotto e inviato o scartato)."""
import json
import os
import re
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from typing import Callable, Dict, List, Optional

from . import lookup
from .service import SH_PROD, nbc

PROGETTI: Dict[str, tuple] = {
    "food": ("Open Food Facts", "https://world.openfoodfacts.org"),
    "pet": ("Open Pet Food Facts", "https://world.openpetfoodfacts.org"),
    "products": ("Open Products Facts", "https://world.openproductsfacts.org"),
    "beauty": ("Open Beauty Facts", "https://world.openbeautyfacts.org"),
}
_PET = ("gatt", "cane", "cani", "animal", "lettiera", "crocchett", "pet ", "petfood", "croccantini", "umido per")
_CASA = ("pulizi", "detersiv", "ammorbident", "lavatrice", "lavastoviglie", "sgrassat", "igienizz", "candeggin", "anticalcare", "disinfett", "spugn",
         "sacchi", "straccio", "scopa", "casalingh", "bucato", "piatti", "pavimenti", "vetri", "carta igienica", "pellicola", "alluminio", "detergent")
_BELLEZZA = ("igiene", "cura persona", "cosmet", "shampoo", "balsamo", "bagnoschiuma", "dentifric", "deodorant", "doccia", "crema viso", "crema corpo",
             "rasatura", "trucco", "profumo", "assorbent", "struccant", "collutorio")
CAMPI_TESTO = ("nome", "marca", "confezione", "descrizione", "categorie", "etichette", "ingredienti", "allergeni", "origine", "imballaggio")
NUTRI = (("energia_kcal", "energy-kcal", "kcal"), ("grassi", "fat", "g"), ("saturi", "saturated-fat", "g"), ("carboidrati", "carbohydrates", "g"),
         ("zuccheri", "sugars", "g"), ("fibre", "fiber", "g"), ("proteine", "proteins", "g"), ("sale", "salt", "g"))
CAMPI = CAMPI_TESTO + tuple("n_" + n[0] for n in NUTRI)
FOTO_OK = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def _n(s) -> str:
    return re.sub(r"\s+", " ", str(s or "").lower()).strip()


def progetto_per(p: dict) -> str:
    """Progetto Open*Facts adatto a un prodotto, dalle parole di categoria, tipo e nome. In dubbio: cibo (si cambia a mano nell'elenco)."""
    t = " " + " ".join(_n(p.get(k)) for k in ("categoria", "sottocategoria", "tipo", "nome")) + " "
    if any(w in t for w in _PET):
        return "pet"
    if any(w in t for w in _BELLEZZA):
        return "beauty"
    if any(w in t for w in _CASA):
        return "products"
    return "food"


def valido_per_off(barcode) -> str:
    """Codice da cercare/inviare, oppure vuoto: servono EAN/UPC veri (8-14 cifre), non i codici interni dei negozi (prefisso 2 su 13 cifre)."""
    c = lookup.codice_da_cercare(barcode)
    if len(c) < 8 or (len(c) == 13 and c.startswith("2")):
        return ""
    return c


def _http(metodo: str, url: str, campi: Optional[dict] = None, file: Optional[tuple] = None, agent: str = "", timeout: float = 30.0):
    """(codice HTTP, json o None). campi in form, file = (nome campo, nome file, byte, tipo) in multipart."""
    corpo, intest = None, {"User-Agent": agent or "InventarioCasa", "Accept": "application/json"}
    if metodo == "POST":
        if file:
            b = "----inv" + uuid.uuid4().hex
            parti = []
            for k, v in (campi or {}).items():
                parti.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (b, k, v)).encode())
            nome, fname, dati, tipo = file
            parti.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n" % (b, nome, fname, tipo)).encode() + dati + b"\r\n")
            parti.append(("--%s--\r\n" % b).encode())
            corpo = b"".join(parti)
            intest["Content-Type"] = "multipart/form-data; boundary=" + b
        else:
            from urllib.parse import urlencode
            corpo = urlencode(campi or {}).encode()
            intest["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=corpo, headers=intest, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            testo, codice = r.read().decode("utf-8", "replace"), r.status
    except urllib.error.HTTPError as e:
        testo, codice = e.read().decode("utf-8", "replace"), e.code
    try:
        return codice, json.loads(testo)
    except Exception:
        return codice, None


class Off:
    def __init__(self, inv, utente: str = "", password: str = "", percorso: str = "", cartella: str = "", http: Callable = _http,
                 pausa: float = 0.8, versione: str = "", oggi: Callable = datetime.now, arricchisci: Optional[Callable] = None, dati_percorso: str = "", leggi_retro: Optional[Callable] = None):
        base = os.environ.get("DATA_DIR") or ("/data" if os.path.isdir("/data") else tempfile.gettempdir())
        self.inv, self.utente, self.password, self.http, self.pausa, self.oggi = inv, (utente or "").strip(), password or "", http, pausa, oggi
        self.percorso = percorso or os.path.join(base, "off_stato.json")
        self.cartella = cartella or os.path.join(base, "foto_off")
        self.dati_percorso = dati_percorso or os.path.join(base, "off_dati.json")
        self.arricchisci, self.leggi_retro = arricchisci, leggi_retro
        self.agent = "InventarioCasa/%s (add-on Home Assistant per uso domestico)" % (versione or "1")
        self._lock = threading.RLock()
        self._in_corso = False
        self._prog = [0, 0]

    # --- stato su file ---------------------------------------------------
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

    def _imposta(self, bc: str, stato: str, progetto: str = "") -> None:
        with self._lock:
            d = self._carica()
            d.setdefault("prodotti", {})[bc] = {"stato": stato, "progetto": progetto, "quando": self.oggi().isoformat(timespec="seconds")}
            self._salva(d)

    def configurato(self) -> bool:
        return bool(self.utente and self.password)

    # --- foto ------------------------------------------------------------
    def _nome_foto(self, k: str, lato: str) -> str:
        return k + ("_retro" if lato == "retro" else "")

    def salva_foto(self, barcode, dati: bytes, mime: str, lato: str = "fronte") -> bool:
        k, ext = nbc(barcode), FOTO_OK.get(mime)
        if not k or not ext or not dati or len(dati) > 8 * 1024 * 1024:
            return False
        try:
            os.makedirs(self.cartella, exist_ok=True)
            self.togli_foto(k, lato)
            with open(os.path.join(self.cartella, "%s.%s" % (self._nome_foto(k, lato), ext)), "wb") as f:
                f.write(dati)
            return True
        except Exception:
            return False

    def foto_file(self, barcode, lato: str = "fronte") -> Optional[tuple]:
        k = nbc(barcode)
        for ext in FOTO_OK.values():
            p = os.path.join(self.cartella, "%s.%s" % (self._nome_foto(k, lato), ext))
            if k and os.path.isfile(p):
                return p, {v: m for m, v in FOTO_OK.items()}[ext]
        return None

    def togli_foto(self, barcode, lato: Optional[str] = None) -> None:
        for l in ((lato,) if lato else ("fronte", "retro")):
            f = self.foto_file(barcode, l)
            if f:
                try:
                    os.remove(f[0])
                except Exception:
                    pass

    # --- scheda da inviare (dati del catalogo + arricchimento + correzioni a mano) ---
    def _dati_tutti(self) -> dict:
        try:
            with open(self.dati_percorso, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    def _scrivi_dati(self, d: dict) -> None:
        try:
            os.makedirs(os.path.dirname(self.dati_percorso), exist_ok=True)
            tmp = self.dati_percorso + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False)
            os.replace(tmp, self.dati_percorso)
        except Exception:
            pass

    def campi(self, p: dict) -> dict:
        """Cosa invierei per questo prodotto: i dati del catalogo, sopra i dati arricchiti e le correzioni a mano."""
        salvati = self._dati_tutti().get(p["barcode"], {}).get("campi", {})
        base = {"nome": p.get("nome", ""), "marca": p.get("marca", ""), "confezione": p.get("confezione", "")}
        return {k: str(salvati.get(k) or base.get(k, "") or "").strip() for k in CAMPI}

    def manca(self, p: dict, prog: str, campi: Optional[dict] = None) -> List[str]:
        c = campi if campi is not None else self.campi(p)
        m = [e for k, e in (("marca", "marca"), ("confezione", "confezione")) if not c.get(k)]
        if prog in ("food", "pet", "beauty") and not c.get("ingredienti"):
            m.append("ingredienti")
        if prog == "food" and sum(1 for n in NUTRI if c.get("n_" + n[0])) < 4:
            m.append("valori nutrizionali")
        if self.foto_file(p["barcode"]) is None:
            m.append("foto")
        return m

    def salva_campi(self, barcode, campi: dict) -> dict:
        """Correzioni a mano dalla scheda: restano sopra qualsiasi arricchimento futuro."""
        k = nbc(barcode)
        with self._lock:
            d = self._dati_tutti()
            e = d.setdefault(k, {})
            att = e.setdefault("campi", {})
            mod = set(e.get("mod", []))
            for c in CAMPI:
                if c in (campi or {}):
                    v = re.sub(r"[ \t]+", " ", str((campi or {})[c] or "")).strip()[:1500]
                    if v != str(att.get(c, "") or ""):
                        att[c] = v
                        mod.add(c)
            e["mod"] = sorted(mod)
            self._scrivi_dati(d)
        return att

    def scheda(self, barcode) -> Optional[dict]:
        k = nbc(barcode)
        p = next((x for x in self._catalogo() if x["barcode"] == k), None)
        if not p:
            return None
        s = self._carica().get("prodotti", {}).get(k, {})
        prog = s.get("progetto") if s.get("progetto") in PROGETTI else progetto_per(p)
        e = self._dati_tutti().get(k, {})
        c = self.campi(p)
        return {"barcode": k, "progetto": prog, "progetto_nome": PROGETTI[prog][0], "campi": c, "manca": self.manca(p, prog, c), "fonte": e.get("fonte", ""),
                "arricchito": bool(e.get("quando")), "foto": self.foto_file(k) is not None, "retro": self.foto_file(k, "retro") is not None, "immagine_web": e.get("immagine_web", "") or p.get("immagine", ""),
                "modificati": e.get("mod", [])}

    def arricchisci_uno(self, barcode) -> Optional[dict]:
        """Cerca per codice a barre (database e web) e compila i campi; i campi corretti a mano non si toccano."""
        k = nbc(barcode)
        p = next((x for x in self._catalogo() if x["barcode"] == k), None)
        if not p or not self.arricchisci:
            return None
        try:
            r = self.arricchisci(dict(p, **{c: v for c, v in self.campi(p).items() if v})) or {}
        except Exception:
            r = {}
        rf = self.foto_file(k, "retro")
        if rf and self.leggi_retro:   # l'etichetta del retro e la fonte piu esatta: vale piu della ricerca sul web
            try:
                with open(rf[0], "rb") as fh:
                    rr = self.leggi_retro(fh.read(), rf[1], dict(p, **{c: v for c, v in self.campi(p).items() if v})) or {}
            except Exception:
                rr = {}
            if rr:
                r = dict(r, **{c: v for c, v in rr.items() if v})
                r["fonte"] = (str(r.get("fonte") or "") + " + foto del retro").strip(" +")
        with self._lock:
            d = self._dati_tutti()
            e = d.setdefault(k, {})
            att, mod = e.setdefault("campi", {}), set(e.get("mod", []))
            for c in CAMPI:
                v = str(r.get(c) or "").strip()
                if v and c not in mod:
                    att[c] = v
            e["fonte"] = r.get("fonte") or e.get("fonte", "")
            if r.get("immagine_web"):
                e["immagine_web"] = r["immagine_web"]
            e["tentato"] = self.oggi().isoformat(timespec="seconds")
            if r:
                e["quando"] = e["tentato"]
            self._scrivi_dati(d)
        return self.scheda(k)

    def arricchisci_elenco(self, massimo: int = 40, pausa: float = 3.0) -> int:
        """In background: arricchisce i prodotti dell'elenco mai provati (o provati senza successo piu di una settimana fa)."""
        n = 0
        dati = self._dati_tutti()
        for p in self.elenco():
            if n >= massimo:
                break
            e = dati.get(p["barcode"], {})
            if e.get("quando"):
                continue
            t = e.get("tentato")
            if t:
                try:
                    if (self.oggi() - datetime.fromisoformat(t)).days < 7:
                        continue
                except Exception:
                    pass
            self.arricchisci_uno(p["barcode"])
            n += 1
            time.sleep(pausa)
        return n

    def pulisci_foto(self, giorni_orfane: int = 60) -> int:
        """Cancella le foto che non servono piu: prodotto gia su Open*Facts, inviato o scartato, oppure fuori catalogo da troppo tempo.
        Restano solo quelle dei prodotti ancora da inviare."""
        try:
            nomi = os.listdir(self.cartella)
        except Exception:
            return 0
        stati = self._carica().get("prodotti", {})
        catalogo = {p["barcode"] for p in self._catalogo()}
        n = 0
        for f in nomi:
            k = f.split(".")[0].replace("_retro", "")
            percorso = os.path.join(self.cartella, f)
            st = stati.get(k, {}).get("stato", "")
            vecchia = False
            try:
                vecchia = (time.time() - os.path.getmtime(percorso)) > giorni_orfane * 86400
            except Exception:
                pass
            if st in ("presente", "inviato", "ignorato") or (k not in catalogo and vecchia) or (not st and vecchia):
                try:
                    os.remove(percorso)
                    n += 1
                except Exception:
                    pass
        return n

    def foto_in_attesa(self) -> dict:
        n, b = 0, 0
        try:
            for f in os.listdir(self.cartella):
                n += 1
                b += os.path.getsize(os.path.join(self.cartella, f))
        except Exception:
            pass
        return {"foto_n": n, "foto_mb": round(b / 1048576, 1)}

    # --- controllo -------------------------------------------------------
    def _catalogo(self) -> List[dict]:
        out = []
        for r in self.inv._dicts(SH_PROD):
            k = nbc(r.get("Barcode"))
            if k and str(r.get("Prodotto", "") or "").strip():
                out.append({"barcode": k, "nome": str(r.get("Prodotto", "")).strip(), "marca": str(r.get("Marca", "") or "").strip(),
                            "confezione": str(r.get("Confezione", "") or "").strip(), "categoria": str(r.get("Categoria", "") or "").strip(),
                            "sottocategoria": str(r.get("Sottocategoria", "") or "").strip(), "tipo": str(r.get("Tipo", "") or "").strip(),
                            "immagine": str(r.get("Immagine", "") or "").strip(),
                            "composizione": str(r.get("Composizione", "") or "").strip(), "nutrizione": str(r.get("Nutrizione (100g)", "") or "").strip()})
        return out

    def _presente(self, progetto: str, codice: str) -> Optional[bool]:
        """True/False se il progetto conosce il codice, None se non si e potuto sapere (rete)."""
        try:
            cod, j = self.http("GET", "%s/api/v2/product/%s.json?fields=code" % (PROGETTI[progetto][1], codice), agent=self.agent, timeout=20.0)
        except Exception:
            return None
        if isinstance(j, dict) and j.get("status") == 1:
            return True
        if cod == 404 or (isinstance(j, dict) and j.get("status") == 0):
            return False
        return None

    def _dove(self, progetto: str, codice: str):
        """Progetto che conosce gia il codice (quello scelto, poi Open Food Facts), False se nessuno, None se non si e potuto sapere."""
        r = self._presente(progetto, codice)
        if r:
            return progetto
        if r is False and progetto != "food":
            time.sleep(self.pausa)
            r2 = self._presente("food", codice)
            return "food" if r2 else (False if r2 is False else None)
        return r

    def _gia_su_off(self, progetto: str, codice: str) -> Optional[bool]:
        """Il codice e gia su uno dei progetti? Si guarda quello scelto e, per i prodotti non alimentari, anche Open Food Facts (capita che ci siano finiti li)."""
        r = self._presente(progetto, codice)
        if r is False and progetto != "food":
            time.sleep(self.pausa)
            r = self._presente("food", codice)
        return r

    def controlla(self, massimo: int = 0) -> dict:
        """Controlla i prodotti non ancora esaminati (in background, con una pausa fra le richieste per non pesare sul servizio)."""
        with self._lock:
            if self._in_corso:
                return {"avviato": False}
            self._in_corso = True
        try:
            gia = self._carica().get("prodotti", {})
            da = [p for p in self._catalogo() if p["barcode"] not in gia and valido_per_off(p["barcode"])]
            if massimo:
                da = da[:massimo]
            self._prog = [0, len(da)]
            for p in da:
                cod = valido_per_off(p["barcode"])
                prog = progetto_per(p)
                r = self._dove(prog, cod)
                if r is not None:
                    self._imposta(p["barcode"], "presente" if r else "assente", r or prog)
                    if r:
                        self.togli_foto(p["barcode"])   # c'e gia: la foto tenuta per l'invio non serve
                self._prog[0] += 1
                time.sleep(self.pausa)
            with self._lock:
                d = self._carica()
                d["ultimo"] = self.oggi().isoformat(timespec="seconds")
                self._salva(d)
            self.pulisci_foto()
            return {"avviato": True, "controllati": len(da)}
        finally:
            self._in_corso = False

    def in_corso(self) -> bool:
        return self._in_corso

    # --- elenco ----------------------------------------------------------
    def elenco(self) -> List[dict]:
        """Prodotti non presenti su Open*Facts e non scartati."""
        stati = self._carica().get("prodotti", {})
        out = []
        for p in self._catalogo():
            s = stati.get(p["barcode"])
            if not s or s.get("stato") != "assente":
                continue
            prog = s.get("progetto") if s.get("progetto") in PROGETTI else progetto_per(p)
            c = self.campi(p)
            out.append(dict(p, nome=c["nome"] or p["nome"], marca=c["marca"], confezione=c["confezione"], progetto=prog, progetto_nome=PROGETTI[prog][0],
                            foto=self.foto_file(p["barcode"]) is not None, manca=self.manca(p, prog, c)))
        return sorted(out, key=lambda x: x["nome"].lower())

    def stato(self) -> dict:
        d = self._carica()
        c = {}
        for v in d.get("prodotti", {}).values():
            c[v.get("stato", "")] = c.get(v.get("stato", ""), 0) + 1
        return {"configurato": self.configurato(), "in_corso": self._in_corso, "controllati": self._prog[0], "totale": self._prog[1],
                "ultimo": d.get("ultimo", ""), "presenti": c.get("presente", 0), "inviati": c.get("inviato", 0), "ignorati": c.get("ignorato", 0), "rimandati": c.get("rimandato", 0),
                "progetti": {k: v[0] for k, v in PROGETTI.items()}, **self.foto_in_attesa()}

    def cambia_progetto(self, barcode, progetto: str) -> None:
        k = nbc(barcode)
        if progetto in PROGETTI and k and self._carica().get("prodotti", {}).get(k, {}).get("stato") == "assente":
            self._imposta(k, "assente", progetto)

    # --- decisioni -------------------------------------------------------
    def ignora(self, barcodes: List[str]) -> int:
        """«Non proporre più»: il codice non torna nell'elenco; la foto tenuta per l'invio si cancella."""
        n = 0
        for b in barcodes or []:
            k = nbc(b)
            if k:
                self._imposta(k, "ignorato")
                self.togli_foto(k)
                n += 1
        return n

    def rimanda(self, barcodes: List[str]) -> int:
        """«Rimanda»: esce dall'elenco finche il prodotto non viene caricato di nuovo; la foto resta."""
        n = 0
        stati = self._carica().get("prodotti", {})
        for b in barcodes or []:
            k = nbc(b)
            if k and stati.get(k, {}).get("stato") == "assente":
                self._imposta(k, "rimandato", stati[k].get("progetto", ""))
                n += 1
        return n

    def riprendi(self, barcode) -> bool:
        """Al nuovo carico del prodotto la richiesta rimandata torna nell'elenco."""
        k = nbc(barcode)
        s = self._carica().get("prodotti", {}).get(k)
        if s and s.get("stato") == "rimandato":
            self._imposta(k, "assente", s.get("progetto", ""))
            return True
        return False

    def invia(self, voci: List[dict]) -> List[dict]:
        """Invia i prodotti scelti. voci = [{barcode, progetto}]. Ritorna per ciascuno {barcode, ok, messaggio}."""
        if not self.configurato():
            raise ValueError("Inserisci utente e password di Open Food Facts nelle opzioni dell'app.")
        cat = {p["barcode"]: p for p in self._catalogo()}
        out = []
        for v in voci or []:
            k = nbc(v.get("barcode"))
            p = cat.get(k)
            prog = v.get("progetto") if v.get("progetto") in PROGETTI else (progetto_per(p) if p else "food")
            if not p or not valido_per_off(k):
                out.append({"barcode": k, "ok": False, "messaggio": "Prodotto non trovato o codice non valido."})
                continue
            try:
                out.append(dict(self._invia_uno(p, prog), barcode=k))
            except Exception as e:   # rete o risposta strana: mai la password nel messaggio
                out.append({"barcode": k, "ok": False, "messaggio": "Non riuscito: %s" % (str(e).replace(self.password, "***") or type(e).__name__)[:120]})
            time.sleep(self.pausa)
        return out

    def _invia_uno(self, p: dict, prog: str) -> dict:
        nome_prog, base = PROGETTI[prog]
        cod = valido_per_off(p["barcode"])
        if self._gia_su_off(prog, cod):
            self._imposta(p["barcode"], "presente", prog)
            return {"ok": True, "messaggio": "C'è già su Open*Facts: non lo invio."}
        auth = {"user_id": self.utente, "password": self.password}
        c = self.campi(p)
        campi = dict(auth, code=cod, product_name=c["nome"] or p["nome"], brands=c["marca"], quantity=c["confezione"], lc="it", cc="it",
                     app_name="InventarioCasa", app_version="1", comment="Aggiunto da Inventario Casa")
        if c["descrizione"]:
            campi["generic_name"] = c["descrizione"]
        for chiave, k in (("categories", "categorie"), ("labels", "etichette"), ("packaging", "imballaggio"), ("origins", "origine")):
            if c[k]:
                campi[chiave] = c[k]
        if prog in ("food", "pet", "beauty") and c["ingredienti"]:
            campi["ingredients_text"] = c["ingredienti"]
        if prog in ("food", "pet") and c["allergeni"]:
            campi["allergens"] = c["allergeni"]
        if prog == "food" and any(c["n_" + n[0]] for n in NUTRI):
            campi["nutrition_data_per"] = "100g"
            for nome, off_n, unita in NUTRI:
                if c["n_" + nome]:
                    campi["nutriment_" + off_n] = c["n_" + nome].replace(",", ".")
                    campi["nutriment_%s_unit" % off_n] = unita
        codice, j = self.http("POST", base + "/cgi/product_jqm2.pl", campi, agent=self.agent, timeout=40.0)
        if not (isinstance(j, dict) and j.get("status") == 1):
            motivo = (j or {}).get("status_verbose") if isinstance(j, dict) else ""
            return {"ok": False, "messaggio": "%s ha rifiutato i dati%s" % (nome_prog, (": " + str(motivo)[:100]) if motivo else " (HTTP %s). Controlla utente e password: l'account vale anche su questo sito?" % codice)}
        msg = "Inviato a %s." % nome_prog
        f = self.foto_file(p["barcode"])
        if f:
            try:
                with open(f[0], "rb") as fh:
                    dati = fh.read()
                c2, j2 = self.http("POST", base + "/cgi/product_image_upload.pl", dict(auth, code=cod, imagefield="front"),
                                   ("imgupload_front", "foto." + FOTO_OK[f[1]], dati, f[1]), agent=self.agent, timeout=90.0)
                if isinstance(j2, dict) and j2.get("status") == "status ok":
                    self.togli_foto(p["barcode"], "fronte")
                    msg += " Foto caricata."
                else:
                    msg += " La foto non è partita (%s): caricala a mano dal sito." % (str((j2 or {}).get("debug") or "HTTP %s" % c2)[:80])
            except Exception as e:
                msg += " La foto non è partita (%s)." % str(e)[:60]
        else:
            msg += " Senza foto."
        rf = self.foto_file(p["barcode"], "retro")
        if rf:
            campi_retro = ("ingredients", "nutrition") if prog == "food" else ("ingredients",) if prog in ("pet", "beauty") else ("other",)
            ok_r = True
            try:
                with open(rf[0], "rb") as fh:
                    dati_r = fh.read()
                for campo in campi_retro:
                    c3, j3 = self.http("POST", base + "/cgi/product_image_upload.pl", dict(auth, code=cod, imagefield=campo),
                                       ("imgupload_" + campo, "retro." + FOTO_OK[rf[1]], dati_r, rf[1]), agent=self.agent, timeout=90.0)
                    ok_r = ok_r and isinstance(j3, dict) and j3.get("status") == "status ok"
            except Exception:
                ok_r = False
            msg += " Foto del retro caricata." if ok_r else " La foto del retro non è partita."
            if ok_r:
                self.togli_foto(p["barcode"], "retro")
        self._imposta(p["barcode"], "inviato", prog)
        return {"ok": True, "messaggio": msg}
