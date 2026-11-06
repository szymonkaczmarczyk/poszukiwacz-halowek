import os
import subprocess
import sys

import requests

ADRES_TELEGRAMU = "https://api.telegram.org/bot{token}/sendMessage"
OFERT_W_WIADOMOSCI = 5


def odmiana(liczba, jeden, kilka, wiele):
    if liczba == 1:
        return jeden
    return kilka if liczba % 10 in (2, 3, 4) and liczba % 100 not in (12, 13, 14) else wiele


def kanaly():
    return {
        "mac": sys.platform == "darwin",
        "telegram": bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID")),
    }


def zl(kwota):
    return f"{kwota:,.0f} zł".replace(",", " ")


def podsumowanie(trafienia):
    nowe = sum(1 for t in trafienia if t["typ"] == "nowa")
    tansze = len(trafienia) - nowe
    czesci = []
    if nowe:
        czesci.append(f"{nowe} {odmiana(nowe, 'nowa oferta', 'nowe oferty', 'nowych ofert')}")
    if tansze:
        czesci.append(f"{tansze} {odmiana(tansze, 'tańsza', 'tańsze', 'tańszych')}")
    return ", ".join(czesci)


def opis_trafienia(t):
    zmiana = "nowa" if t["typ"] == "nowa" else f"taniej o {zl(t['roznica'])}"
    return f"{zl(t['cena'])} · {t['zrodlo']} · {t['tytul']} ({zmiana})"


def tresc(alert, trafienia):
    tytul = f"Szatnia: {alert['nazwa']}, rozmiar {alert['rozmiar']}"
    najtansza = min(trafienia, key=lambda t: t["cena"])
    krotko = f"{podsumowanie(trafienia)}. Najtańsza: {zl(najtansza['cena'])} ({najtansza['zrodlo']})."
    linie = [podsumowanie(trafienia).capitalize() + ":"]
    for t in sorted(trafienia, key=lambda t: t["cena"])[:OFERT_W_WIADOMOSCI]:
        linie += ["", opis_trafienia(t), t["url"]]
    reszta = len(trafienia) - OFERT_W_WIADOMOSCI
    if reszta > 0:
        linie += ["", f"I {reszta} {odmiana(reszta, 'kolejna', 'kolejne', 'kolejnych')} na stronie alertów w Szatni."]
    return tytul, krotko, "\n".join(linie)


def mac(tytul, tekst):
    subprocess.run(
        ["osascript", "-e", "on run argv", "-e", 'display notification (item 2 of argv) with title (item 1 of argv) sound name "Glass"', "-e", "end run", tytul, tekst],
        check=True,
        capture_output=True,
        timeout=15,
    )


def telegram(tekst):
    odpowiedz = requests.post(
        ADRES_TELEGRAMU.format(token=os.environ["TELEGRAM_BOT_TOKEN"]),
        json={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": tekst, "disable_web_page_preview": True},
        timeout=20,
    )
    odpowiedz.raise_for_status()


def _proba(wyslij):
    try:
        wyslij()
    except (OSError, subprocess.SubprocessError, requests.RequestException) as e:
        return f"błąd ({e.__class__.__name__})"
    return "wysłano"


def wyslij(tytul, krotko, dlugo):
    wlaczone = kanaly()
    wyniki = {}
    if wlaczone["mac"]:
        wyniki["Mac"] = _proba(lambda: mac(tytul, krotko))
    if wlaczone["telegram"]:
        wyniki["Telegram"] = _proba(lambda: telegram(f"{tytul}\n\n{dlugo}"))
    return wyniki


def powiadom(alert, trafienia):
    return wyslij(*tresc(alert, trafienia))
