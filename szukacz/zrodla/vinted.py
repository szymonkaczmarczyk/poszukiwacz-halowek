import re

from bs4 import BeautifulSoup

from ..dopasowanie import normalizuj, ocen_pole, ocen_tytul, to_marka
from ..modele import Oferta, kwota
from ..silnik import Zadanie
from ..weryfikacja import do_listy, wymaga_opisu

NAZWA = "Vinted"
BAZA = "https://www.vinted.pl"
KATALOG = f"{BAZA}/catalog"
MAX_OPISOW = 8

OPIS_KARTY = re.compile(
    r"^(?P<tytul>.*?), Marka: (?P<marka>.*?)"
    r"(?:, Stan: (?P<stan>.*?))?"
    r"(?:, Rozmiar: (?P<rozmiar>.*?))?"
    r", (?P<cena>[\d\s .,]+) zł(?:, (?P<suma>[\d\s .,]+) zł)?(?:\s.*)?$",
    re.S,
)


def id_marki(k):
    p = k.profil
    if p.vinted.get("marka_id"):
        return p.vinted["marka_id"]
    odp = k.http.get(f"{BAZA}/api/v2/brands", params={"keyword": p.marka}, naglowki={"Accept": "application/json"}, godziny_cache=24 * 30)
    if odp.status != 200:
        return None
    try:
        marki = odp.json().get("brands") or []
    except ValueError:
        return None
    szukana = normalizuj(p.marka)
    trafiona = next((m for m in marki if normalizuj(m.get("title")) == szukana), None)
    if trafiona:
        k.log(NAZWA, f"marka {p.marka} ma na Vinted id {trafiona['id']} (możesz je wpisać do profilu jako vinted.marka_id)", zawsze=False)
    return trafiona["id"] if trafiona else None


def wyszukiwania(k, marka):
    p = k.profil
    lista = []
    if marka:
        lista.append(({"search_text": p.model, "brand_ids[]": marka, "order": "price_low_to_high"}, 3))
    lista.append(({"search_text": p.fraza, "order": "relevance"}, 1))
    rozmiar_id = (p.vinted.get("rozmiary") or {}).get(k.rozmiar)
    if marka and rozmiar_id and p.vinted.get("katalog_obuwia"):
        lista.append(({
            "brand_ids[]": marka,
            "catalog[]": p.vinted["katalog_obuwia"],
            "size_ids[]": rozmiar_id,
            "order": "price_low_to_high",
        }, 2))
    return lista


def _karty(html):
    soup = BeautifulSoup(html, "lxml")
    for a in soup.select('a[data-testid$="--overlay-link"]'):
        m = re.search(r"product-item-id-(\d+)--overlay-link", a.get("data-testid", ""))
        d = OPIS_KARTY.match(a.get("title") or "")
        if not m or not d:
            continue
        img = soup.select_one(f'img[data-testid="product-item-id-{m.group(1)}--image--img"]')
        yield {
            "id": m.group(1),
            "zdjecie": img.get("src", "") if img else "",
            **d.groupdict(),
        }


def _opis(k, id_przedmiotu):
    odp = k.http.get(f"{BAZA}/items/{id_przedmiotu}", godziny_cache=24)
    if odp.status != 200:
        return ""
    el = BeautifulSoup(odp.tekst, "lxml").select_one('[itemprop="description"]')
    return el.get_text(" ", strip=True) if el else ""


def szukaj(k, oferty):
    widziane = set()
    opisy = 0
    marka = id_marki(k)
    for parametry, strony in wyszukiwania(k, marka):
        for strona in range(1, strony + 1):
            odp = k.http.get(KATALOG, params={**parametry, "page": strona}, naglowki={"Referer": f"{BAZA}/"})
            if odp.status != 200:
                k.log(NAZWA, f"HTTP {odp.status} dla strony {strona}")
                break
            karty = list(_karty(odp.tekst))
            k.zlicz(len(karty))
            opis_wyszukiwania = parametry.get("search_text", f"{k.profil.marka}, rozmiar {k.rozmiar}")
            k.log(NAZWA, f"{opis_wyszukiwania} strona {strona}: {len(karty)} ogłoszeń", zawsze=False)
            nowe = 0
            for karta in karty:
                if karta["id"] in widziane:
                    continue
                widziane.add(karta["id"])
                nowe += 1
                if not to_marka(karta["tytul"], karta["marka"]):
                    continue
                werdykt = ocen_pole(karta["rozmiar"], k.rozmiar) if karta["rozmiar"] else ocen_tytul(karta["tytul"], k.rozmiar)
                if werdykt == "nie":
                    continue
                opis = ""
                if wymaga_opisu(karta["tytul"]) and opisy < MAX_OPISOW:
                    opisy += 1
                    opis = _opis(k, karta["id"])
                pewnosc, powod = do_listy(karta["tytul"], opis)
                if not pewnosc or (pewnosc == "do weryfikacji" and werdykt != "tak"):
                    continue
                cena = kwota(karta["suma"]) or kwota(karta["cena"])
                if not cena:
                    continue
                oferty.append(Oferta(
                    zrodlo=NAZWA,
                    tytul=karta["tytul"],
                    url=f"{BAZA}/items/{karta['id']}",
                    cena=cena,
                    rozmiar_pewny=werdykt == "tak",
                    stan=karta["stan"] or "",
                    wysylka="tak, przez Vinted",
                    zdjecie=karta["zdjecie"],
                    uwagi="cena z opłatą za ochronę kupującego",
                    model=pewnosc,
                    wskazowka="" if pewnosc == "pewny" else powod,
                ))
            if nowe == 0 or len(karty) < 20:
                break


ZADANIA = [Zadanie(NAZWA, szukaj, ("www.vinted.pl",))]
