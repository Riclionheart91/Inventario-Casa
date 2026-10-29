import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.service import Inventory, ApiError
from app.store import MemoryStore


def make():
    st = MemoryStore({
        "prodotti": [["Barcode", "Prodotto", "Marca", "Categoria", "Sottocategoria", "Tipo", "API Status"],
                     [8002795002995, "Latte UHT", "X", "Dispensa", "Bevande", "Latte", ""],
                     [8001111111111, "Pasta penne", "Y", "Dispensa", "Snack e Dolci", "Pasta", ""],
                     [8002222222222, "Pasta fusilli", "Y", "Dispensa", "Snack e Dolci", "Pasta", "✅ DB"],
                     [8003333333333, "Riso", "Z", "Dispensa", "Bevande", "Riso", ""]],
        "categorie": [["Categoria", "Sottocategoria"], ["Dispensa", "Bevande"], ["Dispensa", "Snack e Dolci"], ["Frigorifero", "Latticini"]],
        "movimenti": [["ID_Movimento", "Barcode", "Tipo", "Location", "Quantità", "Prodotto", "Categoria", "Sottocategoria"],
                      ["a", 8002795002995, "Carico", "Casa", 6, "Latte UHT", "Dispensa", "Bevande"],
                      ["b", 8002795002995, "Scarico", "Casa", 6, "Latte UHT", "Dispensa", "Bevande"],
                      ["c", 8001111111111, "Carico", "Casa", 3, "Pasta penne", "Dispensa", "Snack e Dolci"],
                      ["d", 8003333333333, "Carico", "Casa", 1, "Riso", "Dispensa", "Bevande"],
                      ["e", 8004444444444, "Carico", "Casa", 2, "", "", ""]],
        "ai_prodotti": [["Barcode", "Prodotto_Attuale", "Tipo", "Nome_Suggerito", "Categoria_Suggerita", "Sottocategoria_Suggerita", "Confidenza", "Fonte", "Stato", "Motivo", "Aggiornato"],
                        [8001111111111, "Pasta penne", "Pasta", "Penne rigate", "Dispensa", "Bevande", 0.8, "AI", "DA_APPROVARE", "m", ""],
                        [8002222222222, "Pasta fusilli", "Pasta", "Fusilli", "Frigorifero", "Latticini", 0.5, "AI", "DA_APPROVARE", "m", ""]],
        "ai_tipi": [["Tipo", "Scorta_min", "Stato", "Note"],
                    ["Latte", 2, "APPROVATO", ""], ["Pasta", 1, "APPROVATO", ""], ["Riso", 0, "APPROVATO", ""], ["Uova", 3, "DA_APPROVARE", "nuovo"]],
        "bozze": [["ID", "Barcode", "Foto", "Prodotto", "Marca", "Confezione", "Categoria", "Sottocategoria", "Tipo", "Immagine", "Stato", "Fonte", "Nota", "Location", "Movimento", "Quantità", "Aggiornato"],
                  ["b1", 8004444444444, "http://f", "Biscotti", "M", "300 g", "Dispensa", "Snack e Dolci", "Biscotti", "", "PRONTA", "Foto (AI)", "", "Casa", "Carico", 2, ""],
                  ["b2", 8005555555555, "", "", "", "", "", "", "", "", "NUOVA", "", "", "Cantina", "Carico", 1, ""],
                  ["b3", 8006666666666, "", "Vecchia", "", "", "", "", "", "", "INSERITA", "", "", "Casa", "Carico", 1, ""]],
        "ai_categorie": [["Azione", "Categoria", "Sottocategoria", "Nuovo_Nome", "Motivo", "Prodotti_Esempio", "Stato", "Aggiornato"],
                         ["AGGIUNGI_SOTTOCATEGORIA", "Dispensa", "Spezie", "", "serve", "", "PROPOSTA", ""]],
    })
    return st, Inventory(st, ttl=10 ** 6)


