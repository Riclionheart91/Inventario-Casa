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


class TWeb(unittest.TestCase):
    def test_web_riempie_immagine_solo_se_la_pagina_ha_il_codice(self):
        from app import pagina
        html_ok = '<html><head><meta property="og:image" content="/img/p/8001.jpg"></head><body>EAN 8 0 0 1 990037511 8001990037511</body></html>'
        html_altro = '<meta property="og:image" content="https://x/img/a.jpg"><body>altro prodotto 1234567890123</body>'
        self.assertEqual(pagina.immagine_da_pagina("https://negozio.it/p/1", "8001990037511", lambda u: html_ok), "https://negozio.it/img/p/8001.jpg")
        self.assertIsNone(pagina.immagine_da_pagina("https://negozio.it/p/2", "8001990037511", lambda u: html_altro))
        self.assertFalse(pagina.indirizzo_pubblico("http://192.168.1.113:8123/x"))
        self.assertFalse(pagina.indirizzo_pubblico("http://localhost/x"))

    def test_arricchitore_usa_il_web_solo_dopo_gli_archivi(self):
        st, inv, f = make()
        web = lambda bc: {"nome": "Sconosciuto vero", "marca": "Marca X", "confezione": "1 l", "immagine": "https://n.it/i.jpg", "fonte": "Web"} if bc == "2" else None
        a = Arricchitore(inv, lambda bc: INFO.get(bc), TR, f, oggi=lambda: datetime(2026, 10, 31), web=web)
        r = a.esegui(10)
        p = st.sheets["prodotti"]
        self.assertEqual(p[2][1:5], ["Sconosciuto", "Marca X", "1 l", "https://n.it/i.jpg"])   # nome gia presente: intatto
        self.assertEqual(p[2][7], "🔶 Web (AI)")
        self.assertEqual(r["da_web"], 1)

    def test_cerca_web_parsing(self):
        risp = {"candidates": [{"content": {"parts": [{"text": '{"nome":"Sale","marca":"M","confezione":"1 kg","url":"https://a.it/p"}'}]},
                                "groundingMetadata": {"groundingChunks": [{"web": {"uri": "https://b.it/x"}}]}}]}
        r = ai.cerca_web("8001990037511", "k", post=lambda *a: risp)
        self.assertEqual(r["urls"], ["https://a.it/p", "https://b.it/x"])
        self.assertIsNone(ai.cerca_web("8001990037511", "", post=lambda *a: risp))
