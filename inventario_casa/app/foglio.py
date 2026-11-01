"""Riordino del foglio Google ora che l'app e l'unico utilizzatore: fogli e colonne usati solo da AppSheet vengono nascosti (non cancellati),
colonne e schede in ordine logico, intestazioni fisse, filtri, formati e menu a tendina. Si puo ripetere senza danni."""
from typing import Dict, List

# fogli usati dall'app, nell'ordine in cui compaiono (e colore della scheda)
ORDINE = [("movimenti", "#2f6fb5"), ("prodotti", "#2f6fb5"), ("categorie", "#2f8a55"), ("ai_tipi", "#2f8a55"), ("alias", "#2f8a55"),
          ("location", "#2f8a55"), ("bozze", "#a68a1f"), ("ai_prodotti", "#a68a1f"), ("ai_categorie", "#a68a1f"), ("log_ai", "#6b7683"),
          ("modifiche_migrazione", "#6b7683")]
# fogli che servivano solo ad AppSheet: nascosti, in fondo
SOLO_APPSHEET = ["Stock_ByLoc", "lista_spesa", "spesa_menu", "spesa_tipo", "FALLBACK_SOURCES", "BARCODES", "RESULTS", "coda"]
# di questi, quelli che erano solo formule o vuoti si eliminano (la copia di sicurezza li conserva); FALLBACK_SOURCES contiene dati e resta nascosto
DA_ELIMINARE = ["Stock_ByLoc", "lista_spesa", "spesa_menu", "spesa_tipo", "BARCODES", "RESULTS", "coda"]
# colonne calcolate da AppSheet: il calcolo ora lo fa l'app, quindi si eliminano
COLONNE_MORTE = {"movimenti": ["ID_INGRESSO"], "prodotti": ["Quantità", "Scorta Minima", "Giacenza Attuale", "Location Default"]}
# righe chiuse (gia applicate o scartate) che si spostano nel foglio «archivio»
CHIUSE = {"bozze": {"INSERITA", "SCARTATA"}, "ai_categorie": {"APPLICATA", "APPLICATO", "RIFIUTATA", "RIFIUTATO"},
          "ai_prodotti": {"NESSUNA_MODIFICA", "APPLICATO", "RIFIUTATO"}}
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


