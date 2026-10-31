"""Immagine di un prodotto da una pagina web: solo se la pagina riporta davvero il codice a barre cercato (cosi non si prende la foto di un altro prodotto).
Solo libreria standard. Non si apre mai un indirizzo che punta alla rete di casa."""
import ipaddress
import re
import socket
import urllib.request
from typing import Callable, Optional
from urllib.parse import urljoin, urlparse

LIMITE = 900_000
UA = "Mozilla/5.0 (compatible; InventarioCasa/1.0)"


def indirizzo_pubblico(url: str) -> bool:
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.hostname:
            return False
        for info in socket.getaddrinfo(p.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        return True
    except Exception:
        return False


def scarica(url: str, timeout: float = 8.0) -> Optional[str]:
    if not indirizzo_pubblico(url):
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if not indirizzo_pubblico(r.geturl()):   # anche dopo i reindirizzamenti
                return None
            return r.read(LIMITE).decode("utf-8", "replace")
    except Exception:
        return None


def _meta_immagine(html: str):
    for tag in re.findall(r"<meta\b[^>]*>", html, re.I):
        if re.search(r"""(?:property|name)\s*=\s*["'](?:og:image(?::secure_url)?|twitter:image(?::src)?)["']""", tag, re.I):
            m = re.search(r"""content\s*=\s*["']([^"']+)["']""", tag, re.I)
            if m:
                yield m.group(1).strip()
    for m in re.finditer(r'"image"\s*:\s*"(https?:[^"]+)"', html):
        yield m.group(1).replace("\\/", "/")
    for m in re.finditer(r'"image"\s*:\s*\[\s*"(https?:[^"]+)"', html):
        yield m.group(1).replace("\\/", "/")


def immagine_da_pagina(url: str, barcode: str, scarica_fn: Callable = scarica) -> Optional[str]:
    html = scarica_fn(url)
    bc = re.sub(r"\D", "", str(barcode)).lstrip("0")
    if not html or not bc:
        return None
    if bc not in re.sub(r"[\s\-]", "", html):   # il codice deve comparire nella pagina
        return None
    for cand in _meta_immagine(html):
        img = urljoin(url, cand)
        if img.startswith(("http://", "https://")) and re.search(r"\.(jpe?g|png|webp)(\?|$)|/image|/img|/media|/photo", img, re.I):
            return img.replace("http://", "https://", 1) if img.startswith("http://") else img
    return None
