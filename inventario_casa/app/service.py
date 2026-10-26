"""Logica dell'inventario (solo libreria standard, testabile senza rete)."""
import re
import time
from datetime import datetime
from typing import Dict, List, Optional

# TODO: verificare sul foglio reale i nomi esatti di colonne e valori (vedi README).
SH_MOV, SH_PROD, SH_AIP, SH_AIT, SH_AIC, SH_CODA = "movimenti", "prodotti", "ai_prodotti", "ai_tipi", "ai_categorie", "coda"
TIPI_MOV = ("Carico", "Scarico", "Move", "Cng")           # vocabolario del foglio
ALIAS_MOV = {"Sposta": "Move", "Rettifica": "Cng"}        # nomi alternativi accettati dall'app
LUOGHI = ("Casa", "Cantina")                              # TODO: leggerli dal foglio
ST_PENDING = {SH_AIP: "DA_APPROVARE", SH_AIT: "DA_APPROVARE", SH_AIC: "PROPOSTA"}
ST_OK = {SH_AIP: "APPROVATO", SH_AIT: "APPROVATO", SH_AIC: "APPROVATA"}   # TODO: stati finali letti da aiApplyApproved
ST_NO = "RIFIUTATO"
CACHE_TTL = 20


class ApiError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status, self.msg = status, msg


def nbc(x) -> str:
    """Barcode normalizzato: solo cifre, senza zeri iniziali."""
    s = re.sub(r"\D", "", str(x if x is not None else ""))
    return s.lstrip("0")


def _num(x) -> float:
    try:
        return float(str(x).replace(",", "."))
    except ValueError:
        return 0.0


def _minima(p: dict) -> float:
    """Scorta minima dal catalogo: cerca una colonna il cui nome contenga 'scorta' e 'min' (nome esatto da confermare sul foglio)."""
    for h, v in p.items():
        n = str(h).lower()
        if "scorta" in n and "min" in n:
            return _num(v)
    return 0


