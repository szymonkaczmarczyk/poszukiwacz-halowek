import re
import tomllib
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote, quote_plus

from . import ustawienia as U

_aktywny = None


class BladProfilu(Exception):
    pass


def slug(tekst):
    tekst = unicodedata.normalize("NFKD", tekst).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", tekst.lower()).strip("-") or "profil"


@dataclass
class Profil:
    plik: Path
    nazwa: str
    marka: str
    model: str
    rozmiar: str
    frazy: list
    aliasy_marki: list = field(default_factory=list)
    opis_wykluczen: str = ""
    wykluczenia: list = field(default_factory=list)
    kody_modelu: list = field(default_factory=list)
    kody_wykluczone: list = field(default_factory=list)
    inne_modele_marki: list = field(default_factory=list)
    nie_dotyczy: list = field(default_factory=list)
    slowa_kategorii: list = field(default_factory=list)
    wskazowki: list = field(default_factory=list)
    wskazowka_zdjec: str = ""
    vinted: dict = field(default_factory=dict)
    olx: dict = field(default_factory=dict)
    ebay: dict = field(default_factory=dict)
    goalinn: dict = field(default_factory=dict)
    rgol: dict = field(default_factory=dict)
    futbolemotion: dict = field(default_factory=dict)
    ceneo: dict = field(default_factory=dict)
    allegro_lokalnie: dict = field(default_factory=dict)
    odkrywanie: dict = field(default_factory=dict)
    sklepy: list = field(default_factory=list)
    reczne: list = field(default_factory=list)
    minimalne_odczyty: dict = field(default_factory=dict)
    oznaczenia_hali: list = field(default_factory=list)
    identyfikator: str = ""

    @property
    def slug(self):
        return slug(self.identyfikator or self.plik.stem)

    @property
    def fraza(self):
        return self.frazy[0]

    @property
    def katalog_danych(self):
        return U.DANE / "profile" / self.slug

    def katalog_wynikow(self, rozmiar=None):
        return U.WYNIKI / self.slug / str(rozmiar or self.rozmiar)

    def podstaw(self, szablon, rozmiar=None):
        rozmiar = rozmiar or self.rozmiar
        zamiany = {
            "{fraza}": self.fraza,
            "{fraza_url}": quote_plus(self.fraza),
            "{fraza_sciezka}": quote(self.fraza),
            "{fraza_z_rozmiarem_url}": quote_plus(f"{self.fraza} {rozmiar}"),
            "{rozmiar}": rozmiar,
            "{marka}": self.marka,
            "{model}": self.model,
        }
        for klucz, wartosc in zamiany.items():
            szablon = szablon.replace(klucz, str(wartosc))
        return szablon

    def min_odczytow(self, zrodlo):
        return int(self.minimalne_odczyty.get(zrodlo, 0))


def wczytaj(plik):
    plik = Path(plik)
    try:
        dane = tomllib.loads(plik.read_text(encoding="utf-8"))
    except OSError as e:
        raise BladProfilu(f"nie mogę otworzyć profilu {plik}: {e}") from e
    except tomllib.TOMLDecodeError as e:
        raise BladProfilu(f"błąd składni w profilu {plik.name}: {e}") from e
    return z_danych(dane, plik)


def z_danych(dane, plik):
    dane = dict(dane)
    brakujace = [k for k in ("marka", "model") if not dane.get(k)]
    if brakujace:
        raise BladProfilu(f"w profilu {plik.name} brakuje pól: {', '.join(brakujace)}")
    dane.setdefault("nazwa", f"{dane['marka']} {dane['model']}")
    dane.setdefault("rozmiar", U.DOMYSLNY_ROZMIAR)
    dane["rozmiar"] = str(dane["rozmiar"])
    dane.setdefault("frazy", [f"{dane['marka']} {dane['model']}".lower()])
    dane["sklepy"] = dane.pop("sklep", [])
    dane["reczne"] = dane.pop("reczny", [])
    znane = set(Profil.__dataclass_fields__) - {"plik"}
    nieznane = sorted(set(dane) - znane)
    if nieznane:
        raise BladProfilu(f"nieznane pola w profilu {plik.name}: {', '.join(nieznane)}")
    for klucz in ("wykluczenia", "kody_modelu", "kody_wykluczone", "nie_dotyczy", "slowa_kategorii", "oznaczenia_hali"):
        for wzorzec in dane.get(klucz, []):
            try:
                re.compile(wzorzec)
            except re.error as e:
                raise BladProfilu(f"błędny wzorzec w polu {klucz}: {wzorzec!r} ({e})") from e
    return Profil(plik=plik, **dane)


def ustaw(profil):
    global _aktywny
    _aktywny = profil


def aktywny():
    if _aktywny is None:
        from . import katalog
        ustaw(katalog.profil(*U.DOMYSLNY_MODEL))
    return _aktywny
