# Changelog

Tutte le modifiche rilevanti dell'app. Formato: versione, data, cosa cambia.
Home Assistant mostra questo file nella pagina dell'app e prima dell'aggiornamento.

## 0.1.6 — 2026-10-26
- Stock: miniatura del prodotto, marca e confezione sotto al nome (utile per distinguere prodotti con lo stesso nome).
- Scansione: funziona anche su iPhone e nell'app Home Assistant. Con l'indirizzo sicuro (https) usa la fotocamera dal vivo; senza, si scatta una foto al codice e viene letta nel dispositivo. Il lettore si scarica solo quando serve.
- Nuova opzione `url_sicuro`: l'indirizzo https (Tailscale) a cui rimanda il pulsante "Apri con l'indirizzo sicuro".

## 0.1.5 — 2026-10-26
- Allineata al foglio di prova rivisto: il Tipo si legge dalla colonna `Tipo` di `prodotti`.
- La scorta minima si legge da `ai_tipi` (una per tipo), con la scorta del singolo prodotto come ripiego.
- Movimenti: usa i nomi del foglio (`Move`, `Cng`); "Sposta" e "Rettifica" restano accettati come alias.

## 0.1.4 — 2026-10-26
- Immagine precostruita su GitHub (ghcr.io): gli aggiornamenti non compilano più l'app su Home Assistant, quindi sono molto più veloci.

## 0.1.3 — 2026-10-26
- Nuova icona e logo dell'app (casa con scatola), anche per l'installazione sul telefono (PWA).
- Aggiunto questo changelog.

## 0.1.2 — 2026-10-26
- Stock: il tipo del prodotto viene letto da `ai_prodotti` quando manca nella tabella `prodotti`.

## 0.1.1 — 2026-10-26
- Stock: campi allineati tra backend e interfaccia, mostra il tipo del prodotto (etichetta accanto al nome).

## 0.1.0 — 2026-10-25
- Prima versione: Stock e Approvazioni AI in sola lettura, collegamento al foglio Google con account di servizio.
- Opzione `sola_lettura` attiva di default; `drive_folder_id` facoltativo (foto rimandate).
