import unittest
from app.analisi import analizza


class TAnalisi(unittest.TestCase):
    def test_web_con_nome_la_foto_non_si_legge(self):
        chiamate = []
        sug = lambda n, m, c: {"categoria": "Dispensa", "sottocategoria": "Pasta", "tipo": "Pasta", "tipo_nuovo": False}
        a = analizza(lambda: {"nome": "Spaghetti", "marca": "Barilla", "confezione": "500 g", "immagine": "https://x/i.jpg"}, sug,
                     lambda: chiamate.append(1) or {"nome": "altro"})
        self.assertEqual((a["nome"], a["categoria"], a["immagine"], a["fonte"][:3]), ("Spaghetti", "Dispensa", "https://x/i.jpg", "Web"))
        self.assertEqual(chiamate, [])

    def test_web_senza_categoria_completa_con_la_foto(self):
        a = analizza(lambda: {"nome": "Spaghetti", "marca": "", "confezione": ""}, lambda n, m, c: None,
                     lambda: {"nome": "diverso", "categoria": "Dispensa", "sottocategoria": "Pasta", "tipo": "Pasta"})
        self.assertEqual((a["nome"], a["categoria"], a["tipo"]), ("Spaghetti", "Dispensa", "Pasta"))

    def test_web_vuoto_si_legge_la_foto(self):
        a = analizza(lambda: None, lambda *x: None, lambda: {"nome": "Sale", "categoria": "Dispensa"}, immagine="https://db/i.jpg")
        self.assertEqual((a["nome"], a["immagine"]), ("Sale", "https://db/i.jpg"))

    def test_errore_nel_web_non_blocca(self):
        def web():
            raise RuntimeError("rete")
        self.assertEqual(analizza(web, lambda *x: None, lambda: {"nome": "Sale"})["nome"], "Sale")

    def test_niente_di_niente(self):
        self.assertIsNone(analizza(lambda: None, lambda *x: None, lambda: None))


if __name__ == "__main__":
    unittest.main()
