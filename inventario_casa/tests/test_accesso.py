import asyncio, tempfile, unittest
from app.accesso import Accesso, ritorno_sicuro, COOKIE

def chiama(acc, method, path, ip="192.168.1.5", cookie="", corpo=b"", qs=b""):
    out = {}
    async def inner(scope, receive, send):
        out["app"] = True
        await send({"type": "http.response.start", "status": 200, "headers": []}); await send({"type": "http.response.body", "body": b"ok"})
    mw = acc.middleware(inner)
    h = [(b"cookie", cookie.encode())] if cookie else []
    scope = {"type": "http", "method": method, "path": path, "query_string": qs, "headers": h, "client": (ip, 1), "scheme": "http"}
    async def receive(): return {"type": "http.request", "body": corpo, "more_body": False}
    async def send(m):
        if m["type"] == "http.response.start": out["st"] = m["status"]; out["h"] = dict(m["headers"])
    asyncio.run(mw(scope, receive, send))
    return out

class T(unittest.TestCase):
    def setUp(self):
        self.t = [1000.0]; self.cod = "famiglia"
        self.a = Accesso(lambda: self.cod, tempfile.mkdtemp(), lambda: self.t[0])
    def login(self, c="famiglia", ip="192.168.1.5"):
        return chiama(self.a, "POST", "/accesso", ip=ip, corpo=("codice=%s&ricorda=1&ritorno=/x" % c).encode())
    def test_ingress_senza_codice(self):
        self.assertTrue(chiama(self.a, "GET", "/api/stock", ip="172.30.32.2").get("app"))
    def test_diretto_spento_senza_codice(self):
        self.cod = ""
        self.assertEqual(chiama(self.a, "GET", "/").get("st"), 403)
        self.assertEqual(chiama(self.a, "GET", "/api/stock").get("st"), 403)
    def test_senza_sessione(self):
        self.assertEqual(chiama(self.a, "GET", "/api/stock").get("st"), 401)
        r = chiama(self.a, "GET", "/"); self.assertEqual(r["st"], 303)
        self.assertTrue(r["h"][b"location"].startswith(b"/accesso"))
    def test_login_e_sessione(self):
        r = self.login(); self.assertEqual(r["st"], 303); self.assertEqual(r["h"][b"location"], b"/x")
        ck = r["h"][b"set-cookie"].decode().split(";")[0]
        self.assertTrue(chiama(self.a, "GET", "/api/stock", cookie=ck).get("app"))
        self.cod = "nuovo"
        self.assertEqual(chiama(self.a, "GET", "/api/stock", cookie=ck).get("st"), 401)
    def test_scadenza(self):
        ck = self.login()["h"][b"set-cookie"].decode().split(";")[0]
        self.t[0] += 91 * 24 * 3600
        self.assertEqual(chiama(self.a, "GET", "/api/stock", cookie=ck).get("st"), 401)
    def test_cookie_falso(self):
        self.assertEqual(chiama(self.a, "GET", "/api/stock", cookie=COOKIE + "=9999999999.ab.cd").get("st"), 401)
    def test_blocco(self):
        for _ in range(5): self.assertEqual(self.login("no")["st"], 401)
        self.assertEqual(self.login("famiglia")["st"], 401)
        self.t[0] += 16 * 60
        self.assertEqual(self.login("famiglia")["st"], 303)
        self.assertEqual(self.login("no", ip="10.0.0.9")["st"], 401)
    def test_pubblici(self):
        self.assertTrue(chiama(self.a, "GET", "/manifest.json").get("app"))
        self.assertEqual(chiama(self.a, "GET", "/accesso").get("st"), 200)
    def test_ritorno(self):
        for x in ["//evil.com", "http://evil.com", "/\\evil", "", "/accesso", "x"]: self.assertEqual(ritorno_sicuro(x), "/")
        self.assertEqual(ritorno_sicuro("/?a=1"), "/?a=1")
    def test_esci(self):
        r = chiama(self.a, "GET", "/esci"); self.assertEqual(r["st"], 303); self.assertIn(b"Max-Age=0", r["h"][b"set-cookie"])
if __name__ == "__main__": unittest.main()
