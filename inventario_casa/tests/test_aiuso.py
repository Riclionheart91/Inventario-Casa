import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import ai, aiuso
from tests.test_fase4 import make


class TAiUso(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); os.environ["DATA_DIR"] = self.d; aiuso.ATTIVO = True

    def tearDown(self):
        aiuso.ATTIVO = False; os.environ.pop("DATA_DIR", None); ai.regole_provider = None

    def test_memoria_e_conteggio(self):
        n = [0]

        @aiuso.registra("prova", True)
        def f(testo, chiave="", modello="", riserva="", post=None):
            n[0] += 1
            return {"x": testo}
        self.assertEqual(f("a", "K"), {"x": "a"}); self.assertEqual(f("a", "ALTRA"), {"x": "a"}); f("b", "K")
        self.assertEqual(n[0], 2)   # la seconda richiesta uguale arriva dalla memoria, anche con chiave diversa
        r = aiuso.riepilogo(7)
        c = r["compiti"][0]
        self.assertEqual((c["richieste"], c["dalla_memoria"], c["errori"]), (3, 1, 0)); self.assertEqual(r["memoria"], 2)

    def test_risposta_vuota_non_va_in_memoria_e_conta_errore(self):
        n = [0]

        @aiuso.registra("prova", True)
        def f(testo, chiave=""):
            n[0] += 1
            return None
        f("a"); f("a")
        self.assertEqual(n[0], 2)
        self.assertEqual(aiuso.riepilogo()["compiti"][0]["errori"], 2)

    def test_regole_cambiano_la_chiave(self):
        n = [0]
        r = [""]

        @aiuso.registra("prova", True, extra=lambda: r[0])
        def f(testo):
            n[0] += 1
            return "ok"
        f("a"); r[0] = "nuova regola"; f("a")
        self.assertEqual(n[0], 2)

    def test_spento_nei_test(self):
        aiuso.ATTIVO = False
        n = [0]

        @aiuso.registra("prova", True)
        def f(t):
            n[0] += 1
            return "ok"
        f("a"); f("a")
        self.assertEqual(n[0], 2)

    def test_esiti(self):
        aiuso.esito("P", "APPROVA"); aiuso.esito("P", "APPROVA", True); aiuso.esito("P", "RIFIUTA")
        self.assertEqual(aiuso.riepilogo()["esiti"]["P"], {"approvate": 1, "corrette": 1, "rifiutate": 1})


class TRegole(unittest.TestCase):
    def test_aggiungi_elenca_elimina(self):
        st, inv = make()
        self.assertEqual(inv.regole(), [])
        self.assertEqual(inv.aggiungi_regola("  Le uova   vanno in Frigorifero "), ["Le uova vanno in Frigorifero"])
        with self.assertRaises(Exception):
            inv.aggiungi_regola("le uova vanno in frigorifero")   # doppia
        with self.assertRaises(Exception):
            inv.aggiungi_regola("no")
        inv.aggiungi_regola("I detersivi stanno in Cantina")
        self.assertEqual(inv.elimina_regola("le uova vanno in frigorifero"), ["I detersivi stanno in Cantina"])

    def test_prompt_contiene_le_regole(self):
        ai.regole_provider = lambda: ["Le uova vanno in Frigorifero"]
        try:
            p = ai._prompt("Uova", "", "", [{"categoria": "Frigorifero", "sottocategorie": ["Uova"]}], [])
            self.assertIn("REGOLE DELLA CASA", p); self.assertIn("Le uova vanno in Frigorifero", p)
        finally:
            ai.regole_provider = None
        self.assertNotIn("REGOLE", ai._prompt("Uova", "", "", [], []))


if __name__ == "__main__":
    unittest.main()
