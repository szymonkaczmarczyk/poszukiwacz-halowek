import argparse
import os
import sys
import time
import webbrowser

from szukacz import historia, raport, reczne, ukryte, zdrowie
from szukacz import profil as P
from szukacz import ustawienia as U
from szukacz.kursy import Kursy
from szukacz.siec import Cache, KlientHttp, Ogranicznik, host
from szukacz.silnik import Kontekst, uruchom
from szukacz.zrodla import allegro_lokalnie, ceneo, ebay, futbolemotion, goalinn, odkrywanie, olx, rgol, sklepy, vinted

MODULY = [vinted, olx, goalinn, ceneo, futbolemotion, rgol, sklepy, allegro_lokalnie, ebay, odkrywanie]


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


def argumenty():
    p = argparse.ArgumentParser(
        description="Szuka wybranego modelu butów w podanym rozmiarze w sklepach i na marketplace'ach z wysyłką do Polski.",
    )
    p.add_argument("--profil", default=str(U.DOMYSLNY_PROFIL), help="plik profilu z opisem szukanych butów (domyślnie %(default)s)")
    p.add_argument("--lista-profili", action="store_true", help="wypisz profile z katalogu profile/ i zakończ")
    p.add_argument("--rozmiar", help="rozmiar EU (domyślnie z profilu)")
    p.add_argument("--zrodla", help="lista źródeł po przecinku, np. vinted,olx,sportano (domyślnie wszystkie)")
    p.add_argument("--lista-zrodel", action="store_true", help="wypisz dostępne źródła i zakończ")
    p.add_argument("--max-cena", type=float, help="pokaż tylko oferty tańsze niż podana kwota w zł")
    p.add_argument("--tylko-pewne", action="store_true", help="pokaż tylko oferty z potwierdzonym rozmiarem")
    p.add_argument("--odswiez", action="store_true", help="ignoruj pamięć podręczną i pobierz wszystko od nowa")
    p.add_argument("--reset-blokad", action="store_true", help="usuń zapamiętane wstrzymania hostów po wykryciu ochrony antybotowej")
    p.add_argument("--odkrywaj", action="store_true", help="wyszukaj nowe sklepy w Google teraz, bez czekania tygodnia (zużywa kilka zapytań SerpAPI)")
    p.add_argument("--ukryj", nargs="+", metavar="LINK", help="ukryj oferty o podanych linkach w kolejnych wynikach i zakończ")
    p.add_argument("--pokaz-ukryte", action="store_true", help="pokaż także oferty z pliku ukryte.txt")
    p.add_argument("--widoczna-przegladarka", action="store_true", help="pokaż okna przeglądarki używanej dla OLX i Goalinn")
    p.add_argument("--nie-otwieraj", action="store_true", help="nie otwieraj raportu HTML po zakończeniu")
    p.add_argument("-v", "--gadatliwy", action="store_true", help="więcej szczegółów w trakcie działania")
    return p.parse_args()


def przenies_stare_dane(profil):
    if profil.plik.resolve() != U.DOMYSLNY_PROFIL.resolve():
        return
    profil.katalog_danych.mkdir(parents=True, exist_ok=True)
    for nazwa in U.STARE_PLIKI_DANYCH:
        stary = U.DANE / nazwa
        nowy = profil.katalog_danych / (f"historia_{profil.rozmiar}.json" if nazwa.startswith("historia") else nazwa)
        if stary.exists() and not nowy.exists():
            stary.rename(nowy)


def przygotuj(o, kursy):
    o.cena_pln = kursy.na_pln(o.cena, o.waluta)
    o.dostawa_pln = kursy.na_pln(o.dostawa, o.waluta)
    if o.dostawa_pln is None and o.wysylka.startswith("tak"):
        szacunek = o.dostawa_szacunkowa if o.dostawa_szacunkowa is not None else U.WYSYLKA_SZACUNKOWA.get(o.zrodlo)
        if szacunek is not None:
            o.dostawa_pln = szacunek
            o.dostawa_szac = True


def zbanowana(url):
    h = host(url)
    return any(h == b or h.endswith("." + b) for b in U.ZBANOWANE_HOSTY)


def pierwszenstwo(o):
    return (o.model != "do weryfikacji", o.rozmiar_pewny, -o.suma_pln)


def wybierz(zadania, filtr):
    if not filtr:
        return zadania
    szukane = [f.strip().lower() for f in filtr.split(",") if f.strip()]
    return [z for z in zadania if any(s in z.nazwa.lower() for s in szukane)]


def lista_profili():
    for plik in sorted(U.KATALOG_PROFILI.glob("*.toml")):
        try:
            p = P.wczytaj(plik)
            print(f"  {plik.name:<32} {p.nazwa}, rozmiar {p.rozmiar}")
        except P.BladProfilu as e:
            print(f"  {plik.name:<32} BŁĄD: {e}")


