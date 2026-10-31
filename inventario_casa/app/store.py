"""SheetsStore: astrazione sul foglio. MemoryStore per test (MOCK=1), GoogleStore per produzione."""
import json
import os
import threading
from typing import Dict, List, Tuple


class SheetsStore:
    def get_rows(self, sheet: str) -> Tuple[List[str], List[List]]:
        raise NotImplementedError

    def append_row(self, sheet: str, values: Dict[str, object]) -> int:
        """Aggiunge una riga mappando i valori sulle intestazioni. Ritorna il numero di riga (1-based)."""
        raise NotImplementedError

    def get_many(self, sheets):
        """Legge piu fogli in una volta: {nome: (intestazioni, righe)}. Il default li legge uno alla volta."""
        return {n: self.get_rows(n) for n in sheets}

    def update_cell(self, sheet: str, row: int, header: str, value) -> None:
        raise NotImplementedError

    def update_cells(self, sheet: str, items) -> None:
        """Scrive piu celle in una volta: items = [(riga 1-based, intestazione, valore)]."""
        raise NotImplementedError

    def upload_photo(self, name: str, data: bytes, mime: str) -> str:
        raise NotImplementedError


class MemoryStore(SheetsStore):
    def __init__(self, sheets: Dict[str, List[List]] = None):
        self.sheets = sheets or {}
        self.photos: Dict[str, bytes] = {}

    def get_rows(self, sheet):
        data = self.sheets.get(sheet)
        if not data:
            return [], []
        return [str(h) for h in data[0]], [list(r) for r in data[1:]]

    def append_row(self, sheet, values):
        data = self.sheets.setdefault(sheet, [[]])
        headers = data[0]
        for k in values:
            if k not in headers:
                headers.append(k)
        data.append([values.get(h, "") for h in headers])
        return len(data)

    def update_cell(self, sheet, row, header, value):
        data = self.sheets[sheet]
        i = data[0].index(header)
        r = data[row - 1]
        while len(r) <= i:
            r.append("")
        r[i] = value

    def update_cells(self, sheet, items):
        for row, header, value in items:
            self.update_cell(sheet, row, header, value)

    def upload_photo(self, name, data, mime):
        self.photos[name] = data
        return "https://drive.example/mock/" + name


def _testo(v):
    """Cifre lunghe (oltre 15) restano testo: i numeri di Fogli perdono precisione."""
    return "'" + v if isinstance(v, str) and v.isdigit() and len(v) > 15 else v


class GoogleStore(SheetsStore):
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

    def __init__(self, sheet_id: str, folder_id: str, service_account_json: str):
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        info = json.loads(service_account_json)
        creds = service_account.Credentials.from_service_account_info(info, scopes=self.SCOPES)
        self.sheet_id, self.folder_id = sheet_id, folder_id
        self._lock = threading.RLock()   # il client di Google non e sicuro con piu thread insieme (ciclo di aggiornamento + richieste): una chiamata alla volta
        self.sheets = build("sheets", "v4", credentials=creds, cache_discovery=False).spreadsheets()
        self.drive = build("drive", "v3", credentials=creds, cache_discovery=False)

    @staticmethod
    def _col(n: int) -> str:
        s = ""
        n += 1
        while n:
            n, r = divmod(n - 1, 26)
            s = chr(65 + r) + s
        return s

    def get_rows(self, sheet):
        res = self.sheets.values().get(spreadsheetId=self.sheet_id, range="'%s'" % sheet,
                                       valueRenderOption="UNFORMATTED_VALUE").execute(num_retries=3)
        vals = res.get("values", [])
        if not vals:
            return [], []
        return [str(h) for h in vals[0]], vals[1:]

    def get_many(self, sheets):
        sheets = list(sheets)
        res = self.sheets.values().batchGet(spreadsheetId=self.sheet_id, ranges=["'%s'" % n for n in sheets],
                                            valueRenderOption="UNFORMATTED_VALUE").execute(num_retries=3)
        out = {}
        for n, vr in zip(sheets, res.get("valueRanges", [])):
            vals = vr.get("values", [])
            out[n] = ([str(h) for h in vals[0]], vals[1:]) if vals else ([], [])
        return out

    def append_row(self, sheet, values):
        headers, rows = self.get_rows(sheet)
        row = [_testo(values.get(h, "")) for h in headers]
        self.sheets.values().append(spreadsheetId=self.sheet_id, range="'%s'!A1" % sheet,
                                    valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
                                    body={"values": [row]}).execute(num_retries=3)
        return len(rows) + 2

    def update_cell(self, sheet, row, header, value):
        headers, _ = self.get_rows(sheet)
        c = self._col(headers.index(header))
        self.sheets.values().update(spreadsheetId=self.sheet_id, range="'%s'!%s%d" % (sheet, c, row),
                                    valueInputOption="USER_ENTERED", body={"values": [[_testo(value)]]}).execute(num_retries=3)

    def update_cells(self, sheet, items):
        items = list(items)
        if not items:
            return
        headers, _ = self.get_rows(sheet)
        data = [{"range": "'%s'!%s%d" % (sheet, self._col(headers.index(h)), r), "values": [[_testo(v)]]} for r, h, v in items]
        for i in range(0, len(data), 400):
            self.sheets.values().batchUpdate(spreadsheetId=self.sheet_id,
                                             body={"valueInputOption": "USER_ENTERED", "data": data[i:i + 400]}).execute(num_retries=3)

    def upload_photo(self, name, data, mime):
        from googleapiclient.http import MediaInMemoryUpload
        f = self.drive.files().create(
            body={"name": name, "parents": [self.folder_id]},
            media_body=MediaInMemoryUpload(data, mimetype=mime), fields="id,webViewLink").execute(num_retries=3)
        return f.get("webViewLink") or ("https://drive.google.com/file/d/%s/view" % f["id"])


def _una_alla_volta(f):
    def w(self, *a, **k):
        with self._lock:
            return f(self, *a, **k)
    w.__name__, w.__doc__ = f.__name__, f.__doc__
    return w


for _n in ("get_rows", "get_many", "append_row", "update_cell", "update_cells", "upload_photo"):
    setattr(GoogleStore, _n, _una_alla_volta(getattr(GoogleStore, _n)))


def make_store() -> SheetsStore:
    if os.environ.get("MOCK") == "1":
        return MemoryStore()
    return GoogleStore(os.environ["SHEET_ID"], os.environ.get("DRIVE_FOLDER_ID", ""), os.environ["SERVICE_ACCOUNT_JSON"])
