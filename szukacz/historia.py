import json
import time
from dataclasses import dataclass, field

META = "_meta"


@dataclass
class Zmiany:
    poprzednio: str = ""
    pierwsze: bool = False
    nowe: list = field(default_factory=list)
    tansze: list = field(default_factory=list)
    drozsze: list = field(default_factory=list)
    zniknely: list = field(default_factory=list)

    @property
    def puste(self):
        return not (self.nowe or self.tansze or self.drozsze or self.zniknely)

    def do_slownika(self):
        return {
            "poprzednio": self.poprzednio,
            "pierwsze": self.pierwsze,
            "nowe": [o.klucz for o in self.nowe],
            "tansze": [{"klucz": o.klucz, "roznica": round(r, 2)} for o, r in self.tansze],
            "drozsze": [{"klucz": o.klucz, "roznica": round(r, 2)} for o, r in self.drozsze],
            "zniknely": self.zniknely,
        }


def _wczytaj(plik):
    try:
        return json.loads(plik.read_text(encoding="utf-8")), False
    except (OSError, ValueError):
        return {}, True


def oznacz(oferty, plik, czy_sprawdzone):
    dane, pierwsze = _wczytaj(plik)
    meta = dane.pop(META, {})
    zmiany = Zmiany(poprzednio=meta.get("ostatnio", ""), pierwsze=pierwsze)
    teraz = time.strftime("%Y-%m-%d %H:%M")
    obecne = set()
    for o in oferty:
        obecne.add(o.klucz)
        wpis = dane.get(o.klucz)
        if wpis is None:
            if not pierwsze:
                o.flagi.append("NOWE")
                zmiany.nowe.append(o)
            wpis = dane[o.klucz] = {"pierwszy_raz": teraz, "tytul": o.tytul, "zrodlo": o.zrodlo, "ceny": []}
        elif wpis["ceny"]:
            poprzednia = wpis["ceny"][-1][1]
            if o.suma_pln < poprzednia - 0.5:
                o.flagi.append(f"TANIEJ o {poprzednia - o.suma_pln:.0f} zł")
                zmiany.tansze.append((o, poprzednia - o.suma_pln))
            elif o.suma_pln > poprzednia + 0.5:
                o.flagi.append(f"drożej o {o.suma_pln - poprzednia:.0f} zł")
                zmiany.drozsze.append((o, o.suma_pln - poprzednia))
        if not wpis["ceny"] or abs(wpis["ceny"][-1][1] - o.suma_pln) > 0.5:
            wpis["ceny"].append([teraz, round(o.suma_pln, 2)])
        wpis["ostatnio"] = teraz
        wpis["zrodlo"] = o.zrodlo
    for klucz in meta.get("klucze", []):
        wpis = dane.get(klucz)
        if klucz not in obecne and wpis and czy_sprawdzone(wpis.get("zrodlo", "")):
            zmiany.zniknely.append({
                "klucz": klucz,
                "tytul": wpis.get("tytul", ""),
                "zrodlo": wpis.get("zrodlo", ""),
                "cena": wpis["ceny"][-1][1] if wpis.get("ceny") else None,
            })
    pozostale = [k for k in meta.get("klucze", []) if k not in obecne and not czy_sprawdzone(dane.get(k, {}).get("zrodlo", ""))]
    dane[META] = {"ostatnio": teraz, "klucze": sorted(obecne | set(pozostale))}
    plik.parent.mkdir(parents=True, exist_ok=True)
    plik.write_text(json.dumps(dane, ensure_ascii=False, indent=1), encoding="utf-8")
    return zmiany
