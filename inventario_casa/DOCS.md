# Inventario Casa

Interfaccia dell'inventario domestico dietro Home Assistant. Legge e scrive il foglio Google indicato nelle opzioni.

## Opzioni obbligatorie
- **sheet_id**: ID del foglio Google (può restare vuoto se usi `crea_foglio`).
- **service_account_json**: chiave del service account che ha accesso al foglio.
- **sola_lettura**: se attiva, l'app non scrive nulla.

## Primo avvio: creare il foglio (dalla 0.14.0)
Se non hai ancora il foglio, attiva **crea_foglio** e lascia **sheet_id** vuoto. All'avvio l'app crea «Inventario Casa» su Google Drive con tutte le schede (movimenti, prodotti, categorie, ai_tipi, alias, location, bozze, ai_prodotti, ai_categorie, log_ai) e le intestazioni giuste.
- **drive_folder_id**: cartella di Drive dove metterlo. Conviene indicarne una condivisa con il service account (il foglio eredita la condivisione); senza cartella nasce nello spazio del service account.
- **condividi_con**: il tuo indirizzo Google, per vedere e modificare il foglio (come editor).
- L'indirizzo del foglio compare nel registro dell'app. L'ID resta salvato: ai riavvii l'app riusa lo stesso foglio. Se vuoi, copialo in **sheet_id** e spegni **crea_foglio**.
- Se `sheet_id` è indicato ma il foglio non esiste più (risposta 404 di Google), l'app ne crea uno nuovo; per errori di rete o di permessi non fa nulla.
- Le categorie partono vuote: aggiungile dall'app o nel foglio «categorie».

## Opzioni facoltative
- **shared_code**, **url_sicuro**: codice di accesso, indirizzo sicuro per la fotocamera. **drive_folder_id** non serve più: le foto dei prodotti nuovi non si salvano.

## AI per i prodotti nuovi (dalla 0.4.0)
- **gemini_api_key**: chiave Google Gemini. Con la chiave, per un prodotto nuovo l'app suggerisce categoria, sottocategoria e tipo; li rivedi e salvi. Senza chiave i menu restano vuoti.
- **gemini_modello**, **gemini_modello_riserva**: modelli da usare (vuoti = quelli del motore: gemini-3.5-flash-lite e gemini-3.1-flash-lite).
- Un tipo nuovo entra in `ai_tipi` come DA_APPROVARE con scorta minima 0: lo trovi nel tab «Da fare».

## Ricerca del codice: servizi a chiave (ripiego)
Open Food Facts e gli altri database aperti non richiedono chiavi. Se inserisci una chiave, il servizio viene interrogato dopo di quelli:
**barcodelookup_key**, **upcdatabase_key**, **goupc_token**, **spoonacular_key**, **nutritionix_app_id** + **nutritionix_app_key**, **edamam_app_id** + **edamam_app_key**, **icecat_shop** + **icecat_api_token**, **gs1_api_url** + **gs1_api_key**.
Sempre attivi e senza chiave, subito dopo i quattro Open*Facts: FoodRepo, OpenGTINDB, Datakick (e gtinsearch), Open Beer DB, OpenLibrary e Google Books (solo ISBN), OpenFDA.
Chiavi facoltative che alzano i limiti: **google_books_key**, **openfda_key**.
Un servizio a chiave senza tutte le sue chiavi viene saltato. Le chiavi restano sul server e non vengono mai mostrate nell'app né scritte nei log.

## Lista della spesa su iPhone (dalla 0.6.0)
Nella pagina Spesa il pulsante «Aggiungi alla lista della spesa di iOS» manda a Promemoria tutte le voci da comprare che non hai ancora spuntato nel carrello, una per riga.
- **shortcut_spesa**: nome del comando rapido da avviare (default «Spesa AppSheet»).
- Su iPhone e iPad l'app apre il comando rapido con l'elenco come testo in ingresso. Su altri dispositivi apre il foglio di condivisione, oppure copia l'elenco negli appunti.

Per creare il comando rapido (una volta sola, app Comandi):
1. Nuovo comando, chiamalo «Spesa AppSheet» (o il nome che hai messo in **shortcut_spesa**).
2. Azione «Dividi testo» sull'input del comando, separatore «A capo».
3. Azione «Ripeti con ciascun elemento» sul risultato.
4. Dentro la ripetizione: «Aggiungi nuovo promemoria» con titolo = «Elemento ripetuto», lista = «Spesa».
5. Nelle impostazioni del comando, attiva «Accetta input» di tipo testo.
La prima volta iOS chiede il permesso di eseguire il comando dall'app.

## Accesso
Si usa solo tramite Home Assistant (ingress), dal pannello Inventario o dall'indirizzo https di Tailscale: la porta diretta 8099 non viene più pubblicata (dalla 0.7.1). Il codice di accesso diretto è ancora nel programma ma resta spento, perché la porta non è raggiungibile dall'esterno del container.

## Arricchimento notturno e traduzione (dalla 0.8.0)
Opzioni: `arricchimento_notturno` (acceso/spento, di default spento), `arricchimento_ora` (es. 03:00, ora italiana), `arricchimento_max` (prodotti per notte, 60). Funziona solo se `sola_lettura` e spento. Riempie solo i campi vuoti, non cambia nulla se non trova il codice (lo riprova dopo 30 giorni), traduce in italiano i testi lunghi con Gemini. Prima di accenderlo spegni `startNightlyFullEnrich` nello script Google. Il rapporto dell'ultimo giro e in `GET /api/arricchimento`.

