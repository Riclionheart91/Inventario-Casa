import os, sys, time, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import lookup
from app.service import ApiError
from test_service import make

OFF = {"status": 1, "product": {"product_name": "NUTELLA", "product_name_it": "", "brands": "Ferrero", "quantity": "450 g",
       "image_front_url": "http://img/x.jpg", "ingredients_text_it": "zucchero, olio di palma",
       "nutriments": {"energy-kcal_100g": 539, "fat_100g": 30.9, "sugars_100g": 56.3, "salt_100g": 0.107},
       "nutriscore_grade": "e", "nova_group": 4}}


class L(unittest.TestCase):
    def test_pulisci_nome(self):
        self.assertEqual(lookup.pulisci_nome("NUTELLA FERRERO", "Ferrero"), "Nutella")
        self.assertEqual(lookup.pulisci_nome("latte uht intero"), "Latte Uht Intero")
        self.assertEqual(lookup.pulisci_nome("Pasta Barilla  spaghetti", "Barilla"), "Pasta spaghetti")

    def test_normalizza(self):
        r = lookup.normalizza(OFF["product"], "Open Food Facts")
        self.assertEqual((r["nome"], r["marca"], r["confezione"]), ("Nutella", "Ferrero", "450 g"))
        self.assertIn("539 kcal", r["nutrizione"]); self.assertIn("Nutri E", r["punteggi"])
        self.assertIsNone(r["categoria_suggerita"])
        self.assertIsNone(lookup.normalizza({"product_name": ""}, "x"))

    def test_cascata_prende_il_primo_utile_in_ordine_di_priorita(self):
        def fetch(url, t):
            if "openfoodfacts" in url:
                time.sleep(0.2); return OFF
            if "openbeautyfacts" in url:
                return {"status": 1, "product": {"product_name": "Altro", "brands": "X"}}
            return {"status": 0}
        r = lookup.cerca("3017620422003", fetch=fetch)
        self.assertEqual(r["fonte"], "Open Food Facts")   # vince il provider piu prioritario anche se piu lento

    def test_nessun_risultato_e_provider_che_falliscono(self):
        self.assertIsNone(lookup.cerca("1", fetch=lambda u, t: {"status": 0}))
        self.assertIsNone(lookup.cerca("1", fetch=lambda u, t: None))
        def boom(u, t): raise RuntimeError("rete")
        self.assertIsNone(lookup.cerca("1", fetch=boom))
        self.assertIsNone(lookup.cerca("abc", fetch=boom))

    def test_tempo_massimo(self):
        t0 = time.time()
        r = lookup.cerca("1", fetch=lambda u, t: time.sleep(2) or OFF, timeout_totale=0.3)
        self.assertIsNone(r); self.assertLess(time.time() - t0, 1.5)


class P(unittest.TestCase):
    def test_crea_prodotto(self):
        st, inv, _ = make()
        r = inv.crea_prodotto("0008004613310367", "Crema", marca="Ferrero", categoria="Dispensa", sottocategoria="Snack e Dolci",
                              tipo="Crema spalmabile", nutrizione="x", fonte="Open Food Facts")
        self.assertEqual(r["barcode"], 8004613310367)
        p = inv.prodotto("8004613310367")
        self.assertEqual((p["prodotto"], p["categoria"], p["sottocategoria"], p["tipo"]), ("Crema", "Dispensa", "Snack e Dolci", "Crema spalmabile"))
        h = st.sheets["prodotti"][0]; row = dict(zip(h, st.sheets["prodotti"][-1]))
        self.assertEqual(row["API Status"], "✅ App (Open Food Facts)")
        self.assertRegex(row["Aggiornato il"], r"^\d\d/\d\d/\d{4}$")
        self.assertIn("Crema spalmabile", inv.tipi())                  # il tipo nuovo entra in ai_tipi
        ai = st.sheets["ai_tipi"]; riga = dict(zip(ai[0], ai[-1]))
        self.assertEqual(riga["Stato"], "DA_APPROVARE")   # tipo nuovo: sempre in coda Approvazioni
        self.assertEqual(riga["Scorta_min"], 0)           # scorta minima 0 finche non la definisci
        self.assertFalse([r for r in st.sheets["ai_prodotti"][1:] if "Crema" in str(r)])   # nessuna proposta registrata
        self.assertEqual(inv.movimento("8004613310367", "Carico", "Casa", 2)["noto"], True)

    def test_crea_prodotto_validazioni(self):
        _, inv, _ = make()
        for kw in ({"barcode": "abc", "nome": "x"}, {"barcode": "1", "nome": ""},
                   {"barcode": "8002795002995", "nome": "x", "categoria": "Dispensa", "sottocategoria": "Bevande"},   # gia presente
                   {"barcode": "1", "nome": "x", "categoria": "Inesistente", "sottocategoria": "Bevande"},
                   {"barcode": "1", "nome": "x", "categoria": "Dispensa", "sottocategoria": "Latticini"}):
            with self.assertRaises(ApiError):
                inv.crea_prodotto(**kw)


