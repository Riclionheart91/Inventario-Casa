# Changelog

Tutte le modifiche rilevanti dell'app. Formato: versione, data, cosa cambia.
Home Assistant mostra questo file nella pagina dell'app e prima dell'aggiornamento.

## 0.22.2
- Schermo largo (iPad, Mac): barra laterale a sinistra con le sezioni, titolo nella barra in alto, schede prodotto come fogli centrati, effetto al passaggio del mouse. Sul telefono resta la barra in basso.

## 0.22.1
- Differenze con Open Food Facts: scegli su ogni scheda, poi un solo «Applica le scelte» in fondo per tutte (via i pulsanti «per tutte» e «Applica» di ogni scheda).
- Codice nuovo non trovato da nessuna parte: i pulsanti «Foto fronte» e «Foto retro» compaiono subito sotto il codice a barre; il retro viene tenuto per completare i dati per Open Food Facts.
- Messaggi di ricerca più corti.

## 0.22.0
- «Applica» nelle differenze con Open Food Facts lavora in background: la scheda sparisce subito e puoi andare avanti; se qualcosa non riesce, la scheda ritorna con il motivo.
- Pulsanti invertiti: «Usa OFF» (predefinito) e «Lascia»; «Invia il mio» solo dove OFF è vuoto.
- Nuovo «Usa OFF per tutte» e «Applica a tutte» per decidere in massa.
- Scheda «Condividi»: nuovo «Rimanda» (la richiesta torna quando carichi di nuovo il prodotto); niente elenco di ciò che manca, solo «mancano informazioni».
- Foto del retro e «Completa dal codice a barre» lavorano in background; le correzioni nella scheda si salvano da sole alla chiusura.
- Testi, barra in alto e titoli più piccoli; corretto lo spostamento laterale della schermata.

## 0.21.0 — 2026-11-08
**App con l'aspetto di un'app iPhone** (modello: Musica): titolo grande che si riduce allo scorrimento, barra delle schede traslucida, righe con miniatura quadrata arrotondata, intestazioni di sezione in grassetto, controlli segmentati, caselle tonde come in Promemoria, schede e fogli che salgono dal basso, tema scuro iOS. Passando da una scheda all'altra la nuova scheda scorre dal lato giusto.
- **Indice A-Z** sul bordo destro dell'elenco Prodotti e dell'elenco Condividi: trascinando il dito la lettera si evidenzia e l'elenco scorre.
- **Vibrazione aptica** leggera su cambi di scheda, indice, gesti sulle righe e conferme (si spegne in Impostazioni › Aspetto e vibrazione). Su iPhone usa un trucco che funziona da iOS 17.4: se non la senti, il tuo sistema non la permette.
**Open Food Facts · differenze** (in «Da fare», come le altre approvazioni): per i prodotti che su Open Food Facts ci sono già, l'app confronta nome, marca, confezione, ingredienti, valori nutrizionali e foto con il tuo foglio. Per ogni differenza decidi tu: usare il valore di Open Food Facts nel tuo foglio, mandare il tuo a Open Food Facts (solo dove lì è vuoto: non si sovrascrive mai niente) o lasciare com'è. Niente viene scritto finché non applichi; le modifiche al foglio finiscono nel registro con la fonte «OPEN FOOD FACTS». «Non proporre più» le toglie per sempre.
**Foto per Open Food Facts**: restano nell'app solo finché il prodotto non è inviato o scartato; si cancellano da sole anche quando il codice risulta già su Open Food Facts.

