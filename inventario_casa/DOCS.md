# Inventario Casa

Interfaccia dell'inventario domestico dietro Home Assistant. Legge e scrive il foglio Google indicato nelle opzioni.

## Opzioni obbligatorie
- **sheet_id**: ID del foglio Google.
- **service_account_json**: chiave del service account che ha accesso al foglio.
- **sola_lettura**: se attiva, l'app non scrive nulla.

## Opzioni facoltative
- **shared_code**, **url_sicuro**: codice di accesso, indirizzo sicuro per la fotocamera. **drive_folder_id** non serve più: le foto dei prodotti nuovi non si salvano.

## AI per i prodotti nuovi (dalla 0.4.0)
- **gemini_api_key**: chiave Google Gemini. Con la chiave, per un prodotto nuovo l'app suggerisce categoria, sottocategoria e tipo; li rivedi e salvi. Senza chiave i menu restano vuoti.
- **gemini_modello**, **gemini_modello_riserva**: modelli da usare (vuoti = quelli del motore: gemini-3.5-flash-lite e gemini-3.1-flash-lite).
- Un tipo nuovo entra in `ai_tipi` come DA_APPROVARE con scorta minima 0: lo trovi in Approvazioni.

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

Opzione `traduzione_all_avvio`: accendila una volta (con `sola_lettura` spenta) e riavvia l'app per tradurre i testi gia presenti; poi rispegnila.

## Risposte a voce (dalla 0.9.0)
Opzione `voce_token` (una parola d'ordine a tua scelta): accende `GET /voce/manca` e `GET /voce/cerca?q=...&t=TOKEN`, che rispondono con una frase pronta ({"testo": "..."}). Da Home Assistant: file in `home_assistant/` (pacchetto `inventario_voce.yaml` e frasi `inventario_frasi_it.yaml`). Senza token il servizio e spento.

## Accesso per chi non e amministratore (dalla 0.9.5)
Home Assistant non apre le app agli utenti non amministratori. La porta diretta 8099 e quindi di nuovo pubblicata:
- imposta `shared_code` (il codice di famiglia, cambiabile quando vuoi) e riavvia l'app;
- in rete di casa: `http://IP-DI-HOME-ASSISTANT:8099` (senza https la fotocamera non parte: il codice si digita);
- con la fotocamera (https) via Tailscale: da una shell sul Tailscale di Home Assistant, `/opt/tailscale serve --bg --https=8443 localhost:8099`; poi `https://homeassistant-1.tail5d3791.ts.net:8443`. La persona deve avere Tailscale e accesso alla tua rete Tailscale.
