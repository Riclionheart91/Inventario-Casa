"""Effetti delle impostazioni sui dati automatici: approvazione automatica delle proposte molto sicure.
(Le altre impostazioni dati — avvisi, giro notturno, revisione, siti Open Food Facts — vivono nei rispettivi moduli.)"""
import logging
from typing import Callable, Optional

# Approvazione automatica: SOLO le proposte sul singolo prodotto (genere «P»: nome, categoria, sottocategoria, tipo di UN prodotto).
# Sono reversibili (ogni cambio finisce in log_ai con fonte «AUTO», annullabile come le altre) e toccano una riga alla volta.
# Restano SEMPRE manuali: nuovi tipi (T: creano o uniscono tipi), categorie (C: rinominano/uniscono su tutto il catalogo) e voci di
# revisione (R: possono unire o eliminare). Mai in sola lettura.
GENERI_AUTO = ("P",)


def auto_approva(inv, soglia: int, sola_lettura: Callable[[], bool], massimo: int = 50) -> dict:
    """Applica da sola le proposte di prodotto con sicurezza >= soglia. Ritorna {applicate, saltate}."""
    if sola_lettura():
        return {"applicate": 0, "saltate": 0, "motivo": "sola lettura"}
    ok = ko = 0
    for a in inv.approvazioni():
        if ok + ko >= massimo:
            break
        if a.get("genere") not in GENERI_AUTO or a.get("sicurezza") is None or a["sicurezza"] < soglia:
            continue
        try:
            inv.decidi(a["id"], "APPROVA", None, fonte="AUTO")
            ok += 1
        except Exception:
            ko += 1
            logging.getLogger("inventario").warning("approvazione automatica non riuscita: %s", a.get("id"))
    return {"applicate": ok, "saltate": ko}


def registra(app, ctx) -> None:   # nessun endpoint: l'approvazione automatica gira nel ciclo notturno
    return None
