"""Emoji nei nomi di categorie e sottocategorie: ogni nome deve iniziare con un'emoji seguita da uno spazio (es. «🧺 Dispensa»)."""
import re

_EMO = r"[\U0001F000-\U0001FAFF☀-➿⬀-⯿←-⇿©®™]"
INIZIA = re.compile(r"^\s*(%s(?:‍%s)*[️⃣]*)\s*(.*)$" % (_EMO, _EMO), re.S)

PAROLE = [   # parola chiave -> emoji, per i nomi senza emoji (la prima che combacia)
    ("concim", "🌱"), ("terric", "🌱"), ("piant", "🪴"), ("giardin", "🪴"), ("orto", "🥕"), ("animal", "🐾"), ("pet", "🐾"),
    ("auto", "🚗"), ("bici", "🚲"), ("bimb", "🧸"), ("bambin", "🧸"), ("neonat", "🍼"), ("ufficio", "📎"), ("cancelleria", "📎"),
    ("ferrament", "🔧"), ("bricolage", "🔧"), ("fai da te", "🔧"), ("elettr", "🔌"), ("batter", "🔋"), ("farmac", "💊"), ("salute", "💊"),
    ("medic", "💊"), ("igiene", "🧼"), ("pulizi", "🧹"), ("bucato", "🧺"), ("cucina", "🍽️"), ("bevand", "🥤"), ("vino", "🍷"),
    ("birr", "🍺"), ("frutta", "🍎"), ("verdur", "🥦"), ("carne", "🥩"), ("pesce", "🐟"), ("dolc", "🍪"), ("snack", "🍪"),
    ("pane", "🍞"), ("pasta", "🍝"), ("surgel", "🧊"), ("fredd", "❄️"), ("sport", "🏐"), ("pallavolo", "🏐"), ("giocatt", "🧸"),
    ("viaggio", "🧳"), ("candel", "🕯️"), ("decor", "🖼️"), ("luce", "💡"), ("lampad", "💡"),
]


def ha_emoji(s) -> bool:
    return bool(INIZIA.match(str(s or "")))


def senza_emoji(s) -> str:
    m = INIZIA.match(str(s or "").strip())
    return (m.group(2) if m else str(s or "")).strip()


def con_emoji(nome, scelta: str = "") -> str:
    """«🧴Corpo» -> «🧴 Corpo»; «Giardino» -> «🪴 Giardino» (emoji scelta, oppure dedotta dalle parole, oppure 🔹)."""
    nome = re.sub(r"\s+", " ", str(nome or "")).strip()
    m = INIZIA.match(nome)
    if m:
        return ("%s %s" % (m.group(1), m.group(2).strip())).strip()
    sc = (scelta or "").strip()
    if not (sc and INIZIA.match(sc + " x")):
        low = nome.lower()
        sc = next((e for k, e in PAROLE if k in low), "🔹")
    return "%s %s" % (sc, nome)
