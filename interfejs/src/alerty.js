import "./strona.js";
import * as api from "./api.js";
import { nastepneSprawdzenie, opisGodzin } from "./alerty-wspolne.js";
import { bezpiecznyAdres, el, odmiana, wyczysc, zl } from "./dom.js";
import { ikona } from "./ikony.js";
import { powiadom } from "./powiadomienia.js";

const NA_POCZATEK = 8;
const CZAS_POTWIERDZENIA = 4000;
const lista = document.getElementById("alerty-lista");
const ustawienia = document.getElementById("alerty-ustawienia");

function kiedy(tekst) {
  const [data, godzina] = tekst.split(" ");
  const [rok, miesiac, dzien] = data.split("-");
  const dzis = new Date();
  const toDzis = Number(rok) === dzis.getFullYear() && Number(miesiac) === dzis.getMonth() + 1 && Number(dzien) === dzis.getDate();
  return toDzis ? `dziś ${godzina}` : `${dzien}.${miesiac} ${godzina}`;
}

function linia(nazwaIkony, ...tresc) {
  return el("li", { class: "alerty-ustawienia__pozycja" }, ikona(nazwaIkony), el("span", {}, ...tresc));
}

function rysujUstawienia({ godziny, harmonogram, kanaly }) {
  const pozycje = [
    harmonogram
      ? linia("Clock", `Sprawdzam codziennie o ${opisGodzin(godziny)}. Najbliżej ${nastepneSprawdzenie(godziny)}.`)
      : linia("TriangleAlert", "Automatyczne sprawdzanie jest wyłączone. Włączysz je w katalogu projektu poleceniem ", el("code", {}, "narzedzia/alerty/harmonogram.sh"), "."),
    linia(kanaly.mac ? "CircleCheck" : "Minus", kanaly.mac ? "Powiadomienia na Macu są włączone." : "Powiadomienia systemowe działają tylko na Macu."),
    kanaly.telegram
      ? linia("CircleCheck", "Telegram jest podłączony, wiadomość przyjdzie też na telefon.")
      : linia("Minus", "Telegram nie jest ustawiony. Dodaj ", el("code", {}, "TELEGRAM_BOT_TOKEN"), " i ", el("code", {}, "TELEGRAM_CHAT_ID"), " do pliku .env, żeby dostawać alerty na telefon."),
  ];
  wyczysc(
    ustawienia,
    el("ul", { class: "alerty-ustawienia__lista" }, pozycje),
    el("p", { class: "podpowiedz" }, "Próbne powiadomienie wyślesz poleceniem ", el("code", {}, "py szukaj.py --test-powiadomien"), "."),
  );
  ustawienia.dataset.ostrzezenie = String(!harmonogram);
  ustawienia.hidden = false;
}

function trafienie(t, nowe) {
  const adres = bezpiecznyAdres(t.url);
  const znaczek =
    t.typ === "nowa"
      ? el("span", { class: "znaczek znaczek--sukces" }, ikona("Sparkles"), "nowa")
      : el("span", { class: "znaczek znaczek--sukces" }, ikona("TrendingDown"), `taniej o ${zl(t.roznica)}`);
  return el(
    "li",
    { class: "trafienie", "data-nowe": String(nowe) },
    nowe && el("span", { class: "kropka trafienie__kropka", "aria-hidden": "true" }),
    el(
      "div",
      { class: "trafienie__tresc" },
      adres ? el("a", { class: "trafienie__link", href: adres, target: "_blank", rel: "noopener noreferrer" }, t.tytul) : el("span", { class: "trafienie__link" }, t.tytul),
      el("span", { class: "trafienie__meta" }, nowe && el("span", { class: "wizualnie-ukryte" }, "Nowe od ostatniej wizyty. "), znaczek, ` ${t.zrodlo} · ${kiedy(t.kiedy)}`),
    ),
    el("span", { class: "trafienie__cena" }, zl(t.cena)),
  );
}

function listaTrafien(alert) {
  const { trafienia, nowych } = alert;
  if (!trafienia.length) {
    return el("p", { class: "alert__pusto" }, "Na razie bez zmian. Dam znać, gdy pojawi się nowa oferta albo któraś stanieje.");
  }
  const pozycje = trafienia.map((t, i) => trafienie(t, i < nowych));
  const widoczne = Math.max(NA_POCZATEK, nowych);
  return el(
    "div",
    { class: "alert__trafienia" },
    el("ul", { class: "trafienia", "aria-label": `Zmiany dla ${alert.nazwa}, rozmiar ${alert.rozmiar}` }, pozycje.slice(0, widoczne)),
    pozycje.length > widoczne &&
      el(
        "details",
        { class: "zmiany__szczegoly" },
        el("summary", {}, `Pokaż starsze (${pozycje.length - widoczne})`),
        el("ul", { class: "trafienia" }, pozycje.slice(widoczne)),
      ),
  );
}

function stanSprawdzenia(alert, godziny) {
  if (!alert.sprawdzono) return el("p", { class: "alert__stan" }, ikona("Clock"), `Pierwsze sprawdzenie ${nastepneSprawdzenie(godziny)}.`);
  if (alert.stan === "ok") return el("p", { class: "alert__stan" }, ikona("CircleCheck"), `Sprawdzono ${kiedy(alert.sprawdzono)}.`);
  return el("p", { class: "alert__stan alert__stan--ostrzezenie" }, ikona("TriangleAlert"), `Sprawdzono ${kiedy(alert.sprawdzono)}: ${alert.stan}.`);
}