def righe(st, sheet, col, val):
    h = st.sheets[sheet][0]
    return [r for r in st.sheets[sheet][1:] if r[h.index(col)] == val]


class Spesa(unittest.TestCase):
    def test_tipi_sotto_scorta(self):
        _, inv = make()
        s = inv.spesa()
        per = {v["tipo"]: v for v in s["voci"]}
        self.assertEqual(per["Latte"]["stato"], "FINITO")      # caricato e scaricato: zero, scorta 2
        self.assertEqual(per["Latte"]["giacenza"], 0)
        self.assertNotIn("Pasta", per)                          # 3 pezzi contro scorta 1
        self.assertNotIn("Riso", per)                           # scorta 0: mai in spesa
        self.assertNotIn("Uova", per)                           # nessun prodotto di quel tipo
        self.assertEqual(per["Latte"]["barcode"], 8002795002995)
        self.assertEqual((s["finiti"], s["in_esaurimento"]), (1, 0))

    def test_tipo_in_esaurimento(self):
        st, inv = make()
        st.sheets["ai_tipi"][2][1] = 3                          # pasta: scorta 3, ce ne sono 3 -> confronto "<="
        s = inv.spesa()
        self.assertEqual({v["tipo"]: v["stato"] for v in s["voci"]}["Pasta"], "STA_FINENDO")


class Bozze(unittest.TestCase):
    def test_elenco_solo_aperte(self):
        _, inv = make()
        self.assertEqual([b["id"] for b in inv.bozze()], ["b1", "b2"])

    def test_conferma_crea_prodotto_e_completa_movimento_in_sospeso(self):
        st, inv = make()
        r = inv.bozza_conferma("b1", {"nome": "Biscotti frollini"})
        self.assertFalse(r["movimento"])                        # il movimento c'era gia (riga "e"): non si duplica
        self.assertEqual(len(righe(st, "movimenti", "Barcode", 8004444444444)), 1)
        m = righe(st, "movimenti", "Barcode", 8004444444444)[0]
        h = st.sheets["movimenti"][0]
        self.assertEqual((m[h.index("Prodotto")], m[h.index("Categoria")], m[h.index("Sottocategoria")]), ("Biscotti frollini", "Dispensa", "Snack e Dolci"))
        p = righe(st, "prodotti", "Barcode", 8004444444444)[0]
        self.assertEqual(p[st.sheets["prodotti"][0].index("Prodotto")], "Biscotti frollini")
        self.assertEqual(righe(st, "bozze", "ID", "b1")[0][10], "INSERITA")
        self.assertEqual([b["id"] for b in inv.bozze()], ["b2"])
        self.assertTrue(any(e["barcode"] == 8004444444444 and e["qta"] == 2 for e in inv.stock()))

    def test_conferma_senza_movimento_lo_crea(self):
        st, inv = make()
        inv.bozza_salva("b2", {"nome": "Sale", "categoria": "Dispensa", "sottocategoria": "Snack e Dolci"})
        r = inv.bozza_conferma("b2", {})
        self.assertTrue(r["movimento"])
        e = [e for e in inv.stock() if e["barcode"] == 8005555555555][0]
        self.assertEqual((e["luogo"], e["qta"]), ("Cantina", 1))

    def test_conferma_richiede_dati(self):
        _, inv = make()
        with self.assertRaises(ApiError):
            inv.bozza_conferma("b2", {})
        with self.assertRaises(ApiError):
            inv.bozza_conferma("b3", {})                        # gia inserita

    def test_scarta(self):
        st, inv = make()
        inv.bozza_scarta("b2")
        self.assertEqual(righe(st, "bozze", "ID", "b2")[0][10], "SCARTATA")
        self.assertEqual([b["id"] for b in inv.bozze()], ["b1"])


