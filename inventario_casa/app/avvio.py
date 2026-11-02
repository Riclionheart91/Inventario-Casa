"""Primo avvio: se il foglio Google non c'e ancora, l'app lo crea (con tutte le schede e le intestazioni) nella cartella indicata.
L'ID del foglio creato resta in /data (le opzioni dell'app non si possono scrivere da qui) e viene riusato ai riavvii."""
import json
import os
import tempfile
from typing import Callable, Dict, List, Optional

TITOLO = "Inventario Casa"

# schede e intestazioni, nell'ordine in cui compaiono
INTESTAZIONI: Dict[str, List[str]] = {
    "movimenti": ["ID_Movimento", "Data", "Barcode", "Prodotto", "Tipo", "Quantità", "Location", "Categoria", "Sottocategoria", "Scadenza", "Note", "Chi", "Foto"],
    "prodotti": ["Barcode", "Prodotto", "Marca", "Confezione", "Categoria", "Sottocategoria", "Tipo", "Immagine", "Punteggi", "Smaltimento/riciclo",
                 "Dettagli prodotto", "Composizione", "Free-from", "Nutrizione (100g)", "API Status", "Aggiornato il"],
    "categorie": ["Categoria", "Sottocategoria", "Chiave"],
    "ai_tipi": ["Tipo", "Scorta_min", "Stato", "Note"],
    "alias": ["Alias", "Principale", "Creato", "Nome"],
    "location": ["Location"],
    "bozze": ["ID", "Barcode", "Foto", "Prodotto", "Marca", "Confezione", "Categoria", "Sottocategoria", "Tipo", "Immagine", "Nota", "Stato", "Fonte",
              "Location", "Movimento", "Quantità", "Aggiornato"],
    "ai_prodotti": ["Barcode", "Prodotto_Attuale", "Nome_Suggerito", "Categoria_Suggerita", "Sottocategoria_Suggerita", "Tipo", "Confidenza", "Motivo", "Stato", "Aggiornato"],
    "ai_categorie": ["Azione", "Categoria", "Sottocategoria", "Nuovo_Nome", "Motivo", "Prodotti_Esempio", "Stato", "Aggiornato"],
    "log_ai": ["Quando", "Barcode", "Campo", "Prima", "Dopo", "Fonte", "Confidenza"],
    "regole": ["Regola", "Creata"],
    "modifiche_migrazione": ["Quando", "Modifica", "Dettaglio"],
}
VALORI_INIZIALI = {"location": [["Casa"], ["Cantina"]]}


def _cartella() -> str:
    return os.environ.get("DATA_DIR") or ("/data" if os.path.isdir("/data") else tempfile.gettempdir())


def _file() -> str:
    return os.path.join(_cartella(), "foglio_creato.json")


def leggi_salvato(configurato: str) -> str:
    """ID del foglio creato dall'app per questa configurazione (vale solo se l'ID configurato non e cambiato)."""
    try:
        with open(_file(), encoding="utf-8") as f:
            d = json.load(f)
        return d["id"] if d.get("da", "") == (configurato or "") else ""
    except Exception:
        return ""


def _salva(configurato: str, nuovo: str) -> None:
    with open(_file(), "w", encoding="utf-8") as f:
        json.dump({"da": configurato or "", "id": nuovo}, f)


def richieste_struttura(primo_id: int) -> List[dict]:
    """Rinomina la prima scheda in «movimenti» e aggiunge le altre."""
    rq = [{"updateSheetProperties": {"properties": {"sheetId": primo_id, "title": "movimenti", "gridProperties": {"frozenRowCount": 1}}, "fields": "title,gridProperties.frozenRowCount"}}]
    for t in list(INTESTAZIONI)[1:]:
        rq.append({"addSheet": {"properties": {"title": t, "gridProperties": {"frozenRowCount": 1}}}})
    return rq


def crea_foglio(sheets, drive, cartella: str = "", condividi_con: str = "", titolo: str = TITOLO) -> str:
    """Crea il foglio con tutte le schede e le intestazioni; ritorna il suo ID. `sheets` e `drive` sono i client Google gia autenticati."""
    meta = {"name": titolo, "mimeType": "application/vnd.google-apps.spreadsheet"}
    if cartella:
        meta["parents"] = [cartella]
    nuovo = drive.files().create(body=meta, fields="id", supportsAllDrives=True).execute(num_retries=3)["id"]
    info = sheets.get(spreadsheetId=nuovo, fields="sheets.properties").execute(num_retries=3)
    primo = info["sheets"][0]["properties"]["sheetId"]
    sheets.batchUpdate(spreadsheetId=nuovo, body={"requests": richieste_struttura(primo)}).execute(num_retries=3)
    dati = []
    for t, h in INTESTAZIONI.items():
        dati.append({"range": "'%s'!A1" % t, "values": [h] + VALORI_INIZIALI.get(t, [])})
    sheets.values().batchUpdate(spreadsheetId=nuovo, body={"valueInputOption": "RAW", "data": dati}).execute(num_retries=3)
    if condividi_con:
        drive.permissions().create(fileId=nuovo, body={"type": "user", "role": "writer", "emailAddress": condividi_con}, sendNotificationEmail=False,
                                   supportsAllDrives=True).execute(num_retries=3)
    return nuovo


def esiste(sheets, sheet_id: str) -> bool:
    """True se il foglio risponde; False solo se Google dice che non esiste (404). Altri errori (rete, permessi) si propagano."""
    try:
        sheets.get(spreadsheetId=sheet_id, fields="spreadsheetId").execute(num_retries=3)
        return True
    except Exception as e:
        if getattr(getattr(e, "resp", None), "status", None) == 404:
            return False
        raise


def risolvi(configurato: str, crea: bool, sheets, drive, cartella: str = "", condividi_con: str = "",
            log: Callable[[str], None] = print, salva: Callable[[str, str], None] = _salva, letto: Optional[Callable[[str], str]] = None) -> str:
    """ID del foglio da usare. Con `crea` attivo: se manca l'ID o il foglio non esiste, ne crea uno nuovo (una volta sola: poi riusa quello salvato)."""
    if not crea:
        return configurato
    gia = (letto or leggi_salvato)(configurato)
    if gia:
        return gia
    if configurato and esiste(sheets, configurato):
        return configurato
    nuovo = crea_foglio(sheets, drive, cartella, condividi_con)
    salva(configurato, nuovo)
    log("Foglio creato: https://docs.google.com/spreadsheets/d/%s/edit (copia l'ID nell'opzione sheet_id)" % nuovo)
    return nuovo
