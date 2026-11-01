"""Riordino del foglio Google ora che l'app e l'unico utilizzatore: fogli e colonne usati solo da AppSheet vengono nascosti (non cancellati),
colonne e schede in ordine logico, intestazioni fisse, filtri, formati e menu a tendina. Si puo ripetere senza danni."""
from typing import Dict, List

# fogli usati dall'app, nell'ordine in cui compaiono (e colore della scheda)
ORDINE = [("movimenti", "#2f6fb5"), ("prodotti", "#2f6fb5"), ("categorie", "#2f8a55"), ("ai_tipi", "#2f8a55"), ("alias", "#2f8a55"),
          ("location", "#2f8a55"), ("bozze", "#a68a1f"), ("ai_prodotti", "#a68a1f"), ("ai_categorie", "#a68a1f"), ("log_ai", "#6b7683"),
          ("modifiche_migrazione", "#6b7683")]
# fogli che servivano solo ad AppSheet: nascosti, in fondo
SOLO_APPSHEET = ["Stock_ByLoc", "lista_spesa", "spesa_menu", "spesa_tipo", "FALLBACK_SOURCES", "BARCODES", "RESULTS", "coda"]
# ordine delle colonne (quelle non elencate restano in fondo, nascoste se sono di AppSheet)
COLONNE = {
    "movimenti": ["ID_Movimento", "Data", "Barcode", "Prodotto", "Tipo", "Quantità", "Location", "Categoria", "Sottocategoria", "Scadenza", "Note",
                  "Chi", "Foto", "Destinazione", "Categoria_NEW", "Prezzo", "ID_INGRESSO"],
    "prodotti": ["Barcode", "Prodotto", "Marca", "Confezione", "Categoria", "Sottocategoria", "Tipo", "Immagine", "Punteggi", "Smaltimento/riciclo",
                 "Dettagli prodotto", "Composizione", "Free-from", "Nutrizione (100g)", "API Status", "Aggiornato il",
                 "Quantità", "Scorta Minima", "Giacenza Attuale", "Location Default"],
}
NASCOSTE = {"movimenti": ["ID_INGRESSO"], "prodotti": ["Quantità", "Scorta Minima", "Giacenza Attuale", "Location Default"]}
MENU = {("movimenti", "Tipo"): ["Carico", "Scarico"], ("movimenti", "Location"): ["Casa", "Cantina"],
        ("ai_tipi", "Stato"): ["APPROVATO", "DA_APPROVARE", "RIFIUTATO"], ("ai_prodotti", "Stato"): ["DA_APPROVARE", "APPROVATO", "RIFIUTATO"]}


def _hex(c: str) -> dict:
    return {"red": int(c[1:3], 16) / 255, "green": int(c[3:5], 16) / 255, "blue": int(c[5:7], 16) / 255}


