# Changelog

Tutte le modifiche rilevanti dell'app. Formato: versione, data, cosa cambia.
Home Assistant mostra questo file nella pagina dell'app e prima dell'aggiornamento.

## 0.2.0 — 2026-10-26
Fase 2: scritture sul foglio (restano bloccate finché l'opzione "sola lettura" è attiva).
- Correzione importante: la form inviava la posizione con un nome che il server non riconosceva, quindi ogni salvataggio sarebbe stato rifiutato.
- Scarico, Sposta e Cambia categoria: si sceglie da quale giacenza (posizione e categoria) prelevare. Sposta va automaticamente nell'altra posizione. Cambia categoria chiede la nuova categoria. "Rettifica" è stata rinominata "Cambia categoria".
- Sposta e Cambia categoria scrivono una coppia di righe (Scarico dalla situazione vecchia, Carico nella nuova), come i bot di AppSheet.
- Le righe scritte hanno l'ID movimento e la data nel formato del foglio (gg/mm/aaaa).
- Scheda prodotto: con la scrittura attiva compare "Cambia sottocategoria". È una modifica del prodotto: aggiorna il catalogo e le righe di movimento di quel codice senza cambiare le quantità, e accetta solo sottocategorie previste per la categoria.
- I messaggi d'errore del server (per esempio "Giacenza insufficiente") ora si vedono nella schermata.

## 0.1.13 — 2026-10-26
- Correzione: nella schermata Movimento un codice già presente nel catalogo veniva segnalato come "nuovo". Ora il prodotto viene riconosciuto e il nome, la categoria e la sottocategoria si compilano da soli.

## 0.1.12 — 2026-10-26
- Le miniature già elaborate vengono salvate sul dispositivo: dopo la prima volta compaiono subito, senza scaricarle di nuovo.

## 0.1.11 — 2026-10-26
- Pagina "Prodotti" molto più veloce: l'elenco compare subito dall'ultima copia salvata sul dispositivo e si aggiorna in background (senza ridisegnare se non è cambiato nulla).
- Le miniature si caricano solo quando entrano nello schermo (prima ~220 immagini insieme a ogni apertura) e sono elaborate più piccole. Vale anche per lo Stock.
- Server: la giacenza viene calcolata una sola volta per ciclo di cache e riusata da Stock, Prodotti e scheda.

## 0.1.10 — 2026-10-26
- Nuova pagina "Prodotti": tutti i prodotti del catalogo in ordine alfabetico, con ricerca (nome, marca, tipo, categoria, codice) e anche quelli con giacenza zero ("Esaurito"). Toccando un prodotto si apre la scheda.
- Scheda prodotto: pulsante "Carica o scarica" che apre il movimento con il codice già inserito.

## 0.1.9 — 2026-10-26
- Stock: miniature senza sfondo bianco (il bianco collegato ai bordi diventa trasparente, calcolato sul dispositivo).
- Nuova scheda prodotto: si apre toccando una riga dello Stock. Mostra immagine, marca e confezione, tipo e categoria, giacenze per posizione e categoria con il totale, scorta minima, punteggi, nutrizione, compatibilità, dettagli, composizione, smaltimento e data di aggiornamento.

## 0.1.8 — 2026-10-26
- Stock: la giacenza si conta per prodotto, posizione e categoria (lo stesso prodotto può stare in categorie e posizioni diverse). La categoria torna a essere quella della riga di stock; la sottocategoria è del prodotto.
- Movimenti `Move` (cambio posizione) e `Cng` (cambio categoria): come i bot di AppSheet, si scrivono come coppia di righe nette (Scarico dalla situazione vecchia, Carico nella nuova), con controllo della giacenza disponibile. Ancora non attivi: l'app è in sola lettura.

## 0.1.7 — 2026-10-26
- (sostituita dalla 0.1.8) Categoria letta dal prodotto.

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
