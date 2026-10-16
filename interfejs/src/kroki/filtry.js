import * as api from "../api.js";
import { el, odmiana, wyczysc, zl } from "../dom.js";
import { ikona } from "../ikony.js";
import { pobierz, subskrybuj, zmien } from "../stan.js";
import { pojawienie } from "../ruch.js";

const PROGI_CENY = [200, 300, 400];
const POWODY_NIEDOSTEPNOSCI = {
  eBay: "wymaga klucza eBay API w pliku .env",
  "Odkrywanie (Google)": "wymaga klucza SerpAPI w pliku .env",
  Goalinn: "brak listy produktów tej marki",
};

function przelacznik({ id, etykieta, opis, zaznaczony, wylaczony, naZmiane }) {
  return el(
    "label",
    { class: "przelacznik", for: id, "data-wylaczone": String(Boolean(wylaczony)) },
    el("input", { type: "checkbox", id, checked: zaznaczony, disabled: wylaczony, onChange: (z) => naZmiane(z.target.checked) }),
    el("span", {}, etykieta, opis && el("span", { class: "przelacznik__opis" }, opis)),
  );
}

function sekcjaCeny() {
  const komunikat = el("p", { class: "komunikat-bledu", id: "max-cena-blad", "aria-live": "polite", hidden: true });
  const pole = el("input", {
    id: "max-cena",
    name: "max-cena",
    autocomplete: "off",
    type: "number",
    inputmode: "numeric",
    min: "1",
    step: "10",
    placeholder: "np. 300",
    value: pobierz().maxCena ?? "",
    "aria-describedby": "max-cena-blad",
    onInput: (z) => ustaw(z.target.value),
  });

  function ustaw(tekst) {
    if (tekst === "") {
      komunikat.hidden = true;
      pole.removeAttribute("aria-invalid");
      zmien({ maxCena: null });
      return;
    }
    const kwota = Number(tekst);
    if (!Number.isFinite(kwota) || kwota <= 0) {
      wyczysc(komunikat, ikona("CircleAlert"), "Wpisz kwotę większą od zera, np. 300, albo zostaw puste pole.");
      komunikat.hidden = false;
      pole.setAttribute("aria-invalid", "true");
      zmien({ maxCena: "blad" });
      return;
    }
    komunikat.hidden = true;
    pole.removeAttribute("aria-invalid");
    zmien({ maxCena: kwota });
  }

  const progi = PROGI_CENY.map((prog) =>
    el("button", { type: "button", class: "przycisk przycisk--maly", "aria-pressed": String(pobierz().maxCena === prog), "data-prog": prog, onClick: () => { pole.value = prog; ustaw(String(prog)); } }, `do ${zl(prog)}`),
  );
  const bezLimitu = el("button", { type: "button", class: "przycisk przycisk--maly", "aria-pressed": String(pobierz().maxCena === null), onClick: () => { pole.value = ""; ustaw(""); } }, "bez limitu");

  subskrybuj((stan, poprzedni) => {
    if (stan.maxCena === poprzedni.maxCena) return;
    for (const przycisk of progi) przycisk.setAttribute("aria-pressed", String(stan.maxCena === Number(przycisk.dataset.prog)));
    bezLimitu.setAttribute("aria-pressed", String(stan.maxCena === null));
  });

  return el(
    "div",
    { class: "grupa" },
    el("label", { class: "grupa__tytul", for: "max-cena" }, "Maksymalna cena z dostawą"),
    el("div", { class: "cena" }, el("span", { class: "pole" }, pole, el("span", { "aria-hidden": "true" }, "zł")), ...progi, bezLimitu),
    komunikat,
  );
}

