# Inventario Casa

Interfaccia dell'inventario domestico dietro Home Assistant. Legge e scrive il foglio Google indicato nelle opzioni.

## Opzioni obbligatorie
- **sheet_id**: ID del foglio Google.
- **service_account_json**: chiave del service account che ha accesso al foglio.
- **sola_lettura**: se attiva, l'app non scrive nulla.

## Opzioni facoltative
- **shared_code**, **url_sicuro**, **drive_folder_id**: codice di accesso, indirizzo sicuro per la fotocamera, cartella foto.

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

## Accesso diretto (porta 8099)
Oltre all'ingress di Home Assistant l'app risponde su `http://IP-DI-HOME-ASSISTANT:8099`. Imposta `shared_code` (codice unico di famiglia) nelle opzioni: senza codice la porta diretta resta spenta. Cambiare il codice scollega tutti i dispositivi. L'ingress non richiede il codice. Per la fotocamera dal vivo serve https (es. Tailscale) o l'ingress.
