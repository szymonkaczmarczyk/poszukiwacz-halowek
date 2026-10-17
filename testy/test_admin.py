import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from szukacz import admin as A
from szukacz import api

HASLO = "dlugie-haslo-administratora"


def klient(administrator):
    return TestClient(api.utworz(lambda *a: None, api.HOSTY + ["testserver"], Path("/nie-ma"), administrator))


class AdministratorTest(unittest.TestCase):
    def test_bez_logowania_nie_mozna_zmieniac_modeli(self):
        k = klient(A.Administrator(A.hash_hasla(HASLO)))
        self.assertEqual(k.get("/api/admin").json(), {"zalogowany": False, "skonfigurowany": True})
        self.assertEqual(k.post("/api/wlasne", json={"marka": "joma", "model": "Nowy model"}).status_code, 401)
        self.assertEqual(k.delete("/api/wlasne/joma/nowy-model").status_code, 401)

    def test_logowanie_ciastko_i_wylogowanie(self):
        k = klient(A.Administrator(A.hash_hasla(HASLO)))
        self.assertEqual(k.post("/api/admin/logowanie", json={"haslo": "zle"}).status_code, 401)
        odp = k.post("/api/admin/logowanie", json={"haslo": HASLO})
        self.assertEqual(odp.status_code, 200)
        ciastko = odp.headers["set-cookie"].lower()
        self.assertIn("httponly", ciastko)
        self.assertIn("samesite=strict", ciastko)
        self.assertNotIn(HASLO, ciastko)
        self.assertTrue(k.get("/api/admin").json()["zalogowany"])
        k.post("/api/admin/wylogowanie")
        self.assertFalse(k.get("/api/admin").json()["zalogowany"])

    def test_limit_prob_logowania(self):
        k = klient(A.Administrator(A.hash_hasla(HASLO)))
        kody = [k.post("/api/admin/logowanie", json={"haslo": f"zle-{i}"}).status_code for i in range(6)]
        self.assertEqual(kody, [401] * 5 + [429])
        self.assertEqual(k.post("/api/admin/logowanie", json={"haslo": HASLO}).status_code, 429)

    def test_bez_hasla_logowanie_jest_wylaczone(self):
        k = klient(A.Administrator(""))
        self.assertEqual(k.get("/api/admin").json(), {"zalogowany": False, "skonfigurowany": False})
        self.assertEqual(k.post("/api/admin/logowanie", json={"haslo": "cokolwiek"}).status_code, 503)

    def test_sesja_wygasa(self):
        czas = [1000.0]
        administrator = A.Administrator(A.hash_hasla(HASLO), zegar=lambda: czas[0])
        token = administrator.zaloguj(HASLO, "1.2.3.4")
        self.assertTrue(administrator.sprawdz(token))
        czas[0] += A.CZAS_SESJI + 1
        self.assertFalse(administrator.sprawdz(token))
        self.assertFalse(administrator.sprawdz("falszywy"))


if __name__ == "__main__":
    unittest.main()
