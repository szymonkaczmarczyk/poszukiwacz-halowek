import argparse
import os
import sys
import webbrowser

from szukacz import katalog, przebieg, raport, ukryte
from szukacz import profil as P
from szukacz import ustawienia as U


def argumenty():
    p = argparse.ArgumentParser(
        description="Szuka wybranego modelu butów w podanym rozmiarze w sklepach i na marketplace'ach z wysyłką do Polski.",
    )
    p.add_argument("--marka", help="marka z katalogu, np. joma (domyślnie %s)" % U.DOMYSLNY_MODEL[0])
    p.add_argument("--model", help="model z katalogu, np. top-flex (domyślnie %s)" % U.DOMYSLNY_MODEL[1])
    p.add_argument("--lista-modeli", action="store_true", help="wypisz marki i modele z katalogu i zakończ")
    p.add_argument("--profil", help="własny plik profilu .toml zamiast modelu z katalogu")
    p.add_argument("--rozmiar", help="rozmiar EU albo kilka po przecinku, np. 41,42 (domyślnie %s)" % U.DOMYSLNY_ROZMIAR)
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


def lista_modeli():
    for marka in katalog.marki():
        print(f"{marka.nazwa} (--marka {marka.id})")
        for model in marka.modele:
            print(f"  --model {model.id:<22} {model.nazwa}")
    print(f"Rozmiary: {', '.join(katalog.rozmiary())}")


def wczytaj_profil(a):
    if a.profil:
        return P.wczytaj(a.profil)
    if a.marka and not a.model:
        raise P.BladProfilu("podaj też --model (lista: --lista-modeli)")
    marka, model = (a.marka, a.model) if a.model else U.DOMYSLNY_MODEL
    return katalog.profil(marka, model)


def drukuj_zdarzenie(nazwa_profilu):
    def sluchacz(typ, dane):
        if typ == "log":
            print(f"  [{dane['zrodlo']}] {dane['tekst']}", flush=True)
        elif typ == "start":
            wykluczenia = f" ({dane['opis_wykluczen']})" if dane["opis_wykluczen"] else ""
            print(f"Szukam: {dane['nazwa']}{wykluczenia}, rozmiar {dane['rozmiar']}, {len(dane['zrodla'])} źródeł. Profil: {nazwa_profilu}")
            print("Zapytania idą powoli i z losowymi przerwami, wyniki są cache'owane na "
                  f"{dane['cache_godzin']} h, więc ponowne uruchomienie nie obciąża stron.")
            if dane["wstrzymane_hosty"]:
                print(f"Wstrzymane hosty (ochrona antybotowa): {', '.join(dane['wstrzymane_hosty'])}. Użyj --reset-blokad, aby spróbować ponownie.")
            print()

    return sluchacz


def rozmiary(a, profil):
    return [r.strip() for r in str(a.rozmiar or profil.rozmiar).split(",") if r.strip()]


def main():
    if os.name == "nt":
        os.system("")
    for strumien in (sys.stdout, sys.stderr):
        try:
            strumien.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    przebieg.wczytaj_env()
    a = argumenty()
    if a.ukryj:
        dodane = ukryte.dodaj(U.PLIK_UKRYTYCH, a.ukryj)
        print(f"Ukryto {len(dodane)} ofert (plik {U.PLIK_UKRYTYCH.name})." if dodane else "Te oferty były już ukryte.")
        return 0
    if a.lista_modeli:
        lista_modeli()
        return 0
    try:
        profil = wczytaj_profil(a)
    except P.BladProfilu as e:
        print(f"Błąd profilu: {e}")
        return 2
    if a.lista_zrodel:
        for z in przebieg.opis_zrodel(profil):
            stan = "" if z["dostepne"] else "  (wyłączone: brak klucza lub ustawień w profilu)"
            print(f"  {z['nazwa']:<22} {', '.join(z['hosty'])}{stan}")
        return 0

    sluchacz = drukuj_zdarzenie(profil.plik.name if a.profil else profil.slug)
    for i, rozmiar in enumerate(rozmiary(a, profil)):
        if i:
            print()
        opcje = przebieg.Opcje(
            rozmiar=rozmiar,
            zrodla=(a.zrodla or "").split(","),
            max_cena=a.max_cena,
            tylko_pewne=a.tylko_pewne,
            odswiez=a.odswiez,
            reset_blokad=a.reset_blokad,
            odkrywaj=a.odkrywaj,
            pokaz_ukryte=a.pokaz_ukryte,
            widoczna_przegladarka=a.widoczna_przegladarka,
            gadatliwy=a.gadatliwy,
        )
        try:
            w = przebieg.wykonaj(profil, opcje, sluchacz)
        except przebieg.BrakZrodel:
            print("Nie wybrano żadnego źródła. Użyj --lista-zrodel.")
            return 1
        raport.drukuj(w.profil, w.oferty, w.zmiany, w.zrodla, w.reczne, w.rozmiar, w.kursy_przyblizone, w.ukryto)
        print()
        print(f"Gotowe w {w.czas:.0f} s. Raport: {w.plik_html}")
        print(f"Tabela do Excela: {w.plik_csv}")
        if not a.nie_otwieraj:
            webbrowser.open(w.plik_html.as_uri())
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nPrzerwano.")
        sys.exit(130)
