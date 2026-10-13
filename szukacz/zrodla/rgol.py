from ..dopasowanie import ocen_pole, to_szukany_model
from ..modele import Oferta, kwota
from ..silnik import Zadanie

NAZWA = "R-GOL"
API = "https://live.luigisbox.tech/search"
TRACKER = "235446-272522"
BAZA = "https://www.r-gol.com/pl"


def _lista(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def szukaj(k, oferty):
    odp = k.http.get(
        API,
        params={"tracker_id": TRACKER, "q": k.profil.rgol.get("zapytanie") or k.profil.marka, "f[]": "type:product", "size": 100},
        naglowki={
            "Accept": "application/json",
            "Origin": "https://www.r-gol.com",
            "Referer": "https://www.r-gol.com/",
        },
    )
    if odp.status != 200:
        k.log(NAZWA, f"HTTP {odp.status}")
        return
    trafienia = (odp.json().get("results") or {}).get("hits") or []
    k.zlicz(len(trafienia))
    k.log(NAZWA, f"{len(trafienia)} produktów w wynikach", zawsze=False)
    for t in trafienia:
        a = t.get("attributes") or {}
        tytul = str(a.get("title") or "")
        producent = " ".join(str(p) for p in _lista(a.get("Producent")))
        if not to_szukany_model(tytul, producent):
            continue
        rozmiary = [str(r) for r in _lista(a.get("Rozmiar") or a.get("size"))]
        if not any(ocen_pole(r, k.rozmiar) == "tak" for r in rozmiary):
            continue
        ceny = a.get("prices1") or {}
        cena = kwota(ceny.get("promo_brutto")) or kwota(a.get("price1")) or kwota(ceny.get("brutto"))
        if not cena:
            continue
        regularna = kwota(ceny.get("brutto"))
        sciezka = str(t.get("url") or "")
        oferty.append(Oferta(
            zrodlo=NAZWA,
            tytul=tytul,
            url=BAZA + (sciezka if sciezka.startswith("/") else "/" + sciezka),
            cena=cena,
            rozmiar_pewny=True,
            stan="nowe",
            wysylka="tak, sklep w Polsce",
            zdjecie=str(a.get("image_link") or ""),
            uwagi=f"przecena z {regularna:.2f} zł".replace(".", ",") if regularna and regularna > cena + 0.5 else "",
        ))


ZADANIA = [Zadanie(NAZWA, szukaj, ("live.luigisbox.tech",))]
