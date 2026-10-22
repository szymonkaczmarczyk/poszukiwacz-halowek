import re
from dataclasses import dataclass
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup

from .. import ustawienia as U
from ..dopasowanie import ocen_tytul, to_szukany_model
from ..modele import Oferta
from ..siec import host
from ..silnik import Zadanie
from ..strony import analizuj_produkt


@dataclass
class Sklep:
    nazwa: str
    lista: str
    wzor_linku: str
    wysylka: str = "tak, sklep w Polsce"
    max_produktow: int = 8
    uwagi: str = ""
    dostawa_szacunkowa: float | None = None
    szuka_po_frazie: bool = False


def sklepy_profilu(profil):
    wynik = []
    for s in profil.sklepy:
        sklep = Sklep(**s)
        sklep.szuka_po_frazie = "{fraza" in sklep.lista
        sklep.lista = profil.podstaw(sklep.lista)
        if sklep.dostawa_szacunkowa is None and sklep.wysylka.startswith("tak"):
            sklep.dostawa_szacunkowa = U.WYSYLKA_SKLEPU_W_POLSCE
        wynik.append(sklep)
    return wynik


def _opis_linku(url, tekst):
    sciezka = unquote(urlsplit(url).path)
    return f"{tekst} {re.sub(r'[-_/]+', ' ', sciezka)}"


def linki_produktow(html, baza, sklep, marka, rozmiar):
    soup = BeautifulSoup(html, "lxml")
    wszystkie = set()
    wynik = {}
    for a in soup.find_all("a", href=True):
        url = urljoin(baza, a["href"]).split("#")[0]
        if not re.match(sklep.wzor_linku, url):
            continue
        wszystkie.add(url)
        tekst = a.get_text(" ", strip=True) or a.get("title") or ""
        if not to_szukany_model(_opis_linku(url, tekst), marka):
            continue
        if tekst and ocen_tytul(tekst, rozmiar) == "nie":
            continue
        if tekst or url not in wynik:
            wynik[url] = wynik.get(url) or tekst
    return wynik, len(wszystkie)


def _zadanie(sklep):
    def szukaj(k, oferty):
        marka = None if sklep.szuka_po_frazie else k.profil.marka
        odp = k.http.get(sklep.lista)
        if odp.status != 200:
            k.log(sklep.nazwa, f"lista produktów: HTTP {odp.status}")
            return
        linki, wszystkie = linki_produktow(odp.tekst, odp.url, sklep, marka, k.rozmiar)
        k.zlicz(wszystkie)
        k.log(sklep.nazwa, f"{wszystkie} produktów na liście, {len(linki)} kandydatów do sprawdzenia", zawsze=False)
        for url, tekst in list(linki.items())[: sklep.max_produktow]:
            odp = k.http.get(url)
            if odp.status != 200:
                continue
            p = analizuj_produkt(odp.tekst, url, k.rozmiar)
            nazwa = p.nazwa or tekst
            if not to_szukany_model(_opis_linku(url, nazwa), marka) or p.rozmiar == "nie" or not p.cena:
                continue
            if ocen_tytul(nazwa, k.rozmiar) == "nie":
                continue
            oferty.append(Oferta(
                zrodlo=sklep.nazwa,
                tytul=nazwa,
                url=url,
                cena=p.cena,
                waluta=p.waluta or "PLN",
                dostawa=p.dostawa,
                dostawa_szacunkowa=sklep.dostawa_szacunkowa,
                rozmiar_pewny=p.rozmiar == "tak",
                stan="nowe",
                wysylka=sklep.wysylka,
                zdjecie=p.zdjecie,
                uwagi=sklep.uwagi,
            ))

    return Zadanie(sklep.nazwa, szukaj, (host(sklep.lista),))


def zadania(profil):
    return [_zadanie(s) for s in sklepy_profilu(profil)]
