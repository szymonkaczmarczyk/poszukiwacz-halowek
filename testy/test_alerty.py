import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from fastapi.testclient import TestClient

from szukacz import admin as A
from szukacz import alerty, api, powiadomienia
from szukacz import ustawienia as U
from szukacz.blokada import BlokadaPliku


def oferta(klucz, cena, tytul="Joma Top Flex 42"):
    return {"klucz": klucz, "url": klucz, "tytul": tytul, "zrodlo": "Vinted", "suma_pln": cena}


def wpis(rozmiar="42", oferty=(), max_cena=None):
    return {"marka": "joma", "model": "top-flex", "nazwa": "Joma Top Flex", "rozmiar": rozmiar, "max_cena": max_cena, "tylko_pewne": False, "oferty": list(oferty)}


class ZPlikami(unittest.TestCase):
    def setUp(self):
        self.katalog = tempfile.TemporaryDirectory()
        sciezka = Path(self.katalog.name)
        for nazwa, plik in (("PLIK_ALERTOW", "alerty.json"), ("PLIK_BLOKADY_WYSZUKIWANIA", "wyszukiwanie.lock")):
            latka = mock.patch.object(U, nazwa, sciezka / plik)
            latka.start()
            self.addCleanup(latka.stop)
        self.addCleanup(self.katalog.cleanup)


class PorownanieTest(unittest.TestCase):
    def test_nowa_tansza_i_bez_zmian(self):
        alert = {"widziane": {"a": {"cena": 200.0, "kiedy": "2026-10-20 09:00"}, "b": {"cena": 150.0, "kiedy": "2026-10-20 09:00"}}}
        trafienia = alerty.porownaj(alert, [oferta("a", 170), oferta("b", 149.5), oferta("c", 120)], "2026-10-21 09:00")
        self.assertEqual([(t["klucz"], t["typ"], t["roznica"]) for t in trafienia], [("a", "tansza", 30.0), ("c", "nowa", None)])
        self.assertEqual(alert["widziane"]["a"]["cena"], 170.0)

    def test_podwyzka_i_powrot_nie_daja_alertu(self):
        alert = {"widziane": {"a": {"cena": 200.0, "kiedy": "2026-10-20 09:00"}}}
        self.assertEqual(alerty.porownaj(alert, [oferta("a", 260)], "2026-10-20 15:00"), [])
        self.assertEqual(alerty.porownaj(alert, [oferta("a", 210)], "2026-10-20 21:00"), [])
        self.assertEqual(alert["widziane"]["a"]["cena"], 200.0)

    def test_oferty_bez_rozpoznanego_modelu_sa_pomijane(self):
        alert = {"widziane": {}}
        trafienia = alerty.porownaj(alert, [{**oferta("a", 100), "grupa": "weryfikacja"}, {**oferta("b", 150), "grupa": "rozmiar"}], "2026-10-21 09:00")
        self.assertEqual([t["klucz"] for t in trafienia], ["b"])
        self.assertNotIn("a", alert["widziane"])

    def test_stare_wpisy_sa_zapominane(self):
        alert = {"widziane": {"stara": {"cena": 100.0, "kiedy": "2026-08-01 09:00"}, "swieza": {"cena": 100.0, "kiedy": "2026-10-01 09:00"}}}
        alerty.porownaj(alert, [], "2026-10-21 09:00")
        self.assertEqual(set(alert["widziane"]), {"swieza"})


