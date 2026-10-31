# Changelog

Tutte le modifiche rilevanti dell'app. Formato: versione, data, cosa cambia.
Home Assistant mostra questo file nella pagina dell'app e prima dell'aggiornamento.

## 0.10.5 — 2026-10-31
Codici lunghi: oltre 14 cifre l'app non interroga più i database online (nessuno li conosce) e risponde subito «non trovato». I codici di 16 cifre che iniziano per 01 (formato GS1, come 0180232793411114) vengono cercati con il codice a barre che contengono (qui il GTIN 80232793411114).

## 0.10.4 — 2026-10-31
Prodotto nuovo con la foto: la foto va direttamente a Gemini, che legge nome, marca, confezione e propone categoria, sottocategoria e tipo; la foto non si salva più su Drive (la cartella Drive e l'opzione `drive_folder_id` non servono più, e l'errore 404 sparisce). La bozza compare in «Da inserire» già compilata, pronta da confermare. Senza chiave Gemini la bozza arriva vuota, come prima.

## 0.10.3 — 2026-10-31
Foto dei prodotti nuovi: se la cartella Drive non è raggiungibile l'app ora lo dice in chiaro («controlla drive_folder_id e condividi la cartella con l'account di servizio come Editor») invece di mostrare l'errore tecnico 404. Funziona anche con cartelle di un Drive condiviso.

## 0.10.2 — 2026-10-31
Codici più lunghi ancora, come i QR dei prodotti di pallavolo (21 cifre, es. 066400240330063025051): ora si accettano fino a 24 cifre. Gli zeri iniziali vengono ignorati, quindi il codice si salva e si ritrova senza lo zero davanti.

## 0.10.1 — 2026-10-31
Codici a barre fino a 16 cifre (prima 14): servono per alcuni prodotti di pallavolo. L'app li accetta nel campo, nella ricerca e nella scansione; oltre 15 cifre il codice si scrive sul foglio come testo (i numeri di Fogli perdono precisione dopo 15 cifre) e nell'app resta una stringa. Gli zeri iniziali continuano a essere ignorati.

## 0.10.0 — 2026-10-31
Prodotti che nessun archivio conosce: l'app chiede a Gemini (con la ricerca Google) nome, marca, confezione e le pagine dove il prodotto compare; l'immagine si prende dalla pagina solo se la pagina riporta davvero il codice a barre. Si riempiono solo i campi vuoti, lo stato diventa «🔶 Web (AI)», e se non trova niente il prodotto non cambia. Gira nell'arricchimento notturno e, una tantum, con la nuova opzione `arricchimento_all_avvio` (con `sola_lettura` spenta). Non si aprono mai indirizzi della rete di casa.

## 0.9.5 — 2026-10-30
Riaccesa la porta diretta 8099 per chi non puo aprire l'app da Home Assistant (utenti non amministratori). Serve il codice di famiglia (opzione `shared_code`); per la fotocamera va servita in https con Tailscale (vedi DOCS). Da Home Assistant/ingress non cambia nulla.

## 0.9.4 — 2026-10-30
Il pannello Inventario ora e visibile anche agli utenti di Home Assistant che non sono amministratori (prima, come ogni app, compariva solo agli amministratori).

## 0.9.3 — 2026-10-30
Corretto il «Errore 500» al primo salvataggio (serviva premere due volte): le chiamate al foglio Google ora vanno una alla volta (prima il ciclo di aggiornamento in background e il salvataggio potevano scontrarsi) e si ripetono da sole fino a 3 volte se Google o la rete falliscono per un attimo. Se capita ancora, il messaggio mostra il motivo invece di «Errore 500».

## 0.9.2 — 2026-10-30
Le schede «Da inserire» e «Approvazioni» compaiono nella barra in basso solo quando c'e qualcosa da fare (restano visibili finche ci sei dentro). Lo scorrimento tra le pagine salta quelle nascoste.

## 0.9.1 — 2026-10-30
Scorta minima modificabile dall'app: nella scheda del prodotto, sezione «Scorta minima del tipo», un numero e Salva (vale per tutti i prodotti di quel tipo e scrive in ai_tipi; se il tipo non c'è lo crea già approvato). La scheda mostra ora la scorta anche per i prodotti con giacenza zero.

## 0.9.0 — 2026-10-30
Risposte a voce per Home Assistant (opzione `voce_token`): "cosa manca in casa" e "ho X e dove", con frasi pronte. File d'esempio in `home_assistant/`.

## 0.8.1 — 2026-10-30
Nuova opzione `traduzione_all_avvio` (spenta): se accesa, all'avvio dell'app (e solo con `sola_lettura` spenta) traduce una volta in italiano i testi lunghi gia presenti nei prodotti, senza cercare nuovi dati. Ogni testo si traduce una sola volta; se il giro non basta si riavvia l'app. Poi si rispegne.

