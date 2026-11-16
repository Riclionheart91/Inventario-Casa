"""Servizio di stampa: riceve da rete locale un'etichetta PNG (280 x 96 punti) e la stampa sulla X1.
Protetto da un codice condiviso (X-Token). Una sola stampa alla volta."""
import errno
import hmac
import io
import json
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .protocollo import LUNGHEZZA, TESTA, invia

MAX_BYTE = 64 * 1024
TRANSITORI = (errno.EHOSTDOWN, errno.EHOSTUNREACH, errno.ETIMEDOUT, errno.EBUSY, errno.ECONNRESET)


class ErroreStampa(Exception):
    def __init__(self, msg, stato=502):
        super().__init__(msg)
        self.stato = stato


class Stampante:
    def __init__(self, mac, canale=1, offset=9, secondi=30, attesa_finale=3.0, log=print):
        self.mac, self.canale, self.offset, self.secondi, self.attesa_finale, self.log = mac, canale, offset, secondi, attesa_finale, log
        self.lock = threading.Lock()

    def _connetti(self):
        fine = time.monotonic() + self.secondi
        ultimo = None
        while True:
            s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            try:
                s.settimeout(10)
                s.connect((self.mac, self.canale))
                return s
            except OSError as e:
                s.close()
                ultimo = e
                if e.errno not in TRANSITORI or time.monotonic() >= fine:
                    break
                time.sleep(1.5)
        if ultimo is not None and ultimo.errno in TRANSITORI:
            raise ErroreStampa("La stampante non risponde: accendila, avvicinala e scollegala dal telefono.", 504)
        raise ErroreStampa("Connessione Bluetooth non riuscita: %s" % ultimo, 502)

    def stampa(self, img):
        if not self.lock.acquire(timeout=self.secondi + 20):
            raise ErroreStampa("Un'altra stampa e ancora in corso.", 409)
        try:
            s = self._connetti()
            try:
                invia(s, img, self.offset, log=self.log, attesa_finale=self.attesa_finale)
            except RuntimeError as e:
                raise ErroreStampa("La stampante e collegata ma %s" % e, 502)
            except OSError as e:
                raise ErroreStampa("Collegamento interrotto durante la stampa: %s" % e, 502)
            finally:
                s.close()
        finally:
            self.lock.release()


def immagine_da_png(dati: bytes):
    """Valida e apre il PNG: deve essere esattamente 280 x 96 punti."""
    from PIL import Image
    if not dati or len(dati) > MAX_BYTE:
        raise ErroreStampa("Immagine mancante o troppo grande", 400)
    try:
        img = Image.open(io.BytesIO(dati))
        img.load()
    except Exception:
        raise ErroreStampa("Non e un'immagine PNG valida", 400)
    if img.size != (LUNGHEZZA, TESTA):
        raise ErroreStampa("L'etichetta deve essere %d x %d punti, non %d x %d" % (LUNGHEZZA, TESTA, img.size[0], img.size[1]), 400)
    return img.convert("L")


def fai_server(stampante, token, versione="", host="0.0.0.0", porta=8770):
    if not token:
        raise ValueError("serve un codice condiviso (token)")

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):          # niente righe per ogni richiesta (il token non deve finire nei registri)
            pass

        def _r(self, stato, corpo):
            b = json.dumps(corpo).encode()
            self.send_response(stato)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def _ok(self):
            return hmac.compare_digest(self.headers.get("X-Token", "").encode("utf-8", "replace"), token.encode("utf-8"))

        def do_GET(self):
            if self.path != "/stato":
                return self._r(404, {"errore": "non trovato"})
            if not self._ok():
                return self._r(401, {"errore": "codice non valido"})
            self._r(200, {"ok": True, "versione": versione, "stampante": stampante.mac})

        def do_POST(self):
            self.connection.settimeout(15)      # un client che si ferma a meta non tiene occupato il servizio
            if self.path != "/stampa":
                return self._r(404, {"errore": "non trovato"})
            if not self._ok():
                return self._r(401, {"errore": "codice non valido"})
            try:
                n = int(self.headers.get("Content-Length", "0"))
                if not 0 < n <= MAX_BYTE:
                    raise ErroreStampa("Immagine mancante o troppo grande", 400)
                img = immagine_da_png(self.rfile.read(n))
                stampante.stampa(img)
            except ErroreStampa as e:
                return self._r(e.stato, {"errore": str(e)})
            except Exception as e:           # non far cadere il servizio per un errore imprevisto
                return self._r(500, {"errore": "Errore imprevisto: %s" % e})
            self._r(200, {"ok": True})

    return ThreadingHTTPServer((host, porta), H)


def main():
    mac = os.environ.get("STAMPANTE_MAC", "").strip().upper()
    token = os.environ.get("STAMPANTE_TOKEN", "")
    porta = int(os.environ.get("STAMPANTE_PORTA", "8770") or 8770)
    if not token or len(token) < 8:
        print("ERRORE: imposta nelle opzioni un codice condiviso (token) di almeno 8 caratteri e riavvia", flush=True)
        return 1
    st = Stampante(mac, int(os.environ.get("STAMPANTE_CANALE", "1") or 1), int(os.environ.get("STAMPANTE_OFFSET", "9") or 9),
                   log=lambda t: print(t, flush=True))
    srv = fai_server(st, token, os.environ.get("APP_VERSION", ""), porta=porta)
    print("Servizio di stampa attivo sulla porta %d (stampante %s)" % (porta, mac), flush=True)
    srv.serve_forever()
    return 0