class ZapisTest(ZPlikami):
    def test_dodanie_zapamietuje_ostatnie_wyniki_i_pomija_duplikaty(self):
        dodane, pominiete = alerty.dodaj([wpis("42", [oferta("a", 200)]), wpis("43")])
        self.assertEqual([a["rozmiar"] for a in dodane], ["42", "43"])
        self.assertEqual(pominiete, [])
        self.assertNotIn("widziane", dodane[0])
        self.assertIn("a", alerty.wczytaj()[0]["widziane"])
        dodane, pominiete = alerty.dodaj([wpis("42"), wpis("42", max_cena=300)])
        self.assertEqual([a["max_cena"] for a in dodane], [300])
        self.assertEqual(pominiete, ["42"])

    def test_limit_alertow(self):
        alerty.dodaj([wpis(str(r), max_cena=c) for r in range(38, 42) for c in (100, 200, 300, 400, 500)])
        with self.assertRaises(alerty.BladAlertow) as blad:
            alerty.dodaj([wpis("46")])
        self.assertEqual(blad.exception.kod, 409)
        self.assertEqual(len(alerty.wczytaj()), alerty.MAKS_ALERTOW)

    def test_usuwanie_i_przeczytane(self):
        (alert,), _ = alerty.dodaj([wpis()])
        self.assertFalse(alerty.usun("nie-ma"))
        self.assertTrue(alerty.usun(alert["id"]))
        self.assertEqual(alerty.lista(), [])


class SprawdzanieTest(ZPlikami):
    def wynik(self, oferty, status="ok"):
        return SimpleNamespace(dane={"oferty": oferty, "zrodla": [{"nazwa": "Vinted", "status": status}]})

    def test_powiadamia_tylko_o_zmianach(self):
        alerty.dodaj([wpis("42", [oferta("a", 200)])])
        wyslane = []
        opcje_wyszukiwania = []

        def wykonaj(profil, opcje):
            opcje_wyszukiwania.append(opcje)
            return self.wynik([oferta("a", 180), oferta("b", 250)])

        raport = alerty.sprawdz_wszystkie(wykonaj, lambda alert, t: wyslane.append(t) or {"Mac": "wysłano"}, lambda tekst: None)
        self.assertEqual(raport[0]["trafienia"], 2)
        self.assertEqual(sorted(t["typ"] for t in wyslane[0]), ["nowa", "tansza"])
        self.assertTrue(opcje_wyszukiwania[0].odswiez)
        self.assertEqual(opcje_wyszukiwania[0].rozmiar, "42")
        opis = alerty.lista()[0]
        self.assertEqual(opis["stan"], "ok")
        self.assertEqual(opis["nowych"], 0)
        self.assertEqual(len(opis["trafienia"]), 2)

        wyslane.clear()
        alerty.sprawdz_wszystkie(wykonaj, lambda alert, t: wyslane.append(t) or {}, lambda tekst: None)
        self.assertEqual(wyslane, [])

    def test_awaria_zrodel_nie_zmienia_widzianych(self):
        alerty.dodaj([wpis("42", [oferta("a", 200)])])
        alerty.sprawdz_wszystkie(lambda p, o: self.wynik([], status="błąd"), lambda a, t: self.fail("bez powiadomień"), lambda tekst: None)
        alert = alerty.wczytaj()[0]
        self.assertIn("a", alert["widziane"])
        self.assertIn("żadne źródło", alert["stan"])

    def test_czeka_na_wyszukiwanie_z_przegladarki(self):
        blokada = BlokadaPliku(U.PLIK_BLOKADY_WYSZUKIWANIA)
        self.assertTrue(blokada.zajmij())
        self.assertFalse(BlokadaPliku(U.PLIK_BLOKADY_WYSZUKIWANIA).zajmij())
        blokada.zwolnij()
        nastepna = BlokadaPliku(U.PLIK_BLOKADY_WYSZUKIWANIA)
        self.assertTrue(nastepna.zajmij())
        nastepna.zwolnij()


class TrescPowiadomieniaTest(unittest.TestCase):
    def test_tresc_z_linkami_i_odmiana(self):
        trafienia = [alerty._trafienie(oferta(f"https://example.com/{i}", 100 + i), "nowa", None, "2026-10-21 09:00") for i in range(6)]
        trafienia.append(alerty._trafienie(oferta("https://example.com/t", 90), "tansza", 30, "2026-10-21 09:00"))
        tytul, krotko, dlugo = powiadomienia.tresc({"nazwa": "Joma Top Flex", "rozmiar": "42"}, trafienia)
        self.assertEqual(tytul, "Szatnia: Joma Top Flex, rozmiar 42")
        self.assertEqual(krotko, "6 nowych ofert, 1 tańsza. Najtańsza: 90 zł (Vinted).")
        self.assertIn("90 zł · Vinted · Joma Top Flex 42 (taniej o 30 zł)\nhttps://example.com/t", dlugo)
        self.assertIn("I 2 kolejne na stronie alertów", dlugo)