## 0.20.0 — 2026-11-08
**Condividi su Open Food Facts, rifatta**:
- Elenco con filtri (pronti, da completare, per sito), badge «completo» o «manca: …» su ogni prodotto e barra fissa in basso: «Spunta pronti», «Completa», «Invia», «Non proporre più».
- **Completamento dal codice a barre**: l'app cerca prima negli archivi dei codici e sul web, poi l'AI legge i risultati e compila nome esatto, marca, confezione, ingredienti e valori nutrizionali (solo se compaiono davvero, mai inventati). Parte da sola in background per i prodotti dell'elenco.
- **Tocca il nome**: si apre la scheda con tutto quello che verrà inviato, modificabile. Le tue correzioni restano sopra ogni completamento successivo.
- **Foto del retro** (facoltativa): l'AI legge l'etichetta e compila ingredienti e valori per 100 g; la foto parte con il prodotto. Le immagini trovate online non vengono inviate (diritti d'autore).

## 0.19.0 — 2026-11-08
**Condividi su Open Food Facts**: nuova scheda «Condividi», che compare solo quando ci sono prodotti non ancora presenti su Open Food Facts (cibo), Open Pet Food Facts (cibo per animali), Open Products Facts (casa e detersivi) o Open Beauty Facts (cosmetici). Spunti quelli da inviare, scegli il sito se serve e premi «Invia selezionati»: partono nome, marca, confezione e la tua foto. «Non proporre più» li toglie per sempre dall'elenco. Servono `off_utente` e `off_password` nelle opzioni. Il controllo dei codici avviene una volta al giorno, con solo letture. La foto di un codice nuovo resta nell'app fino all'invio o allo scarto.

## 0.18.4 — 2026-11-08
**Correzione urgente della 0.18.3**: in quella versione mancava il collegamento che fa mostrare la pagina dell'app (restava solo il server, senza schermata). Ripristinato. Se hai aggiornato alla 0.18.3, aggiorna subito a questa.

## 0.18.3 — 2026-11-08
**Prima il codice a barre, poi la foto**: per un codice nuovo l'app cerca prima sul web il codice a barre (con la ricerca dell'app, senza passare dall'AI) e, se trova il prodotto, usa quei dati: nome, marca, confezione e immagine, con categoria e tipo suggeriti dall'AI. La foto viene letta dall'AI solo se il web non trova il nome, o per completare la categoria. In «Da inserire» la fonte indica se i dati vengono dal web o dalla foto.

## 0.18.2 — 2026-11-08
**Codice trovato senza nome**: se i database riconoscono il codice ma non danno il nome, l'app usa la foto del database e la fa leggere all'AI (in background, come per le foto scattate): puoi salvare subito e il prodotto si compila da solo in «Da inserire». Se il database non ha nemmeno la foto, l'app ti chiede di scattarla. Puoi comunque scattare una foto tua al posto di quella del database.

## 0.18.1 — 2026-11-08
**Codice nuovo senza attese**: quando inserisci un prodotto nuovo con la foto, il movimento si salva subito e puoi passare al prodotto successivo. La lettura della foto e la ricerca sul web partono dopo, in background: in «Da inserire» il prodotto compare con lo stato «in elaborazione» e si compila da solo appena l'AI finisce (la pagina si aggiorna da sola). Se l'AI non risponde, la scheda resta da compilare a mano, con un avviso.

## 0.18.0 — 2026-11-02
**Ricerca sul web senza passare dall'AI**: per i codici sconosciuti e per punteggi e riciclo, l'app cerca da sola sul web (DuckDuckGo, senza chiave; oppure Brave, Serper o Tavily se metti la chiave nelle opzioni), apre le prime pagine e passa a Gemini i risultati come testo da leggere. Gemini non usa più il suo strumento di ricerca Google, che il tuo account rifiuta; se la ricerca dell'app non trova nulla, prova comunque quello strumento. In «Uso dell'AI» c'è il pulsante «Prova la ricerca web». Google non offre più la sua ricerca ai nuovi clienti, quindi non è usabile direttamente.

## 0.17.1 — 2026-11-02
- **Ricerca Google rifiutata da Gemini**: se il tuo account non accetta lo strumento di ricerca (errore 4xx), l'app sospende per un po' le funzioni che la usano (punteggi e riciclo, ricerca sul web) invece di riprovare a ogni prodotto: 15 minuti se è un limite di quota, 6 ore negli altri casi. «Controlla i modelli» la riabilita se torna a rispondere, e dice chiaramente se nessun modello la accetta, con il motivo.
- «Uso dell'AI» mostra l'ultimo errore di ogni compito e non conta più come errore la risposta «niente da spostare» (controllo categorie).
- «Controlla i modelli» consiglia il modello potente anche se non ha la ricerca.

## 0.17.0 — 2026-11-02
- **Regole desunte dai tuoi dati**: in «Regole della casa» il pulsante «Suggerisci dai miei dati» cerca le tue abitudini (dove tieni i prodotti di uno stesso tipo, almeno 3 e quasi tutti nello stesso posto) e le correzioni che hai fatto più volte alle proposte dell'AI. Gemini riscrive le frasi in modo chiaro, controllando che nomi di tipi e categorie restino identici. Ogni suggerimento si approva (✓) o si scarta (✕) e non torna più; non viene scritto niente senza il tuo ok.
- **Controllo dei modelli Gemini**: in «Uso dell'AI» il pulsante «Controlla i modelli disponibili» prova i modelli del tuo account (anche gratuito), dice quali rispondono, quanto ci mettono e se hanno la ricerca Google, e consiglia uno leggero e uno potente.

## 0.16.0 — 2026-11-02
**Scelta del modello per compito**: nuova opzione `gemini_modello_potente`. Se la compili, la ricerca sul web, la lettura delle foto, i punteggi/riciclo e il controllo delle categorie usano per primo quel modello (poi il normale e la riserva se non risponde); classificazione, traduzione e tipi restano sul modello leggero. Vuota, non cambia niente rispetto a prima.

## 0.15.0 — 2026-11-02
Tre novità sull'uso dell'AI, tutte in Impostazioni:
- **Uso dell'AI**: per ogni compito (classificazione, traduzione, ricerca web, foto, controlli…) quante richieste, quante dalla memoria, quanti errori e quanto tempo; e come tratti le proposte (approvate, corrette, rifiutate), così vedi se i suggerimenti sono affidabili.
- **Memoria delle risposte**: la stessa richiesta (stesso prodotto, stesse regole) non richiama Gemini per 30 giorni. C'è il pulsante «Svuota la memoria».
- **Regole della casa**: frasi tue (per esempio «le uova vanno in Frigorifero») salvate nel foglio «regole» e passate all'AI in classificazioni, foto e controlli. Hanno la precedenza sulle sue deduzioni.

## 0.14.2 — 2026-11-01
Approvare o rifiutare una proposta è molto più rapido: l'app legge il foglio una volta sola invece di rileggerlo a ogni passaggio, e la pagina toglie subito la carta senza ricaricare l'intero elenco.

## 0.14.1 — 2026-11-01
La pagina delle proposte AI si apre più in fretta: i tre fogli delle proposte si leggono con una sola chiamata a Google invece di tre, e l'elenco dei prodotti non viene più ricostruito per ogni proposta (con la 0.13.2 era diventato più lento).

## 0.14.0 — 2026-11-01
**Primo avvio**: nuova opzione `crea_foglio`. Se è attiva e `sheet_id` è vuoto (o il foglio non esiste più), l'app crea da sola il foglio Google con tutte le schede e le intestazioni, nella cartella `drive_folder_id` se indicata, e lo condivide con l'indirizzo `condividi_con`. L'indirizzo del foglio compare nel registro dell'app e resta salvato: ai riavvii riusa lo stesso foglio senza crearne altri. `sheet_id` ora è facoltativo.

## 0.13.2 — 2026-11-01
Ogni proposta (correzioni dei prodotti, nuovi tipi, categorie e voci della revisione) mostra ora anche i prodotti che l'hanno generata, così puoi giudicare se il suggerimento è giusto.

## 0.13.1 — 2026-11-01
Riordino del foglio in versione profonda: elimina i fogli e le colonne calcolati da AppSheet, sposta nel foglio «archivio» le righe chiuse (bozze inserite, proposte già applicate), aggiunge a categorie e tipi quelli usati dai prodotti ma mancanti negli elenchi, e mette in ordine schede e colonne con intestazioni fisse, filtri, formato data e menu a tendina. Serve una copia di sicurezza su Drive (già fatta).

## 0.13.0 — 2026-11-01
- **Scadenze**: nel carico c'è il campo «Scadenza» (facoltativo), salvato nei movimenti. I prodotti si consumano a partire da quelli che scadono prima e la scadenza segue spostamenti e cambi di categoria. Scaduti e in scadenza compaiono in «Da fare».
- **Avviso**: una notifica di Home Assistant al giorno (opzioni `scadenza_notifica`, `scadenza_giorni`, `scadenza_ora`), con pulsante di prova in Impostazioni. L'app ora può parlare con Home Assistant: dopo l'aggiornamento riavvia l'app.
- **Riordino del foglio** (Impostazioni): nasconde fogli e colonne di AppSheet (nulla viene cancellato), ordina schede e colonne, fissa le intestazioni, aggiunge filtri, formato data e menu a tendina.

## 0.12.14 — 2026-11-01
I filtri non si ricordano più tra un'apertura e l'altra: Stock e Prodotti ripartono sempre da «Tutti».

## 0.12.13 — 2026-11-01
Stock: i raggruppamenti restano quelli di prima (categoria e sottocategoria); dentro ogni sottocategoria i prodotti sono ordinati per tipo (quelli senza tipo in fondo) e poi per nome.

## 0.12.12 — 2026-11-01
Stock: scorrendo dentro una sottocategoria, il titolo fisso della categoria diventa «Categoria • Sottocategoria» (la sottocategoria in carattere più piccolo) e torna normale uscendone.

## 0.12.11 — 2026-11-01
Campi di ricerca (Stock e Prodotti): quando scrivi compare una ✕ per cancellare il testo con un tocco.

## 0.12.10 — 2026-11-01
Prodotti: nuovo filtro per posizione (Ovunque / Casa / Cantina), combinabile con categoria, tipo e con gli altri filtri. Si ricorda tra un'apertura e l'altra.

## 0.12.9 — 2026-11-01
Prodotti: i filtri «Esauriti» e «Sotto scorta» ragionano per tipo, come la lista della spesa. «Esauriti» mostra i prodotti a zero solo se anche il tipo è finito (se ne hai un altro dello stesso tipo, non compaiono). «Sotto scorta» mostra i prodotti in casa il cui tipo sta finendo. Anche il «da comprare» sulle righe segue la stessa regola.

## 0.12.8 — 2026-11-01
Correzione: il titolo della categoria (o del tipo) che resta fisso scorrendo l'elenco non si ferma più a metà schermo dopo aver chiuso il suggerimento o cambiato i filtri: segue sempre l'altezza reale della barra in alto.

## 0.12.7 — 2026-11-01
Scheda prodotto: lo smaltimento è l'ultima informazione e si legge a colpo d'occhio: un riquadro colorato per ogni materiale (carta blu, plastica gialla, vetro verde, metalli grigio, umido marrone) con il bidone dove va, senza testi lunghi.

## 0.12.6 — 2026-11-01
La revisione trova lo stesso prodotto censito con due codici (stessi nome, marca e confezione) e in «Da fare» propone «Unisci i prodotti». All'approvazione le giacenze e i movimenti passano al prodotto principale (quello con più dati); l'altro codice resta come **alias** nel nuovo foglio `alias` (creato dall'app) e la sua riga esce dal catalogo. Scansionando l'alias si apre il principale e i nuovi movimenti vanno su quello.

## 0.12.5 — 2026-11-01
- Correzione: «Sotto scorta» si calcola sul totale del **tipo** (la scorta minima è del tipo), non sul singolo prodotto. Tre confezioni di pasta con 7 pezzi in tutto non risultano più sotto scorta; la scheda mostra anche il totale del tipo.
- Punteggi (Nutri-Score, NOVA, Eco-Score) e modalità di riciclo: se non li trova negli archivi dei codici a barre, l'arricchimento li cerca con l'AI su Google (solo celle vuote, mai inventati; se non trova nulla il prodotto resta com'è).
- La revisione semestrale e «Avvia la revisione» contano anche i prodotti senza punteggi o senza riciclo, e l'arricchimento forzato ignora l'attesa dei 30 giorni.

## 0.12.4 — 2026-11-01
Scheda prodotto: categoria, sottocategoria e tipo sono pulsanti. Toccandoli si apre l'elenco Prodotti già filtrato su quella categoria, sottocategoria o tipo (il filtro del tipo si toglie con la ✕).

## 0.12.3 — 2026-11-01
Scheda prodotto: sotto Nutri-Score, NOVA ed Eco c'è una mini spiegazione del valore (es. «Qualità media», «Lavorato», «Impatto medio») e una riga che dice cosa significa ciascun punteggio. Il riciclo della confezione è sempre visibile: per ogni materiale (carta, plastica, vetro, metalli…) dice dove va e come prepararlo; senza dati lo dice. Sono indicazioni generali: i comuni possono avere regole diverse.

## 0.12.2 — 2026-11-01
Scheda prodotto rifatta: in alto immagine grande con nome, marca e codice; sotto categoria, sottocategoria e tipo come etichette; poi la giacenza con il numero grande e lo stato (In casa / Sotto scorta / Esaurito) a colori, con le posizioni; Nutri-Score, NOVA ed Eco come tre riquadri colorati; i valori nutrizionali in quattro riquadri; adatto a e allergeni come etichette. Ingredienti, produttore e smaltimento stanno in sezioni da aprire; le modifiche (sottocategoria, tipo, scorta) sono raccolte in «Modifica classificazione e scorta».

## 0.12.1 — 2026-11-01
Scheda prodotto: la matita (✎) accanto al nome permette di correggere a mano nome, marca e confezione (il nome si aggiorna anche sulle righe di movimento). «Cambia tipo» è ora un menu filtrato sulla categoria e sottocategoria del prodotto: mostra i tipi dei prodotti della stessa sottocategoria (o categoria), con «Tutti i tipi…» per vedere l'elenco completo. Lo stesso filtro vale per i suggerimenti del tipo nelle bozze.

## 0.12.0 — 2026-11-01
Emoji: ogni categoria e sottocategoria nuova (proposta dall'AI o rinominata) ha l'emoji davanti, con lo spazio. La revisione segnala quelle che non ce l'hanno (es. «Piante e Giardino», «Concimi e Terricci») o senza spazio dopo l'emoji (es. «🧴Corpo e Capelli»): «Aggiungi l'emoji» le rinomina anche su prodotti e movimenti.
Tipi: l'AI ora sceglie il tipo come famiglia di prodotti, non il singolo prodotto (Verdure surgelate, non Spinaci o Piselli). La revisione propone di rendere generici i tipi che coincidono col nome del prodotto.
Stock e Prodotti: le sottocategorie aggregano come le categorie. In Stock ogni categoria contiene gruppi per sottocategoria con pezzi e prodotti; in Prodotti, scelta una categoria, compare la riga delle sottocategorie.

## 0.11.5 — 2026-11-01
Scorta minima: accanto al numero ci sono i pulsanti − e + (da 0 a 999), senza tastiera; vale nella scheda del prodotto e nella correzione di un tipo nuovo in «Da fare».

## 0.11.4 — 2026-11-01
Scorta minima 0: vuol dire «non mi serve tenerne in casa», ma quando il tipo è finito compare comunque nella lista della spesa (prima con 0 non compariva mai). Con scorta 1 o più resta come prima: compare quando la giacenza scende a quel numero. La revisione non segnala più i tipi con scorta 0.

## 0.11.3 — 2026-10-31
Revisione, categoria: l'AI ora sa che la categoria dice dove tieni il prodotto, non che cos'è: il latte UHT chiuso, le conserve e simili restano in Dispensa anche se dopo l'apertura vanno in frigo. Quello che scegli «Ignora» non viene più riproposto nelle revisioni successive (vale per categoria, tipo, unioni e tipi senza prodotti).

## 0.11.2 — 2026-10-31
Revisione, controllo della categoria: ora riguarda tutti i prodotti (a gruppi di 40), non solo i primi 200.

## 0.11.1 — 2026-10-31
La revisione controlla anche la categoria dei prodotti: l'AI guarda i prodotti a gruppi di 40 (fino a 200 per revisione) e segnala solo quelli chiaramente nella categoria sbagliata, sempre con una coppia categoria/sottocategoria che esiste già. In «Da fare» compare «Categoria da controllare» con attuale e proposta: «Sposta» la applica (come l'approvazione AI dei prodotti), «Ignora» la scarta.

## 0.11.0 — 2026-10-31
Revisione a tappeto, ogni sei mesi (e a richiesta da Impostazioni › Revisione a tappeto): controlla prodotti senza tipo (l'AI ne propone uno), tipi quasi uguali da unire, tipi senza prodotti, scorte minime a 0, dati mancanti (si può lanciare l'arricchimento), sottocategorie vuote, codici a barre non validi o doppi, giacenze anomale e prodotti fermi da oltre un anno. Le voci compaiono in «Da fare»: quelle con una correzione si applicano con un tocco o si ignorano, le altre si chiudono con «Ok, visto». Non scrive sul foglio finché non approvi, quindi parte anche in sola lettura.
Prodotti esistenti: nella scheda c'è «Cambia tipo», un menu con i tipi esistenti oppure «Nuovo tipo…» (va in «Da fare» per la scorta).

## 0.10.11 — 2026-10-31
Tipo nuovo proposto dall'AI: con «Correggi» ora puoi cambiare anche il nome, oltre alla scorta minima. Il nome nuovo vale subito su prodotti e bozze; se scrivi il nome di un tipo che esiste già, la proposta si unisce a quello e i prodotti passano al tipo esistente.

## 0.10.10 — 2026-10-31
«Da inserire» e «Approvazioni» sono un unico tab, «Da fare»: in alto i prodotti da inserire, sotto le proposte AI da approvare, ciascuna sezione solo se ha elementi. Il tab compare solo quando c'è qualcosa da fare.

## 0.10.9 — 2026-10-31
Categorie nuove: se nessuna categoria/sottocategoria esistente calza (es. concime per piante), l'AI — sia nel suggerimento sia nella lettura della foto — propone una categoria o sottocategoria nuova. La proposta finisce in Approvazioni (senza doppioni); la bozza resta senza categoria con una nota, e dopo l'approvazione la scegli dall'elenco.

## 0.10.8 — 2026-10-31
Impostazioni: l'icona ingranaggio in alto apre una schermata (fuori dal menu in basso) con lo stato dell'arricchimento — ultimo giro, se è in corso, se il notturno è acceso, esito dell'ultimo giro — e il pulsante «Avvia ora», che lancia subito lo stesso lavoro della notte. Serve la sola lettura spenta.

## 0.10.7 — 2026-10-31
Prodotto nuovo con la foto: subito dopo la lettura della foto l'app cerca anche l'immagine sul web (Gemini con la ricerca Google, immagine presa solo da pagine che riportano davvero il codice) e la mette nella bozza. Il resto dei dati (dettagli, composizione, traduzioni) lo cerca il passaggio notturno. Per i codici GS1 di 16 cifre che iniziano per 01 si usa il GTIN contenuto; oltre 14 cifre senza GS1 la ricerca web si salta. Il salvataggio dopo la foto richiede qualche decina di secondi in più.

## 0.10.6 — 2026-10-31
Correzione: con una versione vecchia della pagina rimasta in memoria sul telefono, la foto di un prodotto nuovo non veniva passata al salvataggio e compariva «Codice sconosciuto: serve una foto per creare la bozza». Ora il server risponde in modo valido anche alle pagine vecchie e la pagina si ricarica da sola a ogni versione.

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
