import argparse

import uvicorn

from szukacz import api


def main():
    p = argparse.ArgumentParser(description="Lokalny serwer Szatni: interfejs (po npm run build), katalog modeli, wyszukiwanie i postęp na żywo.")
    p.add_argument("--port", type=int, default=api.PORT, help="port (domyślnie %(default)s)")
    a = p.parse_args()
    uvicorn.run(api.utworz(), host="127.0.0.1", port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
