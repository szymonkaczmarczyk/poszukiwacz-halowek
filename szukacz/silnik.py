import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from .przegladarka import Przegladarka
from .siec import ZrodloNiedostepne


@dataclass
class Zadanie:
    nazwa: str
    funkcja: object
    hosty: tuple = ()


@dataclass
class WynikZrodla:
    nazwa: str
    oferty: list = field(default_factory=list)
    status: str = "ok"
    komunikat: str = ""
    czas: float = 0.0
    zapytania: int = 0
    surowe: int = 0
    min_surowych: int = 0


class Kontekst:
    def __init__(self, profil, http, ogranicznik, cache, rozmiar, widoczna_przegladarka=False, gadatliwy=False):
        self.profil = profil
        self.http = http
        self.ogranicznik = ogranicznik
        self.cache = cache
        self.rozmiar = rozmiar
        self.widoczna_przegladarka = widoczna_przegladarka
        self.gadatliwy = gadatliwy
        self.odkrywaj = False
        self._druk = threading.Lock()
        self._watek = threading.local()

    def log(self, zrodlo, tekst, zawsze=True):
        if zawsze or self.gadatliwy:
            with self._druk:
                print(f"  [{zrodlo}] {tekst}", flush=True)

    def zlicz(self, liczba):
        wynik = getattr(self._watek, "wynik", None)
        if wynik:
            wynik.surowe += liczba

    def przegladarka(self, profil):
        return Przegladarka(self.ogranicznik, self.cache, profil, self.widoczna_przegladarka)


def _wykonaj(zadanie, kontekst):
    wynik = WynikZrodla(zadanie.nazwa)
    kontekst._watek.wynik = wynik
    start = time.time()
    przed = sum(kontekst.ogranicznik.licznik[h] for h in zadanie.hosty)
    try:
        zadanie.funkcja(kontekst, wynik.oferty)
    except ZrodloNiedostepne as e:
        wynik.status = "wstrzymane"
        wynik.komunikat = str(e)
    except Exception as e:
        wynik.status = "błąd"
        wynik.komunikat = f"{e.__class__.__name__}: {e}"
        if kontekst.gadatliwy:
            traceback.print_exc()
    finally:
        kontekst._watek.wynik = None
    wynik.czas = time.time() - start
    wynik.zapytania = sum(kontekst.ogranicznik.licznik[h] for h in zadanie.hosty) - przed
    if wynik.status == "ok":
        kontekst.log(zadanie.nazwa, f"gotowe: {len(wynik.oferty)} pasujących z {wynik.surowe} odczytanych ({wynik.czas:.0f} s)")
    else:
        kontekst.log(zadanie.nazwa, f"{wynik.status}: {wynik.komunikat} (zebrano {len(wynik.oferty)})")
    return wynik


def uruchom(zadania, kontekst):
    wyniki = []
    if not zadania:
        return wyniki
    with ThreadPoolExecutor(max_workers=min(10, len(zadania))) as pula:
        przyszle = {pula.submit(_wykonaj, z, kontekst): z for z in zadania}
        for p in as_completed(przyszle):
            wynik = p.result()
            wynik.min_surowych = kontekst.profil.min_odczytow(przyszle[p].nazwa)
            wyniki.append(wynik)
    return wyniki
