"""Accesso diretto all'app (porta dedicata), oltre all'ingress di Home Assistant. Solo libreria standard, ASGI puro.

Regole:
- Le richieste che arrivano dal gateway ingress di Home Assistant (indirizzo del SOCKET, mai le intestazioni) passano senza codice:
  il login e quello di Home Assistant.
- Tutte le altre richieste (porta diretta) richiedono una sessione valida. Se `shared_code` e vuoto la porta diretta e spenta.
- La sessione e un cookie firmato HMAC; la chiave deriva da un segreto casuale salvato in /data e dal codice: cambiare il codice
  invalida tutte le sessioni aperte.
- Dopo 5 codici errati da uno stesso indirizzo c'e un blocco di 15 minuti. Codice errato e blocco danno la stessa risposta.
Il codice non viene mai scritto nei log ne inviato al frontend."""
import hashlib
import hmac
import html
import json
import os
import secrets
import tempfile
import time
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, quote

INGRESS_IPS = tuple(x.strip() for x in os.environ.get("ACCESSO_INGRESS_IPS", "172.30.32.2").split(",") if x.strip())
COOKIE = "inv_sess"
PUBBLICI = {"/accesso", "/manifest.json", "/icon-192.png", "/icon-512.png", "/icon.svg", "/sw.js"}
DURATA_RICORDA = 90 * 24 * 3600     # "Ricorda questo dispositivo"
DURATA_SESSIONE = 7 * 24 * 3600     # senza "ricorda": cookie di sessione, valido al massimo una settimana
MAX_ERRORI = 5
BLOCCO_SECONDI = 15 * 60
MSG_ERRORE = "Codice errato oppure troppi tentativi: riprova tra qualche minuto."


def ritorno_sicuro(r: str) -> str:
    """Solo percorsi interni: niente indirizzi esterni ne '//' (open redirect)."""
    r = r or ""
    if (not r.startswith("/") or r.startswith("//") or "\\" in r or any(c in r for c in "\r\n\t") or len(r) > 200
            or r.startswith("/accesso") or r.startswith("/esci")):
        return "/"
    return r


