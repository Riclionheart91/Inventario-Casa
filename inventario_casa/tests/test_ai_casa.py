import unittest

from app import ai
from app.service import ApiError, Inventory
from app.store import MemoryStore

RISP = """Ecco le stime.
```json
{"ingredienti": "albicocche, zucchero", "allergeni": [], "energia_kcal": 250, "grassi_g": 0.2, "zuccheri_g": 60, "sale_g": 0, "proteine_g": 0.5,
 "carboidrati_g": 62, "fibre_g": 1.5, "conservazione": "in luogo fresco", "durata": "12 mesi chiuso", "note": "porzione 20 g | molto dolce"}
```"""


class TestAiCasa(unittest.TestCase):
    def test_prompt(self):
        p = ai.prompt_casa({"nome": "Marmellata di albicocche", "categoria": "Dispensa", "composizione": "🧪 Ingredienti: albicocche"})
        self.assertIn("Marmellata di albicocche", p); self.assertIn("albicocche", p); self.assertIn("```json", p)

    def test_scheda_da_risposta(self):
        s = ai.scheda_da_risposta(RISP)
        self.assertEqual(s["composizione"], "🧪 Ingredienti: albicocche, zucchero")
        self.assertIn("🔥 250 kcal", s["nutrizione"]); self.assertIn("🍬 60 g zuccheri", s["nutrizione"]); self.assertNotIn("None", s["nutrizione"])
        self.assertTrue(s["dettagli"].startswith("🤖 Stime indicative")); self.assertNotIn("porzione 20 g |", s["dettagli"])   # il | si toglie: separa le voci
        self.assertIsNone(ai.scheda_da_risposta("niente blocco")); self.assertIsNone(ai.scheda_da_risposta("```json\n{rotto\n```"))
        self.assertIsNone(ai.scheda_da_risposta('```json\n{"energia_kcal": -5}\n```'))

    def test_chat(self):
        visti = []

        def post(url, chiave, corpo, timeout):
            visti.append(corpo)
            return {"candidates": [{"content": {"parts": [{"text": "ciao"}]}}]}
        r = ai.chat_casa([{"ruolo": "utente", "testo": "x"}, {"ruolo": "ai", "testo": "y"}, {"ruolo": "utente", "testo": "z"}], "k", post=post)
        self.assertEqual(r, "ciao")
        self.assertEqual([c["role"] for c in visti[0]["contents"]], ["user", "model", "user"])
        self.assertIsNone(ai.chat_casa([{"ruolo": "utente", "testo": "x"}], "", post=post))
        self.assertIsNone(ai.chat_casa([{"ruolo": "utente", "testo": "x"}], "k", post=lambda *a: None))

    def test_imposta_info(self):
        st = MemoryStore({"prodotti": [["Barcode", "Prodotto", "Composizione", "Nutrizione (100g)", "Dettagli prodotto", "Aggiornato il"],
                                       ["PERS482915307", "Marmellata", "", "", "", ""]]})
        inv = Inventory(st, ttl=20)
        inv.imposta_info("pers482915307", "albicocche, zucchero", "🔥 250 kcal", None)
        r = st.sheets["prodotti"][1]
        self.assertEqual(r[2], "🧪 Ingredienti: albicocche, zucchero"); self.assertEqual(r[3], "🔥 250 kcal"); self.assertEqual(r[4], ""); self.assertTrue(r[5])
        inv.imposta_info("PERS482915307", "", None, "nota")
        self.assertEqual(st.sheets["prodotti"][1][2], ""); self.assertEqual(st.sheets["prodotti"][1][4], "nota")
        with self.assertRaises(ApiError):
            inv.imposta_info("PERS000000000", "x")


if __name__ == "__main__":
    unittest.main()
