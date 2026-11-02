"""Ricerca sul web senza passare dall'AI: i risultati (titoli, frasi, estratti delle pagine) si passano poi a Gemini come semplice testo da leggere.
Fonti, nell'ordine: Brave, Serper o Tavily se hai messo la chiave nelle opzioni; altrimenti DuckDuckGo senza chiave (meno stabile).
Google non offre piu la sua ricerca ai nuovi clienti. Solo libreria standard; le pagine si aprono solo se pubbliche (vedi pagina.py)."""
import html as _html
import json
import re
import urllib.parse
import urllib.request
from typing import Callable, Dict, List, Optional, Tuple

from . import pagina

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
ULTIMO_ERRORE = [""]
MAX_RISULTATI = 6
MAX_PAGINE = 2
MAX_CONTESTO = 6000


def _http(url: str, chiave_header: Optional[dict] = None, dati: Optional[bytes] = None, timeout: float = 10.0) -> Optional[str]:
    h = {"User-Agent": UA, "Accept": "text/html,application/json,*/*", "Accept-Language": "it-IT,it;q=0.9,en;q=0.5"}
    h.update(chiave_header or {})
    try:
        req = urllib.request.Request(url, data=dati, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(900_000).decode("utf-8", "replace")
    except Exception as e:
        ULTIMO_ERRORE[0] = "%s %s" % (type(e).__name__, getattr(e, "code", ""))
        return None


def _testo(s: str) -> str:
    return " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", s or "")).split())


def ddg(q: str, http: Callable = _http) -> List[dict]:
    t = http("https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": q, "kl": "it-it"}))
    if not t:
        return []
    out = []
    for blocco in re.split(r'<div[^>]+class="[^"]*result__body', t)[1:]:
        m = re.search(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', blocco, re.S)
        if not m:
            continue
        url = _html.unescape(m.group(1))
        u = re.search(r"[?&]uddg=([^&]+)", url)
        url = urllib.parse.unquote(u.group(1)) if u else ("https:" + url if url.startswith("//") else url)
        s = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', blocco, re.S)
        out.append({"titolo": _testo(m.group(2))[:150], "url": url, "snippet": _testo(s.group(1) if s else "")[:300]})
    if not out and not ULTIMO_ERRORE[0]:
        ULTIMO_ERRORE[0] = "DuckDuckGo non ha dato risultati (blocco o nessuna corrispondenza)"
    return out


def brave(q: str, chiave: str, http: Callable = _http) -> List[dict]:
    t = http("https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode({"q": q, "country": "it", "search_lang": "it", "count": MAX_RISULTATI}),
             {"X-Subscription-Token": chiave, "Accept": "application/json"})
    try:
        return [{"titolo": _testo(x.get("title"))[:150], "url": x.get("url", ""), "snippet": _testo(x.get("description"))[:300]} for x in json.loads(t)["web"]["results"]]
    except Exception:
        return []


def serper(q: str, chiave: str, http: Callable = _http) -> List[dict]:
    t = http("https://google.serper.dev/search", {"X-API-KEY": chiave, "Content-Type": "application/json"}, json.dumps({"q": q, "gl": "it", "hl": "it", "num": MAX_RISULTATI}).encode())
    try:
        return [{"titolo": _testo(x.get("title"))[:150], "url": x.get("link", ""), "snippet": _testo(x.get("snippet"))[:300]} for x in json.loads(t)["organic"]]
    except Exception:
        return []


def tavily(q: str, chiave: str, http: Callable = _http) -> List[dict]:
    t = http("https://api.tavily.com/search", {"Content-Type": "application/json"}, json.dumps({"api_key": chiave, "query": q, "max_results": MAX_RISULTATI}).encode())
    try:
        return [{"titolo": _testo(x.get("title"))[:150], "url": x.get("url", ""), "snippet": _testo(x.get("content"))[:300]} for x in json.loads(t)["results"]]
    except Exception:
        return []


def fonte(chiavi: Dict[str, str]) -> str:
    return "Brave" if chiavi.get("BRAVE_SEARCH_KEY") else "Serper" if chiavi.get("SERPER_KEY") else "Tavily" if chiavi.get("TAVILY_KEY") else "DuckDuckGo"


def cerca(q: str, chiavi: Optional[Dict[str, str]] = None, http: Callable = _http) -> List[dict]:
    """Risultati [{titolo, url, snippet}] dalla prima fonte disponibile (se una con chiave non risponde, si passa a DuckDuckGo)."""
    chiavi = chiavi or {}
    ULTIMO_ERRORE[0] = ""
    r: List[dict] = []
    if chiavi.get("BRAVE_SEARCH_KEY"):
        r = brave(q, chiavi["BRAVE_SEARCH_KEY"], http)
    if not r and chiavi.get("SERPER_KEY"):
        r = serper(q, chiavi["SERPER_KEY"], http)
    if not r and chiavi.get("TAVILY_KEY"):
        r = tavily(q, chiavi["TAVILY_KEY"], http)
    if not r:
        r = ddg(q, http)
    visti, out = set(), []
    for x in r:
        if x["url"].startswith(("http://", "https://")) and x["url"] not in visti:
            visti.add(x["url"]); out.append(x)
    return out[:MAX_RISULTATI]


def estratto(html: str, barcode: str = "", n: int = 1500) -> str:
    """Testo leggibile di una pagina; se riporta il codice a barre si tiene la parte attorno al codice."""
    t = re.sub(r"(?is)<(script|style|noscript|svg|head)\b.*?</\1>", " ", html or "")
    t = _testo(t)
    bc = re.sub(r"\D", "", str(barcode)).lstrip("0")
    if bc:
        m = re.search(r"[\s\-]*".join(bc), t)   # il codice puo comparire con spazi o trattini
        if m:
            return t[max(0, m.start() - n // 3): m.start() + n]
    return t[:n]


def contesto(domande: List[str], barcode: str = "", chiavi: Optional[Dict[str, str]] = None, http: Callable = _http,
             scarica: Callable = pagina.scarica, pagine: int = MAX_PAGINE) -> Tuple[str, List[str]]:
    """Cerca ogni domanda, apre le prime pagine e compone il testo da dare all'AI. Ritorna (testo, indirizzi). Testo vuoto se non trova niente."""
    risultati: List[dict] = []
    visti = set()
    for q in domande:
        for x in cerca(q, chiavi, http):
            if x["url"] not in visti:
                visti.add(x["url"]); risultati.append(x)
    if not risultati:
        return "", []
    risultati = risultati[:MAX_RISULTATI]
    righe = []
    for i, x in enumerate(risultati, 1):
        riga = "[%d] %s — %s\n%s" % (i, x["titolo"], urllib.parse.urlparse(x["url"]).netloc, x["snippet"])
        if i <= pagine:
            h = scarica(x["url"])
            if h:
                riga += "\nDalla pagina: " + estratto(h, barcode)
        righe.append(riga)
    return "\n\n".join(righe)[:MAX_CONTESTO], [x["url"] for x in risultati]