## 0.8.0 — 2026-10-30
Funzioni dello script Google portate nell'app.
- **Proposte di categoria dell'AI**: da Approvazioni, "Approva" ora applica subito la proposta (aggiungi categoria/sottocategoria, rinomina, unisci: aggiorna elenco categorie, prodotti e movimenti e toglie i doppioni). Prima la applicava lo script.
- **Arricchimento notturno** (nuove opzioni `arricchimento_notturno`, `arricchimento_ora`, `arricchimento_max`; spento di default): cerca i dati dei prodotti incompleti con gli stessi provider della creazione e riempie SOLO i campi vuoti; se non trova nulla il prodotto non cambia (nemmeno stato e data). Un codice non trovato si riprova dopo 30 giorni. Funziona solo con l'app non in sola lettura.
- **Traduzione in italiano** di dettagli, composizione, free-from e smaltimento (Gemini), dentro lo stesso giro notturno; i testi gia in italiano non vengono toccati e ogni testo si traduce una volta sola.
- Nuovi servizi: `GET /api/arricchimento` (stato dell'ultimo giro) e `POST /api/arricchimento/avvia` (lancia subito un giro).
- Importante: accendere `arricchimento_notturno` solo quando si spegne `startNightlyFullEnrich` nello script, altrimenti i due si contraddicono.

## 0.7.4 — 2026-10-30
Collegamento diretto allo scanner: aprendo il pannello con `?scan=1` la fotocamera parte da sola (per un comando rapido iPhone).

## 0.7.3 — 2026-10-28
Prodotti: riga di categorie scorrevole (con conteggio) per isolare un solo reparto; dentro restano i gruppi per tipo. La ricerca vale sulla categoria scelta; la scelta resta memorizzata.

## 0.7.2 — 2026-10-28
Rimossi i pulsanti −1/+1 dalle righe di Stock e Prodotti: restano solo gli scorrimenti (sinistra Scarico 1, destra Carico 1, con Annulla per 5 secondi).

## 0.7.1 — 2026-10-28
Porta diretta 8099 non più pubblicata: si usa solo Home Assistant / Tailscale (https, fotocamera dal vivo funzionante). Il codice di accesso diretto resta nel programma ma non è raggiungibile.

## 0.7.0 — 2026-10-28
Accesso diretto su porta dedicata (8099), oltre all'ingress di Home Assistant: le due vie convivono.
- Ingress / Tailscale su Home Assistant: nessun codice, vale il login di Home Assistant.
- Porta diretta `http://IP:8099`: pagina di accesso con il codice di famiglia (opzione `shared_code`). Senza codice la porta diretta e spenta.
- Cambiando il codice tutte le sessioni aperte si invalidano. "Ricorda questo dispositivo" dura 90 giorni. Dopo 5 codici errati blocco di 15 minuti.
- Pulsante "Esci" nell'intestazione (solo sull'accesso diretto).
- Corretto: impostare `shared_code` bloccava tutte le API perche l'app non invia mai il codice.

## 0.6.5 — 2026-10-28
Swipe riscritti, stile Apple Music (righe e barra in basso), ora anche su iPhone e Mac.
- Funziona con il tocco (iPhone/iPad), con il mouse e con il trackpad a due dita (Mac); prima usava solo i pointer events, che su WebKit non partivano.
- La riga si sposta e dietro compare l'azione colorata con la sua etichetta. Rilasciando oltre un quarto resta aperta: tocca il pulsante per confermare, tocca altrove o scorri per richiuderla. Uno swipe lungo (oltre il 60%) esegue subito l'azione. Una sola riga aperta alla volta.
- Lo scorrimento verticale resta libero: il gesto viene preso solo se chiaramente orizzontale.
- Barra in basso: scorrendo cambia pagina e l'indicatore segue il dito, come la tab bar di iOS.
- Suggerimento discreto la prima volta in Stock e Prodotti (chiudibile, ricordato).
- Diagnostica: tieni premuto 3 secondi sul titolo per vedere se tocco/mouse arrivano all'app.

## 0.6.4 — 2026-10-28
Pagina Prodotti: filtri e pulsanti "Chiudi" / "Apri" (tutti i gruppi) su una sola riga; se i filtri non entrano si scorrono di lato.

## 0.6.3 — 2026-10-28
Pagina Prodotti: una sola vista, più informazioni.
- Le due viste (A-Z e Per tipo) sono unite: gruppi per tipo in ordine alfabetico ("Senza tipo" in fondo) e prodotti in ordine alfabetico dentro ogni gruppo.
- Il numero nell'intestazione del gruppo sono i pezzi che hai in casa (con in piccolo quanti prodotti), non il numero di prodotti.
- Ogni riga mostra marca e confezione, dove si trova (Casa/Cantina con le quantità), categoria › sottocategoria, i pezzi con colore (rosso 0, giallo sotto scorta) e "da comprare".
- Riepilogo in alto (prodotti · pezzi in casa · sotto scorta) e filtri rapidi Tutti / In casa / Esauriti / Sotto scorta; la ricerca cerca anche in marca, confezione e tipo.
- L'elenco prodotti del server include le posizioni con quantità e la scorta minima anche per i prodotti senza giacenza.

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
