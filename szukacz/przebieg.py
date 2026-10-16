import os
import time
from dataclasses import dataclass, field, replace

from . import historia, raport, reczne, ukryte, zdrowie
from . import profil as P
from . import ustawienia as U
from .dopasowanie import normalizuj
from .kursy import Kursy
from .siec import Cache, KlientHttp, Ogranicznik, host
from .silnik import Kontekst, uruchom
from .zrodla import allegro_lokalnie, ceneo, ebay, futbolemotion, goalinn, odkrywanie, olx, rgol, sklepy, vinted

MODULY = [vinted, olx, goalinn, ceneo, futbolemotion, rgol, sklepy, allegro_lokalnie, ebay, odkrywanie]


class BrakZrodel(Exception):
    pass


@dataclass
class Opcje:
    rozmiar: str
    zrodla: list = field(default_factory=list)
    max_cena: float | None = None
    tylko_pewne: bool = False
    odswiez: bool = False
    reset_blokad: bool = False
    odkrywaj: bool = False
    pokaz_ukryte: bool = False
    widoczna_przegladarka: bool = False
    gadatliwy: bool = False
    przerwanie: object = None


@dataclass
class Wynik:
    profil: object
    rozmiar: str
    oferty: list
    zmiany: object
    zrodla: list
    reczne: list
    kursy_przyblizone: set
    ukryto: int
    dane: dict
    plik_html: object
    plik_csv: object
    czas: float


def wczytaj_env():
    try:
        linie = U.PLIK_ENV.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for linia in linie:
        linia = linia.strip()
        if linia and not linia.startswith("#") and "=" in linia:
            klucz, wartosc = linia.split("=", 1)
            os.environ.setdefault(klucz.strip(), wartosc.strip().strip('"').strip("'"))


def wszystkie_zadania(profil):
    zadania = []
    for m in MODULY:
        zadania += m.zadania(profil) if hasattr(m, "zadania") else m.ZADANIA
    return zadania


def dostepne(zadanie, profil):
    warunki = {
        ebay.NAZWA: ebay.skonfigurowany,
        odkrywanie.NAZWA: odkrywanie.skonfigurowany,
        goalinn.NAZWA: lambda: goalinn.skonfigurowany(profil),
    }
    return warunki.get(zadanie.nazwa, lambda: True)()


def wybierz(zadania, nazwy):
    szukane = [normalizuj(n.strip()) for n in nazwy if n.strip()]
    if not szukane:
        return zadania
    return [z for z in zadania if any(s in normalizuj(z.nazwa) for s in szukane)]


def opis_zrodel(profil):
    return [{"nazwa": z.nazwa, "hosty": list(z.hosty), "dostepne": dostepne(z, profil)} for z in wszystkie_zadania(profil)]


def zbanowana(url):
    h = host(url)
    return any(h == b or h.endswith("." + b) for b in U.ZBANOWANE_HOSTY)


def przygotuj(o, kursy):
    o.cena_pln = kursy.na_pln(o.cena, o.waluta)
    o.dostawa_pln = kursy.na_pln(o.dostawa, o.waluta)
    if o.dostawa_pln is None and o.wysylka.startswith("tak"):
        szacunek = o.dostawa_szacunkowa if o.dostawa_szacunkowa is not None else U.WYSYLKA_SZACUNKOWA.get(o.zrodlo)
        if szacunek is not None:
            o.dostawa_pln = szacunek
            o.dostawa_szac = True


def pierwszenstwo(o):
    return (o.model != "do weryfikacji", o.rozmiar_pewny, -o.suma_pln)


def przenies_stare_dane(profil):
    if profil.slug != "-".join(U.DOMYSLNY_MODEL):
        return
    profil.katalog_danych.mkdir(parents=True, exist_ok=True)
    for nazwa in U.STARE_PLIKI_DANYCH:
        stary = U.DANE / nazwa
        nowy = profil.katalog_danych / (f"historia_{profil.rozmiar}.json" if nazwa.startswith("historia") else nazwa)
        if stary.exists() and not nowy.exists():
            stary.rename(nowy)


def _spelnia_filtry(o, opcje):
    if opcje.max_cena and o.suma_pln > opcje.max_cena:
        return False
    return not opcje.tylko_pewne or (o.rozmiar_pewny and o.model != "do weryfikacji")


def _oferta_na_zywo(o):
    return {**o.do_slownika(), "klucz": o.klucz, "grupa": raport.grupa(o)}


def _wynik_zrodla(w):
    return {"nazwa": w.nazwa, "status": w.status, "komunikat": w.komunikat, "ofert": len(w.oferty), "odczytano": w.surowe, "zapytan": w.zapytania, "czas": round(w.czas, 1)}


