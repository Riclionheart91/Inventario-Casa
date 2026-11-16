"""Etichetta per la stampante termica (rotolo pretagliato 12 x 40 mm, 203 DPI): QR del codice a barre + nome + posizione.

Il QR e scritto qui (versione 1, correzione L, solo cifre, fino a 41 cifre): niente librerie in piu, e il lettore dell'app
(che dopo la lettura tiene solo le cifre) trova esattamente il codice a barre del prodotto. Il disegno usa Pillow."""
import io
import re

_CAP_DATI = 19      # versione 1-L: 19 codeword di dati + 7 di correzione
_N = 21


# ---------- QR (versione 1-L, modo numerico) ----------
def _gf_tabelle():
    exp, log, x = [0] * 512, [0] * 256, 1
    for i in range(255):
        exp[i] = x
        log[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11D
    for i in range(255, 512):
        exp[i] = exp[i - 255]
    return exp, log


_EXP, _LOG = _gf_tabelle()


def _mul(a, b):
    return 0 if a == 0 or b == 0 else _EXP[_LOG[a] + _LOG[b]]


def _correzione(dati, n=7):
    gen = [1]
    for i in range(n):
        nuovo = [0] * (len(gen) + 1)
        for j, c in enumerate(gen):
            nuovo[j] ^= c
            nuovo[j + 1] ^= _mul(c, _EXP[i])
        gen = nuovo
    resto = list(dati) + [0] * n
    for i in range(len(dati)):
        c = resto[i]
        if c:
            for j in range(1, len(gen)):
                resto[i + j] ^= _mul(gen[j], c)
    return resto[len(dati):]


_ALFA = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"


def _codeword(cifre):
    if cifre.isdigit():                              # modo numerico
        bit = "0001" + format(len(cifre), "010b")
        for i in range(0, len(cifre), 3):
            g = cifre[i:i + 3]
            bit += format(int(g), {3: "010b", 2: "07b", 1: "04b"}[len(g)])
    else:                                            # modo alfanumerico (lettere maiuscole e cifre): per i codici PERS...
        bit = "0010" + format(len(cifre), "09b")
        for i in range(0, len(cifre), 2):
            g = cifre[i:i + 2]
            bit += format(_ALFA.index(g[0]) * 45 + _ALFA.index(g[1]), "011b") if len(g) == 2 else format(_ALFA.index(g), "06b")
    bit += "0" * min(4, _CAP_DATI * 8 - len(bit))
    bit += "0" * (-len(bit) % 8)
    cw = [int(bit[i:i + 8], 2) for i in range(0, len(bit), 8)]
    pad = [0xEC, 0x11]
    while len(cw) < _CAP_DATI:
        cw.append(pad[(len(cw) - len(bit) // 8) % 2])
    return cw


def _formato(maschera):
    dati = (1 << 3) | maschera          # livello L = 01
    r = dati
    for _ in range(10):
        r = (r << 1) ^ ((r >> 9) * 0x537)
    return ((dati << 10) | r) ^ 0x5412


def _maschera_ok(m, x, y):
    return [(x + y) % 2 == 0, y % 2 == 0, x % 3 == 0, (x + y) % 3 == 0, (x // 3 + y // 2) % 2 == 0,
            x * y % 2 + x * y % 3 == 0, (x * y % 2 + x * y % 3) % 2 == 0, ((x + y) % 2 + x * y % 3) % 2 == 0][m]


def _penalita(mod):
    n, p = _N, 0
    for righe in (mod, [list(c) for c in zip(*mod)]):
        for r in righe:
            corsa = 1
            for i in range(1, n):
                if r[i] == r[i - 1]:
                    corsa += 1
                    if corsa == 5:
                        p += 3
                    elif corsa > 5:
                        p += 1
                else:
                    corsa = 1
            s = "".join("1" if v else "0" for v in r)
            p += 40 * (s.count("10111010000") + s.count("00001011101"))
    for y in range(n - 1):
        for x in range(n - 1):
            if mod[y][x] == mod[y][x + 1] == mod[y + 1][x] == mod[y + 1][x + 1]:
                p += 3
    scuri = sum(v for r in mod for v in r)
    p += 10 * (abs(scuri * 20 - n * n * 10) // (n * n))
    return p


def qr_moduli(cifre: str):
    """Matrice 21x21 di booleani (True = modulo scuro) per una stringa di sole cifre (fino a 41) o di maiuscole e cifre (fino a 25)."""
    if not (re.fullmatch(r"\d{1,41}", cifre or "") or re.fullmatch(r"[0-9A-Z]{1,25}", cifre or "")):
        raise ValueError("il QR contiene solo cifre (da 1 a 41) oppure maiuscole e cifre (fino a 25)")
    cw = _codeword(cifre)
    cw += _correzione(cw)
    bit = [(c >> (7 - i)) & 1 for c in cw for i in range(8)]
    n = _N
    funz = [[False] * n for _ in range(n)]
    base = [[False] * n for _ in range(n)]

    def fun(x, y, scuro):
        if 0 <= x < n and 0 <= y < n:
            base[y][x] = scuro
            funz[y][x] = True

    for cx, cy in ((3, 3), (n - 4, 3), (3, n - 4)):
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                fun(cx + dx, cy + dy, max(abs(dx), abs(dy)) not in (2, 4))
    for i in range(n):
        if not funz[6][i]:
            fun(i, 6, i % 2 == 0)
        if not funz[i][6]:
            fun(6, i, i % 2 == 0)
    for i in range(15):                     # aree del formato (riservate; il valore si scrive dopo)
        for (x, y) in ((8, i if i < 6 else (i + 1 if i < 8 else None)),):
            pass
    riserva = [(8, i) for i in range(6)] + [(8, 7), (8, 8), (7, 8)] + [(14 - i, 8) for i in range(9, 15)] + \
              [(n - 1 - i, 8) for i in range(8)] + [(8, n - 15 + i) for i in range(8, 15)] + [(8, n - 8)]
    for x, y in riserva:
        funz[y][x] = True
    # dati a zig-zag
    base_d = [r[:] for r in base]
    i = 0
    for destra in range(n - 1, 0, -2):
        if destra == 6:
            destra = 5
        for v in range(n):
            for j in range(2):
                x = destra - j
                y = n - 1 - v if ((destra + 1) & 2) == 0 else v
                if not funz[y][x] and i < len(bit):
                    base_d[y][x] = bit[i] == 1
                    i += 1
    migliore = None
    for m in range(8):
        mod = [r[:] for r in base_d]
        for y in range(n):
            for x in range(n):
                if not funz[y][x] and _maschera_ok(m, x, y):
                    mod[y][x] = not mod[y][x]
        f = _formato(m)
        b = lambda k: ((f >> k) & 1) == 1
        for k in range(6):
            mod[k][8] = b(k)
        mod[7][8], mod[8][8], mod[8][7] = b(6), b(7), b(8)
        for k in range(9, 15):
            mod[8][14 - k] = b(k)
        for k in range(8):
            mod[8][n - 1 - k] = b(k)
        for k in range(8, 15):
            mod[n - 15 + k][8] = b(k)
        mod[n - 8][8] = True
        p = _penalita(mod)
        if migliore is None or p < migliore[0]:
            migliore = (p, mod)
    return migliore[1]


# ---------- disegno ----------
_FONT_GRASSETTO = ["/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                   "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf"]
_FONT_NORMALE = [p.replace("-Bold", "") for p in _FONT_GRASSETTO]


def _font(percorsi, dim):
    from PIL import ImageFont
    for p in percorsi:
        try:
            return ImageFont.truetype(p, dim)
        except OSError:
            continue
    return ImageFont.load_default(dim)


def _righe(d, testo, font, largh, max_righe):
    parole, righe, r = str(testo).split(), [], ""
    for w in parole:
        t = (r + " " + w).strip()
        if d.textlength(t, font=font) <= largh or not r:
            r = t
        else:
            righe.append(r)
            r = w
    if r:
        righe.append(r)
    return righe if len(righe) <= max_righe and all(d.textlength(x, font=font) <= largh for x in righe) else None


ICONE = {"freddo": "\u2744", "dolce": "\u2665", "frutta": "\u273f", "bevanda": "\u2615", "speciale": "\u2605"}   # ❄ ♥ ✿ ☕ ★ (nel font DejaVu)


def etichetta_png(codice: str, nome: str, posizione: str = "", testa: int = 96, lunghezza: int = 280,
                  data_txt: str = "", lotto: str = "", mostra_codice: bool = False, icona: str = "") -> bytes:
    """PNG a 1 bit, orizzontale (lunghezza x testa punti a 203 DPI): QR a sinistra (con il numero sotto, se richiesto),
    a destra il nome e, sotto, le righe facoltative (posizione, data, lotto); in alto a destra un'icona.
    Per il rotolo 12 x 40 mm: testa = 96 punti, lunghezza = 280 punti (area stampabile)."""
    from PIL import Image, ImageDraw
    nome = re.sub(r"[\U0001F000-\U0001FFFF\u2600-\u27BF\uFE0F\u200D]", "", str(nome or "")).strip()   # le emoji nel nome uscirebbero come quadratini
    cifre = str(codice).strip().upper() if re.fullmatch(r"PERS\d+", str(codice).strip().upper()) else re.sub(r"\D", "", str(codice))
    mod = qr_moduli(cifre)
    px = 3 if mostra_codice else max(2, min(4, (testa - 12) // _N))
    lato = _N * px
    im = Image.new("L", (lunghezza, testa), 255)
    d = ImageDraw.Draw(im)
    x0, y0 = 6, (4 if mostra_codice else (testa - lato) // 2)
    for y, riga in enumerate(mod):
        for x, v in enumerate(riga):
            if v:
                d.rectangle([x0 + x * px, y0 + y * px, x0 + (x + 1) * px - 1, y0 + (y + 1) * px - 1], fill=0)
    col = lato
    if mostra_codice:                               # il numero sotto il QR, per digitarlo se il QR si rovina
        fc = _font(_FONT_NORMALE, 10)
        while d.textlength(cifre, font=fc) > 86 and fc.size > 7:
            fc = _font(_FONT_NORMALE, fc.size - 1)
        col = max(lato, int(d.textlength(cifre, font=fc)))
        d.text((x0 + (col - d.textlength(cifre, font=fc)) // 2, y0 + lato + 3), cifre, font=fc, fill=0)
    tx = x0 + col + 10
    ic = ICONE.get(icona, "")
    largh = lunghezza - tx - 4 - (26 if ic else 0)
    if ic:
        fi = _font(_FONT_NORMALE, 22)
        d.text((lunghezza - 28, 2), ic, font=fi, fill=0)
    # righe facoltative sotto il nome: si affiancano finche stanno in una riga
    voci = [v for v in (str(posizione or "").strip(), str(data_txt or "").strip(), ("Lotto " + str(lotto).strip()) if str(lotto or "").strip() else "") if v]
    fp = _font(_FONT_NORMALE, 15)
    righe_f = []
    for v in voci:
        if righe_f and d.textlength(righe_f[-1] + "  ·  " + v, font=fp) <= largh:
            righe_f[-1] += "  ·  " + v
        else:
            righe_f.append(v)
    while len(righe_f) > 2 and fp.size > 11 or any(d.textlength(r, font=fp) > largh for r in righe_f) and fp.size > 10:
        fp = _font(_FONT_NORMALE, fp.size - 1)
    h_f = fp.size + 4
    alto_f = len(righe_f) * h_f
    disp = testa - 6 - alto_f                       # altezza rimasta per il nome
    nome_righe, fn = None, None
    for dim in (24, 22, 20, 18, 16, 14, 12, 10):
        fn = _font(_FONT_GRASSETTO, dim)
        nr = _righe(d, nome or "", fn, largh, 2 if dim >= 18 else 3)
        if nr is not None and len(nr) * (dim + 3) <= disp:
            nome_righe = nr
            break
    if nome_righe is None:                          # troppo lungo anche piccolo: si taglia
        t = str(nome)
        while t and d.textlength(t + "…", font=fn) > largh:
            t = t[:-1]
        nome_righe = [t + "…"]
    h_riga = fn.size + 3
    y = max(2, (testa - len(nome_righe) * h_riga - alto_f) // 2)
    for r in nome_righe:
        d.text((tx, y), r, font=fn, fill=0)
        y += h_riga
    for r in righe_f:
        d.text((tx, y + 2), r, font=fp, fill=0)
        y += h_f
    buf = io.BytesIO()
    im.point(lambda v: 0 if v < 128 else 255).convert("1").save(buf, "PNG")
    return buf.getvalue()