def piano(meta: Dict[str, dict], intest: Dict[str, List[str]], profondo: bool = False) -> (List[dict], List[str]):
    """Richieste per batchUpdate e riepilogo a parole. meta: titolo -> {id, hidden, righe}; intest: titolo -> intestazioni attuali."""
    rq: List[dict] = []
    nota: List[str] = []
    # schede nascoste (solo AppSheet)
    if profondo:
        elim = [t for t in DA_ELIMINARE if t in meta]
        for t in elim:
            rq.append({"deleteSheet": {"sheetId": meta[t]["id"]}})
        if elim:
            nota.append("eliminati %d fogli calcolati da AppSheet (%s)" % (len(elim), ", ".join(elim)))
    nascosti = [t for t in SOLO_APPSHEET if t in meta and not meta[t].get("hidden") and not (profondo and t in DA_ELIMINARE)]
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
        # colonne calcolate da AppSheet: eliminate (profondo) o nascoste
        for nome in COLONNE_MORTE.get(t, []) if profondo else []:
            if nome in h:
                i = h.index(nome)
                rq.append({"deleteDimension": {"range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1}}})
                h.pop(i)
                nota.append("%s: colonna «%s» eliminata" % (t, nome))
        for nome in [] if profondo else NASCOSTE.get(t, []):
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


def piano_pulizia(dati: Dict[str, tuple], oggi: str) -> dict:
    """Dai fogli letti {titolo: (intestazioni, righe)} ricava: righe chiuse da archiviare ed eliminare, categorie e tipi mancanti da aggiungere.
    Le righe sono numerate come nel foglio (la 1 e l'intestazione)."""
    import json as _j
    elimina: Dict[str, List[int]] = {}
    archivio: List[List[str]] = []
    for t, chiuse in CHIUSE.items():
        h, righe = dati.get(t, ([], []))
        if "Stato" not in h:
            continue
        i = h.index("Stato")
        for n, r in enumerate(righe, start=2):
            if len(r) > i and str(r[i]).strip().upper() in chiuse:
                elimina.setdefault(t, []).append(n)
                archivio.append([oggi, t, _j.dumps(dict(zip(h, [str(x) for x in r])), ensure_ascii=False)])
    # categorie usate dai prodotti ma assenti dall'elenco
    hc, rc = dati.get("categorie", ([], []))
    hp, rp = dati.get("prodotti", ([], []))
    cats = set()
    if "Categoria" in hc and "Sottocategoria" in hc:
        ic, isu = hc.index("Categoria"), hc.index("Sottocategoria")
        cats = {(str(r[ic]).strip(), str(r[isu]).strip()) for r in rc if len(r) > max(ic, isu)}
    nuove_cat = []
    if "Categoria" in hp and "Sottocategoria" in hp:
        ic, isu = hp.index("Categoria"), hp.index("Sottocategoria")
        for r in rp:
            c, s = (str(r[ic]).strip() if len(r) > ic else ""), (str(r[isu]).strip() if len(r) > isu else "")
            if c and s and (c, s) not in cats and (c, s) not in nuove_cat:
                nuove_cat.append((c, s))
    # tipi dei prodotti senza riga in ai_tipi: scorta 0 (come gia si comportava l'app), cosi si vedono e si possono regolare
    ht, rt = dati.get("ai_tipi", ([], []))
    nuovi_tipi = []
    if "Tipo" in ht and "Tipo" in hp:
        it = ht.index("Tipo"); ist = ht.index("Stato") if "Stato" in ht else None
        noti = {str(r[it]).strip().lower() for r in rt if len(r) > it and (ist is None or len(r) <= ist or str(r[ist]).upper() != "RIFIUTATO")}
        ip = hp.index("Tipo")
        for r in rp:
            t = str(r[ip]).strip() if len(r) > ip else ""
            if t and t.lower() not in noti and t not in nuovi_tipi:
                nuovi_tipi.append(t)
    return {"elimina": elimina, "archivio": archivio, "nuove_categorie": nuove_cat, "nuovi_tipi": nuovi_tipi}


def _intervalli(righe: List[int]) -> List[tuple]:
    """Righe (1-based) -> intervalli consecutivi (da, a esclusa, 0-based), dal fondo verso l'alto perche l'eliminazione non sposti gli indici."""
    out, righe = [], sorted(righe)
    for n in righe:
        if out and n == out[-1][1] + 1:
            out[-1][1] = n
        else:
            out.append([n, n])
    return [(a - 1, b) for a, b in reversed(out)]


def applica(store, log=None, profondo: bool = True) -> dict:
    """Legge il foglio, costruisce il piano e lo applica in un'unica richiesta (tutto o niente). Solo per il foglio Google vero."""
    if not hasattr(store, "sheets") or not hasattr(store, "sheet_id") or isinstance(getattr(store, "sheets"), dict):
        raise RuntimeError("Il riordino funziona solo sul foglio Google vero.")
    with store._lock:
        met = store.sheets.get(spreadsheetId=store.sheet_id, fields="sheets.properties").execute(num_retries=3)
        meta = {s["properties"]["title"]: {"id": s["properties"]["sheetId"], "hidden": bool(s["properties"].get("hidden"))} for s in met.get("sheets", [])}
        titoli = [t for t, _ in ORDINE if t in meta]
        res = store.sheets.values().batchGet(spreadsheetId=store.sheet_id, ranges=["'%s'!1:1" % t for t in titoli], valueRenderOption="UNFORMATTED_VALUE").execute(num_retries=3)
        intest = {t: [str(x) for x in (vr.get("values") or [[]])[0]] for t, vr in zip(titoli, res.get("valueRanges", []))}
        nota_p: List[str] = []
        if profondo:   # 1) pulizia dei dati (righe chiuse archiviate, categorie e tipi mancanti)
            leggi = [t for t in ("bozze", "ai_categorie", "ai_prodotti", "prodotti", "categorie", "ai_tipi") if t in meta]
            dati = store.get_many(leggi)   # il blocco e rientrante: le chiamate dello store dentro «with store._lock» vanno bene
            from datetime import datetime as _dt
            pl = piano_pulizia(dati, _dt.now().strftime("%d/%m/%Y"))
            if pl["archivio"]:
                store.crea_foglio("archivio", ["Quando", "Foglio", "Dati"])
                store.sheets.values().append(spreadsheetId=store.sheet_id, range="'archivio'!A1", valueInputOption="RAW", insertDataOption="INSERT_ROWS",
                                             body={"values": pl["archivio"]}).execute(num_retries=3)
            dele = []
            for t, righe in pl["elimina"].items():
                for a, b in _intervalli(righe):
                    dele.append({"deleteDimension": {"range": {"sheetId": meta[t]["id"], "dimension": "ROWS", "startIndex": a, "endIndex": b}}})
                nota_p.append("%s: %d righe chiuse spostate in «archivio»" % (t, len(righe)))
            if dele:
                store.sheets.batchUpdate(spreadsheetId=store.sheet_id, body={"requests": dele}).execute(num_retries=3)
            if pl["nuove_categorie"] and "categorie" in meta:
                hc = dati["categorie"][0]
                store.sheets.values().append(spreadsheetId=store.sheet_id, range="'categorie'!A1", valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
                                             body={"values": [[(c if k == "Categoria" else s if k == "Sottocategoria" else "") for k in hc] for c, s in pl["nuove_categorie"]]}).execute(num_retries=3)
                nota_p.append("categorie: aggiunte %d coppie usate dai prodotti" % len(pl["nuove_categorie"]))
            if pl["nuovi_tipi"] and "ai_tipi" in meta:
                ht = dati["ai_tipi"][0]
                vals = {"Tipo": None, "Scorta_min": 0, "Stato": "APPROVATO", "Note": "aggiunto dal riordino (scorta 0)"}
                store.sheets.values().append(spreadsheetId=store.sheet_id, range="'ai_tipi'!A1", valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
                                             body={"values": [[(t if k == "Tipo" else vals.get(k, "")) for k in ht] for t in pl["nuovi_tipi"]]}).execute(num_retries=3)
                nota_p.append("ai_tipi: aggiunti %d tipi usati dai prodotti, con scorta 0" % len(pl["nuovi_tipi"]))
        # 2) struttura: fogli, colonne, formati
        rq, nota = piano(meta, intest, profondo)
        nota = nota_p + nota
        store.sheets.batchUpdate(spreadsheetId=store.sheet_id, body={"requests": rq}).execute(num_retries=3)
    riepilogo = " | ".join(nota)
    try:
        from datetime import datetime
        store.append_row("modifiche_migrazione", {"Quando": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "Modifica": "Riordino del foglio per l'app", "Dettaglio": riepilogo})
    except Exception:
        pass
    return {"ok": True, "richieste": len(rq), "riepilogo": nota}
