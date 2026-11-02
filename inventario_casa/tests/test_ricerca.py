import json, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import ai, ricerca

DDG = '''<html><body>
<div class="result results_links results_links_deep web-result"><div class="links_main links_deep result__body">
<h2 class="result__title"><a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.esempio.it%2Fprodotto%2F8076800195057&amp;rut=abc">Spaghetti n.5 <b>Barilla</b> 500 g</a></h2>
<a class="result__snippet" href="//duckduckgo.com/l/?uddg=x">Pasta di semola &amp; <b>grano</b> duro, codice 8076800195057.</a></div></div>
<div class="result"><div class="links_main links_deep result__body">
<h2 class="result__title"><a class="result__a" href="https://altro.it/p">Altro sito</a></h2>
<a class="result__snippet" href="x">Secondo risultato</a></div></div>
</body></html>'''


class TRicerca(unittest.TestCase):
    def test_ddg_estrae_titolo_url_e_snippet(self):
        r = ricerca.ddg("x", http=lambda *a, **k: DDG)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0]["url"], "https://www.esempio.it/prodotto/8076800195057")
        self.assertEqual(r[0]["titolo"], "Spaghetti n.5 Barilla 500 g")
        self.assertIn("grano duro", r[0]["snippet"]); self.assertEqual(r[1]["url"], "https://altro.it/p")

    def test_fonti_con_chiave_e_ripiego(self):
        brave = json.dumps({"web": {"results": [{"title": "T", "url": "https://b.it/x", "description": "D"}]}})
        r = ricerca.cerca("q", {"BRAVE_SEARCH_KEY": "k"}, http=lambda url, *a, **k: brave if "brave" in url else DDG)
        self.assertEqual(r[0]["url"], "https://b.it/x")
        r = ricerca.cerca("q", {"BRAVE_SEARCH_KEY": "k"}, http=lambda url, *a, **k: None if "brave" in url else DDG)   # Brave non risponde: DuckDuckGo
        self.assertEqual(len(r), 2)
        self.assertEqual(ricerca.fonte({}), "DuckDuckGo"); self.assertEqual(ricerca.fonte({"SERPER_KEY": "k"}), "Serper")

    def test_estratto_tiene_la_parte_col_codice(self):
        html = "<head><title>t</title></head><script>var a=1</script><body>" + "x " * 800 + "EAN 8076 8001 95057 Spaghetti" + " y" * 800 + "</body>"
        e = ricerca.estratto(html, "8076800195057")
        self.assertNotIn("var a", e)
        self.assertIn("Spaghetti", e)
        self.assertLessEqual(len(e), 2200)

    def test_contesto_compone_testo_e_indirizzi(self):
        t, urls = ricerca.contesto(["a"], "8076800195057", {}, http=lambda *a, **k: DDG, scarica=lambda u: "<body>Spaghetti 8076800195057 Nutri-Score A</body>")
        self.assertIn("[1] Spaghetti n.5 Barilla 500 g", t); self.assertIn("Dalla pagina: Spaghetti 8076800195057", t)
        self.assertEqual(urls, ["https://www.esempio.it/prodotto/8076800195057", "https://altro.it/p"])
        self.assertEqual(ricerca.contesto(["a"], "1", {}, http=lambda *a, **k: "<html></html>", scarica=lambda u: None), ("", []))

    def test_ai_legge_i_risultati_senza_strumento_di_ricerca(self):
        visto = {}

        def post(url, k, corpo, t):
            visto["corpo"] = corpo
            return {"candidates": [{"content": {"parts": [{"text": '{"nome":"Spaghetti n.5","marca":"Barilla","confezione":"500 g","url":""}'}]}}]}
        r = ai.cerca_web("8076800195057", "K", "m", "r", post=post, contesto="[1] Spaghetti Barilla")
        self.assertEqual((r["nome"], r["marca"]), ("Spaghetti n.5", "Barilla"))
        self.assertNotIn("tools", visto["corpo"])
        self.assertIn("RISULTATI DI RICERCA", visto["corpo"]["contents"][0]["parts"][0]["text"])
        ai.integra_scheda("8076800195057", "Spaghetti", "Barilla", "500 g", "K", post=post, contesto="[1] Nutri-Score A")
        self.assertNotIn("tools", visto["corpo"])
        self.assertIn("SOLO se compaiono nei risultati", visto["corpo"]["contents"][0]["parts"][0]["text"])


if __name__ == "__main__":
    unittest.main()