def wykonaj(profil, opcje, sluchacz=lambda typ, dane: None):
    rozmiar = str(opcje.rozmiar or profil.rozmiar)
    profil = replace(profil, rozmiar=rozmiar)
    P.ustaw(profil)
    zadania = [z for z in wybierz(wszystkie_zadania(profil), opcje.zrodla) if dostepne(z, profil)]
    if not zadania:
        raise BrakZrodel("nie wybrano żadnego dostępnego źródła")

    przenies_stare_dane(profil)
    profil.katalog_danych.mkdir(parents=True, exist_ok=True)
    katalog_wynikow = profil.katalog_wynikow(rozmiar)
    katalog_wynikow.mkdir(parents=True, exist_ok=True)
    cache = Cache(U.KATALOG_CACHE, U.CACHE_GODZIN, pomin_odczyt=opcje.odswiez)
    cache.sprzataj()
    ogranicznik = Ogranicznik(U.PLIK_STANU, opcje.przerwanie)
    if opcje.reset_blokad:
        ogranicznik.wyczysc_blokady()
    schowane = set() if opcje.pokaz_ukryte else ukryte.wczytaj(U.PLIK_UKRYTYCH)
    kursy = None

    def zdarzenie_silnika(typ, dane):
        if typ == "zrodlo_koniec":
            w = dane["wynik"]
            na_zywo = []
            for o in w.oferty:
                if not o.cena or zbanowana(o.url) or o.klucz in schowane:
                    continue
                przygotuj(o, kursy)
                if _spelnia_filtry(o, opcje):
                    na_zywo.append(_oferta_na_zywo(o))
            dane = {"rozmiar": rozmiar, **_wynik_zrodla(w), "oferty": sorted(na_zywo, key=lambda x: x["suma_pln"])}
        else:
            dane = {"rozmiar": rozmiar, **dane}
        sluchacz(typ, dane)

    kontekst = Kontekst(profil, None, ogranicznik, cache, rozmiar, opcje.widoczna_przegladarka, opcje.gadatliwy, zdarzenie_silnika)
    kontekst.odkrywaj = opcje.odkrywaj
    http = KlientHttp(ogranicznik, cache, lambda h, t: kontekst.log(h, t))
    kontekst.http = http
    kursy = Kursy(http)

    sluchacz("start", {
        "rozmiar": rozmiar,
        "nazwa": profil.nazwa,
        "opis_wykluczen": profil.opis_wykluczen,
        "profil": profil.slug,
        "zrodla": [z.nazwa for z in zadania],
        "wstrzymane_hosty": ogranicznik.aktywne_blokady(),
        "cache_godzin": U.CACHE_GODZIN,
    })
    start = time.time()
    wyniki = uruchom(zadania, kontekst)

    zdrowie.ocen(wyniki, profil.katalog_danych / "zdrowie_zrodel.json")
    oferty = {}
    for w in wyniki:
        for o in w.oferty:
            if not o.cena or zbanowana(o.url):
                continue
            przygotuj(o, kursy)
            poprzednia = oferty.get(o.klucz)
            if not poprzednia or pierwszenstwo(o) > pierwszenstwo(poprzednia):
                oferty[o.klucz] = o
    lista = sorted(oferty.values(), key=lambda o: o.suma_pln)

    sprawdzone = [w.nazwa for w in wyniki if w.status == "ok"]
    plik_historii = profil.katalog_danych / f"historia_{rozmiar}.json"
    zmiany = historia.oznacz(lista, plik_historii, lambda z: any(z.startswith(n) for n in sprawdzone))
    ukryto = sum(1 for o in lista if o.klucz in schowane)
    lista = [o for o in lista if o.klucz not in schowane]
    zmiany.nowe = [o for o in zmiany.nowe if o.klucz not in schowane]
    zmiany.tansze = [(o, r) for o, r in zmiany.tansze if o.klucz not in schowane]
    zmiany.drozsze = [(o, r) for o, r in zmiany.drozsze if o.klucz not in schowane]
    zmiany.zniknely = [z for z in zmiany.zniknely if z["klucz"] not in schowane]
    lista = [o for o in lista if _spelnia_filtry(o, opcje)]

    klucze = {"ebay"} if ebay.skonfigurowany() else set()
    linki = reczne.linki(profil, rozmiar, klucze)
    plik_csv = katalog_wynikow / "oferty.csv"
    plik_html = katalog_wynikow / "raport.html"
    raport.zapisz_csv(lista, plik_csv)
    dane = raport.zapisz_json(profil, lista, zmiany, wyniki, linki, rozmiar, katalog_wynikow / "oferty.json")
    raport.zapisz_html(dane, plik_html)
    czas = time.time() - start
    sluchacz("koniec", {"rozmiar": rozmiar, "czas": round(czas, 1), "ukryto": ukryto, "przerwane": ogranicznik.przerwanie.is_set(), "kursy_przyblizone": sorted(kursy.przyblizone), "wyniki": dane})
    return Wynik(profil, rozmiar, lista, zmiany, wyniki, linki, kursy.przyblizone, ukryto, dane, plik_html, plik_csv, czas)
