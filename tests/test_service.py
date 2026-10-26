import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.service import Inventory, ApiError
from app.store import MemoryStore


def make():
    st = MemoryStore({
        "prodotti": [["Barcode", "Prodotto", "Marca", "Categoria", "Sottocategoria", "Tipo"],
                     [8002795002995, "Latte UHT", "X", "Dispensa", "Bevande", "Latte"],
                     [9000000000001, "Si & No Mais", "Y", "Dispensa", "Snack e Dolci", ""]],
        "movimenti": [["Barcode", "Tipo", "Location", "Quantità", "Prodotto", "Categoria", "Sottocategoria", "Foto"],
                      [8002795002995, "Carico", "Casa", 6, "Latte UHT", "Dispensa", "Bevande", ""],
                      [8002795002995, "Scarico", "Casa", 2, "Latte UHT", "Dispensa", "Bevande", ""]],
        "ai_prodotti": [["Barcode", "Prodotto_Attuale", "Nome_Suggerito", "Tipo", "Categoria_Suggerita", "Sottocategoria_Suggerita", "Confidenza", "Stato", "Motivo"],
                        [9000000000001, "Si & No Mais", "Si & No Mais", "Galletta", "Dispensa", "Snack e Dolci", 1, "DA_APPROVARE", "snack di mais"],
                        [8002795002995, "Latte UHT", "Latte UHT", "Latte", "Frigorifero", "Latticini", 0.82, "RIFIUTATO", ""]],
    })
    t = [1000.0]
    return st, Inventory(st, ttl=20, clock=lambda: t[0]), t


class T(unittest.TestCase):
    def test_stock(self):
        _, inv, _ = make()
        s = inv.stock()
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0]["giacenza"], 4)

    def test_prodotto_barcode_misto(self):
        _, inv, _ = make()
        self.assertEqual(inv.prodotto("08002795002995")["prodotto"], "Latte UHT")
        self.assertIsNone(inv.prodotto("123"))

    def test_movimento_riempie_campi_e_numero(self):
        st, inv, _ = make()
        r = inv.movimento("8002795002995", "Carico", "Casa", 3)
        self.assertTrue(r["noto"])
        row = st.sheets["movimenti"][-1]
        self.assertIsInstance(row[0], int)
        self.assertEqual(row[5:7], ["Dispensa", "Bevande"])
        self.assertEqual(inv.stock()[0]["giacenza"], 7)

    def test_movimento_validazioni(self):
        _, inv, _ = make()
        for args in [("abc", "Carico", "Casa", 1), ("8002795002995", "Boh", "Casa", 1),
                     ("8002795002995", "Carico", "Garage", 1), ("8002795002995", "Carico", "Casa", 0)]:
            with self.assertRaises(ApiError) as c:
                inv.movimento(*args)
            self.assertEqual(c.exception.status, 400)
        with self.assertRaises(ApiError) as c:
            inv.movimento("777", "Carico", "Casa", 1)
        self.assertEqual(c.exception.status, 409)
        self.assertTrue(inv.movimento("777", "Carico", "Casa", 1, foto="http://f")["ok"])

    def test_cache(self):
        st, inv, t = make()
        inv.stock()
        st.sheets["movimenti"].append([8002795002995, "Carico", "Casa", 10, "", "", "", ""])
        self.assertEqual(inv.stock()[0]["giacenza"], 4)   # ancora in cache
        t[0] += 21
        self.assertEqual(inv.stock()[0]["giacenza"], 14)

    def test_approvazioni_prima_dopo(self):
        _, inv, _ = make()
        a = inv.approvazioni()
        self.assertEqual(len(a), 1)
        self.assertTrue(a[0]["prima"].startswith("Si & No Mais · Dispensa › Snack e Dolci"))
        self.assertIn("tipo Galletta", a[0]["dopo"])
        self.assertEqual(a[0]["sicurezza"], 100)

    def test_decidi(self):
        st, inv, _ = make()
        self.assertEqual(inv.decidi("P_9000000000001", "SCARTA")["stato"], "RIFIUTATO")
        self.assertEqual(inv.approvazioni(), [])
        with self.assertRaises(ApiError) as c:
            inv.decidi("P_9000000000001", "APPROVA")
        self.assertEqual(c.exception.status, 409)
        with self.assertRaises(ApiError):
            inv.decidi("X_1", "APPROVA")

    def test_foto(self):
        st, inv, _ = make()
        self.assertTrue(inv.foto("123", b"abc", "image/jpeg")["url"].startswith("https://"))
        with self.assertRaises(ApiError):
            inv.foto("123", b"abc", "text/html")


if __name__ == "__main__":
    unittest.main()
