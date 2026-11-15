"""Fase 1: prova di connessione Bluetooth Classic (RFCOMM) alla stampante. NON invia nessun dato: apre e chiude la connessione."""
import errno
import os
import re
import socket
import sys
import time

MAC = os.environ.get("STAMPANTE_MAC", "").strip().upper()
CANALE = int(os.environ.get("STAMPANTE_CANALE", "1") or 1)
MODO = os.environ.get("STAMPANTE_MODO", "connessione").strip()
OFFSET = int(os.environ.get("STAMPANTE_OFFSET", "9") or 9)

SUGGERIMENTI = {
    errno.EAFNOSUPPORT: "il container non puo usare socket Bluetooth (rete non dell'host?)",
    errno.EPROTONOSUPPORT: "il kernel non ha il supporto RFCOMM",
    errno.EPERM: "permesso negato dal sistema",
    errno.EACCES: "permesso negato (forse serve l'abbinamento)",
    errno.ECONNREFUSED: "la stampante rifiuta questo canale: provo gli altri",
    errno.EHOSTDOWN: "la stampante non risponde (spenta, lontana o gia collegata a un altro dispositivo)",
    errno.EHOSTUNREACH: "la stampante non e raggiungibile",
    errno.ETIMEDOUT: "tempo scaduto: nessuna risposta",
    errno.EBUSY: "la stampante e occupata (collegata ad altro, per esempio XeasyLabel sul telefono)",
}


def descrivi(e):
    n = getattr(e, "errno", None)
    nome = errno.errorcode.get(n, "?") if n is not None else type(e).__name__
    return "%s [%s] %s" % (nome, n, SUGGERIMENTI.get(n, str(e)))


def tenta(canale, azione=None):
    """Apre la connessione; se c'e un'azione la esegue sulla connessione aperta, poi chiude."""
    s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    try:
        s.settimeout(10)
        s.connect((MAC, canale))
        if azione:
            azione(s)
        return True
    finally:
        s.close()


def etichetta_di_prova():
    """Etichetta 280 x 96: QR di un codice di prova + testo (stesso disegno che useranno le etichette vere)."""
    import io
    from PIL import Image
    from .etichetta import etichetta_png
    return Image.open(io.BytesIO(etichetta_png("8002795002995", "PROVA X1 Inventario", "QR e testo", 96, 280))).convert("L")


def stampa(s):
    from .protocollo import invia
    invia(s, etichetta_di_prova(), OFFSET, log=lambda t: print(t, flush=True))


def main():
    print("== Prova di connessione alla stampante (nessun dato viene inviato) ==", flush=True)
    if not re.fullmatch(r"([0-9A-F]{2}:){5}[0-9A-F]{2}", MAC):
        print("RISULTATO: indirizzo non valido: %r (formato AA:BB:CC:DD:EE:FF)" % MAC, flush=True)
        return 0
    print("Indirizzo: %s, canale iniziale: %d, modo: %s" % (MAC, CANALE, MODO), flush=True)
    if MODO not in ("connessione", "stampa_prova"):
        print("RISULTATO: modo sconosciuto %r" % MODO, flush=True)
        return 0
    if MODO == "stampa_prova":
        print("ATTENZIONE: stampo UNA etichetta di prova (offset %d punti)" % OFFSET, flush=True)
    print("Adattatori Bluetooth visibili: %s" % (sorted(os.listdir("/sys/class/bluetooth")) if os.path.isdir("/sys/class/bluetooth") else "nessuno (cartella assente)"), flush=True)
    try:
        socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM).close()
        print("Socket Bluetooth RFCOMM: creato", flush=True)
    except (OSError, AttributeError) as e:
        print("Socket Bluetooth RFCOMM: NON creato -> %s" % descrivi(e), flush=True)
        print("RISULTATO: il componente non puo aprire socket Bluetooth", flush=True)
        return 0
    ordine = [CANALE] + [c for c in range(1, 9) if c != CANALE]
    ok = []
    transitori = (errno.EHOSTDOWN, errno.EHOSTUNREACH, errno.ETIMEDOUT, errno.EBUSY)
    print("Se la stampante e spenta o in riposo, accendila ora: ritento per circa 40 secondi", flush=True)
    for giro in range(1, 9):               # fino a 8 giri (circa 40 s): la stampante potrebbe svegliarsi a meta
        fermo = False
        for c in ordine:
            t0 = time.time()
            try:
                tenta(c, stampa if MODO == "stampa_prova" else None)
                print("Giro %d, canale %d: CONNESSO (%.1f s)" % (giro, c, time.time() - t0), flush=True)
                ok.append(c)
                break                       # basta il primo che risponde; si richiude subito
            except RuntimeError as e:        # collegata ma non risponde al saluto: nessun dato di stampa e stato inviato
                print("Giro %d, canale %d: collegata, ma %s" % (giro, c, e), flush=True)
                break
            except OSError as e:
                print("Giro %d, canale %d: %s (%.1f s)" % (giro, c, descrivi(e), time.time() - t0), flush=True)
                if e.errno == errno.EAFNOSUPPORT:
                    fermo = True
                    break
                if e.errno in transitori:   # non risponde: inutile provare altri canali in questo giro
                    break
            time.sleep(0.3)
        if ok or fermo:
            break
        time.sleep(3)
    print("RISULTATO: " + ("connessione riuscita sul canale %d" % ok[0] if ok else "nessuna connessione riuscita"), flush=True)
    return 0        # l'esito sta nel registro: un codice di errore farebbe segnalare un guasto al Supervisor


if __name__ == "__main__":
    if MODO == "servizio":
        from .servizio import main as servizio
        sys.exit(servizio())
    sys.exit(main())