function przyciskUsun(alert, naUsuniete) {
  const etykieta = `Usuń alert ${alert.nazwa}, rozmiar ${alert.rozmiar}`;
  const przycisk = el("button", { type: "button", class: "przycisk przycisk--maly alert__usun", "aria-label": etykieta }, ikona("Trash2"), el("span", {}, "Usuń"));
  let zegar = null;
  przycisk.addEventListener("click", async () => {
    if (przycisk.dataset.potwierdz !== "true") {
      przycisk.dataset.potwierdz = "true";
      przycisk.setAttribute("aria-label", `Potwierdź: ${etykieta}`);
      przycisk.lastChild.textContent = "Na pewno?";
      zegar = setTimeout(() => {
        przycisk.dataset.potwierdz = "false";
        przycisk.setAttribute("aria-label", etykieta);
        przycisk.lastChild.textContent = "Usuń";
      }, CZAS_POTWIERDZENIA);
      return;
    }
    clearTimeout(zegar);
    przycisk.setAttribute("aria-disabled", "true");
    try {
      await api.usunAlert(alert.id);
      naUsuniete();
      powiadom(`Usunięto alert: ${alert.nazwa}, rozmiar ${alert.rozmiar}.`);
    } catch (blad) {
      przycisk.removeAttribute("aria-disabled");
      powiadom(`Nie udało się usunąć alertu: ${blad.message}.`, { rodzaj: "blad" });
    }
  });
  return przycisk;
}

function kartaAlertu(alert, godziny, naUsuniete) {
  const filtry = [alert.max_cena ? `do ${zl(alert.max_cena)}` : "bez limitu ceny", alert.tylko_pewne && "tylko potwierdzony rozmiar"].filter(Boolean);
  const adres = `/?${new URLSearchParams({ marka: alert.marka, model: alert.model, rozmiar: alert.rozmiar })}#krok-filtry`;
  return el(
    "article",
    { class: "alert", "data-nowe": String(alert.nowych > 0), "aria-labelledby": `alert-${alert.id}` },
    el(
      "div",
      { class: "alert__naglowek" },
      el(
        "h2",
        { class: "alert__tytul", id: `alert-${alert.id}` },
        alert.nazwa,
        el("span", { class: "alert__rozmiar" }, `rozmiar ${alert.rozmiar}`),
      ),
      alert.nowych > 0 && el("span", { class: "znaczek znaczek--sukces" }, `${alert.nowych} ${odmiana(alert.nowych, "nowa zmiana", "nowe zmiany", "nowych zmian")}`),
    ),
    el("ul", { class: "znaczki", "aria-label": "Filtry alertu" }, filtry.map((f) => el("li", { class: "znaczek" }, f))),
    stanSprawdzenia(alert, godziny),
    listaTrafien(alert),
    el(
      "div",
      { class: "alert__akcje" },
      przyciskUsun(alert, naUsuniete),
      el("a", { class: "przycisk przycisk--maly", href: adres }, ikona("Search"), "Szukaj teraz"),
    ),
  );
}

function pustyStan(...tresc) {
  return el("div", { class: "pusty-stan" }, ...tresc);
}

function rysuj(dane) {
  lista.removeAttribute("aria-busy");
  rysujUstawienia(dane);
  if (!dane.alerty.length) {
    wyczysc(
      lista,
      pustyStan(
        el("p", { class: "pusty-stan__tytul" }, ikona("Bell"), "Nie masz jeszcze alertów"),
        el("p", {}, "Wybierz buty i rozmiar, kliknij „Szukaj ofert”, a gdy pojawią się wyniki, kliknij „Powiadamiaj o nowych i tańszych”."),
        el("a", { class: "przycisk przycisk--glowny", href: "/#krok-marka" }, "Wybierz buty", ikona("ArrowRight")),
      ),
    );
    return;
  }
  const karty = dane.alerty.map((alert) => {
    const karta = kartaAlertu(alert, dane.godziny, () => {
      karta.remove();
      document.querySelector("main h1").focus();
      if (!lista.querySelector(".alert")) rysuj({ ...dane, alerty: [] });
    });
    return karta;
  });
  wyczysc(lista, karty);
}

async function wczytaj() {
  try {
    const dane = await api.alerty();
    rysuj(dane);
    if (dane.alerty.some((a) => a.nowych > 0)) api.przeczytaneAlerty().catch(() => null);
  } catch (blad) {
    lista.removeAttribute("aria-busy");
    if (blad.status === 401) {
      wyczysc(
        lista,
        pustyStan(
          el("p", { class: "pusty-stan__tytul" }, ikona("Bell"), "Alerty widzi tylko administrator"),
          el("p", {}, "Zaloguj się, żeby zapisywać wyszukiwania i dostawać powiadomienia o nowych ofertach."),
          el("a", { class: "przycisk przycisk--glowny", href: "/admin.html" }, "Zaloguj się", ikona("ArrowRight")),
        ),
      );
      return;
    }
    wyczysc(
      lista,
      el(
        "div",
        { class: "blad-stan", role: "alert" },
        el("p", { class: "blad-stan__tytul" }, ikona("CircleAlert"), "Nie mogę wczytać alertów"),
        el("p", {}, `Sprawdź, czy serwer Szatni działa (`, el("code", {}, "py serwer.py"), `). Szczegóły: ${blad.message}.`),
        el("button", { type: "button", class: "przycisk przycisk--maly", onClick: wczytaj }, ikona("RefreshCw"), "Spróbuj ponownie"),
      ),
    );
  }
}

wyczysc(lista, Array.from({ length: 2 }, () => el("div", { class: "szkielet szkielet--alert", "aria-hidden": "true" })));
wczytaj();
