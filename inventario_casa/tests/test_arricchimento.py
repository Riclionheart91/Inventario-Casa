import os, sys, tempfile, unittest
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import ai
from app.arricchimento import Arricchitore
from app.service import Inventory
from app.store import MemoryStore


def make():
    st = MemoryStore({"prodotti": [
        ["Barcode", "Prodotto", "Marca", "Confezione", "Immagine", "Dettagli prodotto", "Composizione", "API Status", "Aggiornato il"],
        [1, "Latte mio", "", "", "", "", "", "", ""],                           # incompleto: si riempie solo il vuoto
        [2, "Sconosciuto", "", "", "", "", "", "", ""],                         # non trovato: non cambia
        [3, "Pasta", "Barilla", "500 g", "http://i", "Sugar, salt", "Ingredients: flour", "✅ App (X)", "01/01/2026"]]})   # completo ma da tradurre
    d = tempfile.mkdtemp()
    return st, Inventory(st, ttl=0), os.path.join(d, "a.json")


INFO = {"1": {"nome": "Altro nome", "marca": "Parmalat", "confezione": "1 l", "immagine": "http://img", "fonte": "OFF", "dettagli": "", "composizione": "", "nutrizione": "", "punteggi": ""}}
TR = lambda testi: [t.replace("Sugar, salt", "Zucchero, sale").replace("Ingredients: flour", "Ingredienti: farina") for t in testi]


class T(unittest.TestCase):
    def test_riempie_solo_vuoti_e_non_trovato_non_cambia(self):
        st, inv, f = make()
        a = Arricchitore(inv, lambda bc: INFO.get(bc), TR, f, oggi=lambda: datetime(2026, 10, 30, 3, 0))
        r = a.esegui(10)
        p = st.sheets["prodotti"]
        self.assertEqual(p[1][1:], ["Latte mio", "Parmalat", "1 l", "http://img", "", "", "✅ App (OFF)", "30/10/2026"])   # nome gia presente: intatto
        self.assertEqual(p[2][1:], ["Sconosciuto", "", "", "", "", "", "", ""])                                         # nulla di cambiato
        self.assertEqual((r["completati"], r["non_trovati"]), (1, 1))
        self.assertEqual(p[3][5:7], ["Zucchero, sale", "Ingredienti: farina"])   # tradotto
        self.assertEqual(r["tradotti"], 2)

    def test_non_trovato_non_si_riprova_subito_e_traduzione_non_si_ripete(self):
        st, inv, f = make()
        chiam = []
        a = Arricchitore(inv, lambda bc: chiam.append(bc) or INFO.get(bc), TR, f, oggi=lambda: datetime(2026, 10, 30))
        a.esegui(10); chiam.clear()
        r = a.esegui(10)
        self.assertEqual(chiam, [])               # 2 era non trovato: attesa 30 giorni
        self.assertEqual(r["tradotti"], 0)
        self.assertFalse(a.da_fare_oggi())

    def test_traduci_gemini_valida_le_risposte(self):
        risp = {"candidates": [{"content": {"parts": [{"text": '{"r":[{"id":0,"it":"Zucchero"},{"id":1,"it":""},{"id":2,"it":"x"}]}'}]}}]}
        out = ai.traduci(["Sugar", "Salt", "Tre parole lunghe qui"], "k", post=lambda *a: risp)
        self.assertEqual(out, ["Zucchero", None, None])   # vuota o troppo corta: scartata
        self.assertEqual(ai.traduci(["a"], "", post=lambda *a: risp), [None])


if __name__ == "__main__":
    unittest.main()
