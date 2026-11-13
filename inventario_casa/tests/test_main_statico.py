import ast
import os
import unittest

MAIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "main.py")


class TMainStatico(unittest.TestCase):
    """main.py non si importa nei test (manca FastAPI): controlli sul testo."""

    def test_nessuna_funzione_richiama_se_stessa_per_errore(self):
        alb = ast.parse(open(MAIN, encoding="utf-8").read())
        for f in [n for n in alb.body if isinstance(n, ast.FunctionDef)]:
            chiamate = [c for c in ast.walk(f) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == f.name]
            # le funzioni di cache (inv, off_, ...) non si richiamano; solo_lettura in particolare non deve farlo
            if f.name == "solo_lettura":
                self.assertEqual(chiamate, [], "solo_lettura() richiama se stessa")

    def test_mount_statico_per_ultimo(self):
        righe = [r for r in open(MAIN, encoding="utf-8").read().splitlines() if r.strip()]
        self.assertTrue(righe[-1].startswith('app.mount("/"'))


if __name__ == "__main__":
    unittest.main()