def piano(meta: Dict[str, dict], intest: Dict[str, List[str]]) -> (List[dict], List[str]):
    """Richieste per batchUpdate e riepilogo a parole. meta: titolo -> {id, hidden, righe}; intest: titolo -> intestazioni attuali."""
    rq: List[dict] = []
    nota: List[str] = []
    # schede nascoste (solo AppSheet)
    nascosti = [t for t in SOLO_APPSHEET if t in meta and not meta[t].get("hidden")]
    for t in nascosti:
        rq.append({"updateSheetProperties": {"properties": {"sheetId": meta[t]["id"], "hidden": True, "tabColor": _hex("#555555")}, "fields": "hidden,tabColor"}})
    if nascosti:
        nota.append("nascosti %d fogli usati solo da AppSheet (%s)" % (len(nascosti), ", ".join(nascosti)))
    # ordine e colore delle schede
    pos = 0
    for t, col in ORDINE:
        if t in meta:
            rq.append({"updateSheetProperties": {"properties": {"sheetId": meta[t]["id"], "index": pos, "tabColor": _hex(col), "hidden": False}, "fields": "index,tabColor,hidden"}})
            pos += 1
    nota.append("schede in ordine e colorate")
    for t, _ in ORDINE:
        if t not in meta:
            continue
        sid, h = meta[t]["id"], list(intest.get(t, []))
        # colonne in ordine
        if t in COLONNE:
            moss = 0
            for i, nome in enumerate([c for c in COLONNE[t] if c in h]):
                cur = h.index(nome)
                if cur != i:
                    rq.append({"moveDimension": {"source": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": cur, "endIndex": cur + 1}, "destinationIndex": i}})
                    h.insert(i, h.pop(cur)); moss += 1
            if moss:
                nota.append("%s: %d colonne riordinate" % (t, moss))
        # colonne di AppSheet nascoste
        for nome in NASCOSTE.get(t, []):
            if nome in h:
                i = h.index(nome)
                rq.append({"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
                                                         "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}})
        # intestazione fissa, in grassetto, con filtro
        rq.append({"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 1}}, "fields": "gridProperties.frozenRowCount"}})
        rq.append({"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1}, "cell": {"userEnteredFormat": {
            "textFormat": {"bold": True}, "backgroundColor": _hex("#e8eef6")}}, "fields": "userEnteredFormat(textFormat,backgroundColor)"}})
        if h:
            rq.append({"setBasicFilter": {"filter": {"range": {"sheetId": sid, "startRowIndex": 0, "startColumnIndex": 0, "endColumnIndex": len(h)}}}})
            rq.append({"autoResizeDimensions": {"dimensions": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": 0, "endIndex": len(h)}}})
        # formato data e menu a tendina
        if t == "movimenti" and "Scadenza" in h:
            i = h.index("Scadenza")
            rq.append({"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 1, "startColumnIndex": i, "endColumnIndex": i + 1},
                                      "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "dd/mm/yyyy"}}}, "fields": "userEnteredFormat.numberFormat"}})
        for (ft, col), valori in MENU.items():
            if ft == t and col in h:
                i = h.index(col)
                rq.append({"setDataValidation": {"range": {"sheetId": sid, "startRowIndex": 1, "startColumnIndex": i, "endColumnIndex": i + 1},
                                                 "rule": {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": v} for v in valori]},
                                                          "showCustomUi": True, "strict": False}}})
    nota.append("intestazioni fisse, filtri, larghezze, formato data della scadenza e menu a tendina")
    return rq, nota


def applica(store, log=None) -> dict:
    """Legge il foglio, costruisce il piano e lo applica in un'unica richiesta (tutto o niente). Solo per il foglio Google vero."""
    if not hasattr(store, "sheets") or not hasattr(store, "sheet_id") or isinstance(getattr(store, "sheets"), dict):
        raise RuntimeError("Il riordino funziona solo sul foglio Google vero.")
    with store._lock:
        met = store.sheets.get(spreadsheetId=store.sheet_id, fields="sheets.properties").execute(num_retries=3)
        meta = {s["properties"]["title"]: {"id": s["properties"]["sheetId"], "hidden": bool(s["properties"].get("hidden"))} for s in met.get("sheets", [])}
        titoli = [t for t, _ in ORDINE if t in meta]
        res = store.sheets.values().batchGet(spreadsheetId=store.sheet_id, ranges=["'%s'!1:1" % t for t in titoli], valueRenderOption="UNFORMATTED_VALUE").execute(num_retries=3)
        intest = {t: [str(x) for x in (vr.get("values") or [[]])[0]] for t, vr in zip(titoli, res.get("valueRanges", []))}
        rq, nota = piano(meta, intest)
        store.sheets.batchUpdate(spreadsheetId=store.sheet_id, body={"requests": rq}).execute(num_retries=3)
    riepilogo = " | ".join(nota)
    try:
        from datetime import datetime
        store.append_row("modifiche_migrazione", {"Quando": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "Modifica": "Riordino del foglio per l'app", "Dettaglio": riepilogo})
    except Exception:
        pass
    return {"ok": True, "richieste": len(rq), "riepilogo": nota}
