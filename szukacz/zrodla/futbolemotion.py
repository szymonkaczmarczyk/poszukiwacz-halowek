from ..dopasowanie import ocen_pole, to_szukany_model
from ..modele import Oferta, kwota
from ..silnik import Zadanie

NAZWA = "Fútbol Emotion"
API = "https://api.empathy.co/search/v1/query/soloporteros/search"
WYSYLKA_DO_PL = 35.02


def szukaj(k, oferty):
    odp = k.http.get(
        API,
        params={
            "internal": "true",
            "query": k.profil.futbolemotion.get("zapytanie") or k.profil.fraza,
            "start": 0,
            "rows": 48,
            "instance": "soloporteros",
            "scope": "desktop",
            "lang": "pl",
            "currency": "PLN",
            "portal": 1,
            "store": "PL",
            "rate": 1,
        },
        naglowki={
            "Accept": "application/json",
            "Origin": "https://pl.futbolemotion.com",
            "Referer": "https://pl.futbolemotion.com/",
        },
    )
    if odp.status != 200:
        k.log(NAZWA, f"HTTP {odp.status}")
        return
    produkty = (odp.json().get("catalog") or {}).get("content") or []
    k.zlicz(len(produkty))
    k.log(NAZWA, f"{len(produkty)} produktów w wynikach", zawsze=False)
    for p in produkty:
        nazwa = p.get("name") or p.get("__name") or ""
        if not to_szukany_model(nazwa, k.profil.marka):
            continue
        rozmiary = [str(r) for r in p.get("sizes") or []]
        if not any(ocen_pole(r, k.rozmiar) == "tak" for r in rozmiary):
            continue
        cena = kwota(p.get("pvpVariants_PL_PLN_1")) or kwota(p.get("salePrice")) or kwota(p.get("price"))
        regularna = kwota(p.get("price"))
        url = p.get("url") or p.get("__url") or ""
        wariant = url.rstrip("/").rsplit("/", 1)[-1]
        uwagi = f"przecena z {regularna:.2f} zł".replace(".", ",") if regularna and cena and regularna > cena + 0.5 else ""
        oferty.append(Oferta(
            zrodlo=NAZWA,
            tytul=f"{nazwa} ({wariant})",
            url=url,
            cena=cena,
            dostawa=WYSYLKA_DO_PL,
            rozmiar_pewny=True,
            stan="nowe",
            wysylka="tak, do PL (sklep z Hiszpanii, 5–7 dni)",
            zdjecie=(p.get("__images") or [p.get("image") or ""])[0],
            uwagi=uwagi,
        ))


ZADANIA = [Zadanie(NAZWA, szukaj, ("api.empathy.co",))]
