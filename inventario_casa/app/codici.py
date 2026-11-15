"""I miei codici a barre: EAN-13 interni per prodotti senza codice (fatti in casa, sfusi, freschi).
- Intervallo riservato: iniziano per 2999 (nel campo 2xx di GS1 riservato all'uso interno), quindi non sono mai codici di prodotti comprati.
- Non ripetibili: un contatore che solo cresce (mai riusato, anche se il prodotto viene tolto) e il controllo contro ogni codice gia nel foglio.
- Le 8 cifre centrali sono il contatore rimescolato in modo reversibile (nessun doppione fino a 100 milioni di codici) per non sembrare una sequenza.
Solo libreria standard; lo stato sta in /data/miei_codici.json."""
import json
import os
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


def e_mio(codice) -> bool:
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
        usati = {str(u).lstrip("0") for u in usati}
        with self._lock:
            d = self._carica()
            n = int(d.get("contatore", 0))
            while True:
                n += 1
                if n >= _MOD:
                    raise ValueError("Codici esauriti")
                c = da_contatore(n)
                if c.lstrip("0") not in usati and not any(x["codice"] == c for x in d.get("codici", [])):
                    break
            voce = {"codice": c, "nome": str(nome or "").strip()[:80], "creato": self.oggi().strftime("%Y-%m-%d %H:%M")}
            d["contatore"] = n          # salvato comunque: anche se la voce sparisse, il numero non torna
            d.setdefault("codici", []).append(voce)
            self._salva(d)
            return voce

    def elimina(self, codice: str) -> bool:
        """Toglie il codice dall'elenco. Il contatore NON torna indietro: lo stesso codice non verra mai ricreato."""
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
