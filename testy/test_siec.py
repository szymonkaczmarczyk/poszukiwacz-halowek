import tempfile
import threading
import time
import unittest
from pathlib import Path

from szukacz import ukryte
from szukacz.siec import Ogranicznik, Przerwano


class OgranicznikTest(unittest.TestCase):
    def test_przerwanie_zatrzymuje_czekanie_od_razu(self):
        with tempfile.TemporaryDirectory() as katalog:
            przerwanie = threading.Event()
            ogranicznik = Ogranicznik(Path(katalog) / "stan.json", przerwanie)
            threading.Timer(0.2, przerwanie.set).start()
            start = time.time()
            with self.assertRaises(Przerwano):
                ogranicznik.czekaj(30)
            self.assertLess(time.time() - start, 2)

    def test_po_przerwaniu_kolejka_nie_wpuszcza_zapytan(self):
        with tempfile.TemporaryDirectory() as katalog:
            przerwanie = threading.Event()
            przerwanie.set()
            ogranicznik = Ogranicznik(Path(katalog) / "stan.json", przerwanie)
            with self.assertRaises(Przerwano):
                with ogranicznik.kolejka("www.vinted.pl"):
                    self.fail("zapytanie nie powinno wystartować")
            self.assertEqual(ogranicznik.licznik["www.vinted.pl"], 0)


class UkryteTest(unittest.TestCase):
    def test_dodaj_i_usun(self):
        with tempfile.TemporaryDirectory() as katalog:
            plik = Path(katalog) / "ukryte.txt"
            ukryte.dodaj(plik, ["https://www.vinted.pl/items/1?ref=x", "https://www.olx.pl/d/2"])
            self.assertEqual(ukryte.wczytaj(plik), {"https://www.vinted.pl/items/1", "https://www.olx.pl/d/2"})
            self.assertEqual(ukryte.usun(plik, ["https://www.vinted.pl/items/1/"]), 1)
            self.assertEqual(ukryte.wczytaj(plik), {"https://www.olx.pl/d/2"})
            self.assertEqual(ukryte.usun(plik, ["https://example.com/brak"]), 0)


if __name__ == "__main__":
    unittest.main()
