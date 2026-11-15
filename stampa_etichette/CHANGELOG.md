## 0.3.1
- Opzioni riordinate con nomi e descrizioni in italiano.

## 0.3.0
- Nuovo modo `servizio` (predefinito): resta attivo e stampa le etichette PNG 280 x 96 che gli arrivano dalla rete locale, con codice condiviso (`token`) e una stampa alla volta.
- Parte da solo all'avvio di Home Assistant.

## 0.2.1
- Nel registro compaiono tutte le risposte della stampante (in esadecimale), dopo ogni blocco di dati e dopo l'invio.
- Dopo l'invio resta collegata per 8 secondi invece di chiudere subito.

## 0.2.0
- Nuovo modo `stampa_prova`: stampa una etichetta di prova (QR + testo) con il protocollo della X1. Il modo predefinito resta `connessione` (nessun dato inviato).
- Opzione `offset` per la posizione di stampa. Aggiunti Pillow e un font all'immagine.
- Test automatici del protocollo (`tests/`).

## 0.1.2
- La prova ritenta per circa 40 secondi (fino a 8 giri), così non dipende dal momento in cui la stampante si sveglia.

## 0.1.1
- La prova termina sempre senza codice di errore: l'esito è nell'ultima riga «RISULTATO» del registro.

## 0.1.0
- Prima versione: solo prova di connessione RFCOMM alla stampante (nessun dato inviato).
