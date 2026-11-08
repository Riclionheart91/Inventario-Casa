import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.confronti import Confronti, da_off
from app.off import Off
from app.service import Inventory
from app.store import MemoryStore

PROD = {"code": "8002795002995", "product_name_it": "Latte intero fresco", "brands": "Granarolo,Altro", "quantity": "1 l",
        "ingredients_text_it": "", "nutriments": {"energy-kcal_100g": 64, "fat_100g": 3.6}, "image_front_url": ""}


def sheet():
    return Inventory(MemoryStore({
        "prodotti": [["Barcode", "Prodotto", "Marca", "Confezione", "Categoria", "Sottocategoria", "Tipo", "Immagine", "Composizione", "Nutrizione (100g)"],
                     [8002795002995, "Latte UHT", "", "", "Dispensa", "Bevande", "Latte", "", "", ""]],
        "categorie": [["Categoria", "Sottocategoria"], ["Dispensa", "Bevande"]],
        "movimenti": [["ID_Movimento", "Barcode", "Tipo", "Location", "Quantità", "Prodotto"], ["a", 8002795002995, "Carico", "Casa", 1, "Latte UHT"]],
        "log_ai": [["Quando", "Barcode", "Campo", "Prima", "Dopo", "Fonte", "Confidenza", "Modo", "Annullato"]]}))


class Finto:
    def __init__(self, prod=PROD):
        self.prod, self.chiamate = prod, []

    def __call__(self, metodo, url, campi=None, file=None, agent="", timeout=0):
        self.chiamate.append((metodo, url, campi, file))
        if "/api/v2/product/" in url:
            return 200, {"status": 1, "product": self.prod}
        if url.endswith("product_jqm2.pl"):
            return 200, {"status": 1}
        if url.endswith("product_image_upload.pl"):
            return 200, {"status": "status ok"}
        return 500, None


def crea(h=None, arr=None):
    d = tempfile.mkdtemp(); i = sheet(); h = h or Finto()
    o = Off(i, "u", "pw", percorso=os.path.join(d, "s.json"), cartella=os.path.join(d, "f"), http=h, pausa=0, dati_percorso=os.path.join(d, "d.json"), arricchisci=arr)
    o._imposta("8002795002995", "presente", "food")
    return Confronti(o, i, percorso=os.path.join(d, "c.json"), pausa=0), o, i, h


class TConfronti(unittest.TestCase):
    def test_normalizza_off(self):
        o = da_off(PROD)
        self.assertEqual((o["nome"], o["marca"], o["confezione"], o["n"]["energia_kcal"]), ("Latte intero fresco", "Granarolo", "1 l", "64"))
        self.assertIn("🔥 64 kcal", o["nutrizione"])

    def test_scansione_propone_le_differenze(self):
        c, o, i, h = crea()
        self.assertEqual(c.scansiona(), 1)
        el = c.elenco()
        self.assertEqual(len(el), 1)
        v = {x["campo"]: x for x in el[0]["voci"]}
        self.assertEqual(v["nome"]["suggerita"], "nessuna")          # nomi diversi: decide l'utente
        self.assertEqual(v["marca"]["suggerita"], "foglio")          # il foglio e vuoto, OFF ha la marca
        self.assertEqual(v["nutrizione"]["azioni"], ["foglio", "nessuna"])
        self.assertNotIn("off", v["nome"]["azioni"])                 # mai sovrascrivere il nome di OFF
        self.assertEqual(c.scansiona(), 0)                           # una volta sola

    def test_applica_scrive_il_foglio_solo_per_le_voci_scelte(self):
        c, o, i, h = crea(); c.scansiona()
        esiti = c.applica("8002795002995", {"marca": "foglio", "confezione": "foglio", "nome": "nessuna", "nutrizione": "foglio"})
        self.assertTrue(all(e["ok"] for e in esiti), esiti)
        prod = [p for p in i.elenco_prodotti() if str(p["barcode"]) == "8002795002995"][0]
        self.assertEqual(prod["nome"], "Latte UHT")        # il nome non e stato toccato
        r = i._dicts("prodotti", True)[0]
        self.assertEqual((r["Marca"], r["Confezione"]), ("Granarolo", "1 l"))
        self.assertIn("64 kcal", r["Nutrizione (100g)"])
        self.assertTrue(any(x["Fonte"] == "OPEN FOOD FACTS" for x in i._dicts("log_ai", True)))
        self.assertFalse(any(x["campo"] == "marca" for x in c.elenco()[0]["voci"]) if c.elenco() else False)

    def test_nome_di_off_nel_foglio_aggiorna_anche_i_movimenti(self):
        c, o, i, h = crea(); c.scansiona()
        c.applica("8002795002995", {"nome": "foglio"})
        self.assertEqual(i._dicts("prodotti", True)[0]["Prodotto"], "Latte intero fresco")
        self.assertEqual(i._dicts("movimenti", True)[0]["Prodotto"], "Latte intero fresco")

    def test_verso_off_solo_campi_vuoti_su_off(self):
        prod = dict(PROD, ingredients_text_it="", brands="", quantity="1 l")
        c, o, i, h = crea(Finto(prod), arr=lambda p: {"ingredienti": "Latte", "marca": "Granarolo", "n_energia_kcal": "64", "n_grassi": "3.6", "n_proteine": "3", "n_sale": "0.1", "fonte": "web"})
        c.scansiona()
        v = {x["campo"]: x for x in c.elenco()[0]["voci"]}
        self.assertIn("off", v["marca"]["azioni"]); self.assertIn("off", v["ingredienti"]["azioni"]); self.assertNotIn("off", v["confezione"]["azioni"])
        c.applica("8002795002995", {"marca": "off", "ingredienti": "off"})
        inv_ = [x for x in h.chiamate if x[1].endswith("product_jqm2.pl")][0][2]
        self.assertEqual((inv_["brands"], inv_["ingredients_text"]), ("Granarolo", "Latte"))
        self.assertNotIn("quantity", inv_); self.assertNotIn("product_name", inv_)   # niente che non sia stato scelto
        self.assertNotIn("pw", str(c.elenco()))

    def test_ignora_e_senza_credenziali(self):
        c, o, i, h = crea(); c.scansiona()
        c.ignora("8002795002995")
        self.assertEqual(c.elenco(), [])
        c2, o2, i2, h2 = crea(arr=lambda p: {"ingredienti": "Latte"}); o2.utente = ""
        c2.scansiona()
        v = {x["campo"]: x for x in c2.elenco()[0]["voci"]}
        if "ingredienti" in v and "off" in v["ingredienti"]["azioni"]:
            e = c2.applica("8002795002995", {"ingredienti": "off"})
            self.assertFalse(e[0]["ok"])


if __name__ == "__main__":
    unittest.main()
