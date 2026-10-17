import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from szukacz import admin as A
from szukacz import api, katalog
from szukacz import profil as P
from szukacz import ustawienia as U
from szukacz.dopasowanie import model_profilu


class WlasneTest(unittest.TestCase):
    def setUp(self):
        self.katalog = tempfile.TemporaryDirectory()
        self.latka = mock.patch.object(U, "PLIK_WLASNYCH", Path(self.katalog.name) / "wlasne.json")
        self.latka.start()
        administrator = A.Administrator(A.hash_hasla("haslo-testowe-123"))
        self.klient = TestClient(api.utworz(lambda *a: None, api.HOSTY + ["testserver"], Path("/nie-ma"), administrator))
        self.assertEqual(self.klient.post("/api/admin/logowanie", json={"haslo": "haslo-testowe-123"}).status_code, 200)

    def tearDown(self):
        self.latka.stop()
        self.katalog.cleanup()

    def test_dodany_model_trafia_do_katalogu_i_dziala_jak_profil(self):
        odp = self.klient.post("/api/wlasne", json={"marka": "joma", "model": "Top Flex 2402", "wykluczenia": ["Rebound", "jr"]})
        self.assertEqual(odp.status_code, 201)
        self.assertEqual(odp.json(), {"marka": "joma", "model": "top-flex-2402"})
        dane = self.klient.get("/api/katalog").json()
        joma = next(m for m in dane["marki"] if m["id"] == "joma")
        nowy = next(m for m in joma["modele"] if m["id"] == "top-flex-2402")
        self.assertTrue(nowy["wlasny"])
        self.assertEqual(nowy["opis_wykluczen"], "bez: jr, rebound")
        P.ustaw(katalog.profil("joma", "top-flex-2402", "42"))
        self.assertEqual(model_profilu("Joma Top Flex 2402 IN")[0], "model")
        self.assertEqual(model_profilu("Joma Top Flex 2402 Rebound")[0], "wykluczony")
        self.assertEqual(model_profilu("Joma Top Flex 2402 TF")[0], "wykluczony")

    def test_nowa_marka_i_wymog_oznaczenia_hali(self):
        self.klient.post("/api/wlasne", json={"marka": "Kelme", "model": "Precision", "wymagaj_oznaczenia_hali": False})
        dane = self.klient.get("/api/katalog").json()
        self.assertIn("kelme", [m["id"] for m in dane["marki"]])
        self.assertEqual(katalog.profil("kelme", "precision").marka, "Kelme")
        self.klient.post("/api/wlasne", json={"marka": "nike", "model": "Premier 3", "wymagaj_oznaczenia_hali": False})
        self.assertEqual(katalog.profil("nike", "premier-3").oznaczenia_hali, [])
        self.klient.post("/api/wlasne", json={"marka": "nike", "model": "Zoom Vapor"})
        self.assertTrue(katalog.profil("nike", "zoom-vapor").oznaczenia_hali)

    def test_duplikaty_i_walidacja(self):
        self.assertEqual(self.klient.post("/api/wlasne", json={"marka": "munich", "model": "Continental"}).status_code, 409)
        self.klient.post("/api/wlasne", json={"marka": "munich", "model": "Mundial Pro"})
        self.assertEqual(self.klient.post("/api/wlasne", json={"marka": "munich", "model": "mundial pro"}).status_code, 409)
        zle = [
            {"marka": "munich", "model": "x"},
            {"marka": "munich", "model": "<script>"},
            {"marka": "munich", "model": "Ok model", "wykluczenia": ["(a|b)+"]},
            {"marka": "munich", "model": "Ok model", "rola": "admin"},
            {"marka": "munich", "model": "Ok model", "wykluczenia": [str(i) for i in range(16)]},
        ]
        for zapytanie in zle:
            self.assertEqual(self.klient.post("/api/wlasne", json=zapytanie).status_code, 422, zapytanie)

    def test_usuwanie_tylko_wlasnych(self):
        self.klient.post("/api/wlasne", json={"marka": "mizuno", "model": "Vitoria"})
        self.assertEqual(self.klient.delete("/api/wlasne/mizuno/vitoria").status_code, 204)
        self.assertEqual(self.klient.delete("/api/wlasne/mizuno/vitoria").status_code, 404)
        self.assertEqual(self.klient.delete("/api/wlasne/munich/continental").status_code, 404)
        self.assertEqual(self.klient.get("/api/wlasne").json(), [])


if __name__ == "__main__":
    unittest.main()
