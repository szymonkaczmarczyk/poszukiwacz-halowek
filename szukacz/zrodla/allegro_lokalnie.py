from urllib.parse import quote

from bs4 import BeautifulSoup

from ..dopasowanie import model_profilu, ocen_opis, ocen_tytul, to_marka
from ..modele import Oferta, kwota
from ..silnik import Zadanie
from ..strony import obiekty_ld, typy
from ..weryfikacja import do_listy

NAZWA = "Allegro Lokalnie"
MAX_SZCZEGOLOW = 6


def _pozycje(html):
    soup = BeautifulSoup(html, "lxml")
    for o in obiekty_ld(soup):
        if "ItemList" not in typy(o):
            continue
        for el in o.get("itemListElement") or []:
            item = el.get("item") if isinstance(el, dict) else None
            if isinstance(item, dict) and item.get("url"):
                yield item


def _opis(html):
    soup = BeautifulSoup(html, "lxml")
    for o in obiekty_ld(soup):
        if "Product" in typy(o):
            return str(o.get("description") or "")
    return ""


def szukaj(k, oferty):
    kandydaci = {}
    for fraza in k.profil.allegro_lokalnie.get("frazy") or k.profil.frazy:
        odp = k.http.get(f"https://allegrolokalnie.pl/oferty/q/{quote(fraza)}")
        if odp.status != 200:
            k.log(NAZWA, f"HTTP {odp.status}")
            continue
        pozycje = list(_pozycje(odp.tekst))
        k.zlicz(len(pozycje))
        for item in pozycje:
            nazwa = item.get("name", "")
            if to_marka(nazwa) and model_profilu(nazwa)[0] in ("model", "?"):
                kandydaci.setdefault(item["url"], item)
    szczegoly = 0
    for url, item in kandydaci.items():
        nazwa = item.get("name", "")
        of = item.get("offers") if isinstance(item.get("offers"), dict) else {}
        cena = kwota(of.get("price"))
        if not cena:
            continue
        werdykt = ocen_tytul(nazwa, k.rozmiar)
        if werdykt == "nie":
            continue
        opis = ""
        if (werdykt == "?" or model_profilu(nazwa)[0] == "?") and szczegoly < MAX_SZCZEGOLOW:
            szczegoly += 1
            odp = k.http.get(url)
            if odp.status == 200:
                opis = _opis(odp.tekst)
                if werdykt == "?":
                    werdykt = ocen_opis(opis, k.rozmiar)
        if werdykt == "nie":
            continue
        pewnosc, powod = do_listy(nazwa, opis)
        if not pewnosc or (pewnosc == "do weryfikacji" and werdykt != "tak"):
            continue
        zdjecie = item.get("image")
        if isinstance(zdjecie, dict):
            zdjecie = zdjecie.get("url") or zdjecie.get("contentUrl")
        stan = str(item.get("itemCondition", ""))
        oferty.append(Oferta(
            zrodlo=NAZWA,
            tytul=nazwa,
            url=url,
            cena=cena,
            waluta=of.get("priceCurrency") or "PLN",
            rozmiar_pewny=werdykt == "tak",
            stan="nowe" if "NewCondition" in stan else ("używane" if "UsedCondition" in stan else ""),
            wysylka="sprawdź w ogłoszeniu",
            zdjecie=zdjecie or "",
            model=pewnosc,
            wskazowka="" if pewnosc == "pewny" else powod,
        ))


ZADANIA = [Zadanie(NAZWA, szukaj, ("allegrolokalnie.pl",))]
