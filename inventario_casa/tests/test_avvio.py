import unittest

from app import avvio


class Chiamata:
    def __init__(self, f, log, nome):
        self.f, self.log, self.nome = f, log, nome

    def execute(self, num_retries=0):
        return self.f()


class FakeSheets:
    def __init__(self, esistenti=()):
        self.log, self.esistenti = [], set(esistenti)

    def get(self, spreadsheetId, fields=None):
        def f():
            if spreadsheetId not in self.esistenti and spreadsheetId != "NUOVO":
                e = Exception("404"); e.resp = type("R", (), {"status": 404})(); raise e
            return {"sheets": [{"properties": {"sheetId": 7}}]}
        return Chiamata(f, self.log, "get")

    def batchUpdate(self, spreadsheetId, body):
        self.log.append(("batchUpdate", body)); return Chiamata(dict, self.log, "b")

    def values(self):
        s = self
        class V:
            def batchUpdate(self, spreadsheetId, body):
                s.log.append(("valori", body)); return Chiamata(dict, s.log, "v")
        return V()


class FakeDrive:
    def __init__(self):
        self.creati, self.permessi = [], []

    def files(self):
        d = self
        class F:
            def create(self, body, fields, supportsAllDrives):
                d.creati.append(body); return Chiamata(lambda: {"id": "NUOVO"}, [], "c")
        return F()

    def permissions(self):
        d = self
        class P:
            def create(self, fileId, body, sendNotificationEmail, supportsAllDrives):
                d.permessi.append((fileId, body)); return Chiamata(dict, [], "p")
        return P()


class TAvvio(unittest.TestCase):
    def run_(self, conf, crea=True, esistenti=(), salvato="", **k):
        sh, dr, salvati, msg = FakeSheets(esistenti), FakeDrive(), [], []
        r = avvio.risolvi(conf, crea, sh, dr, log=msg.append, salva=lambda a, b: salvati.append((a, b)), letto=lambda c: salvato, **k)
        return r, sh, dr, salvati, msg

    def test_funzione_spenta_non_tocca_nulla(self):
        r, sh, dr, salvati, _ = self.run_("", crea=False)
        self.assertEqual((r, dr.creati, salvati), ("", [], []))

    def test_foglio_esistente_resta(self):
        r, sh, dr, salvati, _ = self.run_("ABC", esistenti=["ABC"])
        self.assertEqual((r, dr.creati), ("ABC", []))

    def test_id_vuoto_crea_con_tutte_le_schede(self):
        r, sh, dr, salvati, msg = self.run_("", cartella="CART", condividi_con="a@b.it")
        self.assertEqual(r, "NUOVO")
        self.assertEqual(dr.creati[0]["parents"], ["CART"])
        self.assertEqual(dr.permessi[0][1]["emailAddress"], "a@b.it")
        self.assertEqual(salvati, [("", "NUOVO")])
        rq = [x for n, x in sh.log if n == "batchUpdate"][0]["requests"]
        self.assertEqual(len(rq), len(avvio.INTESTAZIONI))
        dati = [x for n, x in sh.log if n == "valori"][0]["data"]
        self.assertEqual({d["range"] for d in dati}, {"'%s'!A1" % t for t in avvio.INTESTAZIONI})
        self.assertIn("spreadsheets/d/NUOVO", msg[0])

    def test_id_inesistente_crea(self):
        r, *_ = self.run_("SBAGLIATO")
        self.assertEqual(r, "NUOVO")

    def test_gia_creato_non_ricrea(self):
        r, sh, dr, salvati, _ = self.run_("", salvato="GIA")
        self.assertEqual((r, dr.creati), ("GIA", []))

    def test_intestazioni_coprono_i_fogli_dell_app(self):
        for t in ("movimenti", "prodotti", "categorie", "ai_tipi", "alias", "bozze", "ai_prodotti", "ai_categorie", "log_ai"):
            self.assertIn(t, avvio.INTESTAZIONI)


if __name__ == "__main__":
    unittest.main()