class Accesso:
    def __init__(self, get_codice: Callable[[], str], cartella: Optional[str] = None, orologio: Callable[[], float] = time.time):
        self.get_codice = get_codice
        self.cartella = cartella or os.environ.get("ACCESSO_DIR", "/data")
        self.ora = orologio
        self._segreto: Optional[bytes] = None
        self._errori: Dict[str, List[float]] = {}   # ip -> [conteggio, bloccato_fino]

    # --- segreto e firma -------------------------------------------------
    def _carica_segreto(self) -> bytes:
        if self._segreto:
            return self._segreto
        for base in (self.cartella, tempfile.gettempdir()):
            try:
                os.makedirs(base, exist_ok=True)
                p = os.path.join(base, "accesso_segreto")
                if os.path.exists(p):
                    with open(p, "rb") as f:
                        s = f.read()
                    if len(s) >= 32:
                        self._segreto = s
                        return s
                s = secrets.token_bytes(32)
                fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "wb") as f:
                    f.write(s)
                self._segreto = s
                return s
            except OSError:
                continue
        self._segreto = secrets.token_bytes(32)     # ultima risorsa: valido finche l'app resta accesa
        return self._segreto

    def _chiave(self, codice: str) -> bytes:
        return hmac.new(self._carica_segreto(), b"inventario-sessione|" + codice.encode("utf-8"), hashlib.sha256).digest()

    def crea_sessione(self, codice: str, ricorda: bool) -> str:
        scad = int(self.ora() + (DURATA_RICORDA if ricorda else DURATA_SESSIONE))
        payload = "%d.%s" % (scad, secrets.token_hex(8))
        firma = hmac.new(self._chiave(codice), payload.encode(), hashlib.sha256).hexdigest()
        return payload + "." + firma

    def sessione_valida(self, valore: str, codice: str) -> bool:
        try:
            payload, _, firma = (valore or "").rpartition(".")
            atteso = hmac.new(self._chiave(codice), payload.encode(), hashlib.sha256).hexdigest()
            if not payload or not hmac.compare_digest(firma, atteso):
                return False
            return int(payload.split(".")[0]) > self.ora()
        except Exception:
            return False

    # --- limite tentativi ---------------------------------------------------
    def bloccato(self, ip: str) -> bool:
        e = self._errori.get(ip)
        return bool(e and e[1] > self.ora())

    def registra_errore(self, ip: str) -> None:
        if len(self._errori) > 2000:    # pulizia: indirizzi non piu bloccati
            ora = self.ora()
            self._errori = {k: v for k, v in self._errori.items() if v[1] > ora}
        e = self._errori.setdefault(ip, [0, 0.0])
        e[0] += 1
        if e[0] >= MAX_ERRORI:
            e[0], e[1] = 0, self.ora() + BLOCCO_SECONDI

    def tenta(self, ip: str, inserito: str, codice: str) -> bool:
        """True se il codice e giusto. Blocco e codice errato sono indistinguibili dall'esterno."""
        if self.bloccato(ip):
            return False
        if codice and hmac.compare_digest(inserito.encode("utf-8"), codice.encode("utf-8")):
            self._errori.pop(ip, None)
            return True
        self.registra_errore(ip)
        return False

    # --- ASGI ------------------------------------------------------------------
    @staticmethod
    def _ip(scope) -> str:
        c = scope.get("client")
        return c[0] if c else ""

    def e_ingresso_ha(self, scope) -> bool:
        return self._ip(scope) in INGRESS_IPS

    def e_diretto(self, scope) -> bool:
        return not self.e_ingresso_ha(scope)

    @staticmethod
    def _intest(scope, nome: bytes) -> str:
        for k, v in scope.get("headers", []):
            if k == nome:
                return v.decode("latin-1")
        return ""

    def _cookie(self, scope) -> str:
        for parte in self._intest(scope, b"cookie").split(";"):
            k, _, v = parte.strip().partition("=")
            if k == COOKIE:
                return v
        return ""

    def _https(self, scope) -> bool:
        return scope.get("scheme") == "https" or self._intest(scope, b"x-forwarded-proto").lower() == "https"

    def middleware(self, app):
        return _Mw(app, self)


async def _rispondi(send, stato: int, corpo: bytes, tipo: str, extra: Optional[List[Tuple[bytes, bytes]]] = None):
    h = [(b"content-type", tipo.encode()), (b"content-length", str(len(corpo)).encode()), (b"cache-control", b"no-store"),
         (b"x-content-type-options", b"nosniff")] + (extra or [])
    await send({"type": "http.response.start", "status": stato, "headers": h})
    await send({"type": "http.response.body", "body": corpo})


async def _leggi_corpo(receive, limite: int = 4096) -> bytes:
    out = b""
    while True:
        m = await receive()
        out += m.get("body", b"")
        if len(out) > limite:
            return out[:limite]
        if not m.get("more_body"):
            return out


PAGINA = """<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#14181b"><meta name="robots" content="noindex"><title>Inventario · Accesso</title>
<style>*{box-sizing:border-box}body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#14181b;color:#e8eaed;font:16px/1.4 -apple-system,system-ui,sans-serif;padding:16px}
form{width:100%%;max-width:360px;background:#1d2327;border:1px solid #2d363c;border-radius:16px;padding:24px}
h1{margin:0 0 4px;font-size:22px}p{margin:0 0 18px;color:#9aa4ab;font-size:14px}label{display:block;margin:0 0 6px;font-size:13px;color:#9aa4ab}
input[type=password]{width:100%%;min-height:48px;border-radius:12px;border:1px solid #2d363c;background:#14181b;color:#e8eaed;padding:0 14px;font-size:18px}
.r{display:flex;gap:10px;align-items:center;margin:14px 0 18px;font-size:14px}.r input{width:20px;height:20px}
button{width:100%%;min-height:48px;border:0;border-radius:12px;background:#69b1e3;color:#06222f;font-size:16px;font-weight:700;cursor:pointer}
.e{margin:0 0 14px;padding:10px 12px;border-radius:10px;background:#3a2326;color:#f0a0a0;font-size:14px}</style></head>
<body><form method="post" action="accesso"><h1>Inventario Casa</h1><p>Inserisci il codice di famiglia.</p>%s
<label for="c">Codice</label><input id="c" name="codice" type="password" autocomplete="current-password" autofocus required>
<input type="hidden" name="ritorno" value="%s">
<div class="r"><input id="k" name="ricorda" type="checkbox" value="1" checked><label for="k" style="margin:0">Ricorda questo dispositivo</label></div>
<button type="submit">Entra</button></form></body></html>"""
CSP = (b"content-security-policy", b"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")


