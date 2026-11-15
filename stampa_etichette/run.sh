#!/usr/bin/with-contenv bashio
# Fase 1: solo prova di connessione (nessun dato inviato alla stampante). L'esito e nel registro dell'add-on.
export STAMPANTE_MAC="$(bashio::config 'mac')"
export STAMPANTE_CANALE="$(bashio::config 'canale')"
export STAMPANTE_MODO="$(bashio::config 'modo')" STAMPANTE_OFFSET="$(bashio::config 'offset')"
cd /srv
exec python3 -m app.prova