class Approvazioni(unittest.TestCase):
    def test_elenco_con_campi_modificabili(self):
        _, inv = make()
        a = {x["id"]: x for x in inv.approvazioni()}
        self.assertEqual(set(a), {"P_8001111111111", "P_8002222222222", "T_Uova", "C_2"})
        self.assertEqual(a["P_8001111111111"]["campi"]["nome"], "Penne rigate")
        self.assertEqual(a["T_Uova"]["campi"]["scorta_min"], 3)

    def test_approva_con_correzioni_applica_al_prodotto(self):
        st, inv = make()
        inv.decidi("P_8001111111111", "APPROVA", {"nome": "Penne", "categoria": "Dispensa", "sottocategoria": "Snack e Dolci", "tipo": "Pasta secca"})
        p = righe(st, "prodotti", "Barcode", 8001111111111)[0]
        h = st.sheets["prodotti"][0]
        self.assertEqual((p[h.index("Prodotto")], p[h.index("Tipo")]), ("Penne", "Pasta secca"))
        ai = righe(st, "ai_prodotti", "Barcode", 8001111111111)[0]
        hi = st.sheets["ai_prodotti"][0]
        self.assertEqual((ai[hi.index("Stato")], ai[hi.index("Nome_Suggerito")]), ("APPLICATO", "Penne"))
        self.assertEqual(righe(st, "ai_tipi", "Tipo", "Pasta secca")[0][2], "DA_APPROVARE")   # tipo nuovo: in coda, scorta 0
        self.assertEqual(righe(st, "ai_tipi", "Tipo", "Pasta secca")[0][1], 0)
        self.assertTrue(st.sheets["log_ai"][1:])                                            # registrata la modifica, annullabile

    def test_approva_non_cambia_nome_se_prodotto_verificato(self):
        st, inv = make()
        inv.decidi("P_8002222222222", "APPROVA", {"categoria": "Dispensa", "sottocategoria": "Bevande"})
        p = righe(st, "prodotti", "Barcode", 8002222222222)[0]
        h = st.sheets["prodotti"][0]
        self.assertEqual((p[h.index("Prodotto")], p[h.index("Sottocategoria")]), ("Pasta fusilli", "Bevande"))

    def test_coppia_non_valida_rifiutata(self):
        _, inv = make()
        with self.assertRaises(ApiError):
            inv.decidi("P_8001111111111", "APPROVA", {"categoria": "Frigorifero", "sottocategoria": "Bevande"})

    def test_rifiuta_e_gia_decisa(self):
        st, inv = make()
        inv.decidi("P_8001111111111", "RIFIUTA")
        self.assertEqual(righe(st, "ai_prodotti", "Barcode", 8001111111111)[0][8], "RIFIUTATO")
        with self.assertRaises(ApiError):
            inv.decidi("P_8001111111111", "APPROVA")

    def test_tipo_con_scorta(self):
        st, inv = make()
        inv.decidi("T_Uova", "APPROVA", {"scorta_min": 6})
        self.assertEqual(righe(st, "ai_tipi", "Tipo", "Uova")[0][1:3], [6, "APPROVATO"])
        with self.assertRaises(ApiError):
            inv.decidi("T_Uova", "APPROVA", {"scorta_min": 1})

    def test_categoria_proposta_applicata_dall_app(self):
        _, inv = make()
        r = inv.decidi("C_2", "APPROVA")
        self.assertIn(r["stato"], ("APPLICATA", "GIA_PRESENTE"))


if __name__ == "__main__":
    unittest.main()


