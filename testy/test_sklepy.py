import unittest
from types import SimpleNamespace

from szukacz import katalog
from szukacz import profil as P
from szukacz.zrodla.odkrywanie import kandydat
from szukacz.zrodla.sklepy import _zadanie, sklepy_profilu

LISTA_SPORTANO = """
<a href="/p/1/buty-do-tenisa-meskie-head-revolt-court-5-0-indoor">Buty do tenisa męskie HEAD Revolt Court 5.0 Indoor</a>
<a href="/p/2/kask-rowerowy-uvex-revolt-all-black-matt">Kask rowerowy UVEX Revolt all black matt</a>
<a href="/p/3/buty-halowe-ortuseight-jogosala-revolt-ivory-camo">Buty halowe Ortuseight Jogosala Revolt Ivory Camo</a>
"""


class PodrobionaSiec:
    def __init__(self, lista):
        self.lista = lista
        self.pobrane = []

    def get(self, url):
        self.pobrane.append(url)
        if url == self.lista:
            return SimpleNamespace(status=200, tekst=LISTA_SPORTANO, url=url)
        return SimpleNamespace(status=404, tekst="", url=url)


class SklepyTest(unittest.TestCase):
    def test_sklep_szukajacy_po_frazie_wymaga_marki_w_tytule(self):
        profil = katalog.profil("ortuseight", "jogosala-revolt", "42")
        P.ustaw(profil)
        sportano = next(s for s in sklepy_profilu(profil) if s.nazwa == "Sportano")
        siec = PodrobionaSiec(sportano.lista)
        kontekst = SimpleNamespace(profil=profil, http=siec, rozmiar="42", zlicz=lambda n: None, log=lambda *a, **kw: None)
        _zadanie(sportano).funkcja(kontekst, [])
        self.assertEqual(siec.pobrane[1:], ["https://sportano.pl/p/3/buty-halowe-ortuseight-jogosala-revolt-ivory-camo"])

    def test_lista_marki_nie_wymaga_marki_w_tytule(self):
        sklepy = {s.nazwa: s for s in sklepy_profilu(katalog.profil("munich", "continental", "41"))}
        self.assertFalse(sklepy["Sport-Shop"].szuka_po_frazie)
        self.assertFalse(sklepy["Munich (oficjalny)"].szuka_po_frazie)
        self.assertTrue(sklepy["Sportano"].szuka_po_frazie)

    def test_odkrywanie_wymaga_marki_w_tytule_albo_adresie(self):
        profil = katalog.profil("ortuseight", "jogosala-revolt", "42")
        P.ustaw(profil)
        self.assertFalse(kandydat("https://manchesteruniversitypress.co.uk/9781526151322/", "Turning revolt into style", profil, "42"))
        self.assertTrue(kandydat("https://sklep.example.de/ortuseight-jogosala-revolt-ivory-camo", "Jogosala Revolt Ivory Camo", profil, "42"))


if __name__ == "__main__":
    unittest.main()
