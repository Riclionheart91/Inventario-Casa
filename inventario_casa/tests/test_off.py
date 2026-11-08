import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.off import Off, progetto_per, valido_per_off
from app.service import Inventory
from app.store import MemoryStore


def inv():
    return Inventory(MemoryStore({
        "prodotti": [["Barcode", "Prodotto", "Marca", "Confezione", "Categoria", "Sottocategoria", "Tipo", "Immagine"],
                     [8002795002995, "Latte UHT", "Granarolo", "1 l", "Dispensa", "Bevande", "Latte", ""],
                     [8001234567890, "Crocchette gatto", "Miglior", "1,5 kg", "Animali", "Gatto", "Crocchette", ""],
                     [8009876543210, "Detersivo piatti", "Svelto", "750 ml", "Casa", "Pulizia", "Detersivo", ""],
                     [2012345678905, "Prosciutto al banco", "", "", "Frigorifero", "Salumi", "Prosciutto", ""],
                     [123, "Codice interno", "", "", "Dispensa", "Bevande", "", ""]],
        "categorie": [["Categoria", "Sottocategoria"], ["Dispensa", "Bevande"]]}))


class Finto:
    """Server Open*Facts finto: conosce solo il latte; registra le richieste."""
    def __init__(self, presenti=("8002795002995",), rifiuta=False):
        self.presenti, self.rifiuta, self.chiamate = set(presenti), rifiuta, []

    def __call__(self, metodo, url, campi=None, file=None, agent="", timeout=0):
        self.chiamate.append((metodo, url, campi, file))
        if "/api/v2/product/" in url:
            c = url.split("/product/")[1].split(".json")[0]
            return (200, {"status": 1}) if c in self.presenti else (404, {"status": 0})
        if url.endswith("product_jqm2.pl"):
            return (200, {"status": 0, "status_verbose": "utente errato"}) if self.rifiuta else (200, {"status": 1, "status_verbose": "fields saved"})
        if url.endswith("product_image_upload.pl"):
            return 200, {"status": "status ok", "imgid": 1}
        return 500, None


def crea(http=None, utente="u", password="segreta"):
    d = tempfile.mkdtemp()
    return Off(inv(), utente, password, percorso=os.path.join(d, "s.json"), cartella=os.path.join(d, "foto"), http=http or Finto(), pausa=0)


class TProgetti(unittest.TestCase):
    def test_progetto(self):
        self.assertEqual(progetto_per({"categoria": "Animali", "sottocategoria": "Gatto", "nome": "Crocchette"}), "pet")
        self.assertEqual(progetto_per({"categoria": "Casa", "sottocategoria": "Pulizia", "nome": "Detersivo piatti"}), "products")
        self.assertEqual(progetto_per({"categoria": "Igiene", "nome": "Shampoo"}), "beauty")
        self.assertEqual(progetto_per({"categoria": "Dispensa", "sottocategoria": "Bevande", "nome": "Latte"}), "food")

    def test_codici_validi(self):
        self.assertTrue(valido_per_off("8002795002995"))
        self.assertEqual(valido_per_off("2012345678905"), "")   # codice interno del banco
        self.assertEqual(valido_per_off("123"), "")


class TOff(unittest.TestCase):
    def test_controllo_e_elenco(self):
        h = Finto(); o = crea(h)
        o.controlla()
        nomi = [p["nome"] for p in o.elenco()]
        self.assertEqual(sorted(nomi), ["Crocchette gatto", "Detersivo piatti"])   # il latte c'e gia, i codici interni sono saltati
        self.assertEqual({p["nome"]: p["progetto"] for p in o.elenco()}["Crocchette gatto"], "pet")
        n = len(h.chiamate); o.controlla()
        self.assertEqual(len(h.chiamate), n)   # niente ricontrolli

    def test_invio_con_foto_e_stato(self):
        h = Finto(); o = crea(h)
        o.controlla()
        self.assertTrue(o.salva_foto("8001234567890", b"jpgdata", "image/jpeg"))
        r = o.invia([{"barcode": "8001234567890", "progetto": "pet"}])
        self.assertTrue(r[0]["ok"], r)
        invio = [c for c in h.chiamate if c[1].endswith("product_jqm2.pl")][0]
        self.assertTrue(invio[1].startswith("https://world.openpetfoodfacts.org"))
        self.assertEqual((invio[2]["code"], invio[2]["product_name"], invio[2]["brands"]), ("8001234567890", "Crocchette gatto", "Miglior"))
        self.assertTrue(any(c[1].endswith("product_image_upload.pl") and c[3][0] == "imgupload_front" for c in h.chiamate))
        self.assertIsNone(o.foto_file("8001234567890"))   # foto tolta dopo l'invio
        self.assertNotIn("Crocchette gatto", [p["nome"] for p in o.elenco()])

    def test_rifiuto_resta_in_elenco_e_password_non_trapela(self):
        o = crea(Finto(rifiuta=True)); o.controlla()
        r = o.invia([{"barcode": "8009876543210", "progetto": "products"}])
        self.assertFalse(r[0]["ok"])
        self.assertNotIn("segreta", str(r))
        self.assertIn("Detersivo piatti", [p["nome"] for p in o.elenco()])

    def test_ignora_non_torna_piu(self):
        o = crea(); o.controlla()
        o.salva_foto("8009876543210", b"x", "image/png")
        o.ignora(["8009876543210"])
        self.assertNotIn("Detersivo piatti", [p["nome"] for p in o.elenco()])
        self.assertIsNone(o.foto_file("8009876543210"))
        o.controlla()   # nemmeno un nuovo controllo lo riporta
        self.assertNotIn("Detersivo piatti", [p["nome"] for p in o.elenco()])

    def test_senza_credenziali_non_invia(self):
        o = crea(utente="", password="")
        with self.assertRaises(ValueError):
            o.invia([{"barcode": "8001234567890"}])

    def test_gia_presente_al_momento_dell_invio(self):
        h = Finto(); o = crea(h); o.controlla()
        h.presenti.add("8001234567890")   # nel frattempo l'ha aggiunto qualcun altro
        r = o.invia([{"barcode": "8001234567890", "progetto": "pet"}])
        self.assertIn("già", r[0]["messaggio"])
        self.assertFalse([c for c in h.chiamate if c[1].endswith("product_jqm2.pl")])

    def test_cambia_progetto(self):
        o = crea(); o.controlla()
        o.cambia_progetto("8009876543210", "beauty")
        self.assertEqual({p["nome"]: p["progetto"] for p in o.elenco()}["Detersivo piatti"], "beauty")


if __name__ == "__main__":
    unittest.main()
