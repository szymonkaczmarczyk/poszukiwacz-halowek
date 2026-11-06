try:
    import fcntl
except ImportError:
    fcntl = None
    import msvcrt


def _zablokuj(plik, czekaj):
    if fcntl:
        fcntl.flock(plik, fcntl.LOCK_EX | (0 if czekaj else fcntl.LOCK_NB))
    else:
        msvcrt.locking(plik.fileno(), msvcrt.LK_LOCK if czekaj else msvcrt.LK_NBLCK, 1)


def _odblokuj(plik):
    if fcntl:
        fcntl.flock(plik, fcntl.LOCK_UN)
    else:
        plik.seek(0)
        msvcrt.locking(plik.fileno(), msvcrt.LK_UNLCK, 1)


class BlokadaPliku:
    def __init__(self, sciezka):
        self.sciezka = sciezka
        self._plik = None

    def zajmij(self, czekaj=False):
        self.sciezka.parent.mkdir(parents=True, exist_ok=True)
        plik = open(self.sciezka, "a+")
        try:
            _zablokuj(plik, czekaj)
        except OSError:
            plik.close()
            return False
        self._plik = plik
        return True

    def zwolnij(self):
        if self._plik:
            _odblokuj(self._plik)
            self._plik.close()
            self._plik = None

    def __enter__(self):
        self.zajmij(czekaj=True)
        return self

    def __exit__(self, *_):
        self.zwolnij()
