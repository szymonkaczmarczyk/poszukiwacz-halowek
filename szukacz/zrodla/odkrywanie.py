import json
import os
import time
from urllib.parse import unquote, urlsplit

from .. import ustawienia as U
from ..dopasowanie import ocen_tytul, to_szukany_model
from ..modele import Oferta, klucz_url
from ..siec import ZrodloNiedostepne, host
from ..silnik import Zadanie
from ..strony import analizuj_produkt
from .sklepy import sklepy_profilu

NAZWA = "Odkrywanie (Google)"
API = "https://serpapi.com/search.json"
CO_ILE_DNI = 7
MAX_STRON_NA_URUCHOMIENIE = 25

RYNKI_DOMYSLNE = [("pl", "pl"), ("de", "de"), ("es", "es"), ("it", "it"), ("fr", "fr"), ("uk", "en")]

DOMENY_POMIJANE = (
    "vinted.", "olx.", "allegro", "ebay.", "ceneo.pl", "futbolemotion.com", "tradeinn.com", "r-gol.com",
    "decathlon.", "zalando.", "amazon.", "youtube.", "facebook.", "instagram.",
    "pinterest.", "reddit.", "wikipedia.", "tiktok.", "twitter.", "x.com", "google.", "wallapop.",
    "kleinanzeigen.", "milanuncios.", "leboncoin.", "subito.", "aliexpress.", "temu.", "shein.",
    "mybaze.", "sportcentercesena.", "solopeloteros.",
)

WALUTY_EUROPEJSKIE = {"PLN", "EUR", "GBP", "CZK", "HUF", "RON", "SEK", "DKK", "CHF", "NOK", "BGN"}

KONCOWKI_POZA_ZASIEGIEM =(".ru", ".ua", ".by", ".pe", ".mx", ".ar", ".cl", ".co", ".br", ".hk", ".cn", ".in", ".us")


def skonfigurowany():
    return bool(os.environ.get("SERPAPI_KEY"))


def frazy(k):
    p = k.profil
    if p.odkrywanie.get("frazy"):
        return [(p.podstaw(f, k.rozmiar), kraj, jezyk) for f, kraj, jezyk in p.odkrywanie["frazy"]]
    return [(f"{p.fraza} {k.rozmiar}", kraj, jezyk) for kraj, jezyk in RYNKI_DOMYSLNE]


def _plik(k):
    return k.profil.katalog_danych / "odkryte.json"


def _wczytaj(k):
    try:
        return json.loads(_plik(k).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"ostatnie_wyszukiwanie": 0, "adresy": {}}


def _zapisz(k, dane):
    _plik(k).parent.mkdir(parents=True, exist_ok=True)
    _plik(k).write_text(json.dumps(dane, ensure_ascii=False, indent=1), encoding="utf-8")


def pomijana(url, profil):
    h = host(url)
    sklepy = {host(s.lista) for s in sklepy_profilu(profil)}
    return (
        any(d in h for d in DOMENY_POMIJANE)
        or h in sklepy
        or h.endswith(KONCOWKI_POZA_ZASIEGIEM)
        or any(h == b or h.endswith("." + b) for b in U.ZBANOWANE_HOSTY)
    )


def _z_adresem(url, tytul):
    return f"{tytul} {unquote(urlsplit(url).path).replace('-', ' ').replace('_', ' ')}"


def kandydat(url, tytul, profil, rozmiar):
    return (
        not pomijana(url, profil)
        and to_szukany_model(_z_adresem(url, tytul), profil.marka)
        and ocen_tytul(tytul, rozmiar) != "nie"
    )


