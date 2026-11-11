"""Impostazioni modificabili dall'app (schermata Impostazioni). Si salvano in /data/impostazioni.json.
Le opzioni dell'add-on restano la base: qui ci sono solo ritocchi che l'app puo cambiare da sola. Un valore «0» o vuoto, dove indicato,
significa «usa l'opzione dell'add-on». Solo libreria standard; nessuna chiave o password qui dentro."""
import json
import os
import re
import tempfile
import threading
from typing import Any, Dict, List, Optional

# sch = schermata dove compare; tipo: bool | scelta | numero | ora | testo
SCHEMA: List[dict] = [
    # --- AI ---
    {"k": "ai_sospesa", "tipo": "bool", "default": False, "sch": "ai", "et": "Sospendi l'AI", "desc": "Ferma tutte le chiamate a Gemini (ricerche, foto, classificazioni). Il resto dell'app funziona."},
    {"k": "ai_limite", "tipo": "numero", "default": 0, "min": 0, "max": 5000, "sch": "ai", "et": "Limite giornaliero di chiamate", "desc": "Oltre questo numero l'AI si ferma fino a domani. 0 = nessun limite."},
    # --- avvisi ---
    {"k": "scad_giorni", "tipo": "numero", "default": 0, "min": 0, "max": 60, "sch": "avv", "et": "Giorni di anticipo per le scadenze", "desc": "0 = usa l'opzione dell'add-on."},
    {"k": "scad_ora", "tipo": "ora", "default": "", "sch": "avv", "et": "Ora dell'avviso scadenze", "desc": "Vuoto = usa l'opzione dell'add-on."},
    {"k": "scorte_avviso", "tipo": "bool", "default": False, "sch": "avv", "et": "Avvisa quando una scorta è bassa", "desc": "Una notifica al giorno con i prodotti sotto la soglia."},
    {"k": "scorte_soglia", "tipo": "numero", "default": 1, "min": 0, "max": 50, "sch": "avv", "et": "Soglia scorta bassa (pezzi)", "desc": "Un prodotto con questa quantità o meno è «in esaurimento»."},
    {"k": "riepilogo_sett", "tipo": "bool", "default": False, "sch": "avv", "et": "Riepilogo settimanale", "desc": "Un messaggio con cosa scade, cosa manca e cosa c'è da approvare."},
    {"k": "riepilogo_giorno", "tipo": "scelta", "default": "dom", "opzioni": [["lun", "Lun"], ["mar", "Mar"], ["mer", "Mer"], ["gio", "Gio"], ["ven", "Ven"], ["sab", "Sab"], ["dom", "Dom"]], "sch": "avv", "et": "Giorno del riepilogo", "desc": ""},
    {"k": "riepilogo_ora", "tipo": "ora", "default": "09:00", "sch": "avv", "et": "Ora del riepilogo", "desc": ""},
    # --- dati automatici ---
    {"k": "arr_ora", "tipo": "ora", "default": "", "sch": "arr", "et": "Ora del giro notturno", "desc": "Vuoto = usa l'opzione dell'add-on."},
    {"k": "arr_punteggi", "tipo": "bool", "default": True, "sch": "arr", "et": "Cerca punteggi e riciclo", "desc": "Nutri-Score, NOVA, Eco-Score e materiali della confezione (usa l'AI)."},
    {"k": "arr_traduzioni", "tipo": "bool", "default": True, "sch": "arr", "et": "Traduci i testi in italiano", "desc": ""},
    {"k": "auto_approva", "tipo": "bool", "default": False, "sch": "arr", "et": "Approva da sola le proposte molto sicure", "desc": "Le proposte dell'AI sopra la soglia si applicano senza passare da «Da fare». Le altre restano da approvare."},
    {"k": "auto_soglia", "tipo": "numero", "default": 95, "min": 80, "max": 100, "sch": "arr", "et": "Sicurezza minima per approvare da sola (%)", "desc": ""},
    {"k": "rev_mesi", "tipo": "numero", "default": 6, "min": 1, "max": 24, "sch": "rev", "et": "Revisione a tappeto ogni (mesi)", "desc": ""},
    # --- Open Food Facts ---
    {"k": "off_food", "tipo": "bool", "default": True, "sch": "off", "et": "Open Food Facts (alimenti)", "desc": ""},
    {"k": "off_pet", "tipo": "bool", "default": True, "sch": "off", "et": "Open Pet Food Facts (animali)", "desc": ""},
    {"k": "off_products", "tipo": "bool", "default": True, "sch": "off", "et": "Open Products Facts (casa e pulizia)", "desc": ""},
    {"k": "off_beauty", "tipo": "bool", "default": True, "sch": "off", "et": "Open Beauty Facts (cosmetici)", "desc": ""},
    {"k": "off_controllo", "tipo": "scelta", "default": "giorno", "opzioni": [["giorno", "Ogni giorno"], ["manuale", "Solo se lo chiedo"]], "sch": "off", "et": "Controllo dei prodotti nuovi", "desc": ""},
    {"k": "off_foto_giorni", "tipo": "numero", "default": 30, "min": 1, "max": 365, "sch": "off", "et": "Cancella le foto tenute in memoria dopo (giorni)", "desc": "Vale per le foto di prodotti mai inviati."},
    # --- aspetto ---
    {"k": "tema", "tipo": "scelta", "default": "auto", "opzioni": [["auto", "Automatico"], ["scuro", "Scuro"], ["chiaro", "Chiaro"]], "sch": "asp", "et": "Tema", "desc": "Automatico segue l'impostazione del telefono o del computer."},
    {"k": "testo", "tipo": "scelta", "default": "normale", "opzioni": [["piccolo", "Piccolo"], ["normale", "Normale"], ["grande", "Grande"]], "sch": "asp", "et": "Dimensione del testo", "desc": ""},
    # --- movimento ed elenchi ---
    {"k": "mov_luogo", "tipo": "scelta", "default": "Casa", "opzioni": [["Casa", "Casa"], ["Cantina", "Cantina"]], "sch": "mov", "et": "Posizione predefinita", "desc": "Quella già scelta quando apri Movimento."},
    {"k": "mov_qta", "tipo": "numero", "default": 1, "min": 1, "max": 99, "sch": "mov", "et": "Quantità predefinita", "desc": ""},
    {"k": "ordine", "tipo": "scelta", "default": "nome", "opzioni": [["nome", "Nome"], ["scadenza", "Scadenza"], ["recenti", "Ultimi caricati"]], "sch": "mov", "et": "Ordine degli elenchi", "desc": "Stock e Prodotti."},
    # --- accessi e sicurezza ---
    {"k": "sola_lettura_forza", "tipo": "bool", "default": False, "sch": "sic", "et": "Forza la sola lettura", "desc": "Blocca ogni scrittura sul foglio anche se l'opzione dell'add-on la permette. Non può sbloccare quella dell'add-on."},
    {"k": "accessi_avviso", "tipo": "bool", "default": True, "sch": "sic", "et": "Avvisami per un dispositivo nuovo", "desc": "Una notifica di Home Assistant quando l'app viene aperta da un dispositivo mai visto."},
    {"k": "accessi_giorni", "tipo": "numero", "default": 90, "min": 7, "max": 365, "sch": "sic", "et": "Conserva il registro degli accessi (giorni)", "desc": ""},
    # --- copia di sicurezza ---
    {"k": "copia_auto", "tipo": "bool", "default": False, "sch": "cop", "et": "Copia automatica del foglio", "desc": "Una copia del foglio nella cartella Drive dell'app, a intervalli regolari."},
    {"k": "copia_giorni", "tipo": "numero", "default": 7, "min": 1, "max": 90, "sch": "cop", "et": "Una copia ogni (giorni)", "desc": ""},
]
PER_CHIAVE = {s["k"]: s for s in SCHEMA}
_RE_ORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _cartella() -> str:
    return os.environ.get("DATA_DIR") or ("/data" if os.path.isdir("/data") else tempfile.gettempdir())


