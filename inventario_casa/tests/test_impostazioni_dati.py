"""Effetti delle impostazioni modificabili sui dati automatici: avvisi, giro notturno, revisione, approvazione automatica, siti Open Food Facts."""
import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import impostazioni
from app.arricchimento import Arricchitore
from app.avvisi import Avvisi
from app.ext_dati import auto_approva
from app.revisione import Revisione
from app.service import Inventory
from app.store import MemoryStore
from tests.test_fase4 import make
from tests.test_off import Finto, crea


class Base(unittest.TestCase):
    def setUp(self):
        self._vecchia = impostazioni._istanza
        impostazioni._istanza = impostazioni.Impostazioni(os.path.join(tempfile.mkdtemp(), "i.json"))

    def tearDown(self):
        impostazioni._istanza = self._vecchia

    def imposta(self, **kw):
        impostazioni.imp().imposta(kw)


class TAvvisi(Base):
    def _inv(self):
        st, inv = make()
        st.sheets["movimenti"][0].append("Scadenza")
        inv.movimento(8003333333333, "Carico", "Casa", 3, categoria="Dispensa", scadenza="2026-11-02")
        return inv

    def test_scorte_basse_con_soglia(self):
        inv = self._inv(); a = Avvisi(inv, lambda *x: None, os.path.join(tempfile.mkdtemp(), "a.json"))
        mio = lambda soglia: [v["qta"] for v in a.scorte_basse(soglia) if v["barcode"] == "8003333333333"]
        self.assertEqual(mio(3), [])
        self.assertEqual(mio(4), [4])      # 1 gia presente nel foglio di prova + 3 caricati
        inv.movimento(8003333333333, "Scarico", "Casa", 4, categoria="Dispensa")
        self.assertEqual(mio(0), [0])      # il finito conta

    def test_notifica_scorte_una_al_giorno_e_mai_se_vuota(self):
        inv = self._inv(); inviate = []; ora = [datetime(2026, 11, 1, 7, 0)]
        a = Avvisi(inv, lambda *x: inviate.append(x), os.path.join(tempfile.mkdtemp(), "a.json"), oggi=lambda: ora[0])
        self.assertFalse(a.avvisa_scorte("s", 3, "08:00")["inviata"])      # presto
        ora[0] = datetime(2026, 11, 1, 8, 1)
        self.assertEqual(a.avvisa_scorte("s", -1, "08:00")["motivo"], "nessuna scorta bassa")
        self.assertEqual(len(inviate), 0)
        ora[0] = datetime(2026, 11, 2, 8, 1)
        self.assertTrue(a.avvisa_scorte("s", 3, "08:00")["inviata"])
        self.assertFalse(a.avvisa_scorte("s", 3, "08:00")["inviata"])      # gia oggi
        self.assertIn("in esaurimento", inviate[0][1]); self.assertFalse(a.avvisa_scorte("", 3)["inviata"])

    def test_riepilogo_settimanale_giorno_e_contenuto(self):
        inv = self._inv(); inviate = []
        a = Avvisi(inv, lambda *x: inviate.append(x), os.path.join(tempfile.mkdtemp(), "a.json"), oggi=lambda: datetime(2026, 11, 1, 9, 30))   # domenica
        r = a.riepilogo_settimanale("s", "lun", "09:00", 7, 3, lambda: {"bozze": 2, "proposte": 1})
        self.assertFalse(r["inviata"])                                      # oggi non e lunedi
        r = a.riepilogo_settimanale("s", "dom", "09:00", 7, 3, lambda: {"bozze": 2, "proposte": 1})
        self.assertEqual((r["inviata"], r["in_scadenza"], r["basse"] >= 1, r["da_fare"]), (True, 1, True, 3))
        self.assertIn("3 da fare", inviate[0][2])
        self.assertFalse(a.riepilogo_settimanale("s", "dom", "09:00")["inviata"])   # una volta sola


class TArricchimento(Base):
    def _arr(self, extra, tr):
        st = MemoryStore({"prodotti": [["Barcode", "Prodotto", "Marca", "Confezione", "Immagine", "Dettagli prodotto", "Punteggi", "API Status"],
                                       [1, "Latte", "Parmalat", "1 l", "http://i", "Sugar, salt", "", "✅ App (X)"]]})
        return Arricchitore(Inventory(st, ttl=0), lambda bc: None, tr, os.path.join(tempfile.mkdtemp(), "a.json"), oggi=lambda: datetime(2026, 10, 30), extra=extra), st

    def test_punteggi_e_traduzioni_spenti(self):
        chiam = []
        a, st = self._arr(lambda *x: chiam.append(x) or {"punteggi": "Nutri A"}, lambda t: [x.replace("Sugar, salt", "Zucchero, sale") for x in t])
        self.imposta(arr_punteggi=False, arr_traduzioni=False)
        r = a.esegui(10)
        self.assertEqual((chiam, r["tradotti"]), ([], 0))
        self.assertEqual(st.sheets["prodotti"][1][5:7], ["Sugar, salt", ""])

    def test_acceso_di_serie(self):
        chiam = []
        a, st = self._arr(lambda *x: chiam.append(x) or {"punteggi": "Nutri A"}, lambda t: [x.replace("Sugar, salt", "Zucchero, sale") for x in t])
        r = a.esegui(10)
        self.assertEqual((len(chiam), r["tradotti"]), (1, 1))


