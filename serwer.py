import argparse
import getpass
import sys

import uvicorn

from szukacz import admin, api
from szukacz import ustawienia as U


def ustaw_haslo():
    haslo = getpass.getpass(f"Nowe hasło administratora (min. {admin.MIN_DLUGOSC_HASLA} znaków): ")
    if len(haslo) < admin.MIN_DLUGOSC_HASLA:
        print("Hasło jest za krótkie.")
        return 1
    if getpass.getpass("Powtórz hasło: ") != haslo:
        print("Hasła się różnią.")
        return 1
    try:
        linie = U.PLIK_ENV.read_text(encoding="utf-8").splitlines()
    except OSError:
        linie = []
    linie = [linia for linia in linie if not linia.startswith(f"{admin.ZMIENNA_HASLA}=")]
    linie.append(f"{admin.ZMIENNA_HASLA}={admin.hash_hasla(haslo)}")
    U.PLIK_ENV.write_text("\n".join(linie) + "\n", encoding="utf-8")
    print(f"Zapisano skrót hasła w {U.PLIK_ENV.name}. Uruchom serwer ponownie.")
    return 0


def main():
    p = argparse.ArgumentParser(description="Lokalny serwer Szatni: interfejs (po npm run build), katalog modeli, wyszukiwanie i postęp na żywo.")
    p.add_argument("--port", type=int, default=api.PORT, help="port (domyślnie %(default)s)")
    p.add_argument("--ustaw-haslo", action="store_true", help="ustaw hasło administratora (dodawanie i usuwanie własnych modeli) i zakończ")
    a = p.parse_args()
    if a.ustaw_haslo:
        sys.exit(ustaw_haslo())
    uvicorn.run(api.utworz(), host="127.0.0.1", port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
