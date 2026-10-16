import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import profil as P
from . import ustawienia as U
from . import wlasne

TYLKO_KATALOG = ("model", "inne_modele", "rozmiary", "id", "wlasny")
LACZONE_LISTY = ("wykluczenia", "kody_wykluczone", "nie_dotyczy")
SLOWNIKI = ("vinted", "olx", "ebay", "goalinn", "rgol", "futbolemotion", "ceneo", "allegro_lokalnie", "odkrywanie", "minimalne_odczyty")


class BladKatalogu(P.BladProfilu):
    pass


@dataclass
class Model:
    id: str
    nazwa: str
    dane: dict


@dataclass
class Marka:
    id: str
    nazwa: str
    plik: Path
    dane: dict
    modele: list = field(default_factory=list)

    def model(self, szukany):
        klucz = P.slug(szukany)
        for m in self.modele:
            if klucz in (m.id, P.slug(m.dane["model"]), P.slug(m.nazwa)):
                return m
        return None


def _czytaj(plik):
    try:
        return tomllib.loads(Path(plik).read_text(encoding="utf-8"))
    except OSError as e:
        raise BladKatalogu(f"nie mogę otworzyć pliku katalogu {plik}: {e}") from e
    except tomllib.TOMLDecodeError as e:
        raise BladKatalogu(f"błąd składni w {Path(plik).name}: {e}") from e


def wspolne(katalog=None):
    katalog = Path(katalog or U.KATALOG_MODELI)
    return _czytaj(katalog / U.PLIK_WSPOLNY.name)


def rozmiary(katalog=None):
    return [str(r) for r in wspolne(katalog).get("rozmiary", [])]


def _marka(plik):
    dane = _czytaj(plik)
    if not dane.get("marka"):
        raise BladKatalogu(f"w {plik.name} brakuje pola marka")
    modele = []
    for wpis in dane.get("model", []):
        if not wpis.get("id") or not wpis.get("model"):
            raise BladKatalogu(f"w {plik.name} każdy [[model]] musi mieć id i model")
        nazwa = wpis.get("nazwa") or f"{dane['marka']} {wpis['model']}"
        modele.append(Model(wpis["id"], nazwa, wpis))
    return Marka(P.slug(plik.stem), dane["marka"], plik, dane, modele)


def _dolacz_wlasne(wynik):
    po_id = {m.id: m for m in wynik}
    for wpis in wlasne.wczytaj():
        marka = po_id.get(wpis["marka"])
        if not marka:
            nazwa = wpis.get("nazwa_marki") or wpis["marka"]
            marka = po_id[wpis["marka"]] = Marka(wpis["marka"], nazwa, U.PLIK_WLASNYCH, {"marka": nazwa})
            wynik.append(marka)
        if marka.model(wpis["id"]):
            continue
        dane = wlasne.dane_modelu(wpis)
        marka.modele.append(Model(dane["id"], f"{marka.nazwa} {dane['model']}", dane))
    return sorted(wynik, key=lambda m: m.nazwa.lower())


def marki(katalog=None):
    katalog = Path(katalog or U.KATALOG_MODELI)
    return _dolacz_wlasne([_marka(plik) for plik in sorted(katalog.glob("*.toml")) if plik.name != U.PLIK_WSPOLNY.name])


def znajdz(marka, model, katalog=None):
    wszystkie = marki(katalog)
    if marka:
        klucz = P.slug(marka)
        kandydaci = [m for m in wszystkie if klucz in (m.id, P.slug(m.nazwa))]
        if not kandydaci:
            raise BladKatalogu(f"nie znam marki {marka!r}, dostępne: {', '.join(m.nazwa for m in wszystkie)}")
    else:
        kandydaci = wszystkie
    trafione = [(m, m.model(model)) for m in kandydaci if m.model(model)]
    if not trafione:
        gdzie = f" marki {kandydaci[0].nazwa}" if marka else ""
        raise BladKatalogu(f"nie znam modelu {model!r}{gdzie}, użyj --lista-modeli")
    if len(trafione) > 1:
        raise BladKatalogu(f"model {model!r} jest u kilku marek ({', '.join(m.nazwa for m, _ in trafione)}), podaj --marka")
    return trafione[0]


def _sklepy(*poziomy):
    wynik = {}
    for poziom in poziomy:
        for sklep in poziom.get("sklep", []):
            wynik[sklep["nazwa"]] = sklep
    return list(wynik.values())


def _inne_modele(marka, model):
    wlasna = model.dane["model"].lower()
    nazwy = list(marka.dane.get("inne_modele", []))
    for m in marka.modele:
        nazwa = m.dane["model"].lower()
        if m is not model and nazwa != wlasna and nazwa not in nazwy:
            nazwy.append(nazwa)
    return nazwy


def scal(wspolne_dane, marka, model):
    poziomy = (wspolne_dane, marka.dane, model.dane)
    dane = {}
    for poziom in poziomy:
        for klucz, wartosc in poziom.items():
            if klucz in TYLKO_KATALOG or klucz == "sklep":
                continue
            if klucz in LACZONE_LISTY:
                dane[klucz] = dane.get(klucz, []) + [w for w in wartosc if w not in dane.get(klucz, [])]
            elif klucz in SLOWNIKI:
                dane[klucz] = {**dane.get(klucz, {}), **wartosc}
            else:
                dane[klucz] = wartosc
    dane["marka"] = marka.nazwa
    dane["model"] = model.dane["model"]
    dane["nazwa"] = model.nazwa
    dane.setdefault("frazy", [
        f"{marka.nazwa} {model.dane['model']}".lower(),
        f"halowki {marka.nazwa} {model.dane['model']}".lower(),
    ])
    dane["inne_modele_marki"] = _inne_modele(marka, model)
    dane["sklep"] = _sklepy(*poziomy)
    dane["identyfikator"] = f"{marka.id}-{model.id}"
    return dane


def profil(marka, model, rozmiar=None, katalog=None):
    znaleziona, znaleziony = znajdz(marka, model, katalog)
    dane = scal(wspolne(katalog), znaleziona, znaleziony)
    dane["rozmiar"] = str(rozmiar or dane.get("rozmiar") or U.DOMYSLNY_ROZMIAR)
    return P.z_danych(dane, znaleziona.plik)