class _Mw:
    def __init__(self, app, acc: Accesso):
        self.app, self.acc = app, acc

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or self.acc.e_ingresso_ha(scope):
            return await self.app(scope, receive, send)
        acc, path = self.acc, scope.get("path", "/")
        if path.startswith("/voce/"):   # risposte a voce per Home Assistant: le protegge il proprio token (opzione voce_token)
            return await self.app(scope, receive, send)
        codice = acc.get_codice()
        if not codice:
            if path.startswith("/api/"):
                return await _rispondi(send, 403, json.dumps({"errore": "Accesso diretto spento: imposta il codice nelle opzioni dell'app."}).encode(), "application/json")
            msg = "Accesso diretto spento: imposta il codice (shared_code) nelle opzioni dell'app Inventario Casa in Home Assistant."
            return await _rispondi(send, 403, ("<!doctype html><meta charset=utf-8><title>Inventario</title><p style='font:16px system-ui;padding:24px'>%s</p>" % html.escape(msg)).encode(), "text/html; charset=utf-8")
        if path == "/esci":
            return await _rispondi(send, 303, b"", "text/plain", [(b"location", b"/accesso"),
                                                                (b"set-cookie", ("%s=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax" % COOKIE).encode())])
        if path == "/accesso":
            return await self._accesso(scope, receive, send, codice)
        if path in PUBBLICI:
            return await self.app(scope, receive, send)
        if acc.sessione_valida(acc._cookie(scope), codice):
            return await self.app(scope, receive, send)
        if path.startswith("/api/"):
            return await _rispondi(send, 401, json.dumps({"errore": "Accesso richiesto"}).encode(), "application/json")
        dove = scope.get("raw_path", b"").decode("latin-1") or path
        if scope.get("query_string"):
            dove += "?" + scope["query_string"].decode("latin-1")
        return await _rispondi(send, 303, b"", "text/plain", [(b"location", ("/accesso?ritorno=" + quote(ritorno_sicuro(dove), safe="")).encode())])

    async def _accesso(self, scope, receive, send, codice):
        acc = self.acc
        if scope["method"] == "POST":
            dati = {k: v[0] for k, v in parse_qs((await _leggi_corpo(receive)).decode("utf-8", "replace")).items()}
            ritorno = ritorno_sicuro(dati.get("ritorno", ""))
            if acc.tenta(acc._ip(scope), dati.get("codice", ""), codice):
                ck = "%s=%s; Path=/; HttpOnly; SameSite=Lax" % (COOKIE, acc.crea_sessione(codice, dati.get("ricorda") == "1"))
                if dati.get("ricorda") == "1":
                    ck += "; Max-Age=%d" % DURATA_RICORDA
                if acc._https(scope):
                    ck += "; Secure"
                return await _rispondi(send, 303, b"", "text/plain", [(b"location", ritorno.encode()), (b"set-cookie", ck.encode())])
            corpo = PAGINA % ('<div class="e" role="alert">%s</div>' % html.escape(MSG_ERRORE), html.escape(ritorno, quote=True))
            return await _rispondi(send, 401, corpo.encode(), "text/html; charset=utf-8", [CSP, (b"x-frame-options", b"DENY")])
        qs = {k: v[0] for k, v in parse_qs(scope.get("query_string", b"").decode("latin-1")).items()}
        corpo = PAGINA % ("", html.escape(ritorno_sicuro(qs.get("ritorno", "")), quote=True))
        await _rispondi(send, 200, corpo.encode(), "text/html; charset=utf-8", [CSP, (b"x-frame-options", b"DENY")])
