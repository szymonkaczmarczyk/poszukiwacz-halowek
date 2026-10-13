import math
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..dopasowanie import model_profilu, normalizuj, ocen_opis, ocen_tytul, to_marka
from ..modele import Oferta, kwota
from ..silnik import Zadanie
from ..weryfikacja import do_listy

NAZWA = "OLX"
BAZA = "https://www.olx.pl"
MAX_SZCZEGOLOW = 10


def _slug(tekst):
    return re.sub(r"[^a-z0-9]+", "-", normalizuj(tekst)).strip("-")


def zapytania(k):
    p = k.profil
    if p.olx.get("zapytania"):
        return [(p.podstaw(fraza, k.rozmiar), int(strony)) for fraza, strony in p.olx["zapytania"]]
    lista = [(_slug(f), 2 if i == 0 else 1) for i, f in enumerate(p.frazy)]
    return lista + [(f"{_slug(p.fraza)}-{k.rozmiar}", 1)]


def _karty(html):
    soup = BeautifulSoup(html, "lxml")
    licznik = soup.select_one('[data-testid="total-count"]')
    m = re.search(r"(\d[\d\s]*)", licznik.get_text(" ", strip=True)) if licznik else None
    razem = int(re.sub(r"\s", "", m.group(1))) if m else 0
    karty = []
    for c in soup.select('[data-cy="l-card"]'):
        link = c.select_one('[data-testid="card-title-link"]') or c.select_one("a[href]")
        if not link:
            continue
        naglowek = c.select_one('[data-testid="card-title-link"] h4, [data-testid="card-title-link"] h6, h4, h6')
        tytul = (naglowek or link).get_text(" ", strip=True)
        cena = c.select_one('[data-testid="ad-price"]')
        miejsce = c.select_one('[data-testid="location-date"]')
        tekst = c.get_text(" | ", strip=True)
        img = c.select_one("img[src]")
        karty.append({
            "tytul": tytul,
            "url": urljoin(BAZA, link["href"]).split("?")[0],
            "cena": cena.get_text(" ", strip=True) if cena else "",
            "lokalizacja": miejsce.get_text(" ", strip=True).split(" - ")[0] if miejsce else "",
            "przesylka": bool(
                c.select_one('[data-testid="card-delivery-badge"], [data-testid="free-delivery-tag"]')
                or "Pakietem Ochronnym" in tekst
                or "Dostawa" in tekst
            ),
            "stan": "nowe" if "| Nowe" in tekst else ("używane" if "Używane" in tekst else ""),
            "zdjecie": img["src"] if img else "",
        })
    return razem, karty


def _szczegoly(html):
    soup = BeautifulSoup(html, "lxml")
    czesci = []
    for wybor in ('[data-testid="ad-parameters-container"]', '[data-cy="ad_description"]', '[data-testid="ad_description"]'):
        el = soup.select_one(wybor)
        if el:
            czesci.append(el.get_text(" ", strip=True))
    return " ".join(czesci)


def szukaj(k, oferty):
    przegladarka = k.przegladarka("olx")
    try:
        kandydaci = {}
        for fraza, max_stron in zapytania(k):
            strony = max_stron
            strona = 1
            while strona <= strony:
                url = f"{BAZA}/oferty/q-{fraza}/" + (f"?page={strona}" if strona > 1 else "")
                odp = przegladarka.pobierz(url)
                razem, karty = _karty(odp.tekst)
                k.zlicz(len(karty))
                strony = min(max_stron, max(1, math.ceil(razem / 40)))
                k.log(NAZWA, f"„{fraza}” strona {strona}: {len(karty)} ogłoszeń z {razem}", zawsze=False)
                for karta in karty:
                    if not karta["url"].startswith(BAZA) or not to_marka(karta["tytul"]):
                        continue
                    if model_profilu(karta["tytul"])[0] in ("model", "?"):
                        kandydaci.setdefault(karta["url"], karta)
                if not karty:
                    break
                strona += 1
        szczegoly = 0
        for karta in kandydaci.values():
            if "zamieni" in karta["cena"].lower() or not kwota(karta["cena"]):
                continue
            werdykt = ocen_tytul(karta["tytul"], k.rozmiar)
            if werdykt == "nie":
                continue
            opis = ""
            nieznany_model = model_profilu(karta["tytul"])[0] == "?"
            if (werdykt == "?" or nieznany_model) and szczegoly < MAX_SZCZEGOLOW:
                szczegoly += 1
                opis = _szczegoly(przegladarka.pobierz(karta["url"]).tekst)
                if werdykt == "?":
                    werdykt = ocen_opis(opis, k.rozmiar)
            if werdykt == "nie":
                continue
            pewnosc, powod = do_listy(karta["tytul"], opis)
            if not pewnosc or (pewnosc == "do weryfikacji" and werdykt != "tak"):
                continue
            oferty.append(Oferta(
                model=pewnosc,
                wskazowka="" if pewnosc == "pewny" else powod,
                zrodlo=NAZWA,
                tytul=karta["tytul"],
                url=karta["url"],
                cena=kwota(karta["cena"]),
                rozmiar_pewny=werdykt == "tak",
                stan=karta["stan"],
                wysylka="tak, Przesyłka OLX" if karta["przesylka"] else "do ustalenia ze sprzedającym",
                lokalizacja=karta["lokalizacja"],
                zdjecie=karta["zdjecie"],
                uwagi="do negocjacji" if "negocjac" in karta["cena"].lower() else "",
            ))
    finally:
        przegladarka.zamknij()


ZADANIA = [Zadanie(NAZWA, szukaj, ("www.olx.pl",))]
