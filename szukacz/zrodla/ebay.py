import os
from urllib.parse import quote

from ..dopasowanie import normalizuj, ocen_pole, ocen_tytul, to_szukany_model
from ..modele import Oferta, kwota
from ..siec import ZrodloNiedostepne
from ..silnik import Zadanie

NAZWA = "eBay"
API = "https://api.ebay.com"
RYNKI = ["EBAY_DE", "EBAY_ES", "EBAY_IT", "EBAY_FR", "EBAY_GB"]
KATEGORIE_OBUWIA_SPORTOWEGO = ["15709", "109133"]
MAX_SZCZEGOLOW = 15
NAZWY_ROZMIARU = ("grosse", "große", "size", "taglia", "talla", "pointure", "rozmiar")


def kategorie(k):
    return [str(c) for c in k.profil.ebay.get("kategorie") or KATEGORIE_OBUWIA_SPORTOWEGO]


def skonfigurowany():
    return bool(os.environ.get("EBAY_CLIENT_ID") and os.environ.get("EBAY_CLIENT_SECRET"))


def _token(k):
    odp = k.http.post(
        f"{API}/identity/v1/oauth2/token",
        dane={"grant_type": "client_credentials", "scope": "https://api.ebay.com/oauth/api_scope"},
        naglowki={"Content-Type": "application/x-www-form-urlencoded"},
        auth=(os.environ["EBAY_CLIENT_ID"], os.environ["EBAY_CLIENT_SECRET"]),
    )
    if odp.status != 200:
        try:
            blad = odp.json().get("error", "")
        except ValueError:
            blad = ""
        if blad == "invalid_client":
            raise ZrodloNiedostepne(
                "eBay odrzucił klucze (invalid_client). Sprawdź, czy klucz Production jest aktywny: "
                "developer.ebay.com, Application Keys, Marketplace Account Deletion (zobacz README)"
            )
        raise ZrodloNiedostepne(f"eBay odrzucił klucze API (HTTP {odp.status} {blad})".strip())
    return odp.json()["access_token"]


def _rozmiar_z_aspektow(k, token, rynek, id_przedmiotu):
    odp = k.http.zapytanie(
        "GET",
        f"{API}/buy/browse/v1/item/{quote(id_przedmiotu, safe='|')}",
        naglowki={"Authorization": f"Bearer {token}", "X-EBAY-C-MARKETPLACE-ID": rynek},
        cache=False,
    )
    if odp.status != 200:
        return "?"
    for aspekt in odp.json().get("localizedAspects") or []:
        if any(n in normalizuj(aspekt.get("name", "")) for n in NAZWY_ROZMIARU):
            return ocen_pole(str(aspekt.get("value", "")), k.rozmiar)
    return "?"


def szukaj(k, oferty):
    if not skonfigurowany():
        raise ZrodloNiedostepne("brak kluczy eBay API w pliku .env (zobacz README)")
    token = _token(k)
    widziane = set()
    szczegoly = 0
    for rynek, kategoria in ((r, c) for r in RYNKI for c in kategorie(k)):
        odp = k.http.zapytanie(
            "GET",
            f"{API}/buy/browse/v1/item_summary/search",
            params={"q": k.profil.ebay.get("zapytanie") or k.profil.fraza, "category_ids": kategoria, "filter": "deliveryCountry:PL", "limit": 200},
            naglowki={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": rynek,
                "X-EBAY-C-ENDUSERCTX": "contextualLocation=country%3DPL%2Czip%3D00-001",
            },
            cache=False,
        )
        if odp.status != 200:
            k.log(NAZWA, f"{rynek}/{kategoria}: HTTP {odp.status}")
            continue
        przedmioty = odp.json().get("itemSummaries") or []
        k.zlicz(len(przedmioty))
        k.log(NAZWA, f"{rynek}/{kategoria}: {len(przedmioty)} ofert", zawsze=False)
        for p in przedmioty:
            if not set(p.get("leafCategoryIds") or []) & set(kategorie(k)):
                continue
            tytul = p.get("title", "")
            klucz = p.get("legacyItemId") or p.get("itemId")
            if klucz in widziane or not to_szukany_model(tytul):
                continue
            widziane.add(klucz)
            werdykt = ocen_tytul(tytul, k.rozmiar)
            if werdykt == "?" and szczegoly < MAX_SZCZEGOLOW and p.get("itemId"):
                szczegoly += 1
                werdykt = _rozmiar_z_aspektow(k, token, rynek, p["itemId"])
            if werdykt == "nie":
                continue
            cena = p.get("price") or {}
            wysylki = p.get("shippingOptions") or []
            koszt = (wysylki[0].get("shippingCost") or {}) if wysylki else {}
            oferty.append(Oferta(
                zrodlo=f"{NAZWA} ({rynek.split('_')[1]})",
                tytul=tytul,
                url=p.get("itemWebUrl", "").split("?")[0],
                cena=kwota(cena.get("value")),
                waluta=cena.get("currency", "EUR"),
                dostawa=kwota(koszt.get("value")),
                rozmiar_pewny=werdykt == "tak",
                stan=p.get("condition", ""),
                wysylka="tak, wysyłka do PL",
                lokalizacja=(p.get("itemLocation") or {}).get("country", ""),
                zdjecie=(p.get("image") or {}).get("imageUrl", ""),
            ))


ZADANIA = [Zadanie(NAZWA, szukaj, ("api.ebay.com",))]
