"""Copia di sicurezza del foglio su Drive ed esportazione dell'inventario in CSV.
- La copia usa l'account di servizio gia configurato: files.copy del foglio dentro la cartella Drive dell'app (opzione drive_folder_id).
  Non scrive nel foglio, quindi e consentita anche in sola lettura. Si tengono al massimo le ultime 5 copie fatte dall'app
  (nome con prefisso «Copia Inventario »): le piu vecchie vanno nel cestino, mai altri file.
- La copia automatica (impostazioni copia_auto / copia_giorni) la fa un ciclo che controlla ogni ora.
- L'esportazione e un CSV con «;», UTF-8 con BOM (Excel lo apre bene), intestazioni italiane."""
import csv
import io
import json
import logging
import os
import tempfile
import threading
import time
from datetime import datetime
from typing import Callable, List, Optional

PREFISSO = "Copia Inventario "
MAX_COPIE = 5
INTESTAZIONI = ["Codice a barre", "Prodotto", "Marca", "Confezione", "Tipo", "Categoria", "Sottocategoria", "Quantità totale",
                "Casa", "Cantina", "Scorta minima", "Prossima scadenza", "Ultimo carico"]
log = logging.getLogger("inventario")


class CopiaErrore(Exception):
    """Errore da mostrare all'utente (testo in italiano, mai tecnico)."""


def _data_it(iso: str) -> str:
    try:
        return datetime.strptime(str(iso)[:10], "%Y-%m-%d").strftime("%d/%m/%Y") if iso else ""
    except ValueError:
        return ""


def _testo_sicuro(v) -> str:
    """Un testo che Excel leggerebbe come formula (= + - @) si neutralizza con un apice iniziale."""
    t = str(v if v is not None else "").replace("\r", " ").replace("\n", " ")
    return "'" + t if t[:1] in ("=", "+", "-", "@") else t