function sekcjaZrodel() {
  const lista = el("div", { class: "siatka-zrodel", id: "lista-zrodel" });
  const licznik = el("p", { class: "podpowiedz", id: "zrodla-licznik", "aria-live": "polite" });
  let dostepne = [];
  let zapytanieNr = 0;

  function policz() {
    const pominiete = new Set(pobierz().pominieteZrodla);
    const wlaczone = dostepne.filter((z) => !pominiete.has(z.nazwa)).length;
    licznik.textContent = dostepne.length ? `Włączone ${wlaczone} z ${dostepne.length} ${odmiana(dostepne.length, "źródła", "źródeł", "źródeł")}.` : "";
  }

  function ustawWszystkie(wlacz) {
    const nazwy = new Set(dostepne.map((z) => z.nazwa));
    const reszta = pobierz().pominieteZrodla.filter((n) => !nazwy.has(n));
    zmien({ pominieteZrodla: wlacz ? reszta : [...reszta, ...nazwy] });
    for (const pole of lista.querySelectorAll("input:not(:disabled)")) pole.checked = wlacz;
  }

  async function wczytaj() {
    const { marka, model } = pobierz();
    const numer = ++zapytanieNr;
    if (!marka || !model) {
      dostepne = [];
      wyczysc(lista, el("p", { class: "pusty-stan" }, "Źródła zależą od modelu. Wybierz markę i model, a pokażę, gdzie będę szukać."));
      policz();
      return;
    }
    wyczysc(lista, el("div", { class: "szkielet" }), el("div", { class: "szkielet" }));
    try {
      const zrodla = await api.zrodla(marka, model);
      if (numer !== zapytanieNr) return;
      dostepne = zrodla.filter((z) => z.dostepne);
      const pominiete = new Set(pobierz().pominieteZrodla);
      wyczysc(
        lista,
        zrodla.map((z, i) =>
          przelacznik({
            id: `zrodlo-${i}`,
            etykieta: z.nazwa,
            opis: z.dostepne ? z.hosty.join(", ") : POWODY_NIEDOSTEPNOSCI[z.nazwa] || "niedostępne: brak klucza lub ustawień",
            zaznaczony: z.dostepne && !pominiete.has(z.nazwa),
            wylaczony: !z.dostepne,
            naZmiane: (wlaczone) => {
              const reszta = pobierz().pominieteZrodla.filter((n) => n !== z.nazwa);
              zmien({ pominieteZrodla: wlaczone ? reszta : [...reszta, z.nazwa] });
            },
          }),
        ),
      );
      pojawienie([...lista.children]);
    } catch (blad) {
      if (numer !== zapytanieNr) return;
      dostepne = [];
      wyczysc(
        lista,
        el(
          "div",
          { class: "blad-stan" },
          el("p", { class: "blad-stan__tytul" }, ikona("CircleAlert"), "Nie udało się pobrać listy źródeł"),
          el("p", {}, `Powód: ${blad.message}. Sprawdź, czy serwer działa, i spróbuj jeszcze raz.`),
          el("button", { type: "button", class: "przycisk przycisk--maly", onClick: wczytaj }, ikona("RefreshCw"), "Spróbuj ponownie"),
        ),
      );
    }
    policz();
  }

  subskrybuj((stan, poprzedni) => {
    if (stan.marka !== poprzedni.marka || stan.model !== poprzedni.model) wczytaj();
    else if (stan.pominieteZrodla !== poprzedni.pominieteZrodla) policz();
  });
  wczytaj();

  return el(
    "fieldset",
    { class: "grupa" },
    el("legend", {}, "Źródła"),
    el(
      "div",
      { class: "zrodla-akcje" },
      el("button", { type: "button", class: "przycisk przycisk--maly", onClick: () => ustawWszystkie(true) }, "Zaznacz wszystkie"),
      el("button", { type: "button", class: "przycisk przycisk--maly", onClick: () => ustawWszystkie(false) }, "Odznacz wszystkie"),
    ),
    lista,
    licznik,
  );
}

export function krokFiltry(kontener) {
  const stan = pobierz();
  wyczysc(
    kontener,
    sekcjaCeny(),
    el(
      "fieldset",
      { class: "grupa" },
      el("legend", {}, "Dokładność i świeżość"),
      przelacznik({
        id: "tylko-pewne",
        etykieta: "Tylko potwierdzony rozmiar",
        opis: "Pomija ogłoszenia, w których rozmiar albo model trzeba sprawdzić samemu.",
        zaznaczony: stan.tylkoPewne,
        naZmiane: (wartosc) => zmien({ tylkoPewne: wartosc }),
      }),
      przelacznik({
        id: "odswiez",
        etykieta: "Pobierz wszystko od nowa",
        opis: "Pomija pamięć podręczną z ostatnich 6 godzin. Szukanie potrwa dłużej i bardziej obciąży strony.",
        zaznaczony: stan.odswiez,
        naZmiane: (wartosc) => zmien({ odswiez: wartosc }),
      }),
    ),
    sekcjaZrodel(),
  );
}
