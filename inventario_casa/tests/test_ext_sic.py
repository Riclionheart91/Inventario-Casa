import os
import tempfile
import unittest

from app import accesso, aiuso, ext_sic
from app import impostazioni as I


class Ora:
    t = 1_700_000_000.0

    def __call__(self):
        return self.t


UA_IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"


class TRegistro(unittest.TestCase):
    def setUp(self):
        self.ora = Ora(); self.avvisi = []
        self.r = ext_sic.Registro(os.path.join(tempfile.mkdtemp(), "a.json"), giorni=lambda: 90, avvisa=self.avvisi.append, orologio=self.ora)

    def ev(self, ip="1.2.3.4", ua=UA_IPHONE, **k):
        self.r.evento(dict({"tipo": "visita", "via": "diretto", "ip": ip, "ua": ua, "utente": ""}, **k)); import time as _t; _t.sleep(0.01)

    def test_nome_dispositivo(self):
        self.assertEqual(ext_sic.dispositivo_breve(UA_IPHONE), "iPhone · Safari")
        self.assertEqual(ext_sic.dispositivo_breve("Mozilla/5.0 (Macintosh; Intel Mac OS X) Chrome/120 Safari/537"), "Mac · Chrome")
        self.assertEqual(ext_sic.dispositivo_breve("Mozilla/5.0 (iPhone) HomeAssistant/2024"), "iPhone · App Home Assistant")

    def test_una_voce_per_ora_e_conteggio(self):
        self.ev(); self.ev(); self.ora.t += 600; self.ev()
        d = self.r.elenco()["dispositivi"]
        self.assertEqual((len(d), d[0]["n"]), (1, 1))
        self.ora.t += 4000; self.ev()
        self.assertEqual(self.r.elenco()["dispositivi"][0]["n"], 2)

    def test_silenzio_iniziale_poi_avviso_nuovo_dispositivo(self):
        self.ev("1.1.1.1"); self.assertEqual(self.avvisi, [])         # primo avvio: solo registrato
        self.ora.t += 3 * 86400; self.ev("1.1.1.1"); self.assertEqual(self.avvisi, [])    # gia noto
        self.ev("9.9.9.9", ua="Mozilla/5.0 (Windows NT 10) Firefox/120"); import time; time.sleep(0.1)
        self.assertEqual(len(self.avvisi), 1)

    def test_errori_e_blocchi_senza_codice(self):
        self.ev(tipo="errato", ua=""); self.ev(tipo="blocco", ua="")
        e = self.r.elenco()["errori"]
        self.assertEqual([x["tipo"] for x in e], ["blocco", "errato"])
        self.assertNotIn("codice", open(self.r.percorso).read().lower().replace('"errato"', ""))

    def test_potatura_e_svuota(self):
        self.ev(); self.ora.t += 100 * 86400
        self.assertEqual(self.r.elenco()["dispositivi"], [])
        self.ev(); self.r.svuota(); self.assertEqual(self.r.elenco()["dispositivi"], [])

    def test_utente_solo_da_ingress(self):
        class Acc:
            def e_ingresso_ha(self, s): return s["ingress"]
            def _intest(self, s, n): return {b"x-remote-user-display-name": "Rick ", b"x-remote-user-name": "rick"}.get(n, "")
        self.assertEqual(accesso.utente_ingress(Acc(), {"ingress": True}), "Rick")
        self.assertEqual(accesso.utente_ingress(Acc(), {"ingress": False}), "")


class TFrenoAi(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); os.environ["DATA_DIR"] = self.d; aiuso.ATTIVO = True; I._istanza = None

    def tearDown(self):
        aiuso.ATTIVO = False; os.environ.pop("DATA_DIR", None); I._istanza = None

    def test_sospesa_e_limite(self):
        n = [0]

        @aiuso.registra("prova", True)
        def f(t, chiave=""):
            n[0] += 1
            return {"x": t}
        self.assertEqual(f("a"), {"x": "a"})
        I.imp().imposta({"ai_sospesa": True})
        self.assertIsNone(f("b")); self.assertEqual(n[0], 1)
        self.assertEqual(f("a"), {"x": "a"})                      # dalla memoria: continua a funzionare
        c = aiuso.riepilogo()["compiti"][0]
        self.assertEqual(c["errori"], 0)                          # il freno non e un errore
        I.imp().imposta({"ai_sospesa": False, "ai_limite": 1})
        self.assertIsNone(f("c")); self.assertEqual(n[0], 1)
        self.assertTrue(aiuso.riepilogo()["sospesa"] is False and aiuso.riepilogo()["limite"] == 1)
        I.imp().imposta({"ai_limite": 0}); self.assertEqual(f("c"), {"x": "c"})


if __name__ == "__main__":
    unittest.main()