class Inventory:
    def __init__(self, store, ttl: int = CACHE_TTL, clock=time.time):
        self.store, self.ttl, self.clock = store, ttl, clock
        self._cache: Dict[str, tuple] = {}

    def _rows(self, sheet: str, fresh: bool = False):
        hit = self._cache.get(sheet)
        if hit and not fresh and self.clock() - hit[0] < self.ttl:
            return hit[1], hit[2]
        h, r = self.store.get_rows(sheet)
        self._cache[sheet] = (self.clock(), h, r)
        return h, r

    def _drop(self, *sheets):
        for s in sheets:
            self._cache.pop(s, None)

    def _dicts(self, sheet, fresh=False):
        h, rows = self._rows(sheet, fresh)
        return [dict(zip(h, list(r) + [""] * (len(h) - len(r)))) for r in rows]

    # --- prodotti -------------------------------------------------------
    def prodotto(self, barcode) -> Optional[dict]:
        k = nbc(barcode)
        if not k:
            return None
        for p in self._dicts(SH_PROD):
            if nbc(p.get("Barcode")) == k:
                return {"barcode": int(k), "prodotto": p.get("Prodotto", ""), "marca": p.get("Marca", ""),
                        "categoria": p.get("Categoria", ""), "sottocategoria": p.get("Sottocategoria", ""),
                        "tipo": p.get("Tipo", "")}
        return None

    # --- stock ----------------------------------------------------------
    def stock(self) -> List[dict]:
        """Giacenza per prodotto e luogo, calcolata dai movimenti, con tipo e scorta minima presi dal catalogo.
        TODO: leggere Stock_ByLoc (foglio a formule) se si vuole identica a AppSheet; semantica di Sposta/Rettifica da confermare."""
        tipi_ai: Dict[str, str] = {}
        for a in self._dicts(SH_AIP):  # il Tipo vive in ai_prodotti (prodotti non ha la colonna): vale l'ultimo non rifiutato
            k = nbc(a.get("Barcode"))
            t = str(a.get("Tipo", "") or "").strip()
            if k and t and str(a.get("Stato", "")).upper() != "RIFIUTATO":
                tipi_ai[k] = t
        scorta_tipo: Dict[str, float] = {}   # la scorta minima vive in ai_tipi (una per tipo)
        for t in self._dicts(SH_AIT):
            nome = str(t.get("Tipo", "") or "").strip().lower()
            if nome and str(t.get("Stato", "")).upper() != "RIFIUTATO":
                scorta_tipo[nome] = _num(t.get("Scorta_min", t.get("Scorta min", 0)))
        cat: Dict[str, dict] = {}
        for p in self._dicts(SH_PROD):
            k = nbc(p.get("Barcode"))
            if k:
                tp = str(p.get("Tipo", "") or "").strip() or tipi_ai.get(k, "")
                cat[k] = {"tipo": tp, "minima": scorta_tipo.get(tp.lower(), _minima(p)),
                          "nome": str(p.get("Prodotto", "") or "").strip(),
                          "categoria": str(p.get("Categoria", "") or "").strip(), "sotto": str(p.get("Sottocategoria", "") or "").strip(),
                          "marca": str(p.get("Marca", "") or "").strip(),
                          "conf": str(p.get("Confezione", "") or "").strip(), "img": str(p.get("Immagine", "") or "").strip()}
        acc: Dict[tuple, dict] = {}
        for m in self._dicts(SH_MOV):
            k = nbc(m.get("Barcode"))
            tipo, loc = str(m.get("Tipo", "")).strip(), str(m.get("Location", "")).strip()
            q = _num(m.get("Quantità", m.get("Quantita", 0)))
            if not k or not tipo or not loc:
                continue
            if tipo == "Carico":
                d = q
            elif tipo == "Scarico":
                d = -q
            else:
                continue
            c = cat.get(k, {})
            e = acc.setdefault((k, loc), {"barcode": int(k), "nome": c.get("nome") or m.get("Prodotto", ""),
                                          "marca": c.get("marca", ""), "conf": c.get("conf", ""), "img": c.get("img", ""),
                                          "categoria": c.get("categoria") or m.get("Categoria", ""),   # la categoria vive nel prodotto
                                          "sotto": c.get("sotto") or m.get("Sottocategoria", ""),
                                          "tipo": c.get("tipo", ""), "minima": c.get("minima", 0),
                                          "luogo": loc, "qta": 0})
            e["qta"] += d
        out = [e for e in acc.values() if e["qta"] != 0]
        for e in out:
            e["qta"] = int(e["qta"]) if float(e["qta"]).is_integer() else e["qta"]
        return sorted(out, key=lambda e: (e["categoria"], e["nome"], e["luogo"]))

    # --- movimenti ------------------------------------------------------
    def movimento(self, barcode, tipo: str, location: str, quantita, prodotto: str = "", foto: str = "") -> dict:
        k = nbc(barcode)
        if not k:
            raise ApiError(400, "Barcode non valido: servono solo cifre")
        tipo = ALIAS_MOV.get(tipo, tipo)
        if tipo not in TIPI_MOV:
            raise ApiError(400, "Tipo non valido")
        if location not in LUOGHI:
            raise ApiError(400, "Posizione non valida")
        q = _num(quantita)
        if q <= 0:
            raise ApiError(400, "La quantità deve essere maggiore di zero")
        p = self.prodotto(k)
        if p is None and not foto:
            raise ApiError(409, "Codice sconosciuto: serve una foto per creare la bozza")
        row = {"Barcode": int(k), "Tipo": tipo, "Location": location,
               "Quantità": int(q) if q.is_integer() else q,
               "Prodotto": (p["prodotto"] if p else prodotto), "Categoria": p["categoria"] if p else "",
               "Sottocategoria": p["sottocategoria"] if p else "", "Foto": foto,
               "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  # TODO: colonna data reale
        n = self.store.append_row(SH_MOV, row)
        self._drop(SH_MOV)
        return {"ok": True, "riga": n, "noto": p is not None}

    # --- approvazioni ---------------------------------------------------
    def _prima_dopo(self, a: dict):
        cur = str(a.get("Prodotto_Attuale", "") or "")
        sug = str(a.get("Nome_Suggerito", "") or "")
        pr = self.prodotto(a.get("Barcode")) or {}
        cat_old = " › ".join(x for x in (pr.get("categoria"), pr.get("sottocategoria")) if x)
        cat_new = " › ".join(x for x in (a.get("Categoria_Suggerita"), a.get("Sottocategoria_Suggerita")) if x)
        t_new = str(a.get("Tipo", "") or "") or pr.get("tipo", "")
        j = lambda xs: " · ".join(x for x in xs if x)
        return (j([cur or "(nome vuoto)", cat_old, ("tipo " + pr["tipo"]) if pr.get("tipo") else ""]),
                j([sug or cur or "(nome vuoto)", cat_new or cat_old, ("tipo " + t_new) if t_new else ""]))

    def approvazioni(self) -> List[dict]:
        out = []
        for i, a in enumerate(self._dicts(SH_AIP, True)):
            if str(a.get("Stato", "")) != ST_PENDING[SH_AIP]:
                continue
            prima, dopo = self._prima_dopo(a)
            c = a.get("Confidenza", "")
            pct = None if c in ("", None) else int(round(_num(c) * 100 if _num(c) <= 1 else _num(c)))
            out.append({"id": "P_%s" % a.get("Barcode"), "gruppo": "Prodotti da correggere",
                        "titolo": a.get("Nome_Suggerito") or a.get("Prodotto_Attuale") or str(a.get("Barcode")),
                        "prima": prima, "dopo": dopo, "sicurezza": pct, "motivo": a.get("Motivo", "")})
        for a in self._dicts(SH_AIT, True):
            if str(a.get("Stato", "")) == ST_PENDING[SH_AIT]:
                out.append({"id": "T_%s" % a.get("Tipo"), "gruppo": "Nuovi tipi", "titolo": "Nuovo tipo: %s" % a.get("Tipo"),
                            "prima": "", "dopo": "Tipo %s" % a.get("Tipo"), "sicurezza": None,
                            "motivo": "L'AI vuole creare questo tipo di prodotto."})
        for i, a in enumerate(self._dicts(SH_AIC, True)):
            if str(a.get("Stato", "")) == ST_PENDING[SH_AIC]:
                out.append({"id": "C_%d" % (i + 2), "gruppo": "Categorie proposte",
                            "titolo": "Categoria: %s → %s" % (a.get("Azione", ""), a.get("Nuovo_Nome") or a.get("Sottocategoria", "")),
                            "prima": str(a.get("Sottocategoria", "")), "dopo": str(a.get("Nuovo_Nome", "")),
                            "sicurezza": None, "motivo": a.get("Motivo", "")})
        return out

    def decidi(self, id_: str, azione: str) -> dict:
        if azione not in ("APPROVA", "SCARTA"):
            raise ApiError(400, "Azione non valida")
        kind, _, key = str(id_).partition("_")
        sheet = {"P": SH_AIP, "T": SH_AIT, "C": SH_AIC}.get(kind)
        if not sheet or not key:
            raise ApiError(400, "Id non valido")
        h, rows = self._rows(sheet, True)
        if "Stato" not in h:
            raise ApiError(500, "Colonna Stato mancante in %s" % sheet)
        idx = None
        for i, r in enumerate(rows):
            d = dict(zip(h, r))
            if kind == "P" and nbc(d.get("Barcode")) == nbc(key):
                idx = i
            elif kind == "T" and str(d.get("Tipo")) == key:
                idx = i
            elif kind == "C" and i + 2 == int(key if key.isdigit() else -1):
                idx = i
            if idx is not None:
                break
        if idx is None:
            raise ApiError(404, "Proposta non trovata")
        if str(dict(zip(h, rows[idx])).get("Stato", "")) != ST_PENDING[sheet]:
            raise ApiError(409, "Proposta già decisa")
        self.store.update_cell(sheet, idx + 2, "Stato", ST_OK[sheet] if azione == "APPROVA" else ST_NO)
        self._drop(sheet)
        return {"ok": True, "stato": ST_OK[sheet] if azione == "APPROVA" else ST_NO}

    # --- foto -----------------------------------------------------------
    def foto(self, barcode, data: bytes, mime: str) -> dict:
        k = nbc(barcode)
        if not k:
            raise ApiError(400, "Barcode non valido")
        if mime not in ("image/jpeg", "image/png", "image/webp"):
            raise ApiError(400, "Formato immagine non supportato")
        if not data or len(data) > 8 * 1024 * 1024:
            raise ApiError(400, "Immagine vuota o oltre 8 MB")
        name = "%s_%d.%s" % (k, int(self.clock()), mime.split("/")[1])
        return {"ok": True, "url": self.store.upload_photo(name, data, mime)}
