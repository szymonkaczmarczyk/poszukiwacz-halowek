import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from szukacz import api, przebieg

HOSTY = api.HOSTY + ["testserver"]


def udawane_wykonaj(profil, opcje, sluchacz):
    rozmiar = opcje.rozmiar
    sluchacz("start", {"rozmiar": rozmiar, "nazwa": profil.nazwa, "zrodla": ["Vinted"]})
    sluchacz("zrodlo_start", {"rozmiar": rozmiar, "zrodlo": "Vinted"})
    sluchacz("log", {"rozmiar": rozmiar, "zrodlo": "Vinted", "tekst": "gotowe"})
    oferta = {"tytul": f"{profil.nazwa} {rozmiar}", "suma_pln": 199.0, "grupa": "pewne", "klucz": f"https://example.com/{rozmiar}"}
    sluchacz("zrodlo_koniec", {"rozmiar": rozmiar, "nazwa": "Vinted", "status": "ok", "oferty": [oferta]})
    sluchacz("koniec", {"rozmiar": rozmiar, "czas": 0.1, "wyniki": {"rozmiar": rozmiar, "oferty": [oferta]}})


def zdarzenia_sse(tekst):
    return [json.loads(linia[6:]) for linia in tekst.splitlines() if linia.startswith("data: ")]


