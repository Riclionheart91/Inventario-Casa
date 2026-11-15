import socket
import unittest

from PIL import Image

from app import protocollo as P


def tutto(s):
    s.settimeout(0.2)
    out = b""
    try:
        while True:
            d = s.recv(65536)
            if not d:
                break
            out += d
    except socket.timeout:
        pass
    return out


class TestProtocollo(unittest.TestCase):
    def test_pacchetto(self):
        self.assertEqual(P.pacchetto(0x12, 1).hex(" "), "64 12 01 00 00 00 00 00 00 9b")
        self.assertEqual(P.pacchetto(0x72, 3, b"\x01").hex(" "), "64 72 03 01 00 01 00 00 00 00 9b")

    def test_raster_dimensioni_e_bit(self):
        bianca = Image.new("L", (280, 96), 255)
        self.assertEqual(P.raster(bianca), bytes(3360))
        nera = Image.new("L", (280, 96), 0)
        self.assertEqual(P.raster(nera), b"\xff" * 3360)
        un = Image.new("L", (280, 96), 255)
        un.putpixel((0, 0), 0)                      # angolo in alto a sinistra -> ultima riga, primo bit del primo byte
        r = P.raster(un)
        self.assertEqual(r[279 * 12], 0x80)
        self.assertEqual(sum(bin(b).count("1") for b in r), 1)

    def test_misura_sbagliata(self):
        with self.assertRaises(ValueError):
            P.raster(Image.new("L", (96, 280), 255))

    def test_lavoro(self):
        saluto, prep, job = P.lavoro(Image.new("L", (280, 96), 255), 9)
        self.assertEqual(saluto, P.pacchetto(0x12, 1) + P.pacchetto(0x11, 2))
        self.assertEqual(prep, P.pacchetto(0x72, 3, b"\x01"))
        self.assertTrue(job.startswith(P.pacchetto(0x0A, 4, b"\x19") + P.pacchetto(0x09, 5, b"\x09") +
                                       P.pacchetto(0x03, 6, bytes.fromhex("02 20 03")) + P.pacchetto(0x02, 7, b"\x09\x00")))
        self.assertTrue(job.endswith(P.pacchetto(0x03, 8 + 12, bytes.fromhex("01 20 03"))))
        self.assertEqual(len(job), 11 + 11 + 13 + 12 + 11 * (288 + 10) + (192 + 10) + 13)

    def test_offset_prudente(self):
        P.lavoro(Image.new("L", (280, 96), 255), 17)
        for o in (-1, 65, 2304):
            with self.assertRaises(ValueError):
                P.lavoro(Image.new("L", (280, 96), 255), o)

    def test_invia_con_risposta(self):
        a, b = socket.socketpair()
        b.sendall(bytes.fromhex("64 12 01 02 00 aa bb 00 00 00 00 9b"))   # la stampante si presenta
        log = []
        P.invia(a, Image.new("L", (280, 96), 255), 9, log=log.append, pausa=lambda t: None, attesa_finale=0)
        a.close()
        saluto, prep, job = P.lavoro(Image.new("L", (280, 96), 255), 9)
        self.assertEqual(tutto(b), saluto + prep + job)
        self.assertTrue(log[0].startswith("Risposta al saluto: 12 byte: 64 12 01"))
        self.assertTrue(any(r.startswith("Lavoro inviato: 3540 byte") for r in log))
        b.close()

    def test_invia_senza_risposta_non_stampa(self):
        a, b = socket.socketpair()
        with self.assertRaises(RuntimeError):
            P.invia(a, Image.new("L", (280, 96), 255), 9, log=lambda t: None, pausa=lambda t: None)
        a.close()
        saluto, _, _ = P.lavoro(Image.new("L", (280, 96), 255), 9)
        self.assertEqual(tutto(b), saluto)                                   # solo il saluto, nessun dato di stampa
        b.close()


if __name__ == "__main__":
    unittest.main()
