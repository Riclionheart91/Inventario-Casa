"""I miei codici per prodotti senza codice a barre (fatti in casa, sfusi, freschi).
- Formato: «PERS» + 9 cifre casuali (es. PERS482915307). Non sono codici a barre veri: nessun archivio (Open Food Facts e simili) li conosce
  e l'app non li cerca mai online; la scheda prodotto si compila a mano.
- Non ripetibili: ogni codice emesso resta registrato anche se poi viene tolto dall'elenco, e si controlla contro ogni codice gia nel foglio.
- I vecchi codici EAN-13 che iniziano per 2999 (versioni fino alla 0.28) continuano a funzionare come «miei».
Solo libreria standard; lo stato sta in /data/miei_codici.json."""
import json
import os
import re
import secrets
import tempfile
import threading
from datetime import datetime
from typing import Callable, Iterable, List, Optional

PREFISSO = "2999"
_MOLT = 73856093          # dispari e non multiplo di 5: coprimo con 10^8, quindi la rimescolata e biiettiva
_MOD = 10 ** 8


def cifra_controllo(dodici: str) -> str:
    s = sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(dodici))
    return str((10 - s % 10) % 10)


def ean13_valido(codice: str) -> bool:
    c = str(codice)
    return len(c) == 13 and c.isdigit() and cifra_controllo(c[:12]) == c[12]


_PERS = re.compile(r"PERS\d{9}")


def e_pers(codice) -> bool:
    """Codice nel formato PERS + 9 cifre."""
    return bool(_PERS.fullmatch(str(codice or "").strip().upper()))


def e_mio(codice) -> bool:
    """Un mio codice: PERS + 9 cifre, oppure (vecchio formato) un EAN-13 interno che inizia per 2999."""
    if e_pers(codice):
        return True
    c = "".join(ch for ch in str(codice or "") if ch.isdigit())
    return len(c) == 13 and c.startswith(PREFISSO) and ean13_valido(c)


def da_contatore(n: int) -> str:
    centro = "%08d" % ((n * _MOLT) % _MOD)
    base = PREFISSO + centro
    return base + cifra_controllo(base)


def _cartella() -> str:
    return os.environ.get("DATA_DIR") or ("/data" if os.path.isdir("/data") else tempfile.gettempdir())


class MieiCodici:
    def __init__(self, percorso: Optional[str] = None, oggi: Callable[[], datetime] = datetime.now):
        self.percorso = percorso or os.path.join(_cartella(), "miei_codici.json")
        self.oggi = oggi
        self._lock = threading.RLock()

    def _carica(self) -> dict:
        try:
            with open(self.percorso, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    def _salva(self, d: dict) -> None:
        os.makedirs(os.path.dirname(self.percorso), exist_ok=True)
        tmp = self.percorso + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, self.percorso)

    def elenco(self) -> List[dict]:
        return sorted(self._carica().get("codici", []), key=lambda x: x.get("creato", ""), reverse=True)

    def nuovo(self, nome: str = "", usati: Iterable[str] = ()) -> dict:
        """Crea un codice mai usato: salta qualsiasi codice che compare gia (anche in forma senza zeri iniziali) tra `usati`."""
        usati = {str(u).strip().upper().lstrip("0") for u in usati}
        with self._lock:
            d = self._carica()
            emessi = set(d.get("emessi", [])) | {x["codice"] for x in d.get("codici", [])}
            for _ in range(1000):
                c = "PERS%09d" % secrets.randbelow(10 ** 9)
                if c not in emessi and c.lstrip("0") not in usati:
                    break
            else:
                raise ValueError("Codici esauriti")
            voce = {"codice": c, "nome": str(nome or "").strip()[:80], "creato": self.oggi().strftime("%Y-%m-%d %H:%M")}
            d["emessi"] = sorted(emessi | {c})          # anche se la voce sparisse, il codice non torna
            d.setdefault("codici", []).append(voce)
            self._salva(d)
            return voce

    def elimina(self, codice: str) -> bool:
        """Toglie il codice dall'elenco. Resta tra gli emessi: lo stesso codice non verra mai ricreato."""
        with self._lock:
            d = self._carica()
            resto = [x for x in d.get("codici", []) if x["codice"] != codice]
            if len(resto) == len(d.get("codici", [])):
                return False
            d["codici"] = resto
            self._salva(d)
            return True

    def rinomina(self, codice: str, nome: str) -> bool:
        with self._lock:
            d = self._carica()
            for x in d.get("codici", []):
                if x["codice"] == codice:
                    x["nome"] = str(nome or "").strip()[:80]
                    self._salva(d)
                    return True
        return False
