# Stampa Etichette

Collega Home Assistant alla stampante ORGBRO X1 (rotolo pretagliato 12 × 40 mm) con il Bluetooth Classic.

## Opzioni
- `mac`: indirizzo Bluetooth della X1.
- `canale`: canale della porta seriale (di solito 1).
- `modo`:
  - `connessione`: apre e richiude la connessione. **Non invia dati**, non esce carta.
  - `stampa_prova`: stampa **una** etichetta di prova (QR + testo). Se la stampante non risponde al saluto iniziale non viene inviato nulla di stampa.
- `offset`: posizione di stampa in punti (predefinito 9, valore della cattura originale; 1 punto ≈ 0,125 mm). Si cambia solo se la stampa risulta spostata lungo l'etichetta.

## Uso
1. Accendi la X1, tienila vicina al Raspberry e non collegata al telefono (Bluetooth del telefono spento).
2. Avvia il componente e leggi il **Registro**: l'ultima riga «RISULTATO» dice l'esito. La prova ritenta per circa 40 secondi.

Il componente usa la rete dell'host (`host_network`) perché il kernel permette i socket Bluetooth solo lì.

## Riconoscimenti
Le sequenze di comandi della X1 sono ricavate dalla cattura del traffico di XEasyLabel pubblicata da HWMurxer
(https://github.com/HWMurxer/orgbro-x1-text-labels, licenza MIT). Qui è riscritto solo il protocollo, non il codice dell'altro progetto.
