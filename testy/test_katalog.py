import unittest

from szukacz import katalog
from szukacz import profil as P
from szukacz.dopasowanie import model_profilu, to_szukany_model


def ocena(marka, model, tytul):
    P.ustaw(katalog.profil(marka, model, "42"))
    return model_profilu(tytul)[0]


class KatalogTest(unittest.TestCase):
    def test_kazdy_model_daje_poprawny_profil_w_kazdym_rozmiarze(self):
        rozmiary = katalog.rozmiary()
        self.assertEqual(rozmiary, [str(r) for r in range(38, 47)])
        for marka in katalog.marki():
            for model in marka.modele:
                for rozmiar in rozmiary:
                    profil = katalog.profil(marka.id, model.id, rozmiar)
                    self.assertEqual(profil.rozmiar, rozmiar)
                    self.assertIn(rozmiar, profil.vinted["rozmiary"])
                    self.assertEqual(profil.slug, f"{marka.id}-{model.id}")
                    self.assertTrue(profil.frazy)

    def test_identyfikatory_modeli_sa_unikalne(self):
        for marka in katalog.marki():
            identyfikatory = [m.id for m in marka.modele]
            self.assertEqual(len(identyfikatory), len(set(identyfikatory)), marka.nazwa)

    def test_wyszukiwanie_po_nazwie_i_identyfikatorze(self):
        self.assertEqual(katalog.profil("Joma", "Top Flex").slug, "joma-top-flex")
        self.assertEqual(katalog.profil(None, "lunar-gato").nazwa, "Nike Lunargato II")
        with self.assertRaises(katalog.BladKatalogu):
            katalog.profil("nike", "gresca")

    def test_profil_continental_bez_zmian(self):
        profil = katalog.profil("munich", "continental", "41")
        self.assertEqual(profil.vinted["marka_id"], 173430)
        self.assertEqual(len(profil.sklepy), 7)
        self.assertEqual(len(profil.reczne), 7)
        self.assertTrue(profil.goalinn["lista"].endswith("/munich/11002-629/sm"))

    def test_munich_continental_i_v2(self):
        self.assertEqual(ocena("munich", "continental", "Munich Continental 944 halówki"), "model")
        self.assertEqual(ocena("munich", "continental", "Munich Continental V2 41"), "wykluczony")
        self.assertEqual(ocena("munich", "continental", "Munich 4100958"), "model")
        self.assertEqual(ocena("munich", "continental", "Munich Gresca 41"), "inny")
        self.assertEqual(ocena("munich", "continental-v2", "Munich Continental V 2 41"), "model")
        self.assertEqual(ocena("munich", "continental-v2", "Munich Continental 944"), "inny")
        self.assertEqual(ocena("munich", "continental-v2", "Munich 4100944"), "wykluczony")

    def test_munich_one_rondo_debut(self):
        modele = [m.id for m in katalog.znajdz("munich", "continental")[0].modele]
        self.assertEqual(modele, ["continental", "continental-v2", "gresca", "g-3", "arenga", "one", "debut", "rondo"])
        self.assertEqual(ocena("munich", "one", "Munich One 42 halówki"), "model")
        self.assertEqual(ocena("munich", "one", "Munich Gresca czerwone"), "inny")
        self.assertEqual(ocena("munich", "rondo", "Munich Rondito 33"), "inny")
        self.assertEqual(ocena("munich", "rondo", "Munich Rondo 42"), "model")
        self.assertEqual(ocena("munich", "debut", "Munich Debut 42"), "model")
        self.assertEqual(ocena("munich", "continental", "Munich Tiga indoor"), "inny")

    def test_inne_modele_tylko_calymi_slowami(self):
        self.assertEqual(ocena("munich", "continental", "Halówki Munich czerwone, noszone, zielone"), "?")
        self.assertEqual(ocena("munich", "continental", "Munich One"), "inny")
        self.assertEqual(ocena("munich", "continental-v2", "Munich Continental V 2"), "model")
        self.assertEqual(ocena("nike", "streetgato", "Nike Street Gato IC"), "model")
        self.assertEqual(ocena("joma", "top-flex", "Joma TopFlex 2402"), "model")

    def test_joma(self):
        self.assertEqual(ocena("joma", "top-flex", "Joma Top Flex TOPS2402IN"), "model")
        self.assertEqual(ocena("joma", "top-flex", "Joma Top Flex Rebound 2401"), "wykluczony")
        self.assertEqual(ocena("joma", "top-flex", "Joma Top Flex Turf"), "wykluczony")
        self.assertEqual(ocena("joma", "top-flex", "Joma Liga 5 IN"), "inny")
        self.assertEqual(ocena("joma", "gambeta", "Joma Gambeta 2401 IN"), "model")
        self.assertEqual(ocena("joma", "mundial", "Joma Invicto IN"), "inny")

    def test_nike_wymaga_wersji_halowej(self):
        self.assertEqual(ocena("nike", "phantom", "Nike Phantom GX Academy IC"), "model")
        self.assertEqual(ocena("nike", "phantom", "Nike Phantom GX Academy FG"), "wykluczony")
        self.assertEqual(ocena("nike", "phantom", "Nike Phantom GX Academy"), "?")
        self.assertEqual(ocena("nike", "phantom", "Nike Tiempo Legend 10 IC"), "inny")
        self.assertEqual(ocena("nike", "phantom", "Nike Mercurial Superfly 9 Club IC"), "inny")
        self.assertEqual(ocena("nike", "gato", "Nike Gato II"), "model")
        self.assertEqual(ocena("nike", "gato", "Nike Lunargato II"), "wykluczony")
        self.assertEqual(ocena("nike", "gato", "Nike Tiempo Streetgato"), "wykluczony")
        self.assertEqual(ocena("nike", "react-gato", "Nike Tiempo Reactgato"), "model")
        self.assertEqual(ocena("nike", "lunar-gato", "Nike Lunar Gato II"), "model")
        P.ustaw(katalog.profil("nike", "phantom", "42"))
        self.assertTrue(to_szukany_model("Nike Phantom GX 2 Academy IC"))
        self.assertFalse(to_szukany_model("Nike Phantom GX 2 Academy IC Jr"))

    def test_adidas_mizuno(self):
        self.assertEqual(ocena("adidas", "predator", "adidas Predator League IN"), "model")
        self.assertEqual(ocena("adidas", "predator", "adidas Predator League TF"), "wykluczony")
        self.assertEqual(ocena("adidas", "top-sala", "adidas Top Sala II"), "model")
        self.assertEqual(ocena("adidas", "super-sala", "adidas Super Sala III"), "model")
        self.assertEqual(ocena("adidas", "predator", "adidas Copa Pure IN"), "inny")
        self.assertEqual(ocena("mizuno", "morelia-sala", "Mizuno Monarcida Neo Sala"), "inny")
        self.assertEqual(ocena("mizuno", "morelia-sala", "Mizuno Morelia Sala Elite IN"), "model")
        self.assertEqual(ocena("mizuno", "morelia-sala", "Mizuno Morelia Sala Classic TF"), "wykluczony")


if __name__ == "__main__":
    unittest.main()
