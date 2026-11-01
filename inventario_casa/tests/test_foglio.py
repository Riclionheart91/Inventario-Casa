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
