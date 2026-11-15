"""Fase 1: prova di connessione Bluetooth Classic (RFCOMM) alla stampante. NON invia nessun dato: apre e chiude la connessione."""
import errno
import os
import re
import socket
import sys
import time

MAC = os.environ.get("STAMPANTE_MAC", "").strip().upper()
CANALE = int(os.environ.get("STAMPANTE_CANALE", "1") or 1)

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


def tenta(canale):
    s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    try:
        s.settimeout(10)
        s.connect((MAC, canale))
        return True
    finally:
        s.close()


def main():
    print("== Prova di connessione alla stampante (nessun dato viene inviato) ==", flush=True)
    if not re.fullmatch(r"([0-9A-F]{2}:){5}[0-9A-F]{2}", MAC):
        print("RISULTATO: indirizzo non valido: %r (formato AA:BB:CC:DD:EE:FF)" % MAC, flush=True)
        return 0
    print("Indirizzo: %s, canale iniziale: %d" % (MAC, CANALE), flush=True)
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
    for c in ordine:
        t0 = time.time()
        try:
            tenta(c)
            print("Canale %d: CONNESSO (%.1f s)" % (c, time.time() - t0), flush=True)
            ok.append(c)
            break                       # basta il primo che risponde; si richiude subito
        except OSError as e:
            print("Canale %d: %s (%.1f s)" % (c, descrivi(e), time.time() - t0), flush=True)
            if e.errno in (errno.EHOSTDOWN, errno.EHOSTUNREACH, errno.ETIMEDOUT, errno.EBUSY, errno.EAFNOSUPPORT):
                print("Mi fermo: provare altri canali non cambierebbe l'esito", flush=True)
                break
        time.sleep(0.5)
    print("RISULTATO: " + ("connessione riuscita sul canale %d" % ok[0] if ok else "nessuna connessione riuscita"), flush=True)
    return 0        # l'esito sta nel registro: un codice di errore farebbe segnalare un guasto al Supervisor


if __name__ == "__main__":
    sys.exit(main())
