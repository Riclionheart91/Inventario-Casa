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


class TRegoleAuto(unittest.TestCase):
    def setUp(self):
        from app import regole_auto
        self.ra = regole_auto
        os.environ["DATA_DIR"] = tempfile.mkdtemp()

    def tearDown(self):
        os.environ.pop("DATA_DIR", None)

    def prod(self, n, tipo, cat, sub, bc=None):
        return {"Barcode": bc or "80%05d" % n, "Prodotto": "P%d" % n, "Marca": "M", "Tipo": tipo, "Categoria": cat, "Sottocategoria": sub}

    def test_abitudine_solo_se_forte(self):
        ps = [self.prod(i, "Pasta", "Dispensa", "Pasta") for i in range(4)] + [self.prod(10 + i, "Latte", "Dispensa" if i < 2 else "Frigo", "X") for i in range(4)] \
            + [self.prod(20, "Sale", "Dispensa", "S"), self.prod(21, "Sale", "Dispensa", "S")]
        c = self.ra.candidate(ps, [], [], set())
        self.assertEqual([x["chiave"] for x in c], ["tipo|pasta"])   # Latte e 50% e Sale ha solo 2 prodotti
        self.assertIn("Pasta", c[0]["bozza"]); self.assertEqual((c[0]["n"], c[0]["tot"]), (4, 4))

    def test_correzioni_ripetute_e_gestite(self):
        ps = [self.prod(1, "Birra", "Bevande", "Birre", "111111"), self.prod(2, "Vino", "Bevande", "Vino", "222222")]
        log = [{"Campo": "Categoria", "Fonte": "APPROVATO", "Prima": "❄️ Frigorifero", "Dopo": "🍷 Bevande", "Barcode": "111111"},
               {"Campo": "Categoria", "Fonte": "APPROVATO", "Prima": "Frigorifero", "Dopo": "Bevande", "Barcode": "222222"},
               {"Campo": "Categoria", "Fonte": "REVISIONE", "Prima": "A", "Dopo": "B", "Barcode": "111111"}]
        c = self.ra.candidate(ps, log, [], None)
        self.assertEqual(len(c), 1); self.assertTrue(c[0]["chiave"].startswith("corr|"))
        self.ra.segna(c[0]["chiave"])
        self.assertEqual(self.ra.candidate(ps, log, [], None), [])   # scartata o approvata: non torna

    def test_regola_gia_scritta_non_si_ripropone(self):
        ps = [self.prod(i, "Pasta", "Dispensa", "Pasta") for i in range(4)]
        self.assertEqual(self.ra.candidate(ps, [], ["La pasta va in Dispensa"], set()), [])

    def test_frase_riscritta_vale_solo_se_cita_i_nomi(self):
        c = {"bozza": "B", "obbligatori": ["Pasta", "🧺 Dispensa"]}
        self.assertEqual(self.ra.chiara("La Pasta sta sempre in Dispensa, in casa.", c), "La Pasta sta sempre in Dispensa, in casa.")
        self.assertEqual(self.ra.chiara("La pasta sta in cucina.", c), "B")
        self.assertEqual(self.ra.chiara(None, c), "B")

    def test_riscrittura_ai(self):
        r = ai.riscrivi_regole(["a", "b"], "K", post=lambda u, c, b, t: {"candidates": [{"content": {"parts": [{"text": '{"r":[{"id":1,"frase":"Beta"},{"id":0,"frase":"Alfa"}]}'}]}}]})
        self.assertEqual(r, ["Alfa", "Beta"])
        self.assertEqual(ai.riscrivi_regole(["a"], "", post=None), [None])


class TVerificaModelli(unittest.TestCase):
    def test_elenca_prova_e_consiglia(self):
        elenco = {"models": [{"name": "models/gemini-a-flash-lite", "supportedGenerationMethods": ["generateContent"]},
                             {"name": "models/gemini-b-flash", "supportedGenerationMethods": ["generateContent"]},
                             {"name": "models/gemini-c-pro", "supportedGenerationMethods": ["generateContent"]},
                             {"name": "models/gemini-embedding-001", "supportedGenerationMethods": ["embedContent"]},
                             {"name": "models/gemini-d-tts", "supportedGenerationMethods": ["generateContent"]}]}

        def post(url, k, corpo, t):
            if "gemini-c-pro" in url:
                ai.ULTIMO_ERRORE[0] = "HTTPError 429 limit: 0"; return None
            if "gemini-b-flash" in url and "tools" in corpo:
                return None
            return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
        r = ai.verifica_modelli("K", get=lambda u, k: elenco, post=post)
        per = {m["nome"]: m for m in r["modelli"]}
        self.assertEqual(set(per), {"gemini-a-flash-lite", "gemini-b-flash", "gemini-c-pro"})   # niente embedding ne tts
        self.assertTrue(per["gemini-a-flash-lite"]["ok"] and per["gemini-a-flash-lite"]["ricerca"])
        self.assertFalse(per["gemini-c-pro"]["ok"]); self.assertIn("429", per["gemini-c-pro"]["errore"])
        self.assertEqual(r["consigliati"]["leggero"], "gemini-a-flash-lite")
        self.assertEqual(r["consigliati"]["potente"], "gemini-b-flash")   # il non-lite che risponde, anche se senza ricerca
        self.assertTrue(r["ricerca_google"])   # il modello lite la accetta
        self.assertIn("chiave", ai.verifica_modelli("")["errore"])


class TFrenoRicerca(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); os.environ["DATA_DIR"] = self.d; aiuso.ATTIVO = True; ai.RICERCA_FERMA[0] = 0.0

    def tearDown(self):
        aiuso.ATTIVO = False; os.environ.pop("DATA_DIR", None); ai.RICERCA_FERMA[0] = 0.0

    def test_lista_vuota_non_e_un_errore(self):
        @aiuso.registra("prova", False)
        def f():
            return []
        f()
        self.assertEqual(aiuso.riepilogo()["compiti"][0]["errori"], 0)

    def test_dopo_un_rifiuto_la_ricerca_si_ferma(self):
        n = [0]

        def finta(*a, **k):
            n[0] += 1; ai.ULTIMO_ERRORE[0] = "HTTPError 400 grounding"; return None
        g = ai._con_freno(finta)
        g(); g(); g()
        self.assertEqual(n[0], 1)   # le altre due non partono
        self.assertIn("sospesa", ai.ULTIMO_ERRORE[0])
        ai.RICERCA_FERMA[0] = 0.0
        g()
        self.assertEqual(n[0], 2)

    def test_errore_di_rete_non_ferma(self):
        n = [0]

        def finta(*a, **k):
            n[0] += 1; ai.ULTIMO_ERRORE[0] = "URLError timeout"; return None
        g = ai._con_freno(finta); g(); g()
        self.assertEqual(n[0], 2)

    def test_ultimo_errore_registrato(self):
        @aiuso.registra("ricerca web", False)
        def f():
            ai.ULTIMO_ERRORE[0] = "HTTPError 400 test"; return None
        f()
        self.assertIn("HTTPError 400", aiuso.riepilogo()["ultimo_errore"]["ricerca web"]["testo"])
