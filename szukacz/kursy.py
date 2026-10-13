import threading

from .siec import ZrodloNiedostepne

ZAPASOWE = {"EUR": 4.25, "GBP": 4.90, "USD": 3.70, "CZK": 0.17, "HUF": 0.0105, "RON": 0.85, "SEK": 0.38, "DKK": 0.57}


class Kursy:
    def __init__(self, http):
        self.http = http
        self._kursy = {"PLN": 1.0}
        self.przyblizone = set()
        self._blokada = threading.Lock()

    def kurs(self, waluta):
        waluta = (waluta or "PLN").upper()
        with self._blokada:
            if waluta in self._kursy:
                return self._kursy[waluta]
            try:
                odp = self.http.get(
                    f"https://api.nbp.pl/api/exchangerates/rates/a/{waluta.lower()}/",
                    params={"format": "json"},
                    naglowki={"Accept": "application/json"},
                    godziny_cache=12,
                )
                kurs = float(odp.json()["rates"][0]["mid"]) if odp.status == 200 else None
            except (ZrodloNiedostepne, ValueError, KeyError, IndexError):
                kurs = None
            if kurs is None:
                kurs = ZAPASOWE.get(waluta, 1.0)
                self.przyblizone.add(waluta)
            self._kursy[waluta] = kurs
            return kurs

    def na_pln(self, kwota, waluta):
        if kwota is None:
            return None
        return kwota * self.kurs(waluta)
