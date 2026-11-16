import os
import tempfile
import unittest

from app import codici as C


class TCodici(unittest.TestCase):
    def setUp(self):
        self.c = C.MieiCodici(os.path.join(tempfile.mkdtemp(), "m.json"))

    def test_cifra_di_controllo_ean13(self):
        self.assertEqual(C.cifra_controllo("400638133393"), "1")      # EAN-13 noto 4006381333931
        self.assertTrue(C.ean13_valido("4006381333931")); self.assertFalse(C.ean13_valido("4006381333932"))

    def test_codici_validi_nel_proprio_intervallo(self):
        for i in (1, 2, 999, 123456):
            c = C.da_contatore(i)
            self.assertTrue(C.e_mio(c), c); self.assertEqual(len(c), 13); self.assertTrue(c.startswith("2999"))

    def test_mai_ripetuti(self):
        visti = set()
        for i in range(1, 20000):
            visti.add(C.da_contatore(i))
        self.assertEqual(len(visti), 19999)

    def test_nuovo_formato_pers_casuale_e_mai_ripetuto(self):
        import re
        visti = set()
        for _ in range(300):
            c = self.c.nuovo("x")["codice"]
            self.assertRegex(c, r"^PERS\d{9}$"); self.assertTrue(C.e_mio(c)); self.assertTrue(C.e_pers(c)); visti.add(c)
        self.assertEqual(len(visti), 300)
        # quelli gia nel foglio si saltano; quelli tolti dall'elenco non tornano
        c2 = C.MieiCodici(self.c.percorso)
        self.assertEqual(len(c2.elenco()), 300)
        primo = c2.elenco()[0]["codice"]
        self.assertTrue(c2.elimina(primo))
        self.assertIn(primo, c2._carica()["emessi"])

    def test_salta_i_codici_usati(self):
        import unittest.mock as M
        with M.patch("app.codici.secrets.randbelow", side_effect=[5, 5, 6]):
            self.assertEqual(self.c.nuovo("a", usati=["PERS000000005"])["codice"], "PERS000000006")

    def test_riconoscimento(self):
        self.assertTrue(C.e_mio("pers123456789")); self.assertTrue(C.e_mio(C.da_contatore(1)))
        for x in ("PERS12345678", "PERS1234567890", "8002795002995", "XPERS123456789", ""):
            self.assertFalse(C.e_mio(x), x)

    def test_rinomina(self):
        v = self.c.nuovo("Sugo")
        self.assertTrue(self.c.rinomina(v["codice"], "Sugo di nonna")); self.assertEqual(self.c.elenco()[0]["nome"], "Sugo di nonna")
        self.assertFalse(self.c.rinomina("1", "x"))


if __name__ == "__main__":
    unittest.main()


class TestElimina(unittest.TestCase):
    def test_elimina_non_riusa(self):
        with tempfile.TemporaryDirectory() as d:
            m = C.MieiCodici(os.path.join(d, "m.json"))
            a = m.nuovo("A")["codice"]
            self.assertTrue(m.elimina(a))
            self.assertFalse(m.elimina(a))
            self.assertEqual(m.elenco(), [])
            self.assertNotEqual(m.nuovo("B")["codice"], a)