class TCategorie(unittest.TestCase):
    def _inv(self):
        st = MemoryStore({
            "prodotti": [["Barcode", "Prodotto", "Categoria", "Sottocategoria"], [1, "A", "Dispensa", "Bevande"], [2, "B", "Dispensa", "Snack"]],
            "categorie": [["Categoria", "Sottocategoria", "Chiave"], ["Dispensa", "Bevande", "Dispensa_Bevande"], ["Dispensa", "Snack", "Dispensa_Snack"], ["Dispensa", "Dolci", "Dispensa_Dolci"]],
            "movimenti": [["Barcode", "Tipo", "Location", "Quantità", "Categoria", "Sottocategoria"], [1, "Carico", "Casa", 2, "Dispensa", "Bevande"]],
            "ai_categorie": [["Azione", "Categoria", "Sottocategoria", "Nuovo_Nome", "Motivo", "Prodotti_Esempio", "Stato", "Aggiornato"],
                             ["AGGIUNGI_SOTTOCATEGORIA", "Dispensa", "Conserve", "", "", "", "PROPOSTA", ""],
                             ["RINOMINA", "Dispensa", "Snack", "Dolci", "", "", "PROPOSTA", ""],
                             ["RINOMINA", "Dispensa", "", "", "", "", "PROPOSTA", ""]],
        })
        return st, Inventory(st, ttl=20, clock=lambda: 1000.0)

    def test_aggiungi_e_rinomina_con_unione(self):
        st, inv = self._inv()
        self.assertEqual(inv.decidi("C_2", "APPROVA")["stato"], "APPLICATA")
        self.assertIn(["Dispensa", "Conserve", "Dispensa_Conserve"], st.sheets["categorie"][1:])
        inv.decidi("C_3", "APPROVA")
        cats = [(r[0], r[1]) for r in st.sheets["categorie"][1:] if r[0]]
        self.assertEqual(cats, [("Dispensa", "Bevande"), ("Dispensa", "Dolci"), ("Dispensa", "Conserve")])   # Snack->Dolci unito al doppione
        self.assertEqual(st.sheets["prodotti"][2][3], "Dolci")

    def test_proposta_incompleta_e_rifiuto(self):
        st, inv = self._inv()
        with self.assertRaises(ApiError):
            inv.decidi("C_4", "APPROVA")
        self.assertEqual(st.sheets["ai_categorie"][3][6], "ERRORE")
        self.assertEqual(inv.decidi("C_2", "RIFIUTA")["stato"], "RIFIUTATO")


class TVoce(unittest.TestCase):
    def _inv(self):
        st = MemoryStore({
            "prodotti": [["Barcode", "Prodotto", "Marca", "Categoria", "Sottocategoria", "Tipo"],
                         [1, "Latte UHT", "Parmalat", "Frigorifero", "Latticini", "Latte"],
                         [2, "Biscotti Oro", "Saiwa", "Dispensa", "Snack", "Biscotti"],
                         [3, "Pasta Penne", "Barilla", "Dispensa", "Pasta", "Pasta"]],
            "movimenti": [["Barcode", "Tipo", "Location", "Quantità", "Prodotto", "Categoria", "Sottocategoria"],
                          [1, "Carico", "Casa", 3, "Latte UHT", "Frigorifero", "Latticini"], [1, "Carico", "Cantina", 2, "Latte UHT", "Frigorifero", "Latticini"],
                          [2, "Carico", "Casa", 1, "Biscotti Oro", "Dispensa", "Snack"], [2, "Scarico", "Casa", 1, "Biscotti Oro", "Dispensa", "Snack"]],
            "ai_tipi": [["Tipo", "Scorta_min", "Stato"], ["Biscotti", 2, "APPROVATO"], ["Pasta", 1, "APPROVATO"]],
            "categorie": [["Categoria", "Sottocategoria"], ["Frigorifero", "Latticini"]],
        })
        return Inventory(st, ttl=20, clock=lambda: 1000.0)

    def test_cerca(self):
        inv = self._inv()
        self.assertEqual(inv.voce_cerca("il latte"), "Hai Latte UHT: 5 pezzi. 3 casa, 2 cantina.")
        self.assertIn("Non hai più", inv.voce_cerca("dove sono i biscotti"))
        self.assertIn("Non trovo", inv.voce_cerca("zucchero"))

    def test_manca(self):
        t = self._inv().voce_manca()
        self.assertIn("biscotti", t)
        self.assertTrue(t.endswith("."))
