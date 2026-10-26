"""SheetsStore: astrazione sul foglio. MemoryStore per test (MOCK=1), GoogleStore per produzione."""
import json
import os
from typing import Dict, List, Tuple


class SheetsStore:
    def get_rows(self, sheet: str) -> Tuple[List[str], List[List]]:
        raise NotImplementedError

    def append_row(self, sheet: str, values: Dict[str, object]) -> int:
        """Aggiunge una riga mappando i valori sulle intestazioni. Ritorna il numero di riga (1-based)."""
        raise NotImplementedError

    def update_cell(self, sheet: str, row: int, header: str, value) -> None:
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

    def upload_photo(self, name, data, mime):
        self.photos[name] = data
        return "https://drive.example/mock/" + name


class GoogleStore(SheetsStore):
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

    def __init__(self, sheet_id: str, folder_id: str, service_account_json: str):
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        info = json.loads(service_account_json)
        creds = service_account.Credentials.from_service_account_info(info, scopes=self.SCOPES)
        self.sheet_id, self.folder_id = sheet_id, folder_id
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
                                       valueRenderOption="UNFORMATTED_VALUE").execute()
        vals = res.get("values", [])
        if not vals:
            return [], []
        return [str(h) for h in vals[0]], vals[1:]

    def append_row(self, sheet, values):
        headers, rows = self.get_rows(sheet)
        row = [values.get(h, "") for h in headers]
        self.sheets.values().append(spreadsheetId=self.sheet_id, range="'%s'!A1" % sheet,
                                    valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
                                    body={"values": [row]}).execute()
        return len(rows) + 2

    def update_cell(self, sheet, row, header, value):
        headers, _ = self.get_rows(sheet)
        c = self._col(headers.index(header))
        self.sheets.values().update(spreadsheetId=self.sheet_id, range="'%s'!%s%d" % (sheet, c, row),
                                    valueInputOption="USER_ENTERED", body={"values": [[value]]}).execute()

    def upload_photo(self, name, data, mime):
        from googleapiclient.http import MediaInMemoryUpload
        f = self.drive.files().create(
            body={"name": name, "parents": [self.folder_id]},
            media_body=MediaInMemoryUpload(data, mimetype=mime), fields="id,webViewLink").execute()
        return f.get("webViewLink") or ("https://drive.google.com/file/d/%s/view" % f["id"])


def make_store() -> SheetsStore:
    if os.environ.get("MOCK") == "1":
        return MemoryStore()
    return GoogleStore(os.environ["SHEET_ID"], os.environ.get("DRIVE_FOLDER_ID", ""), os.environ["SERVICE_ACCOUNT_JSON"])
