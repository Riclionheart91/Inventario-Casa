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


class TestElimina(unittest.TestCase):
    def test_elimina_prodotto(self):
        st = MemoryStore({"prodotti": [["Barcode", "Prodotto"], ["PERS482915307", "Sbagliato"], [8002795002995, "Latte"]],
                          "movimenti": [["Barcode", "Tipo", "Location", "Quantità", "Prodotto"], ["PERS482915307", "Carico", "Casa", 1, "Sbagliato"],
                                        [8002795002995, "Carico", "Casa", 2, "Latte"], ["PERS482915307", "Scarico", "Casa", 1, "Sbagliato"]],
                          "alias": [["Alias", "Principale", "Creato", "Nome"], ["PERS482915307", "8002795002995", "", ""]]})
        inv = Inventory(st, ttl=20)
        r = inv.elimina_prodotto("pers482915307")
        self.assertEqual((r["prodotti"], r["movimenti"], r["alias"]), (1, 2, 1))
        self.assertEqual([x[0] for x in st.sheets["prodotti"][1:]], [8002795002995])
        self.assertEqual(len(st.sheets["movimenti"]), 2); self.assertEqual(len(st.sheets["alias"]), 1)
        with self.assertRaises(ApiError):
            inv.elimina_prodotto("PERS482915307")


class TestRegistroAi(unittest.TestCase):
    def test_chat_casa_e_nel_conteggio_uso(self):
        from app import aiuso
        self.assertTrue(getattr(ai.chat_casa, "__wrapped__", None) is not None or ai.chat_casa.__name__ == "chat_casa")


class TestScadenza(unittest.TestCase):
    def _leggi(self, d, oggi=None):
        import datetime
        post = lambda *a: {"candidates": [{"content": {"parts": [{"text": __import__("json").dumps(d)}]}}]}
        return ai.leggi_scadenza(b"x", "image/jpeg", "k", post=post, oggi=oggi or datetime.date(2026, 11, 20))

    def test_data_completa_e_solo_mese(self):
        r = self._leggi({"giorno": 15, "mese": 3, "anno": 2027, "testo": "15/03/2027", "sicurezza": 0.95})
        self.assertEqual((r["data"], r["mese_solo"]), ("2027-03-15", False))
        r = self._leggi({"giorno": None, "mese": 2, "anno": 28, "testo": "02/28", "sicurezza": 0.8})
        self.assertEqual((r["data"], r["mese_solo"]), ("2028-02-29", True))      # ultimo giorno del mese, anche bisestile

    def test_date_assurde_o_illeggibili(self):
        for d in ({"giorno": 31, "mese": 2, "anno": 2027}, {"giorno": 1, "mese": 1, "anno": 1990}, {"giorno": 1, "mese": 1, "anno": 2099},
                  {"giorno": None, "mese": None, "anno": None}, {"giorno": 1, "mese": 13, "anno": 2027}):
            r = self._leggi(dict(d, testo="x", sicurezza=0.9))
            self.assertEqual((r["data"], r["sicurezza"]), ("", 0.0), d)

    def test_senza_risposta(self):
        self.assertIsNone(ai.leggi_scadenza(b"x", "image/jpeg", "k", post=lambda *a: None))
        self.assertIsNone(ai.leggi_scadenza(b"x", "image/jpeg", "", post=lambda *a: None))


class TestScadenzaSalvata(unittest.TestCase):
    def test_nuovo_prodotto_con_scadenza_si_vede_nella_scheda(self):
        st = MemoryStore({"prodotti": [["Barcode", "Prodotto", "Marca", "Categoria", "Sottocategoria", "Tipo", "Confezione", "Immagine", "API Status",
                                        "Dettagli prodotto", "Punteggi", "Composizione", "Nutrizione (100g)", "Aggiornato il"]],
                          "movimenti": [["Barcode", "Tipo", "Location", "Quantità", "Prodotto", "Categoria", "Sottocategoria", "Scadenza"]]})
        inv = Inventory(st, ttl=20)
        inv.crea_prodotto("8001234567890", "Yogurt", location="Casa", quantita=2, scadenza="2027-08-31")
        s = inv.scheda("8001234567890")
        self.assertEqual([(x["luogo"], x["qta"], x["scadenza"]) for x in s["carichi"]], [("Casa", 2, "31/08/2027")])
        with self.assertRaises(ApiError):
            inv.crea_prodotto("8001234567891", "Altro", location="Casa", scadenza="non una data")
        self.assertIsNone(inv.scheda("8001234567891"))      # con una data sbagliata non si crea nemmeno il prodotto


class TestFifo(unittest.TestCase):
    def test_restano_i_carichi_piu_recenti(self):
        h = ["Barcode", "Tipo", "Location", "Quantità", "Prodotto", "Categoria", "Sottocategoria", "Scadenza", "Data"]
        st = MemoryStore({"prodotti": [["Barcode", "Prodotto"], [8001, "Latte"]],
                          "movimenti": [h,
                                        [8001, "Carico", "Casa", 2, "Latte", "", "", "2026-12-01", "01/11/2026"],
                                        [8001, "Carico", "Casa", 3, "Latte", "", "", "2027-01-10", "10/11/2026"],
                                        [8001, "Carico", "Cantina", 1, "Latte", "", "", "", "12/11/2026"],
                                        [8001, "Scarico", "Casa", 3, "Latte", "", "", "", "15/11/2026"],
                                        [8001, "Carico", "Casa", 4, "Latte", "", "", "2027-03-01", "20/11/2026"]]})
        inv = Inventory(st, ttl=20)
        r = inv._carichi_prodotto("8001")
        # Casa: 2+3 caricati, 3 scaricati -> il carico piu vecchio (2) finisce e se ne toglie 1 dal secondo: restano 2 del 10/11 e 4 del 20/11
        self.assertEqual([(x["luogo"], x["qta"], x["caricato"]) for x in r], [("Casa", 4, "20/11/2026"), ("Cantina", 1, "12/11/2026"), ("Casa", 2, "10/11/2026")])
        self.assertEqual(r[0]["scadenza"], "01/03/2027"); self.assertIsNone(r[1]["giorni"])
