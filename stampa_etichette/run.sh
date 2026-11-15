#!/usr/bin/with-contenv bashio
# modo servizio (predefinito): server di stampa; modi connessione e stampa_prova: prove con esito nel registro
export STAMPANTE_MAC="$(bashio::config 'mac')"
export STAMPANTE_CANALE="$(bashio::config 'canale')"
export STAMPANTE_PORTA="$(bashio::config 'porta')" STAMPANTE_TOKEN="$(bashio::config 'token')" APP_VERSION="$(bashio::addon.version 2>/dev/null || true)"
export STAMPANTE_MODO="$(bashio::config 'modo')" STAMPANTE_OFFSET="$(bashio::config 'offset')"
cd /srv
exec python3 -m app.prova