class ApiTest(unittest.TestCase):
    def klient(self, wykonaj=udawane_wykonaj):
        return TestClient(api.utworz(wykonaj, HOSTY, Path("/nie-ma-interfejsu")))

    def test_katalog(self):
        dane = self.klient().get("/api/katalog").json()
        self.assertEqual(dane["rozmiary"][0], "38")
        self.assertEqual(dane["rozmiary"][-1], "46")
        marki = {m["id"]: m for m in dane["marki"]}
        self.assertEqual(set(marki), {"adidas", "joma", "mizuno", "munich", "nike", "ortuseight"})
        self.assertIn("continental", [m["id"] for m in marki["munich"]["modele"]])

    def test_katalog_podaje_plik_3d_tylko_gdy_istnieje(self):
        with tempfile.TemporaryDirectory() as katalog:
            (Path(katalog) / "joma-top-flex.glb").write_bytes(b"glTF")
            with mock.patch.object(api.U, "KATALOG_MODELI_3D", Path(katalog)):
                dane = self.klient().get("/api/katalog").json()
        modele = {(m["id"], mo["id"]): mo["model3d"] for m in dane["marki"] for mo in m["modele"]}
        self.assertEqual(modele[("joma", "top-flex")], "/modele/joma-top-flex.glb")
        self.assertIsNone(modele[("munich", "continental")])

    def test_serwowanie_interfejsu_z_wlasna_strona_404(self):
        with tempfile.TemporaryDirectory() as katalog:
            (Path(katalog) / "index.html").write_text("<p>Szatnia</p>", encoding="utf-8")
            (Path(katalog) / "404.html").write_text("<p>Tej strony nie ma</p>", encoding="utf-8")
            k = TestClient(api.utworz(udawane_wykonaj, HOSTY, Path(katalog)))
            glowna = k.get("/")
            self.assertEqual(glowna.status_code, 200)
            self.assertIn("Szatnia", glowna.text)
            self.assertIn("frame-ancestors 'none'", glowna.headers["content-security-policy"])
            self.assertIn("connect-src 'self' blob:", glowna.headers["content-security-policy"])
            brak = k.get("/nie-ma-takiej-strony")
            self.assertEqual(brak.status_code, 404)
            self.assertIn("Tej strony nie ma", brak.text)
            api_brak = k.get("/api/nie-ma")
            self.assertEqual(api_brak.status_code, 404)
            self.assertEqual(api_brak.json()["detail"], "nie ma takiego adresu API")
            self.assertEqual(k.get("/api/katalog").status_code, 200)

    def test_zrodla_modelu(self):
        k = self.klient()
        zrodla = k.get("/api/katalog/joma/top-flex/zrodla").json()
        self.assertIn("Vinted", [z["nazwa"] for z in zrodla])
        self.assertEqual(k.get("/api/katalog/nike/gresca/zrodla").status_code, 404)

    def test_pelne_wyszukiwanie_ze_strumieniem(self):
        k = self.klient()
        odp = k.post("/api/wyszukiwania", json={"marka": "nike", "model": "phantom", "rozmiary": ["43", "41", "43"]})
        self.assertEqual(odp.status_code, 202)
        opis = odp.json()
        self.assertEqual(opis["rozmiary"], ["41", "43"])
        tekst = k.get(opis["zdarzenia"]).text
        zdarzenia = zdarzenia_sse(tekst)
        typy = [z["typ"] for z in zdarzenia]
        self.assertEqual(typy[0], "wyszukiwanie_start")
        self.assertEqual(typy[-1], "wyszukiwanie_koniec")
        self.assertEqual(typy.count("koniec"), 2)
        self.assertEqual([z["id"] for z in zdarzenia], list(range(len(zdarzenia))))
        self.assertIn("event: zrodlo_koniec", tekst)
        stan = k.get(f"/api/wyszukiwania/{opis['id']}").json()
        self.assertEqual(stan["stan"], "gotowe")
        self.assertEqual(sorted(stan["wyniki"]), ["41", "43"])

    def test_wznowienie_strumienia_od_ostatniego_zdarzenia(self):
        k = self.klient()
        opis = k.post("/api/wyszukiwania", json={"marka": "munich", "model": "continental", "rozmiary": ["41"]}).json()
        wszystkie = zdarzenia_sse(k.get(opis["zdarzenia"]).text)
        dalej = zdarzenia_sse(k.get(opis["zdarzenia"], headers={"Last-Event-ID": "3"}).text)
        self.assertEqual(dalej, wszystkie[4:])

    def test_tylko_jedno_wyszukiwanie_naraz(self):
        zwolnij = threading.Event()

        def wolne(profil, opcje, sluchacz):
            zwolnij.wait(5)
            udawane_wykonaj(profil, opcje, sluchacz)

        k = self.klient(wolne)
        zapytanie = {"marka": "joma", "model": "top-flex", "rozmiary": ["42"]}
        self.assertEqual(k.post("/api/wyszukiwania", json=zapytanie).status_code, 202)
        self.assertIsNotNone(k.get("/api/zdrowie").json()["aktywne"])
        self.assertEqual(k.post("/api/wyszukiwania", json=zapytanie).status_code, 409)
        zwolnij.set()

    def test_blad_silnika_konczy_wyszukiwanie(self):
        def bez_zrodel(profil, opcje, sluchacz):
            raise przebieg.BrakZrodel("nie wybrano żadnego dostępnego źródła")

        k = self.klient(bez_zrodel)
        opis = k.post("/api/wyszukiwania", json={"marka": "joma", "model": "top-flex", "rozmiary": ["42"], "zrodla": ["nic"]}).json()
        zdarzenia = zdarzenia_sse(k.get(opis["zdarzenia"]).text)
        self.assertEqual(zdarzenia[-2]["typ"], "blad")
        self.assertEqual(zdarzenia[-1]["dane"]["stan"], "blad")

    def test_walidacja_wejscia(self):
        k = self.klient()
        zle = [
            {"marka": "nike", "model": "phantom", "rozmiary": ["50"]},
            {"marka": "nike", "model": "phantom", "rozmiary": []},
            {"marka": "nike", "model": "phantom", "rozmiary": ["42"], "max_cena": -5},
            {"marka": "nike", "model": "phantom", "rozmiary": ["42"], "rola": "admin"},
        ]
        for zapytanie in zle:
            self.assertEqual(k.post("/api/wyszukiwania", json=zapytanie).status_code, 422, zapytanie)
        self.assertEqual(k.post("/api/wyszukiwania", json={"marka": "nike", "model": "gresca", "rozmiary": ["42"]}).status_code, 404)

    def test_obca_strona_i_obcy_host_sa_odrzucane(self):
        k = self.klient()
        self.assertEqual(k.get("/api/katalog", headers={"Origin": "https://zla-strona.example"}).status_code, 403)
        self.assertEqual(k.get("/api/katalog", headers={"Origin": "http://localhost:5190"}).status_code, 200)
        self.assertEqual(k.get("/api/katalog", headers={"Origin": "http://testserver"}).status_code, 200)
        self.assertEqual(k.get("/api/katalog", headers={"Origin": "http://testserver.zla-strona.example"}).status_code, 403)
        self.assertEqual(TestClient(api.utworz(udawane_wykonaj)).get("/api/katalog").status_code, 400)
        odp = k.get("/api/zdrowie")
        self.assertEqual(odp.headers["x-content-type-options"], "nosniff")

    def test_przerwanie_konczy_po_biezacym_rozmiarze(self):
        widziane = []

        def czekajace(profil, opcje, sluchacz):
            widziane.append(opcje.rozmiar)
            opcje.przerwanie.wait(5)
            udawane_wykonaj(profil, opcje, sluchacz)

        k = self.klient(czekajace)
        opis = k.post("/api/wyszukiwania", json={"marka": "joma", "model": "top-flex", "rozmiary": ["41", "42"]}).json()
        odp = k.post(f"/api/wyszukiwania/{opis['id']}/przerwij")
        self.assertEqual(odp.status_code, 202)
        zdarzenia = zdarzenia_sse(k.get(opis["zdarzenia"]).text)
        typy = [z["typ"] for z in zdarzenia]
        self.assertIn("przerywanie", typy)
        self.assertEqual(zdarzenia[-1]["dane"]["stan"], "przerwane")
        self.assertEqual(widziane, ["41"])
        self.assertEqual(k.post(f"/api/wyszukiwania/{opis['id']}/przerwij").status_code, 409)
        self.assertEqual(k.post("/api/wyszukiwania/nieznane/przerwij").status_code, 404)

    def test_przywracanie_ukrytej_oferty(self):
        k = self.klient()
        with mock.patch.object(api.ukryte, "usun", return_value=1) as usun:
            odp = k.post("/api/ukryte/przywroc", json={"url": "https://www.vinted.pl/items/1"})
        self.assertEqual(odp.json(), {"przywrocono": True})
        usun.assert_called_once()

    def test_ukrywanie_oferty(self):
        k = self.klient()
        with mock.patch.object(api.ukryte, "dodaj", return_value=["https://www.vinted.pl/items/1"]) as dodaj:
            odp = k.post("/api/ukryte", json={"url": "https://www.vinted.pl/items/1"})
        self.assertEqual(odp.json(), {"ukryto": True})
        dodaj.assert_called_once()
        self.assertEqual(k.post("/api/ukryte", json={"url": "javascript:alert(1)"}).status_code, 422)

    def test_ostatnie_wyniki_bez_danych(self):
        k = self.klient()
        self.assertEqual(k.get("/api/katalog/mizuno/morelia-sala/wyniki/39").status_code, 404)
        self.assertEqual(k.get("/api/katalog/mizuno/morelia-sala/wyniki/99").status_code, 404)


if __name__ == "__main__":
    unittest.main()
