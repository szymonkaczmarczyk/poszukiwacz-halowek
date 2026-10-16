from .modele import klucz_url


def wczytaj(plik):
    try:
        linie = plik.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    return {klucz_url(linia.split()[0]) for linia in linie if linia.strip()}


def usun(plik, adresy):
    klucze = {klucz_url(a) for a in adresy if a.strip()}
    try:
        linie = plik.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    zostaja = [linia for linia in linie if linia.strip() and klucz_url(linia.split()[0]) not in klucze]
    usuniete = len([linia for linia in linie if linia.strip()]) - len(zostaja)
    if usuniete:
        plik.write_text("".join(f"{linia}\n" for linia in zostaja), encoding="utf-8")
    return usuniete


def dodaj(plik, adresy):
    obecne = wczytaj(plik)
    nowe = [klucz_url(a) for a in adresy if a.strip() and klucz_url(a) not in obecne]
    if nowe:
        with open(plik, "a", encoding="utf-8") as f:
            for adres in nowe:
                f.write(adres + "\n")
    return nowe
