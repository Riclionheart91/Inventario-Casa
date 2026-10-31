"""Ricerca del codice a barre su piu database aperti, in parallelo (solo libreria standard)."""
import json
import re
import threading
import time
from collections import deque
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional

# (sigla, host): stesso formato di risposta per tutti
PROVIDERS = (("Open Food Facts", "world.openfoodfacts.org"),
             ("Open Beauty Facts", "world.openbeautyfacts.org"),
             ("Open Pet Food Facts", "world.openpetfoodfacts.org"),
             ("Open Products Facts", "world.openproductsfacts.org"))
CAMPI = "code,product_name,product_name_it,product_name_en,product_name_fr,product_name_ar,generic_name,generic_name_it,abbreviated_product_name,brands,quantity,image_front_url,ingredients_text_it,ingredients_text,nutriments,nutriscore_grade,nova_group,categories_tags"
TIMEOUT_TOTALE = 6.0
ERRORI = deque(maxlen=60)   # (istante, host, motivo): serve a spiegare perche una ricerca non ha trovato nulla


def fetch_http(url: str, timeout: float, headers: Optional[dict] = None) -> Optional[dict]:
    req = urllib.request.Request(url, headers=dict({"User-Agent": "InventarioCasa/0.4 (home assistant add-on)"}, **(headers or {})))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            testo = r.read().decode("utf-8", "replace")
        try:
            return json.loads(testo)
        except ValueError:
            return {"_testo": testo}   # risposta non JSON (es. OpenGTINDB): la legge il provider
    except Exception as e:
        ERRORI.append((time.time(), url.split("/")[2] if "//" in url else url, "%s: %s" % (type(e).__name__, str(e)[:80])))
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
    grezzo = next((str(p.get(c) or "").strip() for c in ("product_name_it", "product_name", "generic_name_it", "product_name_en",
                                                          "product_name_fr", "generic_name", "abbreviated_product_name", "product_name_ar")
                   if str(p.get(c) or "").strip()), "")
    nome = pulisci_nome(grezzo, marca)
    if not nome and not marca and not p.get("image_front_url"):
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


# ---- provider a chiave (opzionali): si usano solo se la chiave e nelle opzioni dell'app; stessi del motore Apps Script ----
def _min(nome, marca, immagine, fonte, ing="") -> Optional[dict]:
    marca = str(marca or "").strip()
    nome = pulisci_nome(str(nome or ""), marca)
    if not nome:
        return None
    return {"nome": nome, "marca": marca, "confezione": "", "immagine": str(immagine or "").strip(), "fonte": fonte,
            "categoria_suggerita": None, "dettagli": "", "composizione": ("🧪 Ingredienti: " + ing) if ing else "",
            "nutrizione": "", "punteggi": ""}


def _barcodelookup(bc, k, f, t):
    d = f("https://api.barcodelookup.com/v3/products?barcode=%s&key=%s" % (bc, k["BARCODELOOKUP_KEY"]), t)
    p = (d or {}).get("products") or []
    if not p:
        return None
    p = p[0]; im = p.get("images") or []
    return _min(p.get("product_name") or p.get("title"), p.get("brand") or p.get("manufacturer"), im[0] if im else "", "BarcodeLookup")


def _upcdatabase(bc, k, f, t):
    d = f("https://upcdatabase.org/api/%s/product/%s" % (k["UPCDATABASE_KEY"], bc), t) or {}
    return _min(d.get("title") or d.get("itemname") or d.get("productname") or d.get("description"),
                d.get("brand") or d.get("manufacturer"), "", "UPCDatabase")


def _goupc(bc, k, f, t):
    d = (f("https://go-upc.com/api/v1/code/%s" % bc, t, {"Authorization": "Bearer " + k["GOUPC_TOKEN"]}) or {}).get("product")
    return _min(d.get("name") or d.get("title"), d.get("brand"), d.get("image"), "Go-UPC", d.get("ingredients") or "") if d else None


def _spoonacular(bc, k, f, t):
    d = f("https://api.spoonacular.com/food/products/upc/%s?apiKey=%s" % (bc, k["SPOONACULAR_KEY"]), t) or {}
    return _min(d.get("title") or d.get("name"), d.get("brand"), d.get("image"), "Spoonacular")


def _nutritionix(bc, k, f, t):
    d = f("https://trackapi.nutritionix.com/v2/search/item?upc=" + bc, t,
          {"x-app-id": k["NUTRITIONIX_APP_ID"], "x-app-key": k["NUTRITIONIX_APP_KEY"]}) or {}
    foods = d.get("foods") or []
    it = foods[0] if foods else None
    return _min(it.get("food_name") or it.get("item_name"), it.get("brand_name"), (it.get("photo") or {}).get("thumb"), "Nutritionix") if it else None


