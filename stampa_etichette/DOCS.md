# Stampa Etichette

Collega Home Assistant alla stampante ORGBRO X1 (rotolo pretagliato 12 × 40 mm) con il Bluetooth Classic. In modo `servizio` (predefinito) resta attivo e stampa le etichette che gli manda l'add-on «Inventario Casa».

## Messa in funzione
1. Nelle opzioni imposta `token`: un codice condiviso lungo almeno 8 caratteri (usa lo stesso in «Inventario Casa» → `stampante_token`).
2. Avvia «Stampa Etichette» (si avvia da solo anche al riavvio).
3. In «Inventario Casa» imposta `stampante_url` = `http://homeassistant:8770` (la porta è l'opzione `porta`) e `stampante_token`, poi riavvia l'inventario.
4. Nell'inventario, scheda prodotto → «Etichetta per la stampante» → «Stampa con la X1».

La X1 deve essere accesa e vicina al Raspberry, con il Bluetooth del telefono spento. Se è in riposo, il servizio ritenta per circa 30 secondi.

## Opzioni
- `mac`: indirizzo Bluetooth della X1. `canale`: canale della porta seriale (di solito 1).
- `modo`: `servizio` (predefinito), `connessione` (solo prova, nessun dato inviato) oppure `stampa_prova` (stampa una etichetta di prova all'avvio).
- `offset`: posizione di stampa in punti (predefinito 9; 1 punto ≈ 0,125 mm).
- `porta` e `token`: porta del servizio e codice condiviso.

## Sicurezza
Il servizio ascolta sulla rete locale (usa la rete dell'host perché il kernel permette i socket Bluetooth solo lì). Risponde solo con il codice condiviso, accetta solo immagini PNG di 280 × 96 punti e stampa una etichetta alla volta. Non esporlo a Internet.

## Riconoscimenti
Le sequenze di comandi della X1 sono ricavate dalla cattura del traffico di XEasyLabel pubblicata da HWMurxer
(https://github.com/HWMurxer/orgbro-x1-text-labels, licenza MIT). Qui è riscritto solo il protocollo, non il codice dell'altro progetto.
