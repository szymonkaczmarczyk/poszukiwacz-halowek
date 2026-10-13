import re
import unicodedata
from functools import lru_cache

from .profil import aktywny

NIE_BUTY = re.compile(
    r"\bkids?\b|\bjunior\b|\bjr\b|dzieci|\bninos?\b|\bnina\b|\bkinder|\bbambin|\benfants?\b"
    r"|postal|postcard|postkarte|cartolina|carte postale"
)

KONTEKST_ROZMIARU = re.compile(
    r"(?<![a-z])(?:rozmiar\w*|rozm\.?|roz\.?|r\.?|size|eu|nr\.?|numer|taglia|talla|große|grosse|groesse|pointure|velicina|velikost)"
    r"\s*[:=\-]?\s*(\d{2})((?:[.,]5)|(?:\s*[12]/3))?(?!\d)"
)

LICZBA_W_TYTULE = re.compile(r"(?<![\d.,/])(3[5-9]|4[0-9])((?:[.,]5)|(?:\s+[12]/3))?(?![\d]|[.,]\d)")


def normalizuj(tekst):
    tekst = unicodedata.normalize("NFKD", str(tekst or ""))
    tekst = "".join(z for z in tekst if not unicodedata.combining(z))
    return tekst.replace("ł", "l").replace("Ł", "L").replace("ß", "ss").lower()


@lru_cache(maxsize=64)
def _wzorzec(wzorce):
    return re.compile("|".join(f"(?:{w})" for w in wzorce)) if wzorce else None


def _pasuje(wzorce, tekst):
    wzor = _wzorzec(tuple(wzorce))
    return bool(wzor and wzor.search(tekst))


def _slowa(tekst):
    return [s for s in re.split(r"[^a-z0-9]+", normalizuj(tekst)) if s]


def _zawiera_slowa(n, slowa):
    if not slowa:
        return False
    zwarte = re.sub(r"[^a-z0-9]+", "", n)
    return all(re.search(rf"(?<![a-z0-9]){re.escape(s)}(?![a-z0-9])", n) for s in slowa) or "".join(slowa) in zwarte


def model_profilu(tekst):
    p = aktywny()
    n = normalizuj(tekst)
    for wzorzec in p.wykluczenia:
        if re.search(wzorzec, n):
            return "wykluczony", f"wykluczona wersja ({p.opis_wykluczen or wzorzec})"
    if _pasuje(p.kody_wykluczone, n):
        return "wykluczony", "kod produktu innej wersji"
    if _pasuje(p.kody_modelu, n):
        return "model", "kod produktu modelu"
    if _zawiera_slowa(n, _slowa(p.model)):
        return "model", "nazwa modelu"
    for nazwa in p.inne_modele_marki:
        if normalizuj(nazwa) in n + " ":
            return "inny", f"inny model ({nazwa.strip()})"
    return "?", ""


def wskazowka_opisu(tekst):
    n = normalizuj(tekst)
    for w in aktywny().wskazowki:
        if re.search(w["wzorzec"], n) and not (w.get("oprocz") and re.search(w["oprocz"], n)):
            return w.get("werdykt", "sprawdz"), w.get("opis", "")
    return None, ""


def wyglada_na_kategorie(tekst):
    p = aktywny()
    return not p.slowa_kategorii or _pasuje(p.slowa_kategorii, normalizuj(tekst))


def to_marka(tekst, marka=None):
    p = aktywny()
    n = normalizuj(tekst)
    nazwy = [p.marka] + list(p.aliasy_marki)
    z_marka = any(_zawiera_slowa(n, _slowa(m)) for m in nazwy) or normalizuj(marka) in {normalizuj(m) for m in nazwy}
    return z_marka and not NIE_BUTY.search(n) and not _pasuje(p.nie_dotyczy, n)


def to_szukany_model(tekst, marka=None):
    return to_marka(tekst, marka) and model_profilu(tekst)[0] == "model"


def _rozmiary(wzor, tekst):
    return {liczba + (ulamek or "").replace(",", ".").strip() for liczba, ulamek in wzor.findall(normalizuj(tekst))}


def ocen_tytul(tytul, rozmiar):
    jawne = _rozmiary(KONTEKST_ROZMIARU, tytul)
    if jawne:
        return "tak" if rozmiar in jawne else "nie"
    luzne = _rozmiary(LICZBA_W_TYTULE, tytul)
    if luzne:
        return "tak" if rozmiar in luzne else "nie"
    return "?"


def ocen_opis(opis, rozmiar):
    jawne = _rozmiary(KONTEKST_ROZMIARU, opis)
    if not jawne:
        return "?"
    return "tak" if rozmiar in jawne else "nie"


def ocen_pole(wartosc, rozmiar):
    m = re.search(r"(?<!\d)(\d{2})(?:[.,](\d))?(\s*[12]/3)?", normalizuj(wartosc))
    if not m:
        return "?"
    if m.group(1) == rozmiar and not (m.group(2) and m.group(2) != "0") and not m.group(3):
        return "tak"
    return "nie"