class ApiAlertowTest(ZPlikami):
    def setUp(self):
        super().setUp()
        administrator = A.Administrator(A.hash_hasla("haslo-testowe-123"))
        self.klient = TestClient(api.utworz(lambda *a: None, api.HOSTY + ["testserver"], Path("/nie-ma"), administrator))

    def zaloguj(self):
        self.assertEqual(self.klient.post("/api/admin/logowanie", json={"haslo": "haslo-testowe-123"}).status_code, 200)

    def test_tylko_dla_administratora(self):
        self.assertEqual(self.klient.get("/api/alerty").status_code, 401)
        self.assertEqual(self.klient.post("/api/alerty", json={"marka": "joma", "model": "top-flex", "rozmiary": ["42"]}).status_code, 401)
        self.assertEqual(self.klient.delete("/api/alerty/abc").status_code, 401)

    def test_dodanie_lista_i_usuniecie(self):
        self.zaloguj()
        odpowiedz = self.klient.post("/api/alerty", json={"marka": "Joma", "model": "Top Flex", "rozmiary": ["43", "42", "42"], "max_cena": 300})
        self.assertEqual(odpowiedz.status_code, 201)
        dane = odpowiedz.json()
        self.assertEqual([a["rozmiar"] for a in dane["dodane"]], ["42", "43"])
        self.assertEqual(dane["dodane"][0]["marka"], "joma")
        self.assertEqual(dane["dodane"][0]["nazwa"], "Joma Top Flex")
        self.assertEqual(self.klient.post("/api/alerty", json={"marka": "joma", "model": "top-flex", "rozmiary": ["42"], "max_cena": 300}).status_code, 409)
        lista = self.klient.get("/api/alerty").json()
        self.assertEqual(len(lista["alerty"]), 2)
        self.assertEqual(lista["godziny"], list(U.GODZINY_ALERTOW))
        self.assertIn("telegram", lista["kanaly"])
        self.assertEqual(self.klient.post("/api/alerty/przeczytane").status_code, 200)
        self.assertEqual(self.klient.delete(f"/api/alerty/{dane['dodane'][0]['id']}").status_code, 204)
        self.assertEqual(self.klient.delete(f"/api/alerty/{dane['dodane'][0]['id']}").status_code, 404)

    def test_walidacja(self):
        self.zaloguj()
        for zle in (
            {"marka": "joma", "model": "top-flex", "rozmiary": ["50"]},
            {"marka": "joma", "model": "top-flex", "rozmiary": []},
            {"marka": "joma", "model": "top-flex", "rozmiary": ["42"], "max_cena": -5},
            {"marka": "joma", "model": "top-flex", "rozmiary": ["42"], "id": "x"},
        ):
            self.assertEqual(self.klient.post("/api/alerty", json=zle).status_code, 422, zle)
        self.assertEqual(self.klient.post("/api/alerty", json={"marka": "joma", "model": "nie-ma", "rozmiary": ["42"]}).status_code, 404)

    def test_wyszukiwanie_czeka_gdy_alerty_sprawdzaja_sie_w_tle(self):
        blokada = BlokadaPliku(U.PLIK_BLOKADY_WYSZUKIWANIA)
        blokada.zajmij()
        self.addCleanup(blokada.zwolnij)
        odpowiedz = self.klient.post("/api/wyszukiwania", json={"marka": "joma", "model": "top-flex", "rozmiary": ["42"]})
        self.assertEqual(odpowiedz.status_code, 409)
        self.assertIn("alertów", odpowiedz.json()["detail"])
