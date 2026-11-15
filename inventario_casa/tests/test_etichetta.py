import io
import random
import unittest

from app import etichetta as E
from app.ext_etichetta import posizione

try:
    import cv2
    import numpy as np
except ImportError:      # il lettore di prova c'e solo dove e installato OpenCV
    cv2 = None


def _img(mod, px=6):
    a = np.array([[0 if v else 255 for v in r] for r in mod], dtype="uint8")
    a = np.kron(a, np.ones((px, px), dtype="uint8"))
    return cv2.copyMakeBorder(a, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=255)


class TestQr(unittest.TestCase):
    def test_dimensioni_e_riquadri(self):
        m = E.qr_moduli("8002795002995")
        self.assertEqual((len(m), len(m[0])), (21, 21))
        for y0, x0 in ((0, 0), (0, 14), (14, 0)):          # i tre riquadri di posizione
            self.assertTrue(all(m[y0][x0 + i] for i in range(7)))
            self.assertTrue(m[y0 + 3][x0 + 3])
        self.assertTrue(m[13][8])                           # modulo scuro fisso

    def test_solo_cifre(self):
        for k in ("", "12a4", "1" * 42, None):
            with self.assertRaises(ValueError):
                E.qr_moduli(k)

    @unittest.skipIf(cv2 is None, "serve OpenCV per leggere il QR")
    def test_si_legge(self):
        det = cv2.QRCodeDetector()
        random.seed(5)
        codici = ["8002795002995", "2999738560932", "123456", "9" * 24] + \
                 ["".join(random.choice("0123456789") for _ in range(random.choice([8, 12, 13, 14]))) for _ in range(60)]
        ko = [c for c in codici if det.detectAndDecode(_img(E.qr_moduli(c)))[0] != c]
        self.assertLessEqual(len(ko), 2, ko)               # il rilevatore sbaglia a volte da solo a certe scale


class TestEtichetta(unittest.TestCase):
    def test_png_a_un_bit(self):
        from PIL import Image
        im = Image.open(io.BytesIO(E.etichetta_png("8002795002995", "Latte fresco intero 1 l", "Cantina")))
        self.assertEqual((im.size, im.mode), ((280, 96), "1"))

    def test_nome_lungo_e_vuoto(self):
        E.etichetta_png("8002795002995", "x " * 200, "Dispensa, Cantina, Garage")
        E.etichetta_png("8002795002995", "", "")

    def test_posizione(self):
        g = [{"luogo": "Casa", "qta": 2}, {"luogo": "Casa", "qta": 1}, {"luogo": "Cantina", "qta": 0}, {"luogo": "Garage", "qta": 1}]
        self.assertEqual(posizione(g), "Casa, Garage")
        self.assertEqual(posizione([]), "")
        self.assertTrue(posizione([{"luogo": l, "qta": 1} for l in "ABC"]).endswith("…"))


if __name__ == "__main__":
    unittest.main()
