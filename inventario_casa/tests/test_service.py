import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.service import Inventory, ApiError, data_it
from app.store import MemoryStore


def make():
    st = MemoryStore({
        "prodotti": [["Barcode", "Prodotto", "Marca", "Categoria", "Sottocategoria", "Tipo"],
                     [8002795002995, "Latte UHT", "X", "Dispensa", "Bevande", "Latte"],
                     [9000000000001, "Si & No Mais", "Y", "Dispensa", "Snack e Dolci", ""]],
        "categorie": [["Categoria", "Sottocategoria"], ["Dispensa", "Bevande"], ["Dispensa", "Snack e Dolci"], ["Frigorifero", "Latticini"]],
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
        self.assertEqual(s[0]["qta"], 4)

    def test_move_e_cng_sono_coppie_nette(self):
        st, inv, _ = make()
        inv.movimento(8002795002995, "Move", "Casa", 1, destinazione="Cantina", categoria="Dispensa")
        self.assertEqual({(e["luogo"], e["qta"]) for e in inv.stock()}, {("Casa", 3), ("Cantina", 1)})
        inv.movimento(8002795002995, "Cng", "Casa", 1, categoria="Dispensa", categoria_new="Cantina e Bevande")
        s = {(e["luogo"], e["categoria"]): e["qta"] for e in inv.stock()}
        self.assertEqual(s, {("Casa", "Dispensa"): 2, ("Casa", "Cantina e Bevande"): 1, ("Cantina", "Dispensa"): 1})
        self.assertEqual(sum(s.values()), 4)   # lo spostamento non crea ne perde pezzi

    def test_move_e_cng_validazioni(self):
        _, inv, _ = make()
        with self.assertRaises(ApiError):
            inv.movimento(8002795002995, "Move", "Casa", 9, destinazione="Cantina", categoria="Dispensa")
        with self.assertRaises(ApiError):
            inv.movimento(8002795002995, "Move", "Casa", 1, destinazione="Casa", categoria="Dispensa")
        with self.assertRaises(ApiError):
            inv.movimento(8002795002995, "Cng", "Casa", 1, categoria="Dispensa", categoria_new="Dispensa")

    def test_elenco_prodotti_alfabetico_con_zero(self):
        _, inv, _ = make()
        e = inv.elenco_prodotti()
        self.assertEqual([x["nome"] for x in e], ["Latte UHT", "Si & No Mais"])
        self.assertEqual([x["qta"] for x in e], [4, 0])

    def test_scheda(self):
        _, inv, _ = make()
        s = inv.scheda("8002795002995")
        self.assertEqual(s["nome"], "Latte UHT")
        self.assertEqual(s["totale"], 4)
        self.assertEqual(s["giacenze"][0]["luogo"], "Casa")
        self.assertIsNone(inv.scheda("1"))

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
        self.assertEqual(inv.stock()[0]["qta"], 7)

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
        self.assertEqual(inv.stock()[0]["qta"], 4)   # ancora in cache
        t[0] += 21
        self.assertEqual(inv.stock()[0]["qta"], 14)

    def test_stock_calcolato_una_volta(self):
        st, inv, t = make()
        a = inv.stock()
        self.assertIs(inv.stock(), a)          # riusato dalla memoria
        inv.movimento("8002795002995", "Carico", "Casa", 1)
        self.assertEqual(inv.stock()[0]["qta"], 5)   # dopo una scrittura si ricalcola

    def test_movimento_scrive_id_e_data(self):
        st, inv, _ = make()
        inv.movimento("8002795002995", "Scarico", "Casa", 1, categoria="Dispensa")
        h = st.sheets["movimenti"][0]; row = dict(zip(h, st.sheets["movimenti"][-1]))
        self.assertEqual(len(row["ID_Movimento"]), 8)
        self.assertRegex(row["Data"], r"^\d\d/\d\d/\d{4}$")

    def test_data_it(self):
        self.assertEqual(data_it(46102), "21/03/2026")
        self.assertEqual(data_it("46102"), "21/03/2026")
        self.assertEqual(data_it("2026-03-21T10:00:00"), "21/03/2026")
        self.assertEqual(data_it("21/3/2026 4.45.20"), "21/03/2026")
        self.assertEqual(data_it(""), "")

    def test_refresh_rilegge_subito(self):
        st, inv, _ = make()
        inv.stock()
        st.sheets["movimenti"].append([8002795002995, "Carico", "Casa", 10, "", "", "", ""])
        self.assertEqual(inv.stock()[0]["qta"], 4)       # ancora in cache
        inv.refresh()                                     # il ciclo in background
        self.assertEqual(inv.stock()[0]["qta"], 14)
        self.assertEqual(inv.elenco_prodotti()[0]["qta"], 14)

    def test_categorie(self):
        _, inv, _ = make()
        self.assertEqual(inv.categorie(), [{"categoria": "Dispensa", "sottocategorie": ["Bevande", "Snack e Dolci"]},
                                           {"categoria": "Frigorifero", "sottocategorie": ["Latticini"]}])

    def test_cambio_sottocategoria_e_modifica_prodotto(self):
        st, inv, _ = make()
        r = inv.modifica_prodotto("8002795002995", "Snack e Dolci")
        self.assertEqual(r["movimenti_aggiornati"], 2)
        self.assertEqual(inv.prodotto("8002795002995")["sottocategoria"], "Snack e Dolci")
        self.assertEqual(inv.stock()[0]["qta"], 4)            # le quantita non cambiano
        self.assertEqual({m[6] for m in st.sheets["movimenti"][1:]}, {"Snack e Dolci"})
        with self.assertRaises(ApiError):
            inv.modifica_prodotto("8002795002995", "Latticini")   # non e una sottocategoria di Dispensa
        with self.assertRaises(ApiError):
            inv.modifica_prodotto("1", "Bevande")

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


class TCreaConCarico(unittest.TestCase):
    def test_crea_e_carica_in_una_chiamata(self):
        _, inv, _ = make()
        r = inv.crea_prodotto("6111246721261", "Yogurt", categoria="Dispensa", sottocategoria="Bevande", location="Casa", quantita=3)
        self.assertTrue(r["movimento"])
        s = [e for e in inv.stock() if str(e["barcode"]) == "6111246721261"]
        self.assertEqual((s[0]["luogo"], s[0]["qta"], s[0]["categoria"]), ("Casa", 3, "Dispensa"))

    def test_posizione_errata_non_crea_nulla(self):
        _, inv, _ = make()
        with self.assertRaises(ApiError):
            inv.crea_prodotto("6111246721261", "Yogurt", categoria="Dispensa", sottocategoria="Bevande", location="Luna")
        self.assertIsNone(inv.prodotto("6111246721261"))


class TElencoPosti(unittest.TestCase):
    def test_posti_e_minima_senza_giacenza(self):
        _, inv, _ = make()
        inv.movimento(8002795002995, "Carico", "Cantina", 2)
        e = {x["barcode"]: x for x in inv.elenco_prodotti()}
        latte = e[8002795002995]
        self.assertEqual(latte["qta"], 6)
        self.assertEqual({(p["luogo"], p["qta"]) for p in latte["posti"]}, {("Casa", 4), ("Cantina", 2)})
        self.assertEqual(e[9000000000001]["posti"], [])


class TBarcode16(unittest.TestCase):
    def test_bco_e_testo(self):
        from app.service import bco, nbc
        from app.store import _testo
        self.assertEqual(bco("8001234567890"), 8001234567890)
        self.assertEqual(bco("1234567890123456"), "1234567890123456")
        self.assertEqual(nbc("0123456789012345"), "123456789012345")
        self.assertEqual(_testo("1234567890123456"), "'1234567890123456")
        self.assertEqual(_testo(8001234567890), 8001234567890)
