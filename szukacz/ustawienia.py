from pathlib import Path

KATALOG = Path(__file__).resolve().parent.parent
DANE = KATALOG / "dane"
WYNIKI = KATALOG / "wyniki"
KATALOG_CACHE = DANE / "cache"
PROFIL_PRZEGLADARKI = DANE / "profil_przegladarki"
PLIK_STANU = DANE / "stan_hostow.json"
PLIK_ENV = KATALOG / ".env"
PLIK_UKRYTYCH = KATALOG / "ukryte.txt"
PLIK_WLASNYCH = DANE / "wlasne_modele.json"
KATALOG_MODELI = KATALOG / "katalog"
PLIK_WSPOLNY = KATALOG_MODELI / "wspolne.toml"
DOMYSLNY_MODEL = ("munich", "continental")
KATALOG_MODELI_3D = KATALOG / "interfejs" / "public" / "modele"
KATALOG_INTERFEJSU = KATALOG / "interfejs" / "dist"
STARE_PLIKI_DANYCH = ("historia.json", "historia_41.json", "zdrowie_zrodel.json", "odkryte.json")

WYSYLKA_SZACUNKOWA = {
    "Vinted": 18.0,
    "OLX": 15.0,
    "Ceneo": 15.0,
    "R-GOL": 15.0,
    "Goalinn": None,
}
WYSYLKA_SKLEPU_W_POLSCE = 15.0

DOMYSLNY_ROZMIAR = "41"
CACHE_GODZIN = 6
BLOKADA_GODZIN = 12

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
)

ZBANOWANE_HOSTY = ("taternik-sklep.pl",)

LIMITY_DOMYSLNE ={"odstep": 7.0, "losowo": 5.0, "max_zapytan": 12}

LIMITY = {
    "www.olx.pl": {"odstep": 11.0, "losowo": 8.0, "max_zapytan": 18},
    "www.vinted.pl": {"odstep": 9.0, "losowo": 6.0, "max_zapytan": 16},
    "api.empathy.co": {"odstep": 5.0, "losowo": 3.0, "max_zapytan": 3},
    "allegrolokalnie.pl": {"odstep": 10.0, "losowo": 6.0, "max_zapytan": 10},
    "www.munichsports.com": {"odstep": 8.0, "losowo": 5.0, "max_zapytan": 14},
    "www.ceneo.pl": {"odstep": 9.0, "losowo": 6.0, "max_zapytan": 16},
    "www.tradeinn.com": {"odstep": 10.0, "losowo": 7.0, "max_zapytan": 22},
    "live.luigisbox.tech": {"odstep": 5.0, "losowo": 3.0, "max_zapytan": 3},
    "api.nbp.pl": {"odstep": 1.0, "losowo": 1.0, "max_zapytan": 10},
    "api.ebay.com": {"odstep": 3.0, "losowo": 2.0, "max_zapytan": 40},
    "serpapi.com": {"odstep": 2.0, "losowo": 2.0, "max_zapytan": 10},
}