def valida(k: str, v: Any) -> Any:
    """Ritorna il valore pulito oppure solleva ValueError."""
    s = PER_CHIAVE.get(k)
    if not s:
        raise ValueError("Impostazione sconosciuta: %s" % k)
    t = s["tipo"]
    if t == "bool":
        if isinstance(v, bool):
            return v
        if str(v).lower() in ("1", "true", "si", "sì"):
            return True
        if str(v).lower() in ("0", "false", "no"):
            return False
        raise ValueError("%s: serve vero o falso" % k)
    if t == "numero":
        try:
            n = int(float(str(v).replace(",", ".")))
        except Exception:
            raise ValueError("%s: serve un numero" % k)
        return max(s.get("min", 0), min(s.get("max", 100000), n))
    if t == "ora":
        v = str(v or "").strip()
        if v and not _RE_ORA.match(v):
            raise ValueError("%s: ora non valida (es. 08:30)" % k)
        return v
    if t == "scelta":
        if str(v) not in [o[0] for o in s["opzioni"]]:
            raise ValueError("%s: scelta non valida" % k)
        return str(v)
    return str(v or "")[:200]


class Impostazioni:
    def __init__(self, percorso: Optional[str] = None):
        self.percorso = percorso or os.path.join(_cartella(), "impostazioni.json")
        self._lock = threading.RLock()

    def _carica(self) -> dict:
        try:
            with open(self.percorso, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    def tutte(self) -> Dict[str, Any]:
        d = self._carica()
        out = {}
        for s in SCHEMA:
            try:
                out[s["k"]] = valida(s["k"], d[s["k"]]) if s["k"] in d else s["default"]
            except Exception:
                out[s["k"]] = s["default"]
        return out

    def get(self, k: str, default: Any = None) -> Any:
        v = self.tutte().get(k)
        return default if v is None else v

    def imposta(self, valori: Dict[str, Any]) -> Dict[str, Any]:
        puliti = {k: valida(k, v) for k, v in (valori or {}).items()}     # se uno non va, non si salva niente
        with self._lock:
            d = self._carica()
            d.update(puliti)
            try:
                os.makedirs(os.path.dirname(self.percorso), exist_ok=True)
                tmp = self.percorso + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(d, f, ensure_ascii=False)
                os.replace(tmp, self.percorso)
            except OSError:
                raise ValueError("Impossibile salvare le impostazioni")
        return self.tutte()


_istanza: Optional[Impostazioni] = None


def imp() -> Impostazioni:
    """Istanza condivisa: gli altri moduli leggono con imp().get('chiave')."""
    global _istanza
    if _istanza is None:
        _istanza = Impostazioni()
    return _istanza
