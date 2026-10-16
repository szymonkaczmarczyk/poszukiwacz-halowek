import json
import os
import re
import threading
import time

from . import profil as P
from . import ustawienia as U
from .dopasowanie import normalizuj

_blokada = threading.Lock()


class BladWlasnych(Exception):
    def __init__(self, komunikat, kod=422):
        super().__init__(komunikat)
        self.kod = kod


def _plik():
    return U.PLIK_WLASNYCH


def wczytaj():
    try:
        dane = json.loads(_plik().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [w for w in dane.get("modele", []) if w.get("marka") and w.get("id") and w.get("model")]


def _zapisz(wpisy):
    plik = _plik()
    plik.parent.mkdir(parents=True, exist_ok=True)
    tymczasowy = plik.with_suffix(".tmp")
    tymczasowy.write_text(json.dumps({"modele": wpisy}, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tymczasowy, plik)


def wzorzec_slowa(slowo):
    return rf"(?<![a-z0-9]){re.escape(normalizuj(slowo).strip())}(?![a-z0-9])"


def dane_modelu(wpis):
    wykluczenia = wpis.get("wykluczenia", [])
    dane = {
        "id": wpis["id"],
        "model": wpis["model"],
        "wlasny": True,
        "wykluczenia": [wzorzec_slowa(s) for s in wykluczenia],
        "opis_wykluczen": wpis.get("opis") or (f"bez: {', '.join(wykluczenia)}" if wykluczenia else ""),
    }
    if not wpis.get("wymagaj_oznaczenia_hali", True):
        dane["oznaczenia_hali"] = []
    return dane


def dodaj(marka, model, wykluczenia, opis, wymagaj_oznaczenia_hali, marki):
    znana = next((m for m in marki if P.slug(marka) in (m.id, P.slug(m.nazwa))), None)
    marka_id = znana.id if znana else P.slug(marka)
    nazwa_marki = znana.nazwa if znana else marka.strip()
    model_id = P.slug(model)
    if znana and znana.model(model):
        raise BladWlasnych(f"{nazwa_marki} {model} jest już w katalogu", 409)
    wpis = {
        "marka": marka_id,
        "nazwa_marki": nazwa_marki,
        "id": model_id,
        "model": " ".join(model.split()),
        "wykluczenia": sorted({" ".join(s.split()).lower() for s in wykluczenia if s.strip()}),
        "opis": opis.strip(),
        "wymagaj_oznaczenia_hali": wymagaj_oznaczenia_hali,
        "dodano": time.strftime("%Y-%m-%d %H:%M"),
    }
    with _blokada:
        wpisy = wczytaj()
        if any(w["marka"] == marka_id and w["id"] == model_id for w in wpisy):
            raise BladWlasnych(f"{nazwa_marki} {model} jest już na liście własnych modeli", 409)
        _zapisz(wpisy + [wpis])
    return marka_id, model_id


def usun(marka_id, model_id):
    with _blokada:
        wpisy = wczytaj()
        zostaja = [w for w in wpisy if not (w["marka"] == marka_id and w["id"] == model_id)]
        if len(zostaja) == len(wpisy):
            return False
        _zapisz(zostaja)
    return True