class K(unittest.TestCase):
    def test_provider_a_chiave_solo_se_c_e_la_chiave(self):
        visti = []
        def fetch(u, t, h=None):
            visti.append(u)
            if "barcodelookup" in u:
                return {"products": [{"product_name": "Biscotti Frollini", "brand": "Mulino", "images": ["http://i/1.jpg"]}]}
            if "go-upc" in u:
                return {"product": {"name": "Altro", "brand": "Z"}}
            return {"status": 0}
        self.assertIsNone(lookup.cerca("123456", fetch=fetch))
        self.assertFalse([u for u in visti if "barcodelookup" in u or "go-upc" in u])
        r = lookup.cerca("123456", fetch=fetch, chiavi={"BARCODELOOKUP_KEY": "k1", "GOUPC_TOKEN": "t"})
        self.assertEqual((r["nome"], r["marca"], r["fonte"]), ("Biscotti Frollini", "Mulino", "BarcodeLookup"))   # vince il piu prioritario

    def test_altri_database_senza_chiave(self):
        def fetch(u, t, h=None):
            if "foodrepo" in u:
                return {"data": [{"name_translations": {"it": "Muesli croccante"}, "display_name_translations": {"it": "Vallée"}}]}
            if "opengtindb" in u:
                return {"_testo": "error=0\nname=Pasta fresca\nhersteller=Bio\n"}
            if "open.beer" in u:
                return {"data": [{"name": "Bionda", "brewery": "Birrificio X"}]}
            if "openlibrary" in u:
                return {"ISBN:9788804668237": {"title": "Un libro", "authors": [{"name": "A. Autore"}]}}
            if "googleapis" in u:
                return {"items": [{"volumeInfo": {"title": "Altro libro", "authors": ["B"], "imageLinks": {"thumbnail": "http://i/x.jpg"}}}]}
            if "api.fda.gov" in u:
                return {"results": [{"brand_name": "Aspirina", "labeler_name": "Bayer", "active_ingredients": [{"name": "ASA", "strength": "500 mg"}]}]}
            return {"status": 0}
        r = lookup.cerca("123456", fetch=fetch)
        self.assertEqual((r["nome"], r["marca"], r["fonte"]), ("Muesli croccante", "Vallée", "FoodRepo"))
        for nome, f in (("opengtindb", lookup._opengtindb), ("beer", lookup._openbeer), ("books", lookup._openlibrary), ("g", lookup._googlebooks), ("fda", lookup._openfda)):
            r = f("9788804668237", {"GOOGLE_BOOKS_KEY": "kk"}, fetch, 1)
            self.assertTrue(r and r["nome"], nome)
        self.assertEqual(lookup._googlebooks("9788804668237", {}, fetch, 1)["immagine"], "https://i/x.jpg")
        self.assertIsNone(lookup._openlibrary("8002795002995", {}, fetch, 1))   # non e un ISBN
        self.assertEqual(lookup._opengtindb("1", {}, fetch, 1)["nome"], "Pasta fresca")

    def test_chiavi_facoltative_nell_url_ma_non_obbligatorie(self):
        visti = []
        def fetch(u, t, h=None):
            visti.append(u); return {}
        lookup._openfda("1", {"OPENFDA_KEY": "seg"}, fetch, 1); lookup._googlebooks("9788804668237", {"GOOGLE_BOOKS_KEY": "seg"}, fetch, 1)
        self.assertTrue(all("seg" in u for u in visti))
        visti.clear(); lookup._openfda("1", {}, fetch, 1)
        self.assertTrue(visti and not any("api_key" in u for u in visti))

    def test_provider_a_chiave_con_intestazioni_e_chiavi_doppie(self):
        viste = {}
        def fetch(u, t, h=None):
            viste[u.split("/")[2]] = h
            return {"foods": [{"food_name": "yogurt greco", "brand_name": "Fage"}]} if "nutritionix" in u else {"status": 0}
        self.assertIsNone(lookup.cerca("9", fetch=fetch, chiavi={"NUTRITIONIX_APP_ID": "a"}))   # manca la seconda chiave: saltato
        r = lookup.cerca("9", fetch=fetch, chiavi={"NUTRITIONIX_APP_ID": "a", "NUTRITIONIX_APP_KEY": "b"})
        self.assertEqual(r["fonte"], "Nutritionix"); self.assertEqual(viste["trackapi.nutritionix.com"], {"x-app-id": "a", "x-app-key": "b"})


if __name__ == "__main__":
    unittest.main()


class TestNomiEErrori(unittest.TestCase):
    def test_nome_da_lingua_straniera(self):
        r = lookup.normalizza({"product_name_fr": "Yaourt nature", "brands": "Jaouda"}, "OFF")
        self.assertEqual(r["nome"], "Yaourt nature")

    def test_senza_nome_ma_con_marca(self):
        r = lookup.normalizza({"brands": "Milky Food"}, "OFF")
        self.assertEqual(r["marca"], "Milky Food")
        self.assertEqual(r["nome"], "")

    def test_nulla_di_utile(self):
        self.assertIsNone(lookup.normalizza({}, "OFF"))


class TCodiciLunghi(unittest.TestCase):
    def test_gs1_01_e_oltre_gtin(self):
        from app import lookup
        visti = []
        def fetch(url, *a, **k):
            visti.append(url)
            return None
        self.assertIsNone(lookup.cerca("066400240330063025051", fetch=fetch))
        self.assertEqual(visti, [])
        lookup.cerca("0180232793411114", fetch=fetch)
        self.assertTrue(visti and all("0180232793411114" not in u for u in visti))
