import os
import tempfile
import unittest
from datetime import datetime

from app import ext_cop
from app.ext_cop import Copia, CopiaErrore, csv_inventario


class Exec:
    def __init__(self, v, errore=None):
        self.v, self.errore = v, errore

    def execute(self, num_retries=0):
        if self.errore:
            raise self.errore
        return self.v


class FakeFiles:
    def __init__(self, esistenti=None, errore=None):
        self.copiati, self.cestinati, self.esistenti, self.errore = [], [], esistenti or [], errore

    def copy(self, fileId, body, supportsAllDrives, fields):
        self.copiati.append((fileId, body))
        return Exec({"id": "nuovo", "name": body["name"], "webViewLink": "https://x/nuovo"}, self.errore)

    def list(self, **k):
        return Exec({"files": self.esistenti})

    def update(self, fileId, body, supportsAllDrives):
        self.cestinati.append((fileId, body))
        return Exec({})


class FakeDrive:
    def __init__(self, **k):
        self.f = FakeFiles(**k)

    def files(self):
        return self.f


class FakeStore:
    def __init__(self, drive, cartella="CART", foglio="FOGLIO"):
        self.drive, self.folder_id, self.sheet_id = drive, cartella, foglio


class ErroreHttp(Exception):
    def __init__(self, st):
        self.resp = type("R", (), {"status": st})()


def crea(store, imp=None):
    d = tempfile.mkdtemp()
    return Copia(lambda: store, lambda: dict({"copia_auto": False, "copia_giorni": 7}, **(imp or {})), os.path.join(d, "s.json"), lambda: datetime(2026, 11, 11, 8, 0))


class TCopia(unittest.TestCase):
    def test_copia_e_stato(self):
        dr = FakeDrive(); c = crea(FakeStore(dr))
        r = c.copia_ora()
        self.assertEqual(dr.f.copiati[0][0], "FOGLIO"); self.assertEqual(dr.f.copiati[0][1]["parents"], ["CART"])
        self.assertEqual(r["nome"], "Copia Inventario 2026-11-11 08:00")
        s = c.stato(); self.assertTrue(s["possibile"]); self.assertEqual(s["ultima"], "2026-11-11T08:00:00"); self.assertEqual(len(s["copie"]), 1)

    def test_tiene_solo_le_ultime_cinque_e_solo_le_proprie(self):
        vecchie = [{"id": "c%d" % i, "name": ext_cop.PREFISSO + "x%d" % i} for i in range(7)] + [{"id": "altro", "name": "Foglio importante"}]
        dr = FakeDrive(esistenti=vecchie); c = crea(FakeStore(dr))
        self.assertEqual(c.copia_ora()["tolte"], 2)
        self.assertEqual([x[0] for x in dr.f.cestinati], ["c5", "c6"])      # «altro» non si tocca mai
        self.assertTrue(all(x[1] == {"trashed": True} for x in dr.f.cestinati))

    def test_senza_cartella_o_senza_drive(self):
        with self.assertRaises(CopiaErrore) as e:
            crea(FakeStore(FakeDrive(), cartella="")).copia_ora()
        self.assertIn("drive_folder_id", e.exception.args[0])
        with self.assertRaises(CopiaErrore):
            crea(object()).copia_ora()                                      # MemoryStore: niente Drive
        self.assertFalse(crea(object()).stato()["possibile"])

    def test_permessi_negati_messaggio_chiaro(self):
        c = crea(FakeStore(FakeDrive(errore=ErroreHttp(403))))
        with self.assertRaises(CopiaErrore) as e:
            c.copia_ora()
        self.assertIn("Editor", e.exception.args[0]); self.assertNotIn("ErroreHttp", e.exception.args[0])
        self.assertTrue(c.stato()["errore"])

    def test_copia_automatica_dovuta(self):
        c = crea(FakeStore(FakeDrive()), {"copia_auto": True, "copia_giorni": 3})
        self.assertTrue(c.dovuta())                                         # mai fatta
        c.copia_ora(); self.assertFalse(c.dovuta())
        c.ora = lambda: datetime(2026, 11, 14, 8, 1); self.assertTrue(c.dovuta())
        self.assertFalse(crea(FakeStore(FakeDrive()), {"copia_auto": False}).dovuta())


class TCsv(unittest.TestCase):
    def test_csv(self):
        b = csv_inventario([{"barcode": 8001, "nome": "=SOMMA(A1)", "marca": "Mulino; Bianco", "conf": "1 kg", "tipo": "Pasta", "categoria": "Dispensa",
                             "sotto": "Pasta", "qta": 3, "posti": [{"luogo": "Casa", "qta": 2}, {"luogo": "Cantina", "qta": 1}], "minima": 1,
                             "scad": "2026-12-01", "ultimo": "2026-11-02"}])
        t = b.decode("utf-8")
        self.assertTrue(t.startswith("﻿Codice a barre;Prodotto;"))
        riga = t.split("\r\n")[1]
        self.assertIn("'=SOMMA(A1)", riga)                                  # niente formule
        self.assertIn('"Mulino; Bianco"', riga)
        self.assertTrue(riga.endswith(";3;2;1;1;01/12/2026;02/11/2026"))

    def test_vuoto(self):
        self.assertEqual(csv_inventario([]).decode("utf-8").count("\r\n"), 1)


if __name__ == "__main__":
    unittest.main()
