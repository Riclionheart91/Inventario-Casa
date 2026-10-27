# Changelog

Tutte le modifiche rilevanti dell'app. Formato: versione, data, cosa cambia.
Home Assistant mostra questo file nella pagina dell'app e prima dell'aggiornamento.

## 0.6.2 — 2026-10-28
Scorrimenti laterali sulle righe, come definiti dall'utente (la 0.6.0 e la 0.6.1 erano già pubblicate: serve un numero nuovo perché Home Assistant proponga l'aggiornamento).
- Spesa: a destra «Comprato +1» (carico di 1 a Casa); a sinistra toglie la voce dalla lista per oggi, solo su questo dispositivo (c'è «Rimetti in lista»).
- Approvazioni: a destra Approva, a sinistra Rifiuta; entrambi con «Annulla» per 5 secondi: il foglio viene scritto solo dopo.
- Stock e Prodotti: a sinistra Scarico di 1 (solo se la giacenza è maggiore di zero), a destra Carico di 1, con «Annulla» per 5 secondi. In Stock vale la posizione e la categoria della riga; in Prodotti la riga di giacenza del prodotto, e se ce n'è più di una un piccolo menu chiede quale.
- Da inserire: a sinistra Scarta (con «Annulla» 5 s); a destra «Aggiungi all'inventario» solo se la bozza è completa, altrimenti vibra, avvisa «Completa prima i campi» e porta al primo campo mancante.
- Ogni gesto ha il pulsante equivalente (−1/+1, ✕ nella Spesa, Approva/Rifiuta/Scarta già presenti), funziona con mouse e trackpad e non ostacola lo scorrimento verticale. Se l'app va in secondo piano durante i 5 secondi, l'azione viene scritta subito.
- Sempre attivo lo scorrimento sulla barra in basso per cambiare pagina.

## 0.6.1 — 2026-10-28
Scorrimento sulla barra in basso e comando rapido predefinito.
- Scorrere la barra del menu in basso cambia pagina (verso sinistra la successiva, verso destra la precedente); un tocco sui pulsanti funziona come prima.
- Il comando rapido iOS predefinito è «Spesa AppSheet» (opzione `shortcut_spesa`).
- Pronta ma spenta l'infrastruttura per gli scorrimenti sulle righe: le azioni per ogni pagina le definirà l'utente.

## 0.6.0 — 2026-10-28
Spesa più leggibile, lista della spesa su iOS, Prodotti per tipo.
- Spesa: voci raggruppate per categoria (gruppi chiudibili), una riga per voce con spunta grande, miniatura, tipo, giacenza/scorta colorata («0 / 2») e «+1» come azione secondaria; filtro Tutti / Finiti / In esaurimento; il titolo mostra «N da comprare · M nel carrello».
- Nuovo pulsante «Aggiungi alla lista della spesa di iOS»: avvia il comando rapido indicato nell'opzione `shortcut_spesa` (default «Spesa AppSheet») con le voci non ancora nel carrello; ripiego: foglio di condivisione o copia negli appunti. Istruzioni per creare il comando in DOCS.
- Prodotti: ordinamento A-Z o Per tipo (gruppo «Senza tipo» in fondo); tutti i gruppi si chiudono e si aprono, con «Chiudi tutti / Apri tutti»; scelta e gruppi chiusi si ricordano sul dispositivo.

## 0.5.1 — 2026-10-27
Scanner: legge anche i codici a barre in verticale. A fotogrammi alterni prova l'inquadratura intera, la fascia centrale e le stesse ruotate di 90 gradi; lo stesso vale per la lettura da foto.

## 0.5.0 — 2026-10-27
Tre nuove pagine: Spesa, Da inserire, Approvazioni complete.
- Spesa: i tipi sotto la scorta minima (da ai_tipi), con stato Finito / In esaurimento; spunta "nel carrello" e "Comprato +1" (carico a Casa).
- Da inserire: le bozze di prodotti nuovi si completano in app (nome, categoria, sottocategoria, tipo), con ricerca nei database e suggerimento AI; "Aggiungi all'inventario" crea il prodotto.
- Approvazioni: Approva, Correggi (nome, categoria, sottocategoria, tipo; scorta minima per i nuovi tipi, default 0) e Rifiuta, con stato scritto come fanno AppSheet e il motore.
- Il cambio di categoria non modifica il prodotto; se la ricerca non trova nulla il prodotto non cambia.

## 0.4.6 — 2026-10-27
Prodotto nuovo: creazione e carico in un'unica chiamata.
- "Conferma e salva" crea il prodotto e registra subito il carico con i dati appena inseriti, senza rileggere il foglio: non serve più riscansionare il codice.
- Se la posizione non è valida non viene creato nulla.

## 0.4.5 — 2026-10-27
La sottocategoria vuota ora dice "Scegli prima la categoria".

## 0.4.4 — 2026-10-27
Suggerimento AI: se Gemini non risponde, la schermata mostra il motivo (codice di errore del servizio, senza la chiave). L'AI parte anche se il prodotto trovato non ha un nome.

## 0.4.3 — 2026-10-27
Proposta per un codice nuovo: menu sempre pronti e AI sempre visibile.
- Categorie e sottocategorie si caricano prima di mostrare la proposta: prima i menu potevano comparire vuoti.
- Il suggerimento AI parte sempre; se manca la chiave Gemini nelle opzioni dell'app la schermata lo dice, invece di non mostrare nulla.

## 0.4.2 — 2026-10-27
Corretti salvataggio con foto, lettura del codice e ricerca.
- Salvataggio di un prodotto nuovo con foto: la foto veniva inviata in un formato non accettato dal server e l'errore era illeggibile. Ora si invia nel formato giusto e gli errori del server sono mostrati come testo.
- Lettore del codice dalla fotocamera: risoluzione piu alta, messa a fuoco continua e lettura alternata della fascia centrale e dell'inquadratura intera.
- Ricerca: se un database ha il prodotto ma senza nome italiano usa il nome in un'altra lingua o la marca; se un database non risponde, la schermata lo dice (e il motivo va nel log dell'app).

