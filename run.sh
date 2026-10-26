#!/usr/bin/with-contenv bashio
# Le opzioni arrivano da Home Assistant; mai stampate nei log.
export SHEET_ID="$(bashio::config 'sheet_id')"
export DRIVE_FOLDER_ID="$(bashio::config 'drive_folder_id')"
export SERVICE_ACCOUNT_JSON="$(bashio::config 'service_account_json')"
export SHARED_CODE="$(bashio::config 'shared_code')"
cd /srv
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8099
