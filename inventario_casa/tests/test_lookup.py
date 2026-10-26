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
        ai = st.sheets["ai_tipi"]; self.assertEqual(dict(zip(ai[0], ai[-1]))["Stato"], "DA_APPROVARE")
        self.assertEqual(inv.movimento("8004613310367", "Carico", "Casa", 2)["noto"], True)

    def test_crea_prodotto_validazioni(self):
        _, inv, _ = make()
        for kw in ({"barcode": "abc", "nome": "x"}, {"barcode": "1", "nome": ""},
                   {"barcode": "8002795002995", "nome": "x", "categoria": "Dispensa", "sottocategoria": "Bevande"},   # gia presente
                   {"barcode": "1", "nome": "x", "categoria": "Inesistente", "sottocategoria": "Bevande"},
                   {"barcode": "1", "nome": "x", "categoria": "Dispensa", "sottocategoria": "Latticini"}):
            with self.assertRaises(ApiError):
                inv.crea_prodotto(**kw)


if __name__ == "__main__":
    unittest.main()
