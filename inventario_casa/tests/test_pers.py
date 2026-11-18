"""I codici PERS non lasciano mai il foglio: niente archivi online, niente Open Food Facts, niente ricerca web."""
import unittest

from app import ai, lookup, off, pagina, ricerca
from app.service import bco, nbc


class TestPers(unittest.TestCase):
    def test_normalizzazione(self):
        self.assertEqual(nbc("pers482915307"), "PERS482915307")
        self.assertEqual(bco("PERS482915307"), "PERS482915307")
        self.assertEqual(nbc("8002795002995"), "8002795002995")
        self.assertEqual(bco("0012345"), 12345)

    def test_nessuna_ricerca_online(self):
        chiamate = []
        self.assertEqual(lookup.codice_da_cercare("PERS482915307"), "")
        self.assertIsNone(lookup.cerca("PERS482915307", fetch=lambda *a, **k: chiamate.append(a)))
        self.assertEqual(chiamate, [])
        self.assertEqual(off.valido_per_off("PERS482915307"), "")

    def test_nessuna_ricerca_ai_o_web(self):
        def post(*a, **k):
            raise AssertionError("l'AI non deve cercare un codice PERS")
        self.assertIsNone(ai.cerca_web("PERS482915307", "chiave", post=post))
        self.assertIsNone(ai.integra_scheda("PERS482915307", "Marmellata", "", "", "chiave", post=post))
        self.assertIsNone(pagina.immagine_da_pagina("http://x", "PERS482915307", scarica_fn=lambda u: "<html>482915307</html>"))
        self.assertEqual(ricerca.estratto("<p>482915307</p>", "PERS482915307"), ricerca.estratto("<p>482915307</p>", ""))


if __name__ == "__main__":
    unittest.main()


class TestNbcAi(unittest.TestCase):
    def test_nbc_ai_conserva_pers(self):
        from app import ai
        self.assertEqual(ai.nbc_("pers482915307"), "PERS482915307")
        self.assertEqual(ai.nbc_("0012345"), "12345")


class TestWebapp(unittest.TestCase):
    def test_installabile_anche_dalla_pagina_di_accesso(self):
        import json, os
        from app import accesso
        self.assertIn("/apple-touch-icon.png", accesso.PUBBLICI)
        self.assertIn("manifest.json", accesso.PAGINA); self.assertIn("apple-touch-icon", accesso.PAGINA)
        self.assertIn(b"manifest-src 'self'", accesso.CSP[1])
        st = os.path.join(os.path.dirname(accesso.__file__), "static")
        self.assertTrue(os.path.exists(os.path.join(st, "apple-touch-icon.png")))
        m = json.load(open(os.path.join(st, "manifest.json")))
        self.assertEqual(m["display"], "standalone"); self.assertTrue(m["id"])
