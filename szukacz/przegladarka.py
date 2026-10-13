import hashlib
import json
import random

from . import ustawienia as U
from .siec import Odpowiedz, ZrodloNiedostepne, host, wyglada_na_blokade


class Przegladarka:
    def __init__(self, ogranicznik, cache, profil, widoczna=False):
        self.ogranicznik = ogranicznik
        self.cache = cache
        self.profil = U.PROFIL_PRZEGLADARKI / profil
        self.widoczna = widoczna
        self._pw = None
        self._kontekst = None
        self._strona = None

    def _uruchom(self):
        if self._strona:
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            raise ZrodloNiedostepne("brak biblioteki Playwright (pip install playwright)") from e
        self._pw = sync_playwright().start()
        self.profil.mkdir(parents=True, exist_ok=True)
        opcje = {
            "headless": not self.widoczna,
            "locale": "pl-PL",
            "timezone_id": "Europe/Warsaw",
            "viewport": {"width": 1366, "height": 860},
        }
        bledy = []
        for kanal in ("chrome", "msedge", None):
            try:
                dodatkowe = {"channel": kanal} if kanal else {}
                self._kontekst = self._pw.chromium.launch_persistent_context(str(self.profil), **dodatkowe, **opcje)
                break
            except Exception as e:
                bledy.append(f"{kanal or 'chromium'}: {e.__class__.__name__}")
        if not self._kontekst:
            self.zamknij()
            raise ZrodloNiedostepne("nie udało się uruchomić przeglądarki (" + ", ".join(bledy) + ")")
        self._strona = self._kontekst.pages[0] if self._kontekst.pages else self._kontekst.new_page()

    def _otworz(self, url, skrypt=None, argument=None):
        self._uruchom()
        h = host(url)
        with self.ogranicznik.kolejka(h):
            try:
                odpowiedz = self._strona.goto(url, wait_until="domcontentloaded", timeout=45000)
                self._strona.wait_for_timeout(random.randint(1800, 3200))
                tekst = self._strona.content()
                status = odpowiedz.status if odpowiedz else 0
                koncowy = self._strona.url
                wynik = self._strona.evaluate(skrypt, argument) if skrypt else None
            except Exception as e:
                raise ZrodloNiedostepne(f"{h}: przeglądarka nie wczytała strony ({e.__class__.__name__})") from e
        if wyglada_na_blokade(status, tekst):
            self.ogranicznik.zablokuj(h, U.BLOKADA_GODZIN, f"ochrona antybotowa w przeglądarce, HTTP {status}")
            raise ZrodloNiedostepne(f"{h}: wykryto ochronę antybotową, host wstrzymany na {U.BLOKADA_GODZIN} h")
        return status, tekst, koncowy, wynik

    def pobierz(self, url, godziny_cache=None):
        z_cache = self.cache.pobierz(url, godziny_cache)
        if z_cache:
            return z_cache
        status, tekst, koncowy, _ = self._otworz(url)
        odp = Odpowiedz(status, tekst, koncowy)
        if status == 200:
            self.cache.zapisz(url, odp)
        return odp

    def wykonaj(self, url, skrypt, argument=None, godziny_cache=None):
        odcisk = hashlib.sha1((skrypt + json.dumps(argument)).encode("utf-8")).hexdigest()[:12]
        klucz = f"{url}#skrypt-{odcisk}"
        z_cache = self.cache.pobierz(klucz, godziny_cache)
        if z_cache:
            return z_cache.json()
        status, _, koncowy, wynik = self._otworz(url, skrypt, argument)
        if status == 200 and wynik is not None:
            self.cache.zapisz(klucz, Odpowiedz(status, json.dumps(wynik, ensure_ascii=False), koncowy))
        return wynik

    def zamknij(self):
        for zasob in (self._kontekst, self._pw):
            try:
                if zasob is self._pw and zasob:
                    zasob.stop()
                elif zasob:
                    zasob.close()
            except Exception:
                pass
        self._kontekst = None
        self._pw = None
        self._strona = None
