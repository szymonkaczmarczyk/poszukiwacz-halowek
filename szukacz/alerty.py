import json
import os
import secrets
import threading
import time
from contextlib import contextmanager

from . import katalog, powiadomienia, przebieg
from . import ustawienia as U
from .blokada import BlokadaPliku

MAKS_ALERTOW = 20
MAKS_TRAFIEN = 40
DNI_PAMIECI = 45
PROG_OBNIZKI = 1.0
GRUPY_POMIJANE = ("weryfikacja",)
FORMAT_CZASU = "%Y-%m-%d %H:%M"
POLA_PUBLICZNE = ("id", "marka", "model", "nazwa", "rozmiar", "max_cena", "tylko_pewne", "utworzono", "sprawdzono", "stan")

_blokada = threading.Lock()


class BladAlertow(Exception):
    def __init__(self, komunikat, kod=422):
        super().__init__(komunikat)
        self.kod = kod


def teraz():
    return time.strftime(FORMAT_CZASU)


def wczytaj():
    try:
        dane = json.loads(U.PLIK_ALERTOW.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [a for a in dane.get("alerty", []) if a.get("id") and a.get("marka") and a.get("model") and a.get("rozmiar")]


def _zapisz(alerty):
    plik = U.PLIK_ALERTOW
    plik.parent.mkdir(parents=True, exist_ok=True)
    tymczasowy = plik.with_suffix(".tmp")
    tymczasowy.write_text(json.dumps({"alerty": alerty}, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tymczasowy, plik)


@contextmanager
def _edycja():
    with _blokada, BlokadaPliku(U.PLIK_ALERTOW.with_suffix(".lock")):
        alerty = wczytaj()
        yield alerty
        _zapisz(alerty)


def opis(alert):
    przeczytano = alert.get("przeczytano", "")
    trafienia = alert.get("trafienia", [])
    return {
        **{pole: alert.get(pole) for pole in POLA_PUBLICZNE},
        "trafienia": trafienia,
        "nowych": sum(1 for t in trafienia if t["kiedy"] > przeczytano),
    }


def lista():
    return [opis(a) for a in wczytaj()]


def _trafienie(oferta, typ, roznica, kiedy):
    return {
        "typ": typ,
        "klucz": oferta["klucz"],
        "url": oferta.get("url") or oferta["klucz"],
        "tytul": oferta.get("tytul", ""),
        "zrodlo": oferta.get("zrodlo", ""),
        "cena": round(oferta["suma_pln"], 2),
        "roznica": round(roznica, 2) if roznica else None,
        "kiedy": kiedy,
    }


def porownaj(alert, oferty, kiedy):
    widziane = alert.setdefault("widziane", {})
    trafienia = []
    for oferta in oferty:
        klucz, cena = oferta.get("klucz"), oferta.get("suma_pln")
        if not klucz or cena is None or oferta.get("grupa") in GRUPY_POMIJANE:
            continue
        wpis = widziane.get(klucz)
        if wpis is None:
            trafienia.append(_trafienie(oferta, "nowa", None, kiedy))
        elif cena < wpis["cena"] - PROG_OBNIZKI:
            trafienia.append(_trafienie(oferta, "tansza", wpis["cena"] - cena, kiedy))
        najnizsza = cena if wpis is None else min(cena, wpis["cena"])
        widziane[klucz] = {"cena": round(najnizsza, 2), "kiedy": kiedy}
    granica = time.strftime(FORMAT_CZASU, time.localtime(time.mktime(time.strptime(kiedy, FORMAT_CZASU)) - DNI_PAMIECI * 86400))
    for klucz in [k for k, w in widziane.items() if w["kiedy"] < granica]:
        del widziane[klucz]
    return trafienia


def _ten_sam(a, wpis):
    return all(a.get(pole) == wpis[pole] for pole in ("marka", "model", "rozmiar", "max_cena", "tylko_pewne"))


def dodaj(wpisy):
    dodane, pominiete = [], []
    kiedy = teraz()
    with _edycja() as alerty:
        for wpis in wpisy:
            if any(_ten_sam(a, wpis) for a in alerty):
                pominiete.append(wpis["rozmiar"])
                continue
            if len(alerty) >= MAKS_ALERTOW:
                raise BladAlertow(f"możesz mieć najwyżej {MAKS_ALERTOW} alertów, usuń któryś na stronie alertów", 409)
            alert = {
                **{pole: wpis[pole] for pole in ("marka", "model", "nazwa", "rozmiar", "max_cena", "tylko_pewne")},
                "id": secrets.token_hex(6),
                "utworzono": kiedy,
                "sprawdzono": None,
                "stan": "czeka na pierwsze sprawdzenie",
                "przeczytano": kiedy,
                "widziane": {},
                "trafienia": [],
            }
            porownaj(alert, wpis.get("oferty", []), kiedy)
            alerty.append(alert)
            dodane.append(opis(alert))
    return dodane, pominiete


def usun(identyfikator):
    with _edycja() as alerty:
        przed = len(alerty)
        alerty[:] = [a for a in alerty if a["id"] != identyfikator]
        return len(alerty) < przed


def oznacz_przeczytane():
    kiedy = teraz()
    with _edycja() as alerty:
        for alert in alerty:
            alert["przeczytano"] = kiedy


def _oferty_z_wyszukiwania(alert, wykonaj):
    try:
        profil = katalog.profil(alert["marka"], alert["model"])
    except katalog.BladKatalogu:
        return None, "nie ma już tego modelu w katalogu"
    opcje = przebieg.Opcje(rozmiar=alert["rozmiar"], max_cena=alert.get("max_cena"), tylko_pewne=alert.get("tylko_pewne", False), odswiez=True)
    try:
        wynik = wykonaj(profil, opcje)
    except Exception as e:
        return None, f"błąd wyszukiwania ({e.__class__.__name__})"
    if not any(z["status"] == "ok" for z in wynik.dane.get("zrodla", [])):
        return None, "żadne źródło nie odpowiedziało, spróbuję przy następnym sprawdzeniu"
    return wynik.dane.get("oferty", []), "ok"


def sprawdz_wszystkie(wykonaj=przebieg.wykonaj, powiadom=powiadomienia.powiadom, wypisz=print):
    raport = []
    with BlokadaPliku(U.PLIK_BLOKADY_WYSZUKIWANIA):
        for alert in wczytaj():
            oferty, stan = _oferty_z_wyszukiwania(alert, wykonaj)
            kiedy = teraz()
            trafienia = []
            with _edycja() as alerty:
                biezacy = next((a for a in alerty if a["id"] == alert["id"]), None)
                if biezacy is None:
                    continue
                biezacy["sprawdzono"] = kiedy
                biezacy["stan"] = stan
                if oferty is not None:
                    trafienia = porownaj(biezacy, oferty, kiedy)
                    biezacy["trafienia"] = (trafienia + biezacy.get("trafienia", []))[:MAKS_TRAFIEN]
            kanaly = powiadom(biezacy, trafienia) if trafienia else {}
            opis_kanalow = ", ".join(f"{k}: {v}" for k, v in kanaly.items())
            wypisz(f"{kiedy} {biezacy['nazwa']} {biezacy['rozmiar']}: {stan}, {powiadomienia.podsumowanie(trafienia) or 'bez zmian'}" + (f" ({opis_kanalow})" if opis_kanalow else ""))
            raport.append({"id": biezacy["id"], "stan": stan, "trafienia": len(trafienia), "kanaly": kanaly})
    return raport
