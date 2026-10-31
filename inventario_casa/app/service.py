"""Logica dell'inventario (solo libreria standard, testabile senza rete)."""
import re
import threading
import time
import unicodedata
import uuid
from datetime import datetime
from typing import Dict, List, Optional

# TODO: verificare sul foglio reale i nomi esatti di colonne e valori (vedi README).
SH_MOV, SH_PROD, SH_AIP, SH_AIT, SH_AIC, SH_CODA = "movimenti", "prodotti", "ai_prodotti", "ai_tipi", "ai_categorie", "coda"
SH_CAT = "categorie"
TIPI_MOV = ("Carico", "Scarico", "Move", "Cng")           # vocabolario del foglio
ALIAS_MOV = {"Sposta": "Move", "Rettifica": "Cng", "Cambia categoria": "Cng"}        # nomi alternativi accettati dall'app
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


def bco(k):
    """Barcode per l'uscita e per il foglio: numero fino a 15 cifre, testo oltre (precisione di Fogli e JSON)."""
    k = nbc(k)
    return int(k) if len(k) <= 15 else k


def data_it(x) -> str:
    """Data in formato gg/mm/aaaa: accetta il numero seriale di Google Sheets, il testo ISO o una data gia italiana."""
    from datetime import timedelta
    if x is None or str(x).strip() == "":
        return ""
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        if 20000 < x < 80000:   # numero seriale (giorni dal 30/12/1899)
            return (datetime(1899, 12, 30) + timedelta(days=int(x))).strftime("%d/%m/%Y")
        return str(x)
    t = str(x).strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        return "%s/%s/%s" % (m.group(3), m.group(2), m.group(1))
    m = re.match(r"^(\d{1,2})[/.](\d{1,2})[/.](\d{4})", t)
    if m:
        return "%02d/%02d/%s" % (int(m.group(1)), int(m.group(2)), m.group(3))
    if re.fullmatch(r"\d{5}(\.\d+)?", t):
        return data_it(float(t))
    return t


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
        self._memo = {}
        self._lock = threading.RLock()
        self.store, self.ttl, self.clock = store, ttl, clock
        self._cache: Dict[str, tuple] = {}

    CORE = (SH_AIP, SH_AIT, SH_PROD, SH_MOV)   # i fogli che servono a Stock e Prodotti: si leggono insieme

    def _rows(self, sheet: str, fresh: bool = False):
        hit = self._cache.get(sheet)
        if hit and not fresh and self.clock() - hit[0] < self.ttl:
            return hit[1], hit[2]
        if sheet in self.CORE and not fresh:
            self.refresh()
            return self._cache[sheet][1], self._cache[sheet][2]
        h, r = self.store.get_rows(sheet)
        self._put(sheet, h, r)
        return h, r

    def _put(self, sheet, h, r):
        old = self._cache.get(sheet)
        self._cache[sheet] = (self.clock(), h, r)
        if not old or old[1] != h or old[2] != r:
            self._memo.clear()   # dati cambiati: i calcoli derivati vanno rifatti

    def refresh(self):
        """Rilegge insieme i fogli principali (una sola chiamata a Google). Usata anche dal ciclo in background."""
        with self._lock:
            for n, (h, r) in self.store.get_many(self.CORE).items():
                self._put(n, h, r)
            self.stock()
            self.elenco_prodotti()

    def _drop(self, *sheets):
        self._memo.clear()
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
                return {"barcode": bco(k), "prodotto": p.get("Prodotto", ""), "marca": p.get("Marca", ""),
                        "categoria": p.get("Categoria", ""), "sottocategoria": p.get("Sottocategoria", ""),
                        "tipo": p.get("Tipo", "")}
        return None

    def categorie(self) -> List[dict]:
        """Categorie con le loro sottocategorie, dal foglio `categorie`, nell'ordine del foglio."""
        out: Dict[str, List[str]] = {}
        for r in self._dicts(SH_CAT):
            c, sc = str(r.get("Categoria", "") or "").strip(), str(r.get("Sottocategoria", "") or "").strip()
            if c:
                out.setdefault(c, [])
                if sc and sc not in out[c]:
                    out[c].append(sc)
        return [{"categoria": c, "sottocategorie": v} for c, v in out.items()]

    def tipi(self) -> List[str]:
        """Tipi esistenti (non rifiutati), per i suggerimenti quando si crea un prodotto."""
        out = {}
        for t in self._dicts(SH_AIT):
            nome = str(t.get("Tipo", "") or "").strip()
            if nome and str(t.get("Stato", "")).upper() != ST_NO:
                out.setdefault(nome.lower(), nome)
        return sorted(out.values(), key=str.casefold)

    def crea_prodotto(self, barcode, nome: str, marca: str = "", confezione: str = "", immagine: str = "",
                      categoria: str = "", sottocategoria: str = "", tipo: str = "", dettagli: str = "",
                      composizione: str = "", nutrizione: str = "", punteggi: str = "", fonte: str = "App",
                      location: str = "", quantita=1) -> dict:
        """Nuovo prodotto del catalogo (una riga in prodotti). Con `location` registra subito anche il Carico, nella stessa chiamata."""
        k = nbc(barcode)
        nome, categoria, sottocategoria, tipo = (nome or "").strip(), (categoria or "").strip(), (sottocategoria or "").strip(), (tipo or "").strip()
        if not k:
            raise ApiError(400, "Barcode non valido: servono solo cifre")
        if not nome:
            raise ApiError(400, "Il nome è obbligatorio")
        if self.prodotto(k) is not None:
            raise ApiError(409, "Codice già presente nel catalogo")
        if location and location not in LUOGHI:
            raise ApiError(400, "Posizione non valida")
        ammesse = {c["categoria"]: c["sottocategorie"] for c in self.categorie()}
        if ammesse:
            if categoria not in ammesse:
                raise ApiError(400, "Categoria non prevista")
            if sottocategoria not in ammesse[categoria]:
                raise ApiError(400, "Sottocategoria non prevista per la categoria %s" % categoria)
        valori = {"Barcode": bco(k), "Prodotto": nome, "Marca": (marca or "").strip(), "Categoria": categoria,
                  "API Status": "✅ App (%s)" % (fonte or "App"), "Confezione": (confezione or "").strip(),
                  "Dettagli prodotto": dettagli, "Punteggi": punteggi, "Composizione": composizione,
                  "Nutrizione (100g)": nutrizione, "Immagine": (immagine or "").strip(),
                  "Aggiornato il": datetime.now().strftime("%d/%m/%Y"), "Sottocategoria": sottocategoria, "Tipo": tipo}
        riga = self.store.append_row(SH_PROD, valori)
        if tipo and tipo.lower() not in {t.lower() for t in self.tipi()}:
            # tipo nuovo: sempre in coda Approvazioni, dove si definisce la scorta minima (0 finche non la imposti) e si approva o corregge
            self.store.append_row(SH_AIT, {"Tipo": tipo, "Scorta_min": 0, "Stato": ST_PENDING[SH_AIT], "Note": "creato dall'app"})
            self._drop(SH_AIT)
        self._drop(SH_PROD)
        out = {"ok": True, "riga": riga, "barcode": bco(k), "movimento": False}
        if location:   # il carico usa i dati appena inseriti, senza rileggere il foglio
            self.movimento(k, "Carico", location, quantita or 1,
                           noto={"prodotto": nome, "categoria": categoria, "sottocategoria": sottocategoria})
            out["movimento"] = True
        return out

    def modifica_prodotto(self, barcode, sottocategoria: str) -> dict:
        """Cambio di sottocategoria = modifica del prodotto: aggiorna il catalogo e le righe di movimento di quel
        codice, senza toccare le quantita."""
        k = nbc(barcode)
        sc = (sottocategoria or "").strip()
        if not k or not sc:
            raise ApiError(400, "Codice o sottocategoria mancante")
        h, rows = self._rows(SH_PROD, True)
        if "Barcode" not in h or "Sottocategoria" not in h:
            raise ApiError(500, "Il foglio prodotti non ha le colonne attese")
        ib, isc, ic = h.index("Barcode"), h.index("Sottocategoria"), (h.index("Categoria") if "Categoria" in h else None)
        riga = next((i for i, r in enumerate(rows) if len(r) > ib and nbc(r[ib]) == k), None)
        if riga is None:
            raise ApiError(404, "Codice sconosciuto")
        cat = str(rows[riga][ic]).strip() if ic is not None and len(rows[riga]) > ic else ""
        ammesse = {c["categoria"]: c["sottocategorie"] for c in self.categorie()}
        if ammesse and sc not in ammesse.get(cat, []):
            raise ApiError(400, "Sottocategoria non prevista per la categoria %s" % (cat or "(vuota)"))
        self.store.update_cells(SH_PROD, [(riga + 2, "Sottocategoria", sc)])
        n = 0
        hm, rm = self._rows(SH_MOV, True)
        if "Barcode" in hm and "Sottocategoria" in hm:
            jb, js = hm.index("Barcode"), hm.index("Sottocategoria")
            ups = [(i + 2, "Sottocategoria", sc) for i, r in enumerate(rm)
                   if len(r) > jb and nbc(r[jb]) == k and (len(r) <= js or str(r[js]).strip() != sc)]
            self.store.update_cells(SH_MOV, ups)
            n = len(ups)
        self._drop(SH_PROD, SH_MOV)
        return {"ok": True, "movimenti_aggiornati": n}

    def elenco_prodotti(self) -> List[dict]:
        """Tutti i prodotti del catalogo in ordine alfabetico, anche quelli con giacenza zero (calcolato una volta per ciclo)."""
        self.stock()   # rilegge i fogli scaduti e svuota la memoria se i dati sono cambiati
        if "elenco" not in self._memo:
            self._memo["elenco"] = self._elenco()
        return self._memo["elenco"]

    def _elenco(self) -> List[dict]:
        tot: Dict[str, float] = {}
        minima: Dict[str, float] = {}
        posti: Dict[str, Dict[str, float]] = {}
        for e in self.stock():
            k = str(e["barcode"])
            tot[k] = tot.get(k, 0) + e["qta"]
            minima[k] = e["minima"]
            posti.setdefault(k, {})[e["luogo"]] = posti.get(k, {}).get(e["luogo"], 0) + e["qta"]
        scorte = self._scorte_tipo()
        out = []
        for p in self._dicts(SH_PROD):
            k = nbc(p.get("Barcode"))
            if not k:
                continue
            g = lambda n: str(p.get(n, "") or "").strip()
            out.append({"barcode": bco(k), "nome": g("Prodotto") or "(senza nome)", "marca": g("Marca"), "conf": g("Confezione"),
                        "tipo": g("Tipo"), "categoria": g("Categoria"), "sotto": g("Sottocategoria"), "img": g("Immagine"),
                        "qta": tot.get(k, 0),
                        "minima": minima.get(k, scorte.get(g("Tipo").lower(), 0)),   # anche per i prodotti senza giacenza
                        "posti": [{"luogo": l, "qta": q} for l, q in sorted(posti.get(k, {}).items()) if q]})
        return sorted(out, key=lambda e: (e["nome"].casefold(), e["marca"].casefold()))

    def scheda(self, barcode) -> Optional[dict]:
        """Scheda prodotto: dati del catalogo + giacenze per posizione e categoria."""
        k = nbc(barcode)
        if not k:
            return None
        for p in self._dicts(SH_PROD):
            if nbc(p.get("Barcode")) != k:
                continue
            g = lambda *names: next((str(p[n]).strip() for n in names if n in p and str(p[n]).strip()), "")
            tipo = g("Tipo")
            giac = [{"luogo": e["luogo"], "categoria": e["categoria"], "qta": e["qta"], "minima": e["minima"]}
                    for e in self.stock() if str(e["barcode"]) == k]
            minima = self._scorte_tipo().get(tipo.lower(), _minima(p)) if tipo else (giac[0]["minima"] if giac else _minima(p))
            return {"barcode": bco(k), "nome": g("Prodotto"), "marca": g("Marca"), "confezione": g("Confezione"),
                    "categoria": g("Categoria"), "sottocategoria": g("Sottocategoria"), "tipo": tipo,
                    "immagine": g("Immagine"), "dettagli": g("Dettagli prodotto"), "punteggi": g("Punteggi"),
                    "composizione": g("Composizione"), "free_from": g("Free-from"), "nutrizione": g("Nutrizione (100g)"),
                    "smaltimento": g("Smaltimento/riciclo"), "aggiornato": data_it(g("Aggiornato il")),
                    "scorta_minima": minima, "giacenze": giac, "totale": sum(x["qta"] for x in giac)}
        return None

    # --- stock ----------------------------------------------------------
    def stock(self) -> List[dict]:
        """Calcolata una volta per ciclo di cache (elenco, scheda e giacenze la riusano)."""
        for n in (SH_AIP, SH_AIT, SH_PROD, SH_MOV):
            self._rows(n)   # rilegge i fogli scaduti e, se cambiano, svuota la memoria dei calcoli
        if "stock" not in self._memo:
            self._memo["stock"] = self._stock()
        return self._memo["stock"]

    def _scorte_tipo(self) -> Dict[str, float]:
        """Scorta minima per tipo (minuscolo), da ai_tipi: una per tipo, esclusi i rifiutati."""
        scorta_tipo: Dict[str, float] = {}
        for t in self._dicts(SH_AIT):
            nome = str(t.get("Tipo", "") or "").strip().lower()
            if nome and str(t.get("Stato", "")).upper() != "RIFIUTATO":
                scorta_tipo[nome] = _num(t.get("Scorta_min", t.get("Scorta min", 0)))
        return scorta_tipo

    def _stock(self, zeri: bool = False) -> List[dict]:
        """Giacenza per prodotto e luogo, calcolata dai movimenti, con tipo e scorta minima presi dal catalogo.
        TODO: leggere Stock_ByLoc (foglio a formule) se si vuole identica a AppSheet; semantica di Sposta/Rettifica da confermare."""
        tipi_ai: Dict[str, str] = {}
        for a in self._dicts(SH_AIP):  # il Tipo vive in ai_prodotti (prodotti non ha la colonna): vale l'ultimo non rifiutato
            k = nbc(a.get("Barcode"))
            t = str(a.get("Tipo", "") or "").strip()
            if k and t and str(a.get("Stato", "")).upper() != "RIFIUTATO":
                tipi_ai[k] = t
        scorta_tipo = self._scorte_tipo()
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
            catm = str(m.get("Categoria", "") or "").strip() or c.get("categoria", "")   # riga senza categoria: vale quella del prodotto
            e = acc.setdefault((k, loc, catm), {"barcode": bco(k), "nome": c.get("nome") or m.get("Prodotto", ""),
                                          "marca": c.get("marca", ""), "conf": c.get("conf", ""), "img": c.get("img", ""),
                                          "categoria": catm,   # la categoria appartiene alla riga di stock (stesso prodotto, categorie diverse)
                                          "sotto": c.get("sotto") or m.get("Sottocategoria", ""),   # la sottocategoria e del prodotto
                                          "tipo": c.get("tipo", ""), "minima": c.get("minima", 0),
                                          "luogo": loc, "qta": 0})
            e["qta"] += d
        out = [e for e in acc.values() if zeri or e["qta"] != 0]
        for e in out:
            e["qta"] = int(e["qta"]) if float(e["qta"]).is_integer() else e["qta"]
        return sorted(out, key=lambda e: (e["categoria"], e["nome"], e["luogo"]))

    # --- movimenti ------------------------------------------------------
    def _giacenza(self, k: str, loc: str, cat: str) -> float:
        tot = 0.0
        pc = (self.prodotto(k) or {}).get("categoria", "")
        for m in self._dicts(SH_MOV, fresh=True):
            if nbc(m.get("Barcode")) != k or str(m.get("Location", "")).strip() != loc:
                continue
            if (str(m.get("Categoria", "") or "").strip() or pc) != cat:
                continue
            q = _num(m.get("Quantità", m.get("Quantita", 0)))
            t = str(m.get("Tipo", "")).strip()
            tot += q if t == "Carico" else -q if t == "Scarico" else 0
        return tot

    def movimento(self, barcode, tipo: str, location: str, quantita, prodotto: str = "", foto: str = "",
                  destinazione: str = "", categoria: str = "", categoria_new: str = "", noto: Optional[dict] = None) -> dict:
        """Carico/Scarico = una riga. Move (cambio posizione) e Cng (cambio categoria) = coppia di righe nette:
        Scarico alla situazione vecchia + Carico alla nuova, come fanno i bot di AppSheet (la riga Move/Cng non resta nel foglio)."""
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
        qv = int(q) if float(q).is_integer() else q
        p = noto or self.prodotto(k)
        if p is None and not prodotto:
            prodotto = (self.__dict__.get("_analisi", {}).get(k) or {}).get("nome", "")
        if p is None and not foto:
            raise ApiError(409, "Codice sconosciuto: serve una foto per creare la bozza")
        cat0 = (categoria or (p["categoria"] if p else "")).strip()
        base = {"Barcode": bco(k), "Quantità": qv, "Prodotto": (p["prodotto"] if p else prodotto),
                "Sottocategoria": p["sottocategoria"] if p else "", "Foto": foto,
                "Data": datetime.now().strftime("%d/%m/%Y"), "Chi": "App"}   # come nel foglio: gg/mm/aaaa
        righe = []
        if tipo in ("Carico", "Scarico"):
            righe.append(dict(base, Tipo=tipo, Location=location, Categoria=cat0))
        elif tipo == "Move":
            if destinazione not in LUOGHI or destinazione == location:
                raise ApiError(400, "Destinazione non valida")
            if self._giacenza(k, location, cat0) < q:
                raise ApiError(409, "Giacenza insufficiente nella posizione di partenza")
            righe.append(dict(base, Tipo="Scarico", Location=location, Categoria=cat0, Destinazione=destinazione))
            righe.append(dict(base, Tipo="Carico", Location=destinazione, Categoria=cat0, Destinazione=location))
        else:  # Cng
            if not categoria_new or categoria_new == cat0:
                raise ApiError(400, "Categoria nuova non valida")
            if self._giacenza(k, location, cat0) < q:
                raise ApiError(409, "Giacenza insufficiente nella categoria di partenza")
            righe.append(dict(base, Tipo="Scarico", Location=location, Categoria=cat0, Categoria_NEW=categoria_new))
            righe.append(dict(base, Tipo="Carico", Location=location, Categoria=categoria_new))
        n = 0
        for r in righe:
            r["ID_Movimento"] = uuid.uuid4().hex[:8]   # AppSheet lo genera da solo solo per le righe inserite da lui
            n = self.store.append_row(SH_MOV, r)
        self._drop(SH_MOV)
        if p is None:
            self._bozza_da_foto(k, tipo, location, qv)
        return {"ok": True, "riga": n, "righe": len(righe), "noto": p is not None}

    # --- fogli facoltativi ----------------------------------------------
    def _opz(self, sheet: str, fresh: bool = False):
        """Righe di un foglio che puo non esistere (bozze, log_ai): se manca, elenco vuoto."""
        try:
            return self._dicts(sheet, fresh)
        except Exception:
            return []

    def _scrivi(self, sheet: str, riga: int, campi: dict, headers=None):
        """Scrive solo le colonne che esistono nel foglio."""
        h = headers if headers is not None else self._rows(sheet, True)[0]
        items = [(riga, k, v) for k, v in campi.items() if k in h]
        if items:
            self.store.update_cells(sheet, items)

    def _log_ai(self, barcode, campo, prima, dopo, fonte="APPROVATO", conf="", modo="MANUALE"):
        try:
            self.store.append_row("log_ai", {"Quando": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "Barcode": bco(barcode),
                                             "Campo": campo, "Prima": prima, "Dopo": dopo, "Fonte": fonte, "Confidenza": conf,
                                             "Modo": modo, "Annullato": ""})
        except Exception:
            pass   # il registro e un di piu: se il foglio manca non blocca la decisione

    def _coppia_valida(self, categoria: str, sottocategoria: str) -> bool:
        ammesse = {c["categoria"]: c["sottocategorie"] for c in self.categorie()}
        return not ammesse or sottocategoria in ammesse.get(categoria, [])

    # --- spesa ----------------------------------------------------------
    SPESA_CONFRONTO = "LE"   # come nel motore: in spesa se giacenza <= scorta minima del tipo ("LT" = solo se sotto)

    def spesa(self) -> dict:
        """Cosa comprare: giacenza totale per TIPO contro la scorta minima del tipo (ai_tipi). Stessa logica di aiBuildShoppingList."""
        scorta: Dict[str, float] = {}
        for t in self._dicts(SH_AIT):
            nome = str(t.get("Tipo", "") or "").strip().lower()
            if nome and str(t.get("Stato", "")).upper() != ST_NO:
                scorta[nome] = _num(t.get("Scorta_min", t.get("Scorta min", 0)))
        ultimo: Dict[str, int] = {}   # ultimo carico per codice (riga di movimento piu alta)
        for i, m in enumerate(self._dicts(SH_MOV)):
            if str(m.get("Tipo", "")).strip() == "Carico":
                ultimo[nbc(m.get("Barcode"))] = i
        gruppi: Dict[str, dict] = {}
        for e in self._stock(True):
            tipo = str(e.get("tipo", "") or "").strip()
            if not tipo or tipo.lower() not in scorta:
                continue
            g = gruppi.setdefault(tipo.lower(), {"tipo": tipo, "tot": 0.0, "per": {}, "bcs": {}, "cat": e["categoria"], "sotto": e["sotto"], "img": ""})
            g["tot"] += e["qta"]
            g["per"][e["luogo"]] = g["per"].get(e["luogo"], 0) + e["qta"]
            b = g["bcs"].setdefault(str(e["barcode"]), {"nome": e["nome"], "img": e.get("img", ""), "q": 0})
            b["q"] += e["qta"]
        voci = []
        for k, g in gruppi.items():
            minima = scorta[k]
            if minima <= 0:
                continue
            tot = g["tot"]
            if not (tot <= minima if self.SPESA_CONFRONTO == "LE" else tot < minima):
                continue
            best = max(g["bcs"], key=lambda b: ultimo.get(nbc(b), -1))
            f = lambda x: int(x) if float(x).is_integer() else x
            voci.append({"tipo": g["tipo"], "categoria": g["cat"], "sottocategoria": g["sotto"], "giacenza": f(tot), "minima": f(minima),
                         "stato": "FINITO" if tot <= 0 else "STA_FINENDO",
                         "dettaglio": " · ".join("%s %s" % (l, f(q)) for l, q in sorted(g["per"].items())) + " (%d codici)" % len(g["bcs"]),
                         "barcode": int(best), "prodotto": g["bcs"][best]["nome"], "immagine": g["bcs"][best]["img"]})
        voci.sort(key=lambda v: (v["stato"] != "FINITO", str(v["categoria"]), str(v["sottocategoria"]), v["tipo"].lower()))
        return {"voci": voci, "finiti": sum(1 for v in voci if v["stato"] == "FINITO"), "in_esaurimento": sum(1 for v in voci if v["stato"] != "FINITO")}

    # --- da inserire (foglio bozze) -------------------------------------
    BOZZE_APERTE = ("", "NUOVA", "IN_ELABORAZIONE", "PRONTA", "NON_TROVATO", "ERRORE")

    def bozze(self) -> List[dict]:
        out = []
        for i, b in enumerate(self._opz("bozze", True)):
            if not nbc(b.get("Barcode")) or str(b.get("Stato", "") or "").strip().upper() not in self.BOZZE_APERTE:
                continue
            g = lambda k: str(b.get(k, "") or "").strip()
            out.append({"id": g("ID") or "R%d" % (i + 2), "barcode": nbc(b.get("Barcode")), "foto": g("Foto"), "nome": g("Prodotto"),
                        "marca": g("Marca"), "confezione": g("Confezione"), "categoria": g("Categoria"), "sottocategoria": g("Sottocategoria"),
                        "tipo": g("Tipo"), "immagine": g("Immagine"), "stato": g("Stato") or "NUOVA", "fonte": g("Fonte"), "nota": g("Nota"),
                        "location": g("Location") or "Casa", "movimento": g("Movimento") or "Carico",
                        "quantita": _num(b.get("Quantità", b.get("Quantita", 1))) or 1})
        return out

    def _trova_bozza(self, id_: str):
        h, rows = self._rows("bozze", True)
        for i, r in enumerate(rows):
            d = dict(zip(h, list(r) + [""] * (len(h) - len(r))))
            if (str(d.get("ID", "") or "") == str(id_) or "R%d" % (i + 2) == str(id_)) and nbc(d.get("Barcode")):
                if str(d.get("Stato", "") or "").strip().upper() not in self.BOZZE_APERTE:
                    raise ApiError(409, "Bozza già chiusa")
                return h, i + 2, d
        raise ApiError(404, "Bozza non trovata")

    def bozza_salva(self, id_: str, campi: dict) -> dict:
        """Salva le correzioni a mano sulla bozza (resta in lista)."""
        h, riga, _ = self._trova_bozza(id_)
        ammessi = {"nome": "Prodotto", "marca": "Marca", "confezione": "Confezione", "categoria": "Categoria",
                   "sottocategoria": "Sottocategoria", "tipo": "Tipo", "immagine": "Immagine", "nota": "Nota"}
        val = {ammessi[k]: str(v or "").strip() for k, v in (campi or {}).items() if k in ammessi}
        val["Aggiornato"] = datetime.now().strftime("%d/%m/%Y")
        self._scrivi("bozze", riga, val, h)
        self._drop("bozze")
        return {"ok": True}

    def bozza_scarta(self, id_: str) -> dict:
        h, riga, _ = self._trova_bozza(id_)
        self._scrivi("bozze", riga, {"Stato": "SCARTATA", "Aggiornato": datetime.now().strftime("%d/%m/%Y")}, h)
        self._drop("bozze")
        return {"ok": True}

    def bozza_conferma(self, id_: str, campi: dict) -> dict:
        """Aggiungi all'inventario: crea il prodotto, registra il movimento in sospeso (se non c'e gia) e chiude la bozza (INSERITA)."""
        campi = campi or {}
        h, riga, d = self._trova_bozza(id_)
        pick = lambda k, col: str(campi[k] if k in campi else d.get(col, "") or "").strip()
        nome, marca, conf = pick("nome", "Prodotto"), pick("marca", "Marca"), pick("confezione", "Confezione")
        cat, sotto, tipo, img = pick("categoria", "Categoria"), pick("sottocategoria", "Sottocategoria"), pick("tipo", "Tipo"), pick("immagine", "Immagine")
        k = nbc(d.get("Barcode"))
        if not nome:
            raise ApiError(400, "Il nome è obbligatorio")
        if not cat or not sotto:
            raise ApiError(400, "Scegli categoria e sottocategoria")
        luogo = str(d.get("Location", "") or "").strip() or "Casa"
        if luogo not in LUOGHI:
            raise ApiError(400, "Posizione non valida")
        mov = str(d.get("Movimento", "") or "").strip() or "Carico"
        if mov not in ("Carico", "Scarico"):
            mov = "Carico"
        q = _num(d.get("Quantità", d.get("Quantita", 1))) or 1
        if self.prodotto(k) is None:
            self.crea_prodotto(k, nome, marca, conf, img, cat, sotto, tipo, fonte="Da inserire")
        movs = self._dicts(SH_MOV, True)
        esistenti = [i for i, m in enumerate(movs) if nbc(m.get("Barcode")) == k]
        if not esistenti:   # nessun movimento in sospeso: lo crea la bozza (come addMovFromDraft_)
            self.movimento(k, mov, luogo, q, noto={"prodotto": nome, "categoria": cat, "sottocategoria": sotto})
        else:               # movimento in sospeso: si completa senza toccare quantita e posizione
            hm = self._rows(SH_MOV, True)[0]
            ups = []
            for i in esistenti:
                m = movs[i]
                for col, v in (("Prodotto", nome), ("Categoria", cat), ("Sottocategoria", sotto)):
                    if col in hm and not str(m.get(col, "") or "").strip():
                        ups.append((i + 2, col, v))
            if ups:
                self.store.update_cells(SH_MOV, ups)
        self._scrivi("bozze", riga, {"Prodotto": nome, "Marca": marca, "Confezione": conf, "Categoria": cat, "Sottocategoria": sotto,
                                     "Tipo": tipo, "Stato": "INSERITA", "Aggiornato": datetime.now().strftime("%d/%m/%Y")}, h)
        self._drop("bozze", SH_PROD, SH_MOV)
        return {"ok": True, "barcode": bco(k), "movimento": not esistenti}

    def imposta_scorta(self, tipo: str, scorta) -> dict:
        """Scorta minima di un TIPO (foglio ai_tipi). Se il tipo non c'e lo crea gia APPROVATO; se era in attesa o rifiutato lo approva."""
        tipo = (tipo or "").strip()
        if not tipo:
            raise ApiError(400, "Manca il tipo")
        try:
            v = float(str(scorta).replace(",", "."))
        except ValueError:
            raise ApiError(400, "La scorta minima deve essere un numero")
        if v < 0 or v > 999:
            raise ApiError(400, "La scorta minima deve essere tra 0 e 999")
        v = int(v) if v.is_integer() else v
        h, rows = self._rows(SH_AIT, True)
        col = next((c for c in ("Scorta_min", "Scorta min") if c in h), "Scorta_min")
        i = next((n for n, r in enumerate(rows) if str(dict(zip(h, r)).get("Tipo", "")).strip().lower() == tipo.lower()), None)
        if i is None:
            self.store.append_row(SH_AIT, {"Tipo": tipo, col: v, "Stato": ST_OK[SH_AIT], "Note": "impostata dall'app"})
        else:
            ups = [(i + 2, col, v)]
            if "Stato" in h and str(dict(zip(h, rows[i])).get("Stato", "")).strip().upper() != ST_OK[SH_AIT]:
                ups.append((i + 2, "Stato", ST_OK[SH_AIT]))
            self.store.update_cells(SH_AIT, ups)
        self._drop(SH_AIT)
        return {"ok": True, "tipo": tipo, "scorta_minima": v}

    # --- approvazioni ---------------------------------------------------
    def approvazioni(self) -> List[dict]:
        """Coda di approvazione: proposte AI sui prodotti, tipi nuovi, categorie proposte. Stesse regole di aiRebuildCoda."""
        out = []
        j = lambda xs: " · ".join(x for x in xs if x)
        for a in self._dicts(SH_AIP, True):
            if str(a.get("Stato", "")) != ST_PENDING[SH_AIP]:
                continue
            pr = self.prodotto(a.get("Barcode")) or {}
            cur, sug = str(a.get("Prodotto_Attuale", "") or ""), str(a.get("Nome_Suggerito", "") or "")
            cat_old = " › ".join(x for x in (pr.get("categoria"), pr.get("sottocategoria")) if x)
            cat_new = " › ".join(x for x in (a.get("Categoria_Suggerita"), a.get("Sottocategoria_Suggerita")) if x)
            t_new = str(a.get("Tipo", "") or "")
            c = a.get("Confidenza", "")
            pct = None if c in ("", None) else int(round(_num(c) * 100 if _num(c) <= 1 else _num(c)))
            out.append({"id": "P_%s" % a.get("Barcode"), "gruppo": "Prodotti da correggere", "genere": "P",
                        "titolo": sug or cur or str(a.get("Barcode")), "barcode": nbc(a.get("Barcode")),
                        "prima": j([cur or "(nome vuoto)", cat_old, ("tipo " + pr["tipo"]) if pr.get("tipo") else ""]),
                        "dopo": j([sug or cur or "(nome vuoto)", cat_new or cat_old, ("tipo " + (t_new or pr.get("tipo", ""))) if (t_new or pr.get("tipo")) else ""]),
                        "sicurezza": pct, "motivo": a.get("Motivo", ""),
                        "campi": {"nome": sug or cur, "categoria": str(a.get("Categoria_Suggerita", "") or pr.get("categoria", "")),
                                  "sottocategoria": str(a.get("Sottocategoria_Suggerita", "") or pr.get("sottocategoria", "")),
                                  "tipo": t_new or pr.get("tipo", "")}})
        for a in self._dicts(SH_AIT, True):
            if str(a.get("Stato", "")) == ST_PENDING[SH_AIT]:
                sm = a.get("Scorta_min", a.get("Scorta min", ""))
                out.append({"id": "T_%s" % a.get("Tipo"), "gruppo": "Nuovi tipi", "genere": "T", "titolo": "Nuovo tipo: %s" % a.get("Tipo"),
                            "prima": "", "dopo": "Tipo %s" % a.get("Tipo"), "sicurezza": None,
                            "motivo": a.get("Note", "") or "L'AI vuole creare questo tipo di prodotto. Imposta la scorta minima e approva.",
                            "campi": {"tipo": str(a.get("Tipo", "")), "scorta_min": _num(sm)}})
        for i, a in enumerate(self._dicts(SH_AIC, True)):
            if str(a.get("Stato", "")) == ST_PENDING[SH_AIC]:
                out.append({"id": "C_%d" % (i + 2), "gruppo": "Categorie proposte", "genere": "C",
                            "titolo": "Categoria: %s → %s" % (a.get("Azione", ""), a.get("Nuovo_Nome") or a.get("Sottocategoria", "")),
                            "prima": str(a.get("Sottocategoria", "")), "dopo": str(a.get("Nuovo_Nome", "")),
                            "sicurezza": None, "motivo": a.get("Motivo", ""), "campi": {}})
        return out

    def decidi(self, id_: str, azione: str, campi: Optional[dict] = None) -> dict:
        """APPROVA (con eventuali correzioni in `campi`) oppure RIFIUTA. Gli stati sono quelli del motore:
        ai_prodotti DA_APPROVARE -> APPLICATO (la modifica al prodotto la fa subito l'app, come aiApplyApproved) o RIFIUTATO;
        ai_tipi -> APPROVATO (+ Scorta_min) o RIFIUTATO; ai_categorie PROPOSTA -> APPLICATA (la applica subito l'app) o RIFIUTATO."""
        azione = {"SCARTA": "RIFIUTA", "CORREGGI": "APPROVA"}.get(str(azione).upper(), str(azione).upper())
        if azione not in ("APPROVA", "RIFIUTA"):
            raise ApiError(400, "Azione non valida")
        campi = campi or {}
        kind, _, key = str(id_).partition("_")
        sheet = {"P": SH_AIP, "T": SH_AIT, "C": SH_AIC}.get(kind)
        if not sheet or not key:
            raise ApiError(400, "Id non valido")
        h, rows = self._rows(sheet, True)
        if "Stato" not in h:
            raise ApiError(500, "Colonna Stato mancante in %s" % sheet)
        idx, decisa = None, False
        for i, r in enumerate(rows):
            d = dict(zip(h, list(r) + [""] * (len(h) - len(r))))
            if kind == "C":
                stessa = i + 2 == int(key if key.isdigit() else -1)
            elif kind == "T":
                stessa = str(d.get("Tipo")) == key
            else:
                stessa = nbc(d.get("Barcode")) == nbc(key)
            if not stessa:
                continue
            if str(d.get("Stato", "")) == ST_PENDING[sheet]:   # lo stesso codice puo avere piu righe: conta quella in attesa
                idx = i
                break
            decisa = True
        if idx is None:
            raise ApiError(409 if decisa else 404, "Proposta già decisa" if decisa else "Proposta non trovata")
        d = dict(zip(h, list(rows[idx]) + [""] * (len(h) - len(rows[idx]))))
        if str(d.get("Stato", "")) != ST_PENDING[sheet]:
            raise ApiError(409, "Proposta già decisa")
        riga = idx + 2
        oggi = datetime.now().strftime("%d/%m/%Y")
        if azione == "RIFIUTA":
            self._scrivi(sheet, riga, {"Stato": ST_NO, "Aggiornato": oggi}, h)
            self._drop(sheet)
            return {"ok": True, "stato": ST_NO}
        if kind == "T":
            sm = campi.get("scorta_min", d.get("Scorta_min", 0))
            if _num(sm) < 0:
                raise ApiError(400, "La scorta minima non può essere negativa")
            self._scrivi(sheet, riga, {"Stato": ST_OK[sheet], "Scorta_min": int(_num(sm)) if float(_num(sm)).is_integer() else _num(sm)}, h)
            self._drop(sheet)
            return {"ok": True, "stato": ST_OK[sheet]}
        if kind == "C":
            stato, n = self._applica_categoria(d)   # come aiApplyCategories: ora lo fa subito l'app
            self._scrivi(sheet, riga, {"Stato": stato, "Aggiornato": oggi}, h)
            self._drop(sheet)
            if stato == "ERRORE":
                raise ApiError(400, "Proposta incompleta: mancano categoria o nuovo nome")
            return {"ok": True, "stato": stato, "righe": n}
        # prodotto: valori finali = correzioni oppure proposta
        pick = lambda k, col: str(campi[k] if k in campi else d.get(col, "") or "").strip()
        nome, cat, sotto, tipo = pick("nome", "Nome_Suggerito"), pick("categoria", "Categoria_Suggerita"), pick("sottocategoria", "Sottocategoria_Suggerita"), pick("tipo", "Tipo")
        k = nbc(d.get("Barcode"))
        p = self.prodotto(k)
        if p is None:
            raise ApiError(404, "Il prodotto non è nel catalogo")
        cat = cat or p["categoria"]
        sotto = sotto or p["sottocategoria"]
        if not self._coppia_valida(cat, sotto):
            raise ApiError(400, "Categoria e sottocategoria non corrispondono all'elenco")
        conf = d.get("Confidenza", "")
        hp, rp = self._rows(SH_PROD, True)
        ip = next((i for i, r in enumerate(rp) if nbc(dict(zip(hp, r)).get("Barcode")) == k), None)
        pd = dict(zip(hp, rp[ip])) if ip is not None else {}
        ups = []
        if cat and cat != p["categoria"]:
            ups.append((ip + 2, "Categoria", cat)); self._log_ai(k, "Categoria", p["categoria"], cat, conf=conf)
        if nome and nome != str(pd.get("Prodotto", "") or "").strip() and not str(pd.get("API Status", "") or "").startswith("✅"):
            ups.append((ip + 2, "Prodotto", nome)); self._log_ai(k, "Prodotto", pd.get("Prodotto", ""), nome, conf=conf)   # come il motore: il nome non si tocca se il prodotto e ✅
        if tipo and "Tipo" in hp and tipo != str(pd.get("Tipo", "") or "").strip():
            ups.append((ip + 2, "Tipo", tipo))
        if ups:
            self.store.update_cells(SH_PROD, ups)
        self._drop(SH_PROD)
        if sotto and sotto != p["sottocategoria"]:   # la sottocategoria e una modifica del prodotto: aggiorna anche i movimenti
            self.modifica_prodotto(k, sotto)
            self._log_ai(k, "Sottocategoria", p["sottocategoria"], sotto, conf=conf)
        if tipo and tipo.lower() not in {t.lower() for t in self.tipi()}:   # tipo nuovo: in coda, con scorta 0
            self.store.append_row(SH_AIT, {"Tipo": tipo, "Scorta_min": 0, "Stato": ST_PENDING[SH_AIT], "Note": "creato dall'app"})
            self._drop(SH_AIT)
        self._scrivi(sheet, riga, {"Nome_Suggerito": nome, "Categoria_Suggerita": cat, "Sottocategoria_Suggerita": sotto, "Tipo": tipo,
                                   "Stato": "APPLICATO", "Aggiornato": oggi}, h)
        self._drop(sheet, SH_PROD)
        return {"ok": True, "stato": "APPLICATO"}

    # --- categorie: applicazione delle proposte AI (porting di aiApplyCategories / renameCategory_) ----
    def _applica_categoria(self, d: dict):
        """AGGIUNGI_CATEGORIA/SOTTOCATEGORIA aggiunge una riga a `categorie`; RINOMINA/UNISCI rinomina su prodotti, movimenti e
        categorie (poi toglie i doppioni). Ritorna (stato, righe toccate): APPLICATA, GIA_PRESENTE o ERRORE."""
        az = str(d.get("Azione", "") or "").strip().upper()
        cat, sub, nuovo = (str(d.get(k, "") or "").strip() for k in ("Categoria", "Sottocategoria", "Nuovo_Nome"))
        if az in ("RINOMINA", "UNISCI"):
            if not nuovo or not cat:
                return "ERRORE", 0
            return "APPLICATA", self._rinomina_categoria(cat, sub, nuovo)
        if az in ("AGGIUNGI_CATEGORIA", "AGGIUNGI_SOTTOCATEGORIA"):
            c, sc = cat, sub or nuovo
            if not c or not sc:
                return "ERRORE", 0
            h, rows = self._rows(SH_CAT, True)
            if any(len(r) > 1 and str(r[0]).strip() == c and str(r[1]).strip() == sc for r in rows):
                return "GIA_PRESENTE", 0
            val = {"Categoria": c, "Sottocategoria": sc}
            if len(h) > 2:
                val[h[2]] = "%s_%s" % (c, sc)
            self.store.append_row(SH_CAT, val)
            self._drop(SH_CAT)
            self._registra_cat("", "%s > %s" % (c, sc), "AI_CATEGORIE")
            return "APPLICATA", 1
        return "ERRORE", 0

    def _registra_cat(self, prima, dopo, fonte):
        try:
            self.store.append_row("log_ai", {"Quando": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "Barcode": "", "Campo": "categorie",
                                             "Prima": prima, "Dopo": dopo, "Fonte": fonte, "Confidenza": "", "Modo": "APPROVATA", "Annullato": ""})
        except Exception:
            pass

    def _rinomina_categoria(self, cat: str, sub: str, nuovo: str) -> int:
        n = 0
        for foglio, hc, hs in ((SH_PROD, "Categoria", "Sottocategoria"), (SH_MOV, "Categoria", "Sottocategoria")):
            h, rows = self._rows(foglio, True)
            if hc not in h or (sub and hs not in h):
                continue
            ic, isb = h.index(hc), (h.index(hs) if hs in h else None)
            ups = []
            for i, r in enumerate(rows):
                if len(r) <= ic or str(r[ic]).strip() != cat:
                    continue
                if sub:
                    if isb is not None and len(r) > isb and str(r[isb]).strip() == sub:
                        ups.append((i + 2, hs, nuovo))
                else:
                    ups.append((i + 2, hc, nuovo))
            if ups:
                self.store.update_cells(foglio, ups)
                n += len(ups)
            self._drop(foglio)
        h, rows = self._rows(SH_CAT, True)
        if h and len(h) > 1:
            out, visti = [], set()
            for r in rows:
                r = list(r) + [""] * (len(h) - len(r))
                if str(r[0]).strip() == cat and (not sub or str(r[1]).strip() == sub):
                    r[1 if sub else 0] = nuovo
                k = (str(r[0]).strip(), str(r[1]).strip())
                if k in visti:
                    continue
                visti.add(k)
                if len(h) > 2 and "_" in str(r[2]):
                    r[2] = "%s_%s" % k
                out.append(r)
            out += [[""] * len(h)] * (len(rows) - len(out))   # le righe in meno (doppioni) restano vuote in fondo
            ups = [(i + 2, h[j], out[i][j]) for i in range(len(rows)) for j in range(len(h))
                   if str((list(rows[i]) + [""] * len(h))[j]) != str(out[i][j])]
            if ups:
                self.store.update_cells(SH_CAT, ups)
            self._drop(SH_CAT)
        self._registra_cat(("%s > %s" % (cat, sub)) if sub else cat, ("%s > %s" % (cat, nuovo)) if sub else nuovo, "AI_RINOMINA")
        return n

    # --- risposte a voce (Google Home / Assist): frasi pronte da leggere ad alta voce ---------------
    PAROLE_VUOTE = {"il", "lo", "la", "l", "i", "gli", "le", "un", "uno", "una", "dei", "degli", "delle", "del", "dello", "della", "di", "da",
                    "ho", "hai", "abbiamo", "ce", "c", "e", "in", "casa", "dove", "sono", "sta", "stanno", "ancora", "qualche", "alcuni", "alcune"}

    @staticmethod
    def _norma(t) -> str:
        t = unicodedata.normalize("NFD", str(t or "").lower())
        return " ".join("".join(c for c in t if not unicodedata.combining(c) and (c.isalnum() or c == " ")).split())

    def voce_manca(self) -> str:
        """Cosa manca in casa: le voci della lista della spesa (finito / in esaurimento), in una frase."""
        voci = self.spesa()["voci"]
        if not voci:
            return "In casa non manca niente."
        fin = [v["tipo"] for v in voci if v["stato"] == "FINITO"]
        esa = [v["tipo"] for v in voci if v["stato"] != "FINITO"]
        def elenco(xs):
            xs = [x.lower() for x in xs]
            return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " e " + xs[-1]
        parti = []
        if fin:
            parti.append("Sono finiti: " + elenco(fin))
        if esa:
            parti.append("Stanno finendo: " + elenco(esa))
        return ". ".join(parti) + "."

    def voce_cerca(self, domanda: str) -> str:
        """Ho questo prodotto e dove? Cerca per nome, marca, tipo o sottocategoria, anche al plurale."""
        parole = [w for w in self._norma(domanda).split() if w not in self.PAROLE_VUOTE]
        if not parole:
            return "Non ho capito che prodotto cerchi."
        radici = [w[:max(3, len(w) - 1)] for w in parole]
        trovati = []
        for e in self.elenco_prodotti():
            testo = self._norma(" ".join((e["nome"], e["marca"], e["tipo"], e["sotto"]))).split()
            if all(any(t.startswith(r) for t in testo) for r in radici):
                trovati.append(e)
        nome = " ".join(parole)
        if not trovati:
            return "Non trovo %s nell'inventario." % nome
        con = [e for e in trovati if e["qta"] > 0]
        if not con:
            return "Non hai più %s." % nome
        f = lambda x: int(x) if float(x).is_integer() else x
        per: Dict[str, float] = {}
        for e in con:
            for q in e["posti"]:
                per[q["luogo"]] = per.get(q["luogo"], 0) + q["qta"]
        totale = f(sum(e["qta"] for e in con))
        dove = ", ".join("%s %s" % (f(q), l.lower()) for l, q in sorted(per.items(), key=lambda kv: -kv[1]))
        if len(con) == 1:
            return "Hai %s: %s pezzi. %s." % (con[0]["nome"], totale, dove[:1].upper() + dove[1:])
        nomi = ", ".join(e["nome"] for e in sorted(con, key=lambda e: -e["qta"])[:3])
        return "Hai %s pezzi tra %d prodotti, per esempio %s. %s." % (totale, len(con), nomi, dove[:1].upper() + dove[1:])

    # --- foto -----------------------------------------------------------
    def foto(self, barcode, data: bytes, mime: str) -> dict:
        k = nbc(barcode)
        if not k:
            raise ApiError(400, "Barcode non valido")
        if mime not in ("image/jpeg", "image/png", "image/webp"):
            raise ApiError(400, "Formato immagine non supportato")
        if not data or len(data) > 8 * 1024 * 1024:
            raise ApiError(400, "Immagine vuota o oltre 8 MB")
        return {"ok": True, "url": ""}   # la foto non si salva: la legge l'AI (main.foto) e si butta

    def memorizza_analisi(self, barcode, analisi: dict) -> None:
        if analisi:
            self.__dict__.setdefault("_analisi", {})[nbc(barcode)] = analisi

    def _bozza_da_foto(self, k: str, tipo: str, location: str, q) -> None:
        """Bozza gia compilata dall'AI per un codice nuovo (se esiste l'analisi della foto)."""
        a = self.__dict__.get("_analisi", {}).pop(k, None)
        if not a:
            return
        try:
            if any(nbc(b.get("Barcode")) == k and str(b.get("Stato", "") or "").strip().upper() in self.BOZZE_APERTE
                   for b in self._opz("bozze", True)):
                return
            self.store.append_row("bozze", {
                "ID": "A" + uuid.uuid4().hex[:7], "Barcode": bco(k), "Foto": "AI", "Prodotto": a.get("nome", ""), "Marca": a.get("marca", ""),
                "Confezione": a.get("confezione", ""), "Categoria": a.get("categoria", ""), "Sottocategoria": a.get("sottocategoria", ""),
                "Tipo": a.get("tipo", ""), "Stato": "PRONTA", "Fonte": "AI (foto)", "Location": location, "Movimento": tipo,
                "Quantità": q, "Aggiornato": datetime.now().strftime("%d/%m/%Y")})
            self._drop("bozze")
        except Exception:
            pass   # la bozza la crea comunque lo script dal movimento in sospeso
