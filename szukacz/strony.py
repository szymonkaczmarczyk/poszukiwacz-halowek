import json
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from .dopasowanie import normalizuj, ocen_pole
from .modele import kwota

NAZWY_ROZMIARU = ("size", "rozmiar", "talla", "taglia", "grosse", "große", "pointure", "eu")


@dataclass
class Produkt:
    nazwa: str = ""
    cena: float | None = None
    waluta: str = "PLN"
    dostawa: float | None = None
    rozmiar: str = "?"
    zdjecie: str = ""
    opis: str = ""


def _lista(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def _splaszcz(d):
    if isinstance(d, list):
        for x in d:
            yield from _splaszcz(x)
    elif isinstance(d, dict):
        yield d
        if "@graph" in d:
            yield from _splaszcz(d["@graph"])


def obiekty_ld(soup):
    for s in soup.select('script[type="application/ld+json"]'):
        try:
            dane = json.loads(s.string or s.get_text() or "", strict=False)
        except ValueError:
            continue
        yield from _splaszcz(dane)


def typy(o):
    return {str(t).rstrip("/").rsplit("/", 1)[-1] for t in _lista(o.get("@type"))}


def _scal(cel, zrodlo):
    for klucz, wartosc in zrodlo.items():
        if klucz == "@type" and klucz in cel:
            cel[klucz] = sorted({str(t) for t in _lista(cel[klucz]) + _lista(wartosc)})
        elif klucz not in cel:
            cel[klucz] = wartosc
        elif isinstance(cel[klucz], dict) and isinstance(wartosc, dict):
            cel[klucz] = _scal(dict(cel[klucz]), wartosc)
    return cel


def scalone_ld(soup):
    wynik, po_id = [], {}
    for o in obiekty_ld(soup):
        ident = o.get("@id")
        if isinstance(ident, str) and ident:
            if ident in po_id:
                _scal(po_id[ident], o)
                continue
            po_id[ident] = dict(o)
            wynik.append(po_id[ident])
        else:
            wynik.append(o)
    return wynik


def _oferty(o):
    return [x for x in _lista(o.get("offers")) if isinstance(x, dict)]


def _cena(oferty):
    ceny, waluta = [], None
    for of in oferty:
        c = kwota(of.get("price") if of.get("price") not in (None, "") else of.get("lowPrice"))
        if c:
            ceny.append(c)
            waluta = waluta or of.get("priceCurrency")
    return (min(ceny) if ceny else None), waluta


def _dostepnosc(oferty):
    stany = [normalizuj(of.get("availability", "")) for of in oferty]
    if any(s.endswith(("instock", "limitedavailability", "onlineonly", "preorder", "instoreonly")) for s in stany):
        return True
    if any(s.endswith(("outofstock", "soldout", "discontinued")) for s in stany):
        return False
    return None


def _dostawa(oferty):
    for of in oferty:
        for szczegoly in _lista(of.get("shippingDetails")):
            if isinstance(szczegoly, dict):
                stawka = szczegoly.get("shippingRate") or {}
                if isinstance(stawka, dict) and kwota(stawka.get("value")) is not None:
                    return kwota(stawka.get("value"))
    return None


def _zdjecie(o):
    for z in _lista(o.get("image")):
        if isinstance(z, str):
            return z
        if isinstance(z, dict) and (z.get("url") or z.get("contentUrl")):
            return z.get("url") or z.get("contentUrl")
    return ""


def _rozmiar_wariantu(v):
    r = v.get("size")
    if isinstance(r, dict):
        r = r.get("name") or r.get("value")
    if not r:
        for p in _lista(v.get("additionalProperty")):
            if isinstance(p, dict) and normalizuj(p.get("name", "")) in NAZWY_ROZMIARU:
                r = p.get("value")
    return str(r) if r else None


def _glowny(obiekty, url):
    kandydaci = [o for o in obiekty if typy(o) & {"Product", "ProductGroup"}]
    if not kandydaci:
        return None
    sciezka = urlsplit(url).path.rstrip("/")
    if sciezka:
        for o in kandydaci:
            if sciezka in json.dumps(o, ensure_ascii=False):
                return o
    grupy = [o for o in kandydaci if "ProductGroup" in typy(o)]
    return grupy[0] if grupy else kandydaci[0]


def _werdykt_ld(o, rozmiar, produkt, obiekty):
    if "ProductGroup" in typy(o):
        warianty = [v for v in _lista(o.get("hasVariant")) if isinstance(v, dict)]
    else:
        warianty = [
            p for p in obiekty
            if "Product" in typy(p) and p.get("name") == o.get("name") and _rozmiar_wariantu(p)
        ]
        if len(warianty) < 2:
            return "?"
    return _werdykt_wariantow(warianty, rozmiar, produkt)


def _werdykt_wariantow(warianty, rozmiar, produkt):
    wszystkie = [of for v in warianty for of in _oferty(v)]
    if produkt.cena is None:
        produkt.cena, waluta = _cena(wszystkie)
        produkt.waluta = waluta or produkt.waluta
    z_rozmiarem = [(v, r) for v in warianty if (r := _rozmiar_wariantu(v))]
    if not z_rozmiarem:
        return "?"
    pasujace = [v for v, r in z_rozmiarem if ocen_pole(r, rozmiar) == "tak"]
    dostepne = [v for v in pasujace if _dostepnosc(_oferty(v)) is not False]
    if not dostepne:
        return "nie"
    cena, waluta = _cena([of for v in dostepne for of in _oferty(v)])
    if cena:
        produkt.cena, produkt.waluta = cena, waluta or produkt.waluta
    return "tak"


def _werdykt_magento(html, rozmiar):
    pary = re.findall(r'"label"\s*:\s*"([^"]{1,30})"[^{}]{0,400}?"isInStock"\s*:\s*(true|false)', html)
    pary = [(etykieta, stan == "true") for etykieta, stan in pary if re.search(r"(?<!\d)(3\d|4\d)(?!\d)", etykieta)]
    if not pary:
        return "?"
    if any(ocen_pole(e, rozmiar) == "tak" and dostepny for e, dostepny in pary):
        return "tak"
    return "nie"


def _etykieta_radia(soup, inp):
    if inp.get("id"):
        label = soup.find("label", attrs={"for": inp["id"]})
        if label and label.get_text(strip=True):
            return label.get_text(" ", strip=True)
    if inp.get("title"):
        return inp["title"]
    nastepny = inp.find_next("span")
    return nastepny.get_text(" ", strip=True) if nastepny else ""


def _werdykt_presta(soup, rozmiar):
    zakres = soup.select_one("#add-to-cart-or-refresh .product-variants") or soup.select_one(".product-variants") or soup
    opcje = []
    for sel in zakres.select('select[name^="group["]'):
        for op in sel.find_all("option"):
            tekst = op.get_text(" ", strip=True)
            if re.match(r"\s*(?:eu\s*)?(3\d|4\d)\b", normalizuj(tekst)):
                niedostepna = op.has_attr("disabled") or "niedostepn" in normalizuj(tekst)
                opcje.append((tekst, not niedostepna))
    for inp in zakres.select('input[type="radio"][name^="group["]'):
        etykieta = _etykieta_radia(soup, inp)
        if re.match(r"\s*(?:eu\s*)?(3\d|4\d)\b", normalizuj(etykieta)):
            rodzic = " ".join(inp.parent.get("class", [])) if inp.parent else ""
            opcje.append((etykieta, not (inp.has_attr("disabled") or "disabled" in rodzic or "unavailable" in rodzic)))
    if len(opcje) < 1:
        return "?"
    if any(ocen_pole(t, rozmiar) == "tak" and ok for t, ok in opcje):
        return "tak"
    return "nie"


def _werdykt_przyciski(soup, rozmiar):
    opcje = []
    for el in soup.find_all(["button", "li", "a", "span", "label", "div"]):
        atrybuty = " ".join(
            " ".join(v) if isinstance(v, list) else str(v)
            for k, v in el.attrs.items()
            if k in ("class", "id", "data-element", "data-testid", "data-qa", "name")
        ).lower()
        if not any(s in atrybuty for s in ("size", "talla", "rozmiar", "taille", "groesse", "taglia")):
            continue
        tekst = el.get_text(" ", strip=True)
        if not re.fullmatch(r"(?:eu\s*)?(3\d|4\d)(?:[.,]5|\s[12]/3)?(?:\s*eu)?", normalizuj(tekst)):
            continue
        wylaczony = (
            el.has_attr("disabled")
            or el.get("aria-disabled") == "true"
            or any(s in atrybuty for s in ("disabled", "unavailable", "sold", "agotad", "out-of-stock", "outofstock"))
        )
        opcje.append((tekst, not wylaczony))
    if len(opcje) < 2:
        return "?"
    if any(ocen_pole(t, rozmiar) == "tak" and ok for t, ok in opcje):
        return "tak"
    return "nie"


def _werdykt_woo(soup, rozmiar, produkt):
    formularz = soup.select_one("form.variations_form[data-product_variations]")
    if not formularz:
        return "?"
    try:
        warianty = json.loads(formularz["data-product_variations"])
    except (ValueError, TypeError):
        return "?"
    if not isinstance(warianty, list):
        return "?"
    trafione = False
    for w in warianty:
        for klucz, wartosc in (w.get("attributes") or {}).items():
            if any(n in normalizuj(klucz) for n in ("rozmiar", "size", "roz")) and ocen_pole(str(wartosc), rozmiar) == "tak":
                trafione = True
                if w.get("is_in_stock"):
                    produkt.cena = kwota(w.get("display_price")) or produkt.cena
                    return "tak"
    return "nie" if trafione or warianty else "?"


def analizuj_produkt(html, url, rozmiar):
    soup = BeautifulSoup(html, "lxml")
    produkt = Produkt()
    obiekty = scalone_ld(soup)
    glowny = _glowny(obiekty, url)
    dostepny = None
    werdykt = "?"
    if glowny:
        produkt.nazwa = str(glowny.get("name") or "")
        produkt.zdjecie = _zdjecie(glowny)
        produkt.opis = str(glowny.get("description") or "")
        oferty = _oferty(glowny)
        cena, waluta = _cena(oferty)
        if cena:
            produkt.cena, produkt.waluta = cena, waluta or "PLN"
        produkt.dostawa = _dostawa(oferty)
        dostepny = _dostepnosc(oferty)
        werdykt = _werdykt_ld(glowny, rozmiar, produkt, obiekty)
    if not produkt.nazwa:
        h1 = soup.find("h1")
        produkt.nazwa = h1.get_text(" ", strip=True) if h1 else (soup.title.get_text(strip=True) if soup.title else "")
    if werdykt == "?":
        werdykt = _werdykt_magento(html, rozmiar)
    if werdykt == "?":
        werdykt = _werdykt_presta(soup, rozmiar)
    if werdykt == "?":
        werdykt = _werdykt_woo(soup, rozmiar, produkt)
    if werdykt == "?":
        werdykt = _werdykt_przyciski(soup, rozmiar)
    if werdykt == "?" and dostepny is False:
        werdykt = "nie"
    if produkt.cena is None:
        meta = soup.select_one('meta[property="product:price:amount"], meta[itemprop="price"]')
        if meta and kwota(meta.get("content")):
            produkt.cena = kwota(meta.get("content"))
            waluta = soup.select_one('meta[property="product:price:currency"], meta[itemprop="priceCurrency"]')
            produkt.waluta = (waluta.get("content") if waluta else None) or "PLN"
    produkt.rozmiar = werdykt
    return produkt
