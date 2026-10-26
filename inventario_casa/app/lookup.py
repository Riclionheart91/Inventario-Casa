"""Ricerca del codice a barre su piu database aperti, in parallelo (solo libreria standard)."""
import json
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional

# (sigla, host): stesso formato di risposta per tutti
PROVIDERS = (("Open Food Facts", "world.openfoodfacts.org"),
             ("Open Beauty Facts", "world.openbeautyfacts.org"),
             ("Open Pet Food Facts", "world.openpetfoodfacts.org"),
             ("Open Products Facts", "world.openproductsfacts.org"))
CAMPI = "code,product_name,product_name_it,brands,quantity,image_front_url,ingredients_text_it,ingredients_text,nutriments,nutriscore_grade,nova_group,categories_tags"
TIMEOUT_TOTALE = 6.0


def fetch_http(url: str, timeout: float) -> Optional[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "InventarioCasa/0.3 (home assistant add-on)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


def pulisci_nome(nome: str, marca: str = "") -> str:
    n = re.sub(r"\s+", " ", (nome or "").strip())
    if not n:
        return ""
    for m in [x.strip() for x in (marca or "").split(",") if x.strip()]:   # toglie la marca ripetuta nel nome
        n = re.sub(r"(?i)(^|\s)%s(\s|$)" % re.escape(m), " ", n).strip(" -–,")
    n = re.sub(r"\s+", " ", n).strip()
    return n.title() if (n.isupper() or n.islower()) else n[:1].upper() + n[1:]


def _num(x):
    try:
        return round(float(x), 1)
    except (TypeError, ValueError):
        return None


def normalizza(p: dict, fonte: str) -> Optional[dict]:
    """Da un prodotto Open*Facts al formato dell'app. None se non c'e nulla di utile."""
    marca = str(p.get("brands", "") or "").split(",")[0].strip()
    nome = pulisci_nome(p.get("product_name_it") or p.get("product_name") or "", marca)
    if not nome:
        return None
    nu = p.get("nutriments") or {}
    parti = []
    for chiave, icona, unita in (("energy-kcal_100g", "🔥", "kcal"), ("fat_100g", "🫙", "g grassi"),
                                 ("sugars_100g", "🍬", "g zuccheri"), ("salt_100g", "🧂", "g sale")):
        v = _num(nu.get(chiave))
        if v is not None:
            parti.append("%s %s %s" % (icona, ("%g" % v), unita))
    punteggi = []
    if p.get("nutriscore_grade"):
        punteggi.append("Nutri %s" % str(p["nutriscore_grade"]).upper())
    if p.get("nova_group"):
        punteggi.append("NOVA %s" % p["nova_group"])
    ing = str(p.get("ingredients_text_it") or p.get("ingredients_text") or "").strip()
    return {"nome": nome, "marca": marca, "confezione": str(p.get("quantity", "") or "").strip(),
            "immagine": str(p.get("image_front_url", "") or "").strip(), "fonte": fonte,
            "categoria_suggerita": None, "dettagli": "",
            "composizione": ("🧪 Ingredienti: " + ing) if ing else "",
            "nutrizione": "  |  ".join(parti), "punteggi": "  |  ".join(punteggi)}


def _un_provider(bc: str, fonte: str, host: str, fetch: Callable, timeout: float) -> Optional[dict]:
    d = fetch("https://%s/api/v2/product/%s.json?fields=%s" % (host, bc, CAMPI), timeout)
    if not d or d.get("status") not in (1, "1") or not d.get("product"):
        return None
    return normalizza(d["product"], fonte)


def cerca(barcode: str, fetch: Callable = fetch_http, providers=PROVIDERS, timeout_totale: float = TIMEOUT_TOTALE) -> Optional[dict]:
    """Interroga tutti i provider insieme e restituisce il primo risultato utile, rispettando l'ordine di priorita
    se piu provider rispondono entro il tempo massimo."""
    bc = re.sub(r"\D", "", str(barcode))
    if not bc:
        return None
    t0 = time.time()
    risultati: Dict[int, Optional[dict]] = {}
    ex = ThreadPoolExecutor(max_workers=len(providers))
    try:
        fut = {ex.submit(_un_provider, bc, f, h, fetch, timeout_totale): i for i, (f, h) in enumerate(providers)}
        try:
            for f in as_completed(fut, timeout=timeout_totale):
                i = fut[f]
                try:
                    risultati[i] = f.result()
                except Exception:
                    risultati[i] = None
                # uscita anticipata: se il provider piu prioritario ancora in corsa non puo battere quello trovato, basta
                trovati = [k for k, v in risultati.items() if v]
                if trovati:
                    prima = min(trovati)
                    if all(k in risultati for k in range(prima)):
                        break
        except Exception:   # tempo scaduto: si usa quello che c'e
            pass
    finally:
        ex.shutdown(wait=False, cancel_futures=True)
    for i in sorted(risultati):
        if risultati[i]:
            return risultati[i]
    return None
