import os, sys, tempfile, unittest
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.avvisi import Avvisi, testo
from tests.test_fase4 import make


class T(unittest.TestCase):
    def _mk(self):
        st, inv = make()
        st.sheets["movimenti"][0].append("Scadenza")
        inv.movimento(8003333333333, "Carico", "Casa", 2, categoria="Dispensa", scadenza="2026-11-02")
        inv.movimento(8003333333333, "Carico", "Casa", 1, categoria="Dispensa", scadenza="2026-10-30")
        return inv

    def test_una_notifica_al_giorno_dopo_l_ora(self):
        inv = self._mk(); inviate = []
        f = os.path.join(tempfile.mkdtemp(), "a.json")
        ora = [datetime(2026, 11, 1, 7, 0)]
        a = Avvisi(inv, lambda *x: inviate.append(x), f, oggi=lambda: ora[0])
        self.assertFalse(a.esegui("mobile_app_x", 7, "08:00")["inviata"])   # troppo presto
        ora[0] = datetime(2026, 11, 1, 8, 5)
        self.assertTrue(a.esegui("notify.mobile_app_x", 7, "08:00")["inviata"])
        self.assertFalse(a.esegui("mobile_app_x", 7, "08:00")["inviata"])   # gia mandata oggi
        self.assertEqual(len(inviate), 1)
        ora[0] = datetime(2026, 11, 2, 9, 0)
        self.assertTrue(a.esegui("mobile_app_x", 7, "08:00")["inviata"])    # il giorno dopo di nuovo

    def test_testo_e_prova_senza_scadenze(self):
        inv = self._mk()
        t, m = testo(inv.scadenze(7, datetime(2026, 11, 1).date()))
        self.assertIn("1 scaduto", t); self.assertIn("1 in scadenza", t); self.assertIn("domani", m)
        inviate = []
        inv = make()[1]   # senza scadenze
        a = Avvisi(inv, lambda *x: inviate.append(x), os.path.join(tempfile.mkdtemp(), "b.json"), oggi=lambda: datetime(2027, 6, 1, 10, 0))
        self.assertTrue(a.esegui("s", 7, forza=True)["inviata"])   # la prova scrive anche se non c'e nulla
        self.assertIn("Nessun prodotto", inviate[0][2])
