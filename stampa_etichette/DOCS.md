# Stampa Etichette (fase 1: prova di connessione)

Prova se Home Assistant riesce ad aprire la connessione Bluetooth Classic (porta seriale) verso la stampante ORGBRO X1.
**Non invia nessun dato**: apre e richiude la connessione, quindi non esce carta.

1. Accendi la X1, tienila vicina al Raspberry e non collegata al telefono.
2. Verifica nelle opzioni l'indirizzo (`mac`) e il canale (`canale`, di solito 1).
3. Avvia l'add-on e leggi il registro: l'ultima riga «RISULTATO» dice come è andata.

Il componente usa la rete dell'host (`host_network`) perché il kernel permette i socket Bluetooth solo lì.
