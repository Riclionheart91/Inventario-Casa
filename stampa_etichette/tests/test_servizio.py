import io
import json
import threading
import unittest
import urllib.error
import urllib.request

from PIL import Image

from app import servizio as S


class Finta:
    mac = "AA:BB:CC:DD:EE:FF"

    def __init__(self, errore=None):
        self.viste, self.errore = [], errore

    def stampa(self, img):
        if self.errore:
            raise self.errore
        self.viste.append(img.size)


def png(size=(280, 96)):
    b = io.BytesIO()
    Image.new("L", size, 255).save(b, "PNG")
    return b.getvalue()


class TestServizio(unittest.TestCase):
    def avvia(self, st):
        self.srv = S.fai_server(st, "codice-segreto", "t", host="127.0.0.1", porta=0)
        self.url = "http://127.0.0.1:%d" % self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)

    def chiama(self, metodo, percorso, corpo=None, token="codice-segreto"):
        r = urllib.request.Request(self.url + percorso, data=corpo, method=metodo, headers={"X-Token": token} if token is not None else {})
        try:
            with urllib.request.urlopen(r, timeout=5) as x:
                return x.status, json.loads(x.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_stampa_ok(self):
        st = Finta()
        self.avvia(st)
        self.assertEqual(self.chiama("POST", "/stampa", png()), (200, {"ok": True}))
        self.assertEqual(st.viste, [(280, 96)])

    def test_token(self):
        st = Finta()
        self.avvia(st)
        self.assertEqual(self.chiama("POST", "/stampa", png(), token="sbagliato")[0], 401)
        self.assertEqual(self.chiama("POST", "/stampa", png(), token=None)[0], 401)
        self.assertEqual(self.chiama("GET", "/stato", token="x")[0], 401)
        self.assertEqual(st.viste, [])
        self.assertEqual(self.chiama("GET", "/stato")[0], 200)

    def test_immagine_non_valida(self):
        st = Finta()
        self.avvia(st)
        self.assertEqual(self.chiama("POST", "/stampa", png((96, 280)))[0], 400)
        self.assertEqual(self.chiama("POST", "/stampa", b"non e un png")[0], 400)
        self.assertEqual(self.chiama("POST", "/stampa", b"")[0], 400)
        self.assertEqual(self.chiama("POST", "/stampa", b"x" * (S.MAX_BYTE + 1))[0], 400)
        self.assertEqual(st.viste, [])

    def test_errore_della_stampante(self):
        self.avvia(Finta(S.ErroreStampa("La stampante non risponde", 504)))
        st, corpo = self.chiama("POST", "/stampa", png())
        self.assertEqual((st, corpo["errore"]), (504, "La stampante non risponde"))

    def test_errore_imprevisto_non_butta_giu_il_servizio(self):
        self.avvia(Finta(ValueError("boom")))
        self.assertEqual(self.chiama("POST", "/stampa", png())[0], 500)
        self.assertEqual(self.chiama("GET", "/stato")[0], 200)

    def test_senza_token_non_parte(self):
        with self.assertRaises(ValueError):
            S.fai_server(Finta(), "")


if __name__ == "__main__":
    unittest.main()
