import json
import re
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

from ..dopasowanie import normalizuj, ocen_pole, ocen_tytul, to_szukany_model
from ..modele import Oferta, kwota
from ..silnik import Zadanie
from ..strony import obiekty_ld, typy

NAZWA = "Ceneo"
BAZA = "https://www.ceneo.pl"
MAX_PRODUKTOW = 12


def _produkty(html):
    soup = BeautifulSoup(html, "lxml")
    wynik = {}
    for a in soup.find_all("a", href=True):
        if not re.fullmatch(r"/\d{5,}", a["href"]):
            continue
        tekst = a.get_text(" ", strip=True)
        if tekst:
            wynik.setdefault(urljoin(BAZA, a["href"]), tekst)
    return wynik


def _rozmiary(html):
    i = html.find("OffersAttributeFilters:")
    if i < 0:
        return []
    try:
        dane, _ = json.JSONDecoder().raw_decode(html[i + len("OffersAttributeFilters:"):].lstrip())
    except ValueError:
        return []
    rozmiary = []
    for atrybut in dane.get("Attributes") or []:
        if normalizuj(atrybut.get("FilterName", "")).startswith("rozmiar"):
            rozmiary += [str(o.get("Text", "")) for o in atrybut.get("Options") or []]
    return rozmiary


def _oferty_w_rozmiarze(soup, rozmiar):
    wynik = []
    for o in soup.select(".product-offer__container"):
        wariant = o.select_one(".offer-variant-attributes")
        cena = o.select_one(".product-price .price")
        if not wariant or not cena:
            continue
        m = re.search(r"rozmiar\s*:?\s*([^,;|]+)", normalizuj(wariant.get_text(" ", strip=True)))
        if m and ocen_pole(m.group(1), rozmiar) == "tak":
            logo = o.select_one(".store-logo img")
            wynik.append((kwota(cena.get_text("", strip=True)), logo.get("alt", "") if logo else ""))
    return sorted(w for w in wynik if w[0])


def szukaj(k, oferty):
    kandydaci = {}
    for fraza in k.profil.ceneo.get("frazy") or k.profil.frazy[:2]:
        odp = k.http.get(f"{BAZA}/;szukaj-{quote_plus(fraza)}")
        if odp.status != 200:
            k.log(NAZWA, f"wyszukiwanie: HTTP {odp.status}")
            continue
        produkty = _produkty(odp.tekst)
        k.zlicz(len(produkty))
        for url, tekst in produkty.items():
            if to_szukany_model(tekst, k.profil.marka) and ocen_tytul(tekst, k.rozmiar) != "nie":
                kandydaci.setdefault(url, tekst)
    k.log(NAZWA, f"{len(kandydaci)} produktów do sprawdzenia", zawsze=False)
    for url, tekst in list(kandydaci.items())[:MAX_PRODUKTOW]:
        odp = k.http.get(url)
        if odp.status != 200:
            continue
        rozmiary = _rozmiary(odp.tekst)
        if rozmiary and not any(ocen_pole(r, k.rozmiar) == "tak" for r in rozmiary):
            continue
        soup = BeautifulSoup(odp.tekst, "lxml")
        produkt = next((o for o in obiekty_ld(soup) if "Product" in typy(o)), {})
        nazwa = str(produkt.get("name") or tekst)
        if not to_szukany_model(nazwa, k.profil.marka):
            continue
        of = produkt.get("offers") if isinstance(produkt.get("offers"), dict) else {}
        w_rozmiarze = _oferty_w_rozmiarze(soup, k.rozmiar)
        if w_rozmiarze:
            cena, sklep = w_rozmiarze[0]
            uwagi = f"najtańsza oferta w rozmiarze {k.rozmiar}: {sklep}" if sklep else ""
        else:
            cena = kwota(of.get("lowPrice")) or kwota(of.get("price"))
            uwagi = f"najniższa cena z {of.get('offerCount', '?')} ofert, cena dla rozmiaru {k.rozmiar} może być inna"
        if not cena:
            continue
        zdjecia = produkt.get("image") or []
        oferty.append(Oferta(
            zrodlo=NAZWA,
            tytul=nazwa,
            url=url,
            cena=cena,
            waluta=of.get("priceCurrency") or "PLN",
            rozmiar_pewny=bool(rozmiary) or bool(w_rozmiarze),
            stan="nowe",
            wysylka="tak, sklepy w Polsce",
            zdjecie=zdjecia[0] if isinstance(zdjecia, list) and zdjecia else (zdjecia if isinstance(zdjecia, str) else ""),
            uwagi=uwagi,
        ))


ZADANIA = [Zadanie(NAZWA, szukaj, ("www.ceneo.pl",))]
