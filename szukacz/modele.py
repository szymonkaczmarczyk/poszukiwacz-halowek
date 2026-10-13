import re
from dataclasses import dataclass, field


def kwota(wartosc):
    if wartosc is None or isinstance(wartosc, bool):
        return None
    if isinstance(wartosc, (int, float)):
        return float(wartosc)
    m = re.search(r"\d[\d\s .,]*", str(wartosc))
    if not m:
        return None
    t = re.sub(r"[\s ]", "", m.group(0)).rstrip(".,")
    if "," in t and "." in t:
        dziesietny = "," if t.rfind(",") > t.rfind(".") else "."
        tysiace = "." if dziesietny == "," else ","
        t = t.replace(tysiace, "").replace(dziesietny, ".")
    elif "," in t or "." in t:
        sep = "," if "," in t else "."
        czesci = t.split(sep)
        if len(czesci) == 2 and len(czesci[1]) <= 2:
            t = czesci[0] + "." + czesci[1]
        else:
            t = "".join(czesci)
    try:
        return float(t)
    except ValueError:
        return None


def klucz_url(url):
    return str(url).strip().split("#")[0].split("?")[0].rstrip("/")


@dataclass
class Oferta:
    zrodlo: str
    tytul: str
    url: str
    cena: float
    waluta: str = "PLN"
    dostawa: float | None = None
    dostawa_szacunkowa: float | None = None
    rozmiar_pewny: bool = False
    stan: str = ""
    wysylka: str = ""
    lokalizacja: str = ""
    zdjecie: str = ""
    uwagi: str = ""
    model: str = "pewny"
    wskazowka: str = ""
    cena_pln: float = 0.0
    dostawa_pln: float | None = None
    dostawa_szac: bool = False
    flagi: list = field(default_factory=list)

    @property
    def suma_pln(self):
        return self.cena_pln + (self.dostawa_pln or 0.0)

    @property
    def klucz(self):
        return klucz_url(self.url)

    def do_slownika(self):
        return {
            "zrodlo": self.zrodlo,
            "tytul": self.tytul,
            "url": self.url,
            "cena": self.cena,
            "waluta": self.waluta,
            "dostawa": self.dostawa,
            "cena_pln": round(self.cena_pln, 2),
            "dostawa_pln": None if self.dostawa_pln is None else round(self.dostawa_pln, 2),
            "dostawa_szacunkowa": self.dostawa_szac,
            "suma_pln": round(self.suma_pln, 2),
            "rozmiar_potwierdzony": self.rozmiar_pewny,
            "model": self.model,
            "wskazowka": self.wskazowka,
            "stan": self.stan,
            "wysylka": self.wysylka,
            "lokalizacja": self.lokalizacja,
            "zdjecie": self.zdjecie,
            "uwagi": self.uwagi,
            "flagi": self.flagi,
        }
