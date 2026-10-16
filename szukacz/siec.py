import hashlib
import json
import random
import threading
import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import requests

from . import ustawienia as U

ZNACZNIKI_BLOKADY = (
    "captcha-delivery.com",
    "cf-chl-",
    "Attention Required! | Cloudflare",
    "Just a moment...",
    "Request blocked",
    "px-captcha",
    "_Incapsula_",
    "Access Denied",
    "Pardon Our Interruption",
)


class ZrodloNiedostepne(Exception):
    pass


class Przerwano(Exception):
    pass


@dataclass
class Odpowiedz:
    status: int
    tekst: str
    url: str
    z_cache: bool = False

    def json(self):
        return json.loads(self.tekst)


def host(url):
    return urlsplit(url).netloc.lower()


def wyglada_na_blokade(status, tekst, typ=""):
    znaczniki = len(tekst) < 40000 and any(z in tekst for z in ZNACZNIKI_BLOKADY)
    if "json" in typ.lower():
        return znaczniki
    return status in (401, 403) or znaczniki


def _retry_after(odpowiedz):
    wartosc = odpowiedz.headers.get("Retry-After")
    if not wartosc:
        return None
    try:
        return float(wartosc)
    except ValueError:
        pass
    try:
        return max(0.0, parsedate_to_datetime(wartosc).timestamp() - time.time())
    except (TypeError, ValueError):
        return None


