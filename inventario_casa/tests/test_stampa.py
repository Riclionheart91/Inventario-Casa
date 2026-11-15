import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from app.ext_etichetta import manda_a_stampante


def server(stato, corpo):
    visti = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            n = int(self.headers["Content-Length"])
            visti.append((self.path, self.headers.get("X-Token"), self.rfile.read(n)))
            b = json.dumps(corpo).encode()
            self.send_response(stato)
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

    s = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, "http://127.0.0.1:%d" % s.server_address[1], visti


class TestMandaAStampante(unittest.TestCase):
    def test_ok(self):
        s, url, visti = server(200, {"ok": True})
        self.addCleanup(s.shutdown)
        manda_a_stampante(b"PNG", url + "/", "tok")
        self.assertEqual(visti, [("/stampa", "tok", b"PNG")])

    def test_errore_del_servizio_con_messaggio(self):
        s, url, _ = server(504, {"errore": "La stampante non risponde"})
        self.addCleanup(s.shutdown)
        with self.assertRaises(RuntimeError) as c:
            manda_a_stampante(b"PNG", url, "tok")
        self.assertEqual(str(c.exception), "La stampante non risponde")

    def test_servizio_spento(self):
        with self.assertRaises(RuntimeError) as c:
            manda_a_stampante(b"PNG", "http://127.0.0.1:9", "tok", timeout=2)
        self.assertIn("non è raggiungibile", str(c.exception))


if __name__ == "__main__":
    unittest.main()