class TRevisione(Base):
    def _rev(self):
        f = os.path.join(tempfile.mkdtemp(), "r.json")
        with open(f, "w") as fh:
            json.dump({"ultima": "2026-05-01"}, fh)
        return Revisione(object(), percorso=f, oggi=lambda: datetime(2026, 11, 1))   # 184 giorni dopo

    def test_mesi_configurabili(self):
        r = self._rev()
        self.assertTrue(r.dovuta())                    # 6 mesi di serie
        self.imposta(rev_mesi=12)
        self.assertFalse(r.dovuta())
        self.imposta(rev_mesi=3)
        self.assertTrue(r.dovuta())


class TAutoApprova(Base):
    class Finto:
        def __init__(self, voci):
            self.voci, self.decise = voci, []

        def approvazioni(self):
            return self.voci

        def decidi(self, id_, azione, campi=None, fonte=""):
            self.decise.append((id_, azione, fonte))
            return {"ok": True}

    VOCI = [{"id": "P_1", "genere": "P", "sicurezza": 97}, {"id": "P_2", "genere": "P", "sicurezza": 90}, {"id": "P_3", "genere": "P", "sicurezza": None},
            {"id": "T_x", "genere": "T", "sicurezza": 99}, {"id": "C_2", "genere": "C", "sicurezza": 99}]

    def test_solo_prodotti_sopra_soglia(self):
        f = self.Finto(list(self.VOCI))
        r = auto_approva(f, 95, lambda: False)
        self.assertEqual(f.decise, [("P_1", "APPROVA", "AUTO")]); self.assertEqual(r["applicate"], 1)

    def test_mai_in_sola_lettura(self):
        f = self.Finto(list(self.VOCI))
        self.assertEqual(auto_approva(f, 80, lambda: True)["applicate"], 0); self.assertEqual(f.decise, [])

    def test_il_log_ai_porta_la_fonte_auto(self):
        st, inv = make(); righe = []
        inv.store.append_row = lambda foglio, riga: righe.append((foglio, riga))
        inv._ctx_decisione.fonte = "AUTO"
        try:
            inv._log_ai(1, "Categoria", "a", "b")
        finally:
            inv._ctx_decisione.fonte = ""
        inv._log_ai(1, "Categoria", "a", "b")
        self.assertEqual([(r[1]["Fonte"], r[1]["Modo"]) for r in righe], [("AUTO", "AUTO"), ("APPROVATO", "MANUALE")])


class TSitiOff(Base):
    def test_sito_spento_non_si_controlla_ne_si_propone_ne_si_invia(self):
        self.imposta(off_pet=False)
        h = Finto(); o = crea(h)
        o.controlla()
        self.assertEqual([p["nome"] for p in o.elenco()], ["Detersivo piatti"])          # niente crocchette (Open Pet Food Facts spento)
        self.assertFalse(any("8001234567890" in c[1] for c in h.chiamate))               # nemmeno interrogato
        self.imposta(off_pet=True); o.controlla()
        self.assertEqual(len(o.elenco()), 2)
        self.imposta(off_pet=False)
        r = o.invia([{"barcode": "8001234567890", "progetto": "pet"}])
        self.assertFalse(r[0]["ok"]); self.assertIn("disattivato", r[0]["messaggio"])

    def test_foto_vecchie_si_cancellano_anche_se_da_inviare(self):
        o = crea(Finto()); o.controlla()
        o.salva_foto("8001234567890", b"x", "image/jpeg"); o.salva_foto("8009876543210", b"x", "image/jpeg")
        vecchio = time.time() - 40 * 86400
        os.utime(o.foto_file("8001234567890")[0], (vecchio, vecchio))
        self.assertEqual(o.pulisci_foto(), 1)                                            # 30 giorni di serie: la vecchia va, la nuova resta
        self.assertIsNone(o.foto_file("8001234567890")); self.assertIsNotNone(o.foto_file("8009876543210"))
        os.utime(o.foto_file("8009876543210")[0], (vecchio, vecchio))
        self.imposta(off_foto_giorni=60)
        self.assertEqual(o.pulisci_foto(), 0)                                            # con 60 giorni resta


if __name__ == "__main__":
    unittest.main()
