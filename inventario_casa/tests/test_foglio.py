import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.foglio import piano, COLONNE


class T(unittest.TestCase):
    def test_piano_ordina_nasconde_e_non_cancella(self):
        meta = {t: {"id": i, "hidden": False} for i, t in enumerate(["prodotti", "movimenti", "Stock_ByLoc", "ai_tipi"])}
        h = ["ID_Movimento", "Data", "Barcode", "Tipo", "Quantità", "Note", "Location", "Prodotto", "Categoria", "Sottocategoria", "ID_INGRESSO", "Scadenza"]
        rq, nota = piano(meta, {"movimenti": h, "prodotti": ["Barcode", "Prodotto"], "ai_tipi": ["Tipo", "Scorta_min", "Stato"]})
        chiavi = {k for r in rq for k in r}
        self.assertNotIn("deleteDimension", chiavi); self.assertNotIn("deleteSheet", chiavi)
        for r in rq:   # simulazione dell'ordine finale delle colonne di movimenti
            m = r.get("moveDimension")
            if m and m["source"]["sheetId"] == 1:
                h.insert(m["destinationIndex"], h.pop(m["source"]["startIndex"]))
        self.assertEqual(h[:6], ["ID_Movimento", "Data", "Barcode", "Prodotto", "Tipo", "Quantità"])
        self.assertLess(h.index("Scadenza"), h.index("Note"))
        nasc = [r["updateSheetProperties"]["properties"] for r in rq if "updateSheetProperties" in r and r["updateSheetProperties"]["properties"].get("hidden") is True]
        self.assertEqual([p["sheetId"] for p in nasc], [2])   # solo Stock_ByLoc
        self.assertTrue(any("setDataValidation" in r for r in rq))


class TProfondo(unittest.TestCase):
    def test_pulizia_archivia_righe_chiuse_e_completa_elenchi(self):
        from app.foglio import piano_pulizia, _intervalli
        dati = {
            "bozze": (["ID", "Stato"], [["a", "INSERITA"], ["b", "PRONTA"], ["c", "SCARTATA"], ["d", "INSERITA"]]),
            "ai_prodotti": (["Barcode", "Stato"], [[1, "NESSUNA_MODIFICA"], [2, "DA_APPROVARE"]]),
            "prodotti": (["Barcode", "Categoria", "Sottocategoria", "Tipo"], [[1, "Casa", "Superfici", "Sgrassatore"], [2, "Cibo", "Pasta", "pasta"]]),
            "categorie": (["Categoria", "Sottocategoria"], [["Cibo", "Pasta"]]),
            "ai_tipi": (["Tipo", "Scorta_min", "Stato"], [["Pasta", 2, "APPROVATO"], ["Sgrassatore", 0, "RIFIUTATO"]]),
        }
        r = piano_pulizia(dati, "01/11/2026")
        self.assertEqual(r["elimina"], {"bozze": [2, 4, 5], "ai_prodotti": [2]})
        self.assertEqual(len(r["archivio"]), 4)
        self.assertEqual(r["nuove_categorie"], [("Casa", "Superfici")])
        self.assertEqual(r["nuovi_tipi"], ["Sgrassatore"])   # quello rifiutato non conta come esistente; «pasta» c'e gia (senza badare alle maiuscole)
        self.assertEqual(_intervalli([2, 4, 5]), [(3, 5), (1, 2)])   # dal fondo verso l'alto

    def test_piano_profondo_elimina_i_fogli_calcolati_e_le_colonne_morte(self):
        meta = {t: {"id": i, "hidden": False} for i, t in enumerate(["prodotti", "movimenti", "Stock_ByLoc", "FALLBACK_SOURCES"])}
        rq, _ = piano(meta, {"prodotti": ["Barcode", "Prodotto", "Quantità", "Tipo"], "movimenti": ["ID_Movimento", "Barcode", "ID_INGRESSO"]}, profondo=True)
        self.assertEqual([r["deleteSheet"]["sheetId"] for r in rq if "deleteSheet" in r], [2])   # FALLBACK_SOURCES ha dati: resta (nascosto)
        self.assertEqual(sum(1 for r in rq if "deleteDimension" in r), 2)