## 0.4.1 — 2026-10-26
Ricerca del codice: altri database dal motore di arricchimento.
- Nuovi, senza chiave: FoodRepo, OpenGTINDB, Datakick (con gtinsearch), Open Beer DB; per i libri OpenLibrary e Google Books (solo ISBN), per i farmaci OpenFDA.
- Nuove opzioni facoltative: google_books_key e openfda_key (alzano i limiti giornalieri).
- Non portati: Wikidata, USDA, Untappd, Amazon e i ripieghi che leggono dal foglio.

## 0.4.0 — 2026-10-26
L'AI suggerisce categoria, sottocategoria e tipo quando crei un prodotto nuovo.
- Dopo la proposta dai database, Gemini propone categoria, sottocategoria e tipo; i menu arrivano già compilati e li correggi prima di "Conferma e salva". Non viene registrata nessuna proposta del prodotto (niente righe in ai_prodotti).
- Il tipo viene preso tra quelli esistenti; se nessuno calza ne propone uno nuovo, che entra in ai_tipi come "DA_APPROVARE" con scorta minima 0: compare in Approvazioni, dove definisci la scorta minima e approvi o correggi.
- Senza chiave o se Gemini non risponde, tutto funziona come prima (menu vuoti) con una nota discreta.
- Nuove opzioni dell'app (tutte facoltative): chiave Gemini, modello e modello di riserva; chiavi dei servizi di ricerca usati come ripiego dal motore: BarcodeLookup, UPCDatabase, Go-UPC, Spoonacular, Nutritionix, Edamam, Icecat, GS1. Un servizio senza chiave viene saltato. Le chiavi restano sul server.
- Non ancora fatti: USDA, Untappd, Google Books, OpenFDA, Amazon.

## 0.3.1 — 2026-10-26
Corretto: nello Scarico poteva comparire "Nessuna giacenza" anche con prodotto in magazzino.
- Se la scheda del prodotto non risponde, la giacenza viene letta dall'elenco Stock.
- Se la lettura fallisce davvero, l'app mostra il motivo invece di dire che non c'è giacenza.

## 0.3.0 — 2026-10-26
Fase 3, primo passo: ricerca del codice dentro l'app.
- Un codice nuovo viene cercato subito su Open Food Facts, Open Beauty Facts, Open Pet Food Facts e Open Products Facts, tutti insieme (massimo 6 secondi, si ferma al primo risultato utile in ordine di priorità).
- La schermata mostra una proposta (immagine, nome modificabile, marca, confezione): scegli categoria e sottocategoria dai menu, il tipo è facoltativo con i suggerimenti dei tipi esistenti, e "Conferma e salva" crea il prodotto e registra il carico in un tocco. Un tipo nuovo entra in ai_tipi come "da approvare".
- Se il codice non si trova, resta il flusso con la foto.
- Il prodotto nuovo ha "API Status" = ✅ App (fonte) e la data nel formato gg/mm/aaaa. La creazione richiede la scrittura attiva.

## 0.2.3 — 2026-10-26
- Stock e Prodotti: la barra di ricerca e i filtri restano fissi in alto durante lo scorrimento; sotto di essi resta fissa la categoria (o la lettera) in cui ti trovi, finché non arriva la successiva.
- Pulsanti dei filtri più piccoli.

## 0.2.2 — 2026-10-26
- Stock e Prodotti molto più veloci da aprire: il server legge insieme tutti i fogli con una sola richiesta a Google e li tiene aggiornati in background ogni 20 secondi, quindi le richieste rispondono dalla memoria invece di rileggere il foglio ogni volta.
- Anche lo Stock mostra subito l'ultima copia salvata sul telefono e si aggiorna in background.
- Le risposte del server sono compresse.

## 0.2.1 — 2026-10-26
- Scheda prodotto: "Aggiornato il" ora è sempre gg/mm/aaaa (prima poteva comparire come numero o in formato internazionale).

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

---
Regola: ad ogni modifica, aggiungere una voce in `inventario_casa/CHANGELOG.md` e alzare `version` in `inventario_casa/config.yaml`. Il file in questa cartella è una copia: aggiornare entrambi.
