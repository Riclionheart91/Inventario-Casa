#!/usr/bin/with-contenv bashio
# Le opzioni arrivano da Home Assistant; mai stampate nei log.
export SHEET_ID="$(bashio::config 'sheet_id')"
export DRIVE_FOLDER_ID="$(bashio::config 'drive_folder_id')"
export SERVICE_ACCOUNT_JSON="$(bashio::config 'service_account_json')"
export SHARED_CODE="$(bashio::config 'shared_code')"
export READ_ONLY="$(bashio::config 'sola_lettura')"
export SECURE_URL="$(bashio::config 'url_sicuro')"
# Chiavi opzionali dei servizi di ricerca e dell'AI (vuote = servizio saltato)
opt() { local v; v="$(bashio::config "$1")"; [ "$v" = "null" ] && v=""; printf '%s' "$v"; }
export GEMINI_API_KEY="$(opt gemini_api_key)" GEMINI_MODELLO="$(opt gemini_modello)" GEMINI_MODELLO_RISERVA="$(opt gemini_modello_riserva)"
export BARCODELOOKUP_KEY="$(opt barcodelookup_key)" UPCDATABASE_KEY="$(opt upcdatabase_key)" GOUPC_TOKEN="$(opt goupc_token)"
export SPOONACULAR_KEY="$(opt spoonacular_key)" NUTRITIONIX_APP_ID="$(opt nutritionix_app_id)" NUTRITIONIX_APP_KEY="$(opt nutritionix_app_key)"
export EDAMAM_APP_ID="$(opt edamam_app_id)" EDAMAM_APP_KEY="$(opt edamam_app_key)" ICECAT_SHOP="$(opt icecat_shop)"
export ICECAT_API_TOKEN="$(opt icecat_api_token)" GS1_API_URL="$(opt gs1_api_url)" GS1_API_KEY="$(opt gs1_api_key)" GOOGLE_BOOKS_KEY="$(opt google_books_key)" OPENFDA_KEY="$(opt openfda_key)"
cd /srv
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8099