def _edamam(bc, k, f, t):
    d = f("https://api.edamam.com/api/food-database/v2/parser?upc=%s&app_id=%s&app_key=%s" % (bc, k["EDAMAM_APP_ID"], k["EDAMAM_APP_KEY"]), t) or {}
    h = d.get("hints") or []
    food = h[0].get("food") if h else None
    return _min(food.get("label"), food.get("brand"), food.get("image"), "Edamam") if food else None


def _icecat(bc, k, f, t):
    d = (f("https://live.icecat.biz/api?lang=IT&shopname=%s&GTIN=%s&content=essentialinfo" % (k["ICECAT_SHOP"], bc), t,
           {"api_token": k["ICECAT_API_TOKEN"]}) or {}).get("data")
    if not d:
        return None
    b = d.get("brand")
    return _min(d.get("title") or d.get("producttitle"), (b.get("name") or b.get("title")) if isinstance(b, dict) else b, "", "Icecat")


def _gs1(bc, k, f, t):
    d = f("%s/gtin/%s" % (k["GS1_API_URL"].rstrip("/"), bc), t, {"apikey": k["GS1_API_KEY"]}) or {}
    return _min(d.get("labelDescription") or d.get("shortDescription"), d.get("brandName"), "", "Verified by GS1")


# ---- altri database senza chiave (e libri/farmaci con chiave facoltativa), dal motore Apps Script ----
def _foodrepo(bc, k, f, t):
    d = f("https://www.foodrepo.org/api/v3/products?barcodes=" + bc, t, {"Accept": "application/json"}) or {}
    data = d.get("data") if isinstance(d.get("data"), list) else []
    if not data:
        return None
    p = data[0]; nt = p.get("name_translations") or {}
    nome = nt.get("it") or nt.get("en") or nt.get("de") or nt.get("fr") or p.get("name")
    dn = p.get("display_name_translations") or {}
    ing = (p.get("ingredients_translations") or {})
    im = ""
    try:
        im = p["images"][0]["categories"]["front"]["thumb"]
    except (KeyError, IndexError, TypeError):
        im = p.get("image_url") or ""
    return _min(nome, dn.get("it") or dn.get("en"), im, "FoodRepo", ing.get("it") or ing.get("en") or ing.get("de") or "")


def _opengtindb(bc, k, f, t):
    d = f("https://opengtindb.org/?ean=%s&cmd=query&queryid=%s" % (bc, k.get("OPENGTINDB_QUERYID") or "400000000"), t) or {}
    mappa = {}
    for riga in str(d.get("_testo", "")).splitlines():
        m = re.match(r"^([^=]+)=(.*)$", riga)
        if m:
            mappa[m.group(1).strip().lower()] = m.group(2).strip()
    return _min(mappa.get("name") or mappa.get("beschreibung"), mappa.get("brand") or mappa.get("hersteller"), "", "OpenGTINDB")


def _datakick(bc, k, f, t):
    for url, fonte in (("https://www.datakick.org/api/items/" + bc, "Datakick"), ("https://www.gtinsearch.org/api/products/" + bc, "gtinsearch")):
        d = f(url, t) or {}
        r = _min(d.get("name") or d.get("product_name"), d.get("brand_name") or d.get("brand"), "", fonte, d.get("ingredients") or "")
        if r:
            return r
    return None


def _openbeer(bc, k, f, t):
    d = f("https://open.beer/api/v1/beers?barcode=%s&limit=1" % bc, t)
    items = (d.get("data") or d.get("items")) if isinstance(d, dict) else d
    if not isinstance(items, list) or not items:
        return None
    b = items[0]
    br = b.get("brewery") or b.get("brand")
    if not br:
        try:
            br = b["relationships"]["brewery"]["data"]["name"]
        except (KeyError, TypeError):
            br = ""
    return _min(b.get("name") or b.get("title"), br, "", "Open Beer DB")


def _isbn(bc):
    return bc.startswith(("978", "979")) and len(bc) == 13


def _openlibrary(bc, k, f, t):
    if not _isbn(bc):
        return None
    b = (f("https://openlibrary.org/api/books?bibkeys=ISBN:%s&format=json&jscmd=data" % bc, t) or {}).get("ISBN:" + bc)
    if not b:
        return None
    autori = ", ".join(a.get("name", "") for a in b.get("authors") or [] if isinstance(a, dict))
    c = b.get("cover") or {}
    return _min(b.get("title"), autori, c.get("large") or c.get("medium") or c.get("small"), "OpenLibrary")


