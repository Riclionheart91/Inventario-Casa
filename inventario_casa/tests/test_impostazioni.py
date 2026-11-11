import os
import tempfile
import unittest

from app import impostazioni as I


class TImpostazioni(unittest.TestCase):
    def setUp(self):
        self.i = I.Impostazioni(os.path.join(tempfile.mkdtemp(), "i.json"))

    def test_default_e_salvataggio(self):
        self.assertFalse(self.i.get("ai_sospesa")); self.assertEqual(self.i.get("auto_soglia"), 95)
        r = self.i.imposta({"ai_sospesa": True, "ai_limite": "40", "scad_ora": "07:30", "tema": "chiaro"})
        self.assertTrue(r["ai_sospesa"]); self.assertEqual((r["ai_limite"], r["scad_ora"], r["tema"]), (40, "07:30", "chiaro"))
        self.assertEqual(I.Impostazioni(self.i.percorso).get("ai_limite"), 40)

    def test_valori_non_validi_non_salvano_niente(self):
        for k, v in (("ai_limite", "abc"), ("scad_ora", "25:00"), ("tema", "rosa"), ("inesistente", 1)):
            with self.assertRaises(ValueError):
                self.i.imposta({"ai_sospesa": True, k: v})
        self.assertFalse(self.i.get("ai_sospesa"))

    def test_limiti_numerici(self):
        self.assertEqual(self.i.imposta({"auto_soglia": 10})["auto_soglia"], 80)
        self.assertEqual(self.i.imposta({"mov_qta": 0})["mov_qta"], 1)


if __name__ == "__main__":
    unittest.main()