def _szukaj_w_google(k, dane):
    nowe = 0
    for wpis in dane["adresy"].values():
        wpis.pop("nie_produkt", None)
    for fraza, kraj, jezyk in frazy(k):
        odp = k.http.zapytanie(
            "GET",
            API,
            params={"engine": "google", "q": fraza, "gl": kraj, "hl": jezyk, "num": 30, "api_key": os.environ["SERPAPI_KEY"]},
            naglowki={"Accept": "application/json"},
            cache=False,
        )
        if odp.status != 200:
            try:
                blad = odp.json().get("error", "")
            except ValueError:
                blad = ""
            raise ZrodloNiedostepne(f"SerpAPI: HTTP {odp.status} {blad}".strip())
        for w in odp.json().get("organic_results") or []:
            url = w.get("link", "")
            if not url.startswith("http") or not kandydat(url, w.get("title", ""), k.profil, k.rozmiar):
                continue
            klucz = klucz_url(url)
            if klucz not in dane["adresy"]:
                dane["adresy"][klucz] = {"url": url, "tytul": w.get("title", ""), "fraza": fraza, "znaleziono": time.strftime("%Y-%m-%d")}
                nowe += 1
    dane["ostatnie_wyszukiwanie"] = time.time()
    return nowe


def szukaj(k, oferty):
    if not skonfigurowany():
        raise ZrodloNiedostepne("brak klucza SERPAPI_KEY w pliku .env (zobacz README)")
    dane = _wczytaj(k)
    if k.odkrywaj or time.time() - dane.get("ostatnie_wyszukiwanie", 0) > CO_ILE_DNI * 86400:
        nowe = _szukaj_w_google(k, dane)
        _zapisz(k, dane)
        k.log(NAZWA, f"wyszukiwanie w Google: {nowe} nowych stron, razem zapamiętanych {len(dane['adresy'])}")
    else:
        dni = (time.time() - dane["ostatnie_wyszukiwanie"]) / 86400
        k.log(NAZWA, f"ostatnie wyszukiwanie {dni:.0f} dni temu, sprawdzam {len(dane['adresy'])} zapamiętanych stron", zawsze=False)
    do_sprawdzenia = [w for w in dane["adresy"].values() if not w.get("nie_produkt") and not pomijana(w["url"], k.profil)]
    for wpis in do_sprawdzenia[:MAX_STRON_NA_URUCHOMIENIE]:
        try:
            odp = k.http.get(wpis["url"])
        except ZrodloNiedostepne as e:
            k.log(NAZWA, f"pomijam {host(wpis['url'])}: {e}", zawsze=False)
            continue
        if odp.status in (404, 410):
            wpis["nie_produkt"] = True
            continue
        if odp.status != 200:
            continue
        k.zlicz(1)
        p = analizuj_produkt(odp.tekst, wpis["url"], k.rozmiar)
        if not p.cena or not p.nazwa:
            wpis["nie_produkt"] = True
            continue
        if (p.waluta or "PLN").upper() not in WALUTY_EUROPEJSKIE:
            wpis["nie_produkt"] = True
            continue
        nazwa = p.nazwa
        z_adresem = _z_adresem(wpis["url"], nazwa)
        if not to_szukany_model(z_adresem, k.profil.marka) or p.rozmiar == "nie" or ocen_tytul(nazwa, k.rozmiar) == "nie":
            continue
        polski = host(wpis["url"]).endswith(".pl")
        oferty.append(Oferta(
            zrodlo=f"Odkryte: {host(wpis['url']).removeprefix('www.')}",
            tytul=nazwa,
            url=wpis["url"],
            cena=p.cena,
            waluta=p.waluta or "PLN",
            dostawa=p.dostawa if polski else None,
            dostawa_szacunkowa=U.WYSYLKA_SKLEPU_W_POLSCE if polski else None,
            rozmiar_pewny=p.rozmiar == "tak",
            stan="nowe",
            wysylka="tak, sklep w Polsce" if polski else "sprawdź, czy sklep wysyła do PL",
            zdjecie=p.zdjecie,
            uwagi=f"znalezione w Google: „{wpis['fraza']}”",
        ))
    _zapisz(k, dane)


ZADANIA = [Zadanie(NAZWA, szukaj, ("serpapi.com",))]