def _googlebooks(bc, k, f, t):
    if not _isbn(bc):
        return None
    chiave = ("&key=" + k["GOOGLE_BOOKS_KEY"]) if k.get("GOOGLE_BOOKS_KEY") else ""
    d = f("https://www.googleapis.com/books/v1/volumes?q=isbn:%s%s" % (bc, chiave), t) or {}
    it = d.get("items") or []
    if not it:
        return None
    vi = it[0].get("volumeInfo") or {}; im = vi.get("imageLinks") or {}
    return _min(vi.get("title"), ", ".join(vi.get("authors") or []), (im.get("thumbnail") or im.get("smallThumbnail") or "").replace("http:", "https:"), "Google Books")


def _openfda(bc, k, f, t):
    chiave = ("&api_key=" + k["OPENFDA_KEY"]) if k.get("OPENFDA_KEY") else ""
    for url in ('https://api.fda.gov/drug/ndc.json?search=product_ndc:"%s"&limit=1%s' % (bc, chiave),
                'https://api.fda.gov/drug/label.json?search=openfda.upc_code:"%s"&limit=1%s' % (bc, chiave)):
        res = ((f(url, t) or {}).get("results") or [None])[0]
        if not res:
            continue
        of = res.get("openfda") or {}
        nome = res.get("brand_name") or res.get("generic_name") or (of.get("brand_name") or [""])[0]
        marca = res.get("labeler_name") or (of.get("manufacturer_name") or [""])[0]
        ing = "; ".join(("%s %s" % (i.get("name", ""), i.get("strength", ""))).strip() for i in res.get("active_ingredients") or [] if isinstance(i, dict))
        r = _min(nome, marca, "", "OpenFDA", ing)
        if r:
            return r
    return None


# (chiavi necessarie, funzione): dopo i database aperti nell'ordine di priorita, come nel motore; senza chiavi richieste = sempre attivo
CON_CHIAVE = (((), _foodrepo), ((), _opengtindb), ((), _datakick), ((), _openbeer), ((), _openlibrary), ((), _googlebooks), ((), _openfda),
              (("BARCODELOOKUP_KEY",), _barcodelookup), (("UPCDATABASE_KEY",), _upcdatabase), (("GOUPC_TOKEN",), _goupc),
              (("SPOONACULAR_KEY",), _spoonacular), (("NUTRITIONIX_APP_ID", "NUTRITIONIX_APP_KEY"), _nutritionix),
              (("EDAMAM_APP_ID", "EDAMAM_APP_KEY"), _edamam), (("ICECAT_SHOP", "ICECAT_API_TOKEN"), _icecat),
              (("GS1_API_URL", "GS1_API_KEY"), _gs1))


def codice_da_cercare(barcode) -> str:
    """Codice da usare nelle ricerche online: GS1 (01 + GTIN-14) estratto, niente per i codici oltre 14 cifre."""
    bc = re.sub(r"\D", "", str(barcode))
    if len(bc) == 16 and bc.startswith("01"):
        bc = bc[2:]
    return bc.lstrip("0") if 0 < len(bc) <= 14 else ""


def cerca(barcode: str, fetch: Callable = fetch_http, providers=PROVIDERS, timeout_totale: float = TIMEOUT_TOTALE,
          chiavi: Optional[Dict[str, str]] = None) -> Optional[dict]:
    """Interroga tutti i provider insieme e restituisce il primo risultato utile, rispettando l'ordine di priorita
    se piu provider rispondono entro il tempo massimo."""
    bc = re.sub(r"\D", "", str(barcode))
    if not bc:
        return None
    if len(bc) == 16 and bc.startswith("01"):   # GS1: identificativo 01 + GTIN-14 (es. QR dei prodotti sportivi)
        bc = bc[2:]
    if len(bc) > 14:   # oltre un GTIN: nessun archivio lo conosce, inutile interrogare la rete
        return None
    risultati: Dict[int, Optional[dict]] = {}
    chiavi = {k: v for k, v in (chiavi or {}).items() if v}
    lavori = [(lambda f=f, h=h: _un_provider(bc, f, h, fetch, timeout_totale)) for f, h in providers]
    for needs, fn in CON_CHIAVE:   # solo i provider di cui c'e la chiave
        if all(n in chiavi for n in needs):
            lavori.append(lambda fn=fn: fn(bc, chiavi, fetch, timeout_totale))
    ex = ThreadPoolExecutor(max_workers=len(lavori))
    try:
        fut = {ex.submit(w): i for i, w in enumerate(lavori)}
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