def csv_inventario(prodotti: List[dict]) -> bytes:
    """CSV (UTF-8 con BOM, separatore «;») dei prodotti con giacenze, come da inv().elenco_prodotti()."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    w.writerow(INTESTAZIONI)
    for p in prodotti:
        posti = {x.get("luogo"): x.get("qta", 0) for x in (p.get("posti") or [])}
        w.writerow([_testo_sicuro(p.get("barcode")), _testo_sicuro(p.get("nome")), _testo_sicuro(p.get("marca")), _testo_sicuro(p.get("conf")),
                    _testo_sicuro(p.get("tipo")), _testo_sicuro(p.get("categoria")), _testo_sicuro(p.get("sotto")), p.get("qta", 0) or 0,
                    posti.get("Casa", 0), posti.get("Cantina", 0), p.get("minima", 0) or 0, _data_it(p.get("scad", "")), _data_it(p.get("ultimo", ""))])
    return ("﻿" + buf.getvalue()).encode("utf-8")


def _cartella_dati() -> str:
    return os.environ.get("DATA_DIR") or ("/data" if os.path.isdir("/data") else tempfile.gettempdir())


class Copia:
    def __init__(self, get_store: Callable, get_impostazioni: Callable, percorso: str = "", orologio: Callable[[], datetime] = datetime.now):
        self.get_store, self.get_imp, self.ora = get_store, get_impostazioni, orologio
        self.percorso = percorso or os.path.join(_cartella_dati(), "copia_stato.json")
        self._lock = threading.RLock()
        self._in_corso = False

    # --- stato su file -------------------------------------------------
    def _carica(self) -> dict:
        try:
            with open(self.percorso, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    def _salva(self, d: dict) -> None:
        try:
            os.makedirs(os.path.dirname(self.percorso), exist_ok=True)
            tmp = self.percorso + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False)
            os.replace(tmp, self.percorso)
        except OSError:
            pass

    # --- Drive ----------------------------------------------------------
    def _drive(self):
        s = self.get_store()
        drive, cartella, foglio = getattr(s, "drive", None), getattr(s, "folder_id", ""), getattr(s, "sheet_id", "")
        if drive is None or not foglio:
            raise CopiaErrore("La copia su Drive funziona solo con il foglio Google collegato.")
        if not cartella:
            raise CopiaErrore("Manca la cartella Drive: inserisci drive_folder_id nelle opzioni dell'app e condividila con l'account di servizio come Editor.")
        return s, drive, cartella, foglio

    @staticmethod
    def _errore_drive(e: Exception) -> CopiaErrore:
        st = getattr(getattr(e, "resp", None), "status", None)
        if st in (403, 404):
            return CopiaErrore("La cartella Drive non è raggiungibile: controlla drive_folder_id e condividila con l'account di servizio come Editor.")
        if st == 429:
            return CopiaErrore("Google ha limitato le richieste: riprova tra qualche minuto.")
        return CopiaErrore("La copia non è riuscita (Google non ha risposto): riprova più tardi.")

    def _elenco_drive(self, store, drive, cartella: str) -> List[dict]:
        q = "'%s' in parents and name contains '%s' and trashed = false and mimeType = 'application/vnd.google-apps.spreadsheet'" % (cartella, PREFISSO.strip())
        with getattr(store, "_lock", threading.RLock()):
            r = drive.files().list(q=q, fields="files(id,name,createdTime,webViewLink)", orderBy="createdTime desc", pageSize=50,
                                   supportsAllDrives=True, includeItemsFromAllDrives=True).execute(num_retries=2)
        return [f for f in r.get("files", []) if str(f.get("name", "")).startswith(PREFISSO)]

    def copia_ora(self) -> dict:
        """Crea una copia del foglio; ritorna {nome, quando, link, tolte}. Solleva CopiaErrore con un testo chiaro."""
        with self._lock:
            if self._in_corso:
                raise CopiaErrore("Una copia è già in corso.")
            self._in_corso = True
        try:
            store, drive, cartella, foglio = self._drive()
            nome = PREFISSO + self.ora().strftime("%Y-%m-%d %H:%M")
            try:
                with getattr(store, "_lock", threading.RLock()):
                    f = drive.files().copy(fileId=foglio, body={"name": nome, "parents": [cartella]}, supportsAllDrives=True,
                                           fields="id,name,webViewLink").execute(num_retries=3)
            except CopiaErrore:
                raise
            except Exception as e:
                d = self._carica(); d["errore"] = self._errore_drive(e).args[0]; self._salva(d)
                raise self._errore_drive(e)
            tolte = 0
            try:   # al massimo le ultime MAX_COPIE copie dell'app; il resto nel cestino (mai file senza il nostro prefisso)
                vecchie = self._elenco_drive(store, drive, cartella)[MAX_COPIE:]
                for v in vecchie:
                    with getattr(store, "_lock", threading.RLock()):
                        drive.files().update(fileId=v["id"], body={"trashed": True}, supportsAllDrives=True).execute(num_retries=2)
                    tolte += 1
            except Exception:
                log.exception("pulizia delle vecchie copie non riuscita")
            quando = self.ora().isoformat(timespec="seconds")
            link = f.get("webViewLink") or ("https://docs.google.com/spreadsheets/d/%s/edit" % f.get("id", ""))
            d = self._carica(); d.pop("errore", None); d["ultima"] = quando
            d["recenti"] = ([{"nome": nome, "quando": quando, "link": link}] + d.get("recenti", []))[:MAX_COPIE]
            self._salva(d)
            return {"nome": nome, "quando": quando, "link": link, "tolte": tolte}
        finally:
            self._in_corso = False

    # --- stato per la schermata -----------------------------------------
    def possibile(self) -> str:
        """Vuoto se la copia si puo fare, altrimenti il motivo (in italiano)."""
        try:
            self._drive()
            return ""
        except CopiaErrore as e:
            return e.args[0]

    def stato(self) -> dict:
        d, imp = self._carica(), self.get_imp()
        giorni = int(imp.get("copia_giorni") or 7)
        prossima = ""
        if imp.get("copia_auto") and d.get("ultima"):
            try:
                from datetime import timedelta
                prossima = (datetime.fromisoformat(d["ultima"]) + timedelta(days=giorni)).isoformat(timespec="minutes")
            except ValueError:
                prossima = ""
        return {"possibile": self.possibile() == "", "motivo": self.possibile(), "in_corso": self._in_corso, "ultima": d.get("ultima", ""),
                "prossima": prossima, "errore": d.get("errore", ""), "copie": d.get("recenti", []),
                "auto": bool(imp.get("copia_auto")), "giorni": giorni}

    def dovuta(self) -> bool:
        imp = self.get_imp()
        if not imp.get("copia_auto"):
            return False
        ultima = self._carica().get("ultima")
        if not ultima:
            return True
        try:
            return (self.ora() - datetime.fromisoformat(ultima)).total_seconds() >= int(imp.get("copia_giorni") or 7) * 86400
        except ValueError:
            return True

    def ciclo(self, pausa: float = 3600.0) -> None:
        """Ogni ora controlla se serve la copia automatica (solo se Drive e configurato)."""
        time.sleep(300)
        while True:
            try:
                if self.dovuta() and self.possibile() == "":
                    self.copia_ora()
            except CopiaErrore:
                pass
            except Exception:
                log.exception("copia automatica")
            time.sleep(pausa)


def registra(app, ctx) -> None:
    from fastapi import Header, HTTPException
    from fastapi.responses import Response

    copia = Copia(lambda: ctx.inv().store, lambda: ctx.impostazioni().tutte())
    threading.Thread(target=copia.ciclo, daemon=True).start()

    @app.get("/api/copia")
    def copia_stato(x_code: str = Header(None)):
        ctx.check(x_code)
        return copia.stato()

    @app.post("/api/copia/ora")
    def copia_ora(x_code: str = Header(None)):
        ctx.check(x_code)     # niente writable(): la copia non scrive sul foglio
        try:
            return dict(copia.copia_ora(), ok=True)
        except CopiaErrore as e:
            raise HTTPException(400, e.args[0])

    @app.get("/api/esporta.csv")
    def esporta_csv(x_code: str = Header(None)):
        ctx.check(x_code)
        dati = csv_inventario(ctx.inv().elenco_prodotti())
        return Response(content=dati, media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="inventario_%s.csv"' % datetime.now().strftime("%Y-%m-%d"), "Cache-Control": "no-store"})
