"""Protocollo della ORGBRO X1 (rotolo 12 x 40 mm), ricavato dalla cattura del traffico dell'app XEasyLabel fatta da HWMurxer
(https://github.com/HWMurxer/orgbro-x1-text-labels, licenza MIT). Qui sono riscritti solo i fatti del protocollo, non il codice dell'altro progetto.

Pacchetto: 64 CMD SEQ LEN_LO LEN_HI PAYLOAD 00 00 00 00 9B. Immagine: 280 x 96 punti, ruotata di 90 gradi e inviata come
96 punti per riga, 1 bit per punto, bit piu alto per primo, 1 = nero."""
import socket
import time

LUNGHEZZA = 280
TESTA = 96
BYTE_RASTER = 3360          # 280 righe x 12 byte
OFFSET_PREDEFINITO = 9      # posizione di stampa registrata nella cattura (punti)


def pacchetto(cmd: int, seq: int, payload: bytes = b"") -> bytes:
    return bytes((0x64, cmd, seq)) + len(payload).to_bytes(2, "little") + payload + b"\x00\x00\x00\x00\x9b"


def raster(img) -> bytes:
    """Immagine 280 x 96 (Pillow) -> 3360 byte nel formato della testina."""
    from PIL import Image
    if img.size != (LUNGHEZZA, TESTA):
        raise ValueError("l'etichetta deve essere %d x %d punti, non %s" % (LUNGHEZZA, TESTA, img.size))
    r = img.transpose(Image.Transpose.ROTATE_90).convert("L")
    px, out = r.load(), bytearray()
    for y in range(LUNGHEZZA):
        for x0 in range(0, TESTA, 8):
            v = 0
            for b in range(8):
                if px[x0 + b, y] < 128:
                    v |= 1 << (7 - b)
            out.append(v)
    return bytes(out)


def lavoro(img, offset: int = OFFSET_PREDEFINITO):
    """(saluto, preparazione, lavoro) come pacchetti pronti da inviare."""
    if not 0 <= offset <= 64:
        raise ValueError("offset fuori dai limiti prudenziali (0-64 punti)")
    dati = raster(img)
    assert len(dati) == BYTE_RASTER
    saluto = pacchetto(0x12, 0x01) + pacchetto(0x11, 0x02)
    prep = pacchetto(0x72, 0x03, b"\x01")
    j = bytearray()
    j += pacchetto(0x0A, 0x04, b"\x19")
    j += pacchetto(0x09, 0x05, b"\x09")
    j += pacchetto(0x03, 0x06, bytes.fromhex("02 20 03"))
    j += pacchetto(0x02, 0x07, offset.to_bytes(2, "little"))      # posizione di stampa, little-endian (09 00 = 9 punti)
    seq = 0x08
    for i in range(0, len(dati), 288):
        j += pacchetto(0x00, seq, dati[i:i + 288])
        seq += 1
    j += pacchetto(0x03, seq, bytes.fromhex("01 20 03"))
    return saluto, prep, bytes(j)


def _svuota(s, attesa=0.05) -> bytes:
    """Legge quello che la stampante ha risposto (stato), senza aspettare."""
    s.settimeout(attesa)
    out = b""
    while True:
        try:
            d = s.recv(4096)
        except (socket.timeout, BlockingIOError):
            return out
        if not d:
            return out
        out += d


def invia(s, img, offset: int = OFFSET_PREDEFINITO, log=print, pausa=time.sleep):
    """Stampa l'immagine su una connessione RFCOMM aperta. Si ferma prima di stampare se la stampante non risponde al saluto."""
    saluto, prep, job = lavoro(img, offset)
    s.sendall(saluto)
    pausa(1.05)                                   # la stampante ha bisogno di tempo per presentarsi: comandi troppo presto = avanzamenti a vuoto
    ident = _svuota(s)
    log("Risposta al saluto: %d byte %s" % (len(ident), ident[:48].hex(" ")))
    if not ident:
        raise RuntimeError("la stampante non risponde al saluto: non invio nulla")
    s.sendall(prep)
    pausa(1.05)
    log("Risposta alla preparazione: %d byte" % len(_svuota(s)))
    for i in range(0, len(job), 255):             # blocchi da 255 byte, breve pausa e lettura dello stato dopo ciascuno
        s.sendall(job[i:i + 255])
        pausa(0.03)
        _svuota(s)
    pausa(1.2)
    fine = _svuota(s)
    log("Lavoro inviato: %d byte (%d pacchetti di immagine). Ultima risposta: %d byte" % (len(job), 12, len(fine)))
