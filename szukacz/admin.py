import os
import secrets
import threading
import time
from collections import defaultdict, deque

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

ZMIENNA_HASLA = "SZATNIA_ADMIN_HASLO_HASH"
CIASTKO = "szatnia_admin"
CZAS_SESJI = 12 * 3600
LIMIT_PROB = 5
OKNO_PROB = 15 * 60
MIN_DLUGOSC_HASLA = 12

_hasher = PasswordHasher()


class ZaDuzoProb(Exception):
    pass


def hash_hasla(haslo):
    return _hasher.hash(haslo)


class Administrator:
    def __init__(self, hash_hasla=None, zegar=time.time):
        self.hash = os.environ.get(ZMIENNA_HASLA, "") if hash_hasla is None else hash_hasla
        self.zegar = zegar
        self.sesje = {}
        self.proby = defaultdict(deque)
        self._blokada = threading.Lock()

    @property
    def skonfigurowany(self):
        return bool(self.hash)

    def _policz_probe(self, ip):
        teraz = self.zegar()
        proby = self.proby[ip]
        while proby and teraz - proby[0] > OKNO_PROB:
            proby.popleft()
        if len(proby) >= LIMIT_PROB:
            raise ZaDuzoProb()
        proby.append(teraz)

    def zaloguj(self, haslo, ip):
        with self._blokada:
            self._policz_probe(ip)
        try:
            _hasher.verify(self.hash, haslo)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return None
        token = secrets.token_urlsafe(32)
        with self._blokada:
            self.proby.pop(ip, None)
            self.sesje[token] = self.zegar() + CZAS_SESJI
        return token

    def sprawdz(self, token):
        if not token:
            return False
        with self._blokada:
            wygasa = self.sesje.get(token)
            if wygasa and wygasa < self.zegar():
                self.sesje.pop(token, None)
                return False
            return bool(wygasa)

    def wyloguj(self, token):
        with self._blokada:
            self.sesje.pop(token, None)