def main():
    if os.name == "nt":
        os.system("")
    for strumien in (sys.stdout, sys.stderr):
        try:
            strumien.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    wczytaj_env()
    a = argumenty()
    if a.ukryj:
        dodane = ukryte.dodaj(U.PLIK_UKRYTYCH, a.ukryj)
        print(f"Ukryto {len(dodane)} ofert (plik {U.PLIK_UKRYTYCH.name})." if dodane else "Te oferty były już ukryte.")
        return 0
    if a.lista_profili:
        lista_profili()
        return 0
    try:
        profil = P.wczytaj(a.profil)
    except P.BladProfilu as e:
        print(f"Błąd profilu: {e}")
        return 2
    P.ustaw(profil)
    rozmiar = str(a.rozmiar or profil.rozmiar)

    zadania = wszystkie_zadania(profil)
    if a.lista_zrodel:
        for z in zadania:
            stan = "" if dostepne(z, profil) else "  (wyłączone: brak klucza lub ustawień w profilu)"
            print(f"  {z.nazwa:<22} {', '.join(z.hosty)}{stan}")
        return 0
    zadania = [z for z in wybierz(zadania, a.zrodla) if dostepne(z, profil)]
    if not zadania:
        print("Nie wybrano żadnego źródła. Użyj --lista-zrodel.")
        return 1

    przenies_stare_dane(profil)
    profil.katalog_danych.mkdir(parents=True, exist_ok=True)
    profil.katalog_wynikow.mkdir(parents=True, exist_ok=True)
    cache = Cache(U.KATALOG_CACHE, U.CACHE_GODZIN, pomin_odczyt=a.odswiez)
    cache.sprzataj()
    ogranicznik = Ogranicznik(U.PLIK_STANU)
    if a.reset_blokad:
        ogranicznik.wyczysc_blokady()
    kontekst = Kontekst(profil, None, ogranicznik, cache, rozmiar, a.widoczna_przegladarka, a.gadatliwy)
    kontekst.odkrywaj = a.odkrywaj
    http = KlientHttp(ogranicznik, cache, lambda h, t: kontekst.log(h, t))
    kontekst.http = http

    blokady = ogranicznik.aktywne_blokady()
    wykluczenia = f" ({profil.opis_wykluczen})" if profil.opis_wykluczen else ""
    print(f"Szukam: {profil.nazwa}{wykluczenia}, rozmiar {rozmiar}, {len(zadania)} źródeł. Profil: {profil.plik.name}")
    print("Zapytania idą powoli i z losowymi przerwami, wyniki są cache'owane na "
          f"{U.CACHE_GODZIN} h, więc ponowne uruchomienie nie obciąża stron.")
    if blokady:
        print(f"Wstrzymane hosty (ochrona antybotowa): {', '.join(blokady)}. Użyj --reset-blokad, aby spróbować ponownie.")
    print()

    start = time.time()
    wyniki = uruchom(zadania, kontekst)

    zdrowie.ocen(wyniki, profil.katalog_danych / "zdrowie_zrodel.json")
    kursy = Kursy(http)
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
    schowane = set() if a.pokaz_ukryte else ukryte.wczytaj(U.PLIK_UKRYTYCH)
    ukryto = sum(1 for o in lista if o.klucz in schowane)
    lista = [o for o in lista if o.klucz not in schowane]
    zmiany.nowe = [o for o in zmiany.nowe if o.klucz not in schowane]
    zmiany.tansze = [(o, r) for o, r in zmiany.tansze if o.klucz not in schowane]
    zmiany.drozsze = [(o, r) for o, r in zmiany.drozsze if o.klucz not in schowane]
    zmiany.zniknely = [z for z in zmiany.zniknely if z["klucz"] not in schowane]
    if a.max_cena:
        lista = [o for o in lista if o.suma_pln <= a.max_cena]
    if a.tylko_pewne:
        lista = [o for o in lista if o.rozmiar_pewny and o.model != "do weryfikacji"]

    klucze = {"ebay"} if ebay.skonfigurowany() else set()
    linki = reczne.linki(profil, rozmiar, klucze)
    raport.drukuj(profil, lista, zmiany, wyniki, linki, rozmiar, kursy.przyblizone, ukryto)
    wyniki_dir = profil.katalog_wynikow
    raport.zapisz_csv(lista, wyniki_dir / "oferty.csv")
    dane = raport.zapisz_json(profil, lista, zmiany, wyniki, linki, rozmiar, wyniki_dir / "oferty.json")
    plik_html = wyniki_dir / "raport.html"
    raport.zapisz_html(dane, plik_html)
    print()
    print(f"Gotowe w {time.time() - start:.0f} s. Raport: {plik_html}")
    print(f"Tabela do Excela: {wyniki_dir / 'oferty.csv'}")
    if not a.nie_otwieraj:
        webbrowser.open(plik_html.as_uri())
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nPrzerwano.")
        sys.exit(130)