class Cache:
    def __init__(self, katalog, godziny, pomin_odczyt=False):
        self.katalog = katalog
        self.godziny = godziny
        self.pomin_odczyt = pomin_odczyt
        katalog.mkdir(parents=True, exist_ok=True)

    def _plik(self, klucz):
        return self.katalog / (hashlib.sha1(klucz.encode("utf-8")).hexdigest() + ".json")

    def pobierz(self, klucz, godziny=None):
        if self.pomin_odczyt:
            return None
        plik = self._plik(klucz)
        try:
            dane = json.loads(plik.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        limit = self.godziny if godziny is None else godziny
        if time.time() - dane["czas"] > limit * 3600:
            return None
        return Odpowiedz(dane["status"], dane["tekst"], dane["url"], True)

    def zapisz(self, klucz, odp):
        dane = {"czas": time.time(), "klucz": klucz, "status": odp.status, "url": odp.url, "tekst": odp.tekst}
        self._plik(klucz).write_text(json.dumps(dane, ensure_ascii=False), encoding="utf-8")

    def sprzataj(self, dni=3):
        granica = time.time() - dni * 86400
        for plik in self.katalog.glob("*.json"):
            try:
                if plik.stat().st_mtime < granica:
                    plik.unlink()
            except OSError:
                pass


class Ogranicznik:
    def __init__(self, plik, przerwanie=None):
        self.plik = plik
        self.przerwanie = przerwanie or threading.Event()
        self._blokada = threading.RLock()
        self._kolejki = defaultdict(threading.Lock)
        self.licznik = Counter()
        self.stan = self._wczytaj()

    def _wczytaj(self):
        try:
            stan = json.loads(self.plik.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            stan = {}
        stan.setdefault("ostatnie", {})
        stan.setdefault("blokady", {})
        return stan

    def _zapisz(self):
        with self._blokada:
            self.plik.parent.mkdir(parents=True, exist_ok=True)
            self.plik.write_text(json.dumps(self.stan, ensure_ascii=False, indent=1), encoding="utf-8")

    def limity(self, h):
        return {**U.LIMITY_DOMYSLNE, **U.LIMITY.get(h, {})}

    def blokada(self, h):
        with self._blokada:
            wpis = self.stan["blokady"].get(h)
        if wpis and wpis["do"] > time.time():
            return wpis
        return None

    def aktywne_blokady(self):
        with self._blokada:
            hosty = list(self.stan["blokady"])
        return {h: w for h in hosty if (w := self.blokada(h))}

    def zablokuj(self, h, godziny, powod):
        with self._blokada:
            self.stan["blokady"][h] = {"do": time.time() + godziny * 3600, "powod": powod}
            self._zapisz()

    def wyczysc_blokady(self):
        with self._blokada:
            self.stan["blokady"] = {}
            self._zapisz()

    def czekaj(self, sekundy):
        if self.przerwanie.wait(max(0.0, sekundy)):
            raise Przerwano("wyszukiwanie przerwane")

    def sprawdz(self, h):
        if self.przerwanie.is_set():
            raise Przerwano("wyszukiwanie przerwane")
        wpis = self.blokada(h)
        if wpis:
            do = time.strftime("%d.%m %H:%M", time.localtime(wpis["do"]))
            raise ZrodloNiedostepne(f"{h} wstrzymany do {do} ({wpis['powod']})")
        limit = self.limity(h)["max_zapytan"]
        if self.licznik[h] >= limit:
            raise ZrodloNiedostepne(f"{h}: wykorzystano limit {limit} zapytań na jedno uruchomienie")

    def _kolejka_hosta(self, h):
        with self._blokada:
            return self._kolejki[h]

    @contextmanager
    def kolejka(self, h):
        with self._kolejka_hosta(h):
            self.sprawdz(h)
            lim = self.limity(h)
            with self._blokada:
                ostatnie = self.stan["ostatnie"].get(h, 0)
            czekaj = ostatnie + lim["odstep"] + random.uniform(0, lim["losowo"]) - time.time()
            if czekaj > 0:
                self.czekaj(czekaj)
            self.licznik[h] += 1
            try:
                yield
            finally:
                with self._blokada:
                    self.stan["ostatnie"][h] = time.time()
                    self._zapisz()


class KlientHttp:
    def __init__(self, ogranicznik, cache, log):
        self.ogranicznik = ogranicznik
        self.cache = cache
        self.log = log
        self._sesje = {}
        self._blokada = threading.Lock()

    def _sesja(self, h):
        with self._blokada:
            if h not in self._sesje:
                sesja = requests.Session()
                sesja.headers.update({
                    "User-Agent": U.USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.7,en;q=0.6",
                })
                self._sesje[h] = sesja
            return self._sesje[h]

    def get(self, url, params=None, naglowki=None, godziny_cache=None):
        return self.zapytanie("GET", url, params=params, naglowki=naglowki, godziny_cache=godziny_cache)

    def post(self, url, dane=None, naglowki=None, auth=None):
        return self.zapytanie("POST", url, dane=dane, naglowki=naglowki, auth=auth, cache=False)

    def zapytanie(self, metoda, url, params=None, dane=None, naglowki=None, auth=None, godziny_cache=None, cache=True):
        pelny = requests.Request(metoda, url, params=params).prepare().url
        uzyj_cache = cache and metoda == "GET"
        if uzyj_cache:
            z_cache = self.cache.pobierz(pelny, godziny_cache)
            if z_cache:
                return z_cache
        h = host(pelny)
        proba = 0
        while True:
            proba += 1
            blad = None
            r = None
            with self.ogranicznik.kolejka(h):
                try:
                    r = self._sesja(h).request(metoda, pelny, data=dane, headers=naglowki, auth=auth, timeout=30)
                except requests.RequestException as e:
                    blad = e
            if r is None:
                if proba >= 3:
                    raise ZrodloNiedostepne(f"{h}: błąd sieci ({blad.__class__.__name__})")
                self.ogranicznik.czekaj(10 * proba)
                continue
            odp = Odpowiedz(r.status_code, r.text, r.url)
            if r.status_code in (429, 503) and not wyglada_na_blokade(200, odp.tekst):
                if proba >= 3:
                    self.ogranicznik.zablokuj(h, 2, f"HTTP {r.status_code}: serwer prosi o zwolnienie tempa")
                    raise ZrodloNiedostepne(f"{h}: HTTP {r.status_code}, host wstrzymany na 2 h")
                przerwa = min(_retry_after(r) or 40 * proba, 180)
                self.log(h, f"HTTP {r.status_code}, odczekuję {przerwa:.0f} s")
                self.ogranicznik.czekaj(przerwa)
                continue
            if wyglada_na_blokade(r.status_code, odp.tekst, r.headers.get("Content-Type", "")):
                self.ogranicznik.zablokuj(h, U.BLOKADA_GODZIN, f"ochrona antybotowa, HTTP {r.status_code}")
                raise ZrodloNiedostepne(
                    f"{h}: wykryto ochronę antybotową, host wstrzymany na {U.BLOKADA_GODZIN} h"
                )
            if r.status_code >= 500 and proba < 2:
                self.ogranicznik.czekaj(20)
                continue
            if uzyj_cache and r.status_code == 200:
                self.cache.zapisz(pelny, odp)
            return odp
