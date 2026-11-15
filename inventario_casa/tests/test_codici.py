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

    def test_nuovo_salta_i_codici_gia_usati_e_non_torna_indietro(self):
        primo = self.c.nuovo("Marmellata")["codice"]
        secondo_atteso = C.da_contatore(2)
        v = self.c.nuovo("Pane", usati=[secondo_atteso.lstrip("0")])     # il 2 e gia nel foglio: si salta
        self.assertEqual(v["codice"], C.da_contatore(3)); self.assertNotEqual(v["codice"], primo)
        c2 = C.MieiCodici(self.c.percorso)                               # anche dopo un riavvio
        self.assertEqual(c2.nuovo()["codice"], C.da_contatore(4))
        self.assertEqual(len(c2.elenco()), 3)

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
