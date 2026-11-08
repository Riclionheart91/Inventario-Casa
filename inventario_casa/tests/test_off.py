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


def crea_arr(arr, http=None):
    d = tempfile.mkdtemp()
    return Off(inv(), "u", "segreta", percorso=os.path.join(d, "s.json"), cartella=os.path.join(d, "foto"), http=http or Finto(), pausa=0,
               arricchisci=arr, dati_percorso=os.path.join(d, "d.json"))


SCHEDA = {"nome": "Croccantini gatto sterilizzato", "marca": "Miglior Gatto", "confezione": "1,5 kg", "ingredienti": "Pollo, riso", "allergeni": "",
          "n_energia_kcal": "350", "n_grassi": "12", "fonte": "ricerca web", "immagine_web": "https://x/i.jpg"}


class TArricchimento(unittest.TestCase):
    def test_arricchisce_nome_marca_e_manca(self):
        o = crea_arr(lambda p: dict(SCHEDA)); o.controlla()
        prima = [x for x in o.elenco() if x["barcode"] == "8001234567890"][0]
        self.assertIn("ingredienti", prima["manca"])
        sc = o.arricchisci_uno("8001234567890")
        self.assertEqual((sc["campi"]["nome"], sc["campi"]["marca"], sc["campi"]["ingredienti"]), ("Croccantini gatto sterilizzato", "Miglior Gatto", "Pollo, riso"))
        self.assertTrue(sc["arricchito"])
        self.assertEqual(sc["immagine_web"], "https://x/i.jpg")
        dopo = [x for x in o.elenco() if x["barcode"] == "8001234567890"][0]
        self.assertEqual(dopo["nome"], "Croccantini gatto sterilizzato")
        self.assertNotIn("marca", dopo["manca"])
        self.assertIn("foto", dopo["manca"])

    def test_correzione_a_mano_resiste_all_arricchimento(self):
        o = crea_arr(lambda p: dict(SCHEDA)); o.controlla()
        o.salva_campi("8001234567890", {"nome": "Il mio nome", "marca": ""})
        sc = o.arricchisci_uno("8001234567890")
        self.assertEqual(sc["campi"]["nome"], "Il mio nome")
        self.assertIn("nome", sc["modificati"])
        self.assertEqual(sc["campi"]["marca"], "Miglior Gatto")   # la marca non era stata toccata

    def test_invio_manda_i_campi_arricchiti(self):
        h = Finto(); o = crea_arr(lambda p: dict(SCHEDA, n_sale="1.2"), h); o.controlla()
        o.arricchisci_uno("8001234567890")
        o.invia([{"barcode": "8001234567890", "progetto": "pet"}])
        c = [x for x in h.chiamate if x[1].endswith("product_jqm2.pl")][0][2]
        self.assertEqual((c["product_name"], c["brands"], c["quantity"], c["ingredients_text"]), ("Croccantini gatto sterilizzato", "Miglior Gatto", "1,5 kg", "Pollo, riso"))
        self.assertNotIn("nutriment_fat", c)   # i valori nutrizionali vanno solo su Open Food Facts (cibo)
        self.assertNotIn("segreta", str(h.chiamate[-1][2].get("comment", "")))

    def test_nutrizione_per_il_cibo(self):
        h = Finto(); o = crea_arr(lambda p: dict(SCHEDA, nome="Latte intero", n_grassi="3,6"), h); o.controlla()
        o.arricchisci_uno("8002795002995")   # presente: non e nell'elenco, ma si puo inviare comunque la scheda? no: controllo sul catalogo
        h.presenti.clear()
        o.salva_campi("8002795002995", {"n_energia_kcal": "64", "n_grassi": "3,6"})
        o._imposta("8002795002995", "assente", "food")
        o.invia([{"barcode": "8002795002995"}])
        c = [x for x in h.chiamate if x[1].endswith("product_jqm2.pl")][0][2]
        self.assertEqual((c["nutrition_data_per"], c["nutriment_energy-kcal"], c["nutriment_energy-kcal_unit"], c["nutriment_fat"]), ("100g", "64", "kcal", "3.6"))

    def test_arricchimento_in_background_una_volta(self):
        n = []
        o = crea_arr(lambda p: n.append(p["barcode"]) or dict(SCHEDA)); o.controlla()
        self.assertEqual(o.arricchisci_elenco(pausa=0), 2)
        self.assertEqual(o.arricchisci_elenco(pausa=0), 0)
        self.assertEqual(len(n), 2)

    def test_fallimento_non_si_ripete_subito(self):
        o = crea_arr(lambda p: {}); o.controlla()
        self.assertEqual(o.arricchisci_elenco(pausa=0), 2)
        self.assertEqual(o.arricchisci_elenco(pausa=0), 0)   # riprovera dopo una settimana


class TRetro(unittest.TestCase):
    def crea(self, h=None):
        d = tempfile.mkdtemp()
        letto = []
        o = Off(inv(), "u", "segreta", percorso=os.path.join(d, "s.json"), cartella=os.path.join(d, "foto"), http=h or Finto(), pausa=0,
                arricchisci=lambda p: dict(SCHEDA, ingredienti="dal web"), dati_percorso=os.path.join(d, "d.json"),
                leggi_retro=lambda dati, mime, p: letto.append(dati) or {"ingredienti": "Pollo 40%, riso", "n_proteine": "30", "fonte": "x"})
        return o, letto

    def test_il_retro_vale_piu_del_web(self):
        o, letto = self.crea(); o.controlla()
        self.assertTrue(o.salva_foto("8001234567890", b"retrodata", "image/jpeg", "retro"))
        sc = o.arricchisci_uno("8001234567890")
        self.assertEqual(letto, [b"retrodata"])
        self.assertEqual((sc["campi"]["ingredienti"], sc["campi"]["n_proteine"], sc["campi"]["marca"]), ("Pollo 40%, riso", "30", "Miglior Gatto"))
        self.assertIn("foto del retro", sc["fonte"])
        self.assertTrue(sc["retro"])
        self.assertFalse(sc["foto"])   # fronte e retro sono foto distinte

    def test_invio_del_retro_e_pulizia(self):
        h = Finto(); o, _ = self.crea(h); o.controlla()
        o.salva_foto("8001234567890", b"f", "image/jpeg"); o.salva_foto("8001234567890", b"r", "image/jpeg", "retro")
        r = o.invia([{"barcode": "8001234567890", "progetto": "pet"}])
        self.assertIn("del retro caricata", r[0]["messaggio"])
        campi = [c[2]["imagefield"] for c in h.chiamate if c[1].endswith("product_image_upload.pl")]
        self.assertEqual(campi, ["front", "ingredients"])
        self.assertIsNone(o.foto_file("8001234567890")); self.assertIsNone(o.foto_file("8001234567890", "retro"))

    def test_ignora_toglie_entrambe_le_foto(self):
        o, _ = self.crea(); o.controlla()
        o.salva_foto("8001234567890", b"f", "image/jpeg"); o.salva_foto("8001234567890", b"r", "image/png", "retro")
        o.ignora(["8001234567890"])
        self.assertIsNone(o.foto_file("8001234567890", "retro"))


if __name__ == "__main__":
    unittest.main()