## Scadenze e avviso

Nel carico c'e il campo **Scadenza** (facoltativo): la data finisce nella colonna `Scadenza` dei movimenti. I prodotti si consumano a partire da quelli che scadono prima; spostando un prodotto da Casa a Cantina (o cambiando categoria) la scadenza lo segue. In **Da fare** compare la sezione *Scadenze* con i prodotti scaduti o in scadenza.

Per ricevere una notifica sul telefono imposta nelle opzioni: `scadenza_notifica` (il servizio notify di Home Assistant, per esempio `mobile_app_il_mio_telefono`: lo trovi in Strumenti per sviluppatori › Azioni, cercando «notify»), `scadenza_giorni` (anticipo, 7 di default) e `scadenza_ora` (08:00 di default, ora italiana). Arriva al massimo una notifica al giorno e solo se c'e qualcosa da dire. In Impostazioni › *Avviso scadenze* c'e il pulsante **Invia notifica di prova**. Serve riavviare l'app dopo aver cambiato le opzioni (l'accesso a Home Assistant e gia incluso).

## Modelli per compito (dalla 0.16.0)
`gemini_modello` è il modello leggero (classificare, tradurre); `gemini_modello_riserva` subentra se non risponde. `gemini_modello_potente`, facoltativo, è per i compiti che richiedono più giudizio: ricerca sul web, foto, punteggi e riciclo, controllo delle categorie. Se è vuoto, tutti i compiti usano il modello normale. Un modello più capace di solito risponde più lentamente: usalo se preferisci la precisione alla rapidità.

## AI: uso, memoria e regole (dalla 0.15.0)
Dalla 0.17.0: «Suggerisci dai miei dati» propone regole ricavate dal catalogo e dalle tue correzioni (soglie: almeno 3 prodotti e 80% nello stesso posto, oppure 2 correzioni uguali), e «Controlla i modelli disponibili» verifica quali modelli Gemini risponde il tuo account.
In Impostazioni: **Regole della casa** (frasi che l'AI rispetta nelle classificazioni, salvate nel foglio «regole»; servono `sola_lettura` spenta per aggiungerle o toglierle) e **Uso dell'AI** (richieste, errori, tempi e come hai trattato le proposte). Le risposte ripetute restano in memoria 30 giorni per non richiamare Gemini inutilmente; il pulsante «Svuota la memoria» le toglie. I conteggi sono in `/data` e non contengono chiavi né testi dei prodotti.

## Riordino del foglio

Impostazioni › *Riordino del foglio* (con `sola_lettura` spenta; due tocchi). È un riordino profondo, pensato per quando AppSheet non serve più:

- elimina i fogli solo di calcolo di AppSheet (`Stock_ByLoc`, `lista_spesa`, `spesa_menu`, `spesa_tipo`, `BARCODES`, `RESULTS`, `coda`); `FALLBACK_SOURCES` contiene dati e resta nascosto;
- elimina le colonne calcolate da AppSheet (prodotti: `Quantità`, `Scorta Minima`, `Giacenza Attuale`, `Location Default`; movimenti: `ID_INGRESSO`);
- sposta nel foglio `archivio` le righe chiuse (bozze inserite o scartate, proposte AI già applicate o senza modifica);
- aggiunge a `categorie` le coppie categoria/sottocategoria usate dai prodotti e a `ai_tipi` i tipi dei prodotti che non hanno una riga (scorta 0);
- mette in ordine schede e colonne, fissa le intestazioni, aggiunge filtri, formato data per la scadenza e menu a tendina.

Prima fai una copia di sicurezza del foglio su Drive: ripristina tutto. L'operazione si può ripetere.

Opzione `traduzione_all_avvio`: accendila una volta (con `sola_lettura` spenta) e riavvia l'app per tradurre i testi gia presenti; poi rispegnila.

## Risposte a voce (dalla 0.9.0)
Opzione `voce_token` (una parola d'ordine a tua scelta): accende `GET /voce/manca` e `GET /voce/cerca?q=...&t=TOKEN`, che rispondono con una frase pronta ({"testo": "..."}). Da Home Assistant: file in `home_assistant/` (pacchetto `inventario_voce.yaml` e frasi `inventario_frasi_it.yaml`). Senza token il servizio e spento.

## Accesso per chi non e amministratore (dalla 0.9.5)
Home Assistant non apre le app agli utenti non amministratori. La porta diretta 8099 e quindi di nuovo pubblicata:
- imposta `shared_code` (il codice di famiglia, cambiabile quando vuoi) e riavvia l'app;
- in rete di casa: `http://IP-DI-HOME-ASSISTANT:8099` (senza https la fotocamera non parte: il codice si digita);
- con la fotocamera (https) via Tailscale: da una shell sul Tailscale di Home Assistant, `/opt/tailscale serve --bg --https=8443 localhost:8099`; poi `https://homeassistant-1.tail5d3791.ts.net:8443`. La persona deve avere Tailscale e accesso alla tua rete Tailscale.
