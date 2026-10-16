import * as api from "./api.js";
import { el, wyczysc } from "./dom.js";
import { ikona } from "./ikony.js";
import { powiadom } from "./powiadomienia.js";
import { wstrzymajPrzewijanie } from "./ruch.js";
import { pobierz } from "./stan.js";

const WZOR_NAZWY = /^[\p{L}\p{N}_][\p{L}\p{N}_ .+/-]*$/u;
const WZOR_SLOWA = /^[\p{L}\p{N}_][\p{L}\p{N}_ .-]*$/u;
const INNA_MARKA = "__inna__";
const GOTOWE_WYKLUCZENIA = ["jr", "junior", "kids", "turf", "tf", "fg"];
const CZAS_POTWIERDZENIA = 4000;

function pole({ id, etykieta, podpowiedz, kontrolka }) {
  const blad = el("p", { class: "komunikat-bledu", id: `${id}-blad`, "aria-live": "polite", hidden: true });
  kontrolka.setAttribute("aria-describedby", `${id}-podpowiedz ${id}-blad`);
  return {
    element: el("div", { class: "pole-formularza" }, el("label", { for: id, class: "pole-formularza__etykieta" }, etykieta), kontrolka, el("p", { class: "podpowiedz", id: `${id}-podpowiedz` }, podpowiedz), blad),
    pokazBlad(tekst) {
      if (!tekst) {
        blad.hidden = true;
        kontrolka.removeAttribute("aria-invalid");
        return;
      }
      wyczysc(blad, ikona("CircleAlert"), tekst);
      blad.hidden = false;
      kontrolka.setAttribute("aria-invalid", "true");
    },
  };
}

function slowa(tekst) {
  return [...new Set(tekst.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean))];
}

export function edytorModelu(katalog, { naZmiane }) {
  const okno = el("dialog", { class: "okno", "aria-labelledby": "okno-tytul", "data-lenis-prevent": "" });
  const wyborMarki = el("select", { id: "edytor-marka", name: "marka" });
  const nowaMarka = el("input", { id: "edytor-nowa-marka", name: "nowa-marka", type: "text", autocomplete: "off", maxlength: "40", placeholder: "np. Kelme…" });
  const nazwa = el("input", { id: "edytor-model", name: "model", type: "text", autocomplete: "off", maxlength: "40", placeholder: "np. Top Flex 2402…", required: true });
  const wykluczenia = el("input", { id: "edytor-wykluczenia", name: "wykluczenia", type: "text", autocomplete: "off", spellcheck: "false", placeholder: "np. rebound, jr, turf…" });
  const hala = el("input", { id: "edytor-hala", name: "hala", type: "checkbox", checked: true });
  const notatka = el("input", { id: "edytor-opis", name: "opis", type: "text", autocomplete: "off", maxlength: "120", placeholder: "np. wersja z 2024 roku…" });
  const bladOgolny = el("div", { class: "blad-stan", role: "alert", hidden: true });
  const listaWlasnych = el("ul", { class: "okno__lista" });
  const etykietaWyslij = el("span", {}, "Dodaj model");
  const wyslij = el("button", { type: "submit", class: "przycisk przycisk--glowny" }, ikona("Plus"), etykietaWyslij);

  const poleMarki = pole({ id: "edytor-marka", etykieta: "Marka", podpowiedz: "Wybierz z listy albo dopisz nową markę.", kontrolka: wyborMarki });
  const poleNowejMarki = pole({ id: "edytor-nowa-marka", etykieta: "Nazwa nowej marki", podpowiedz: "Tak, jak pisze się ją w ogłoszeniach.", kontrolka: nowaMarka });
  const poleModelu = pole({ id: "edytor-model", etykieta: "Nazwa modelu", podpowiedz: "Wszystkie te słowa muszą być w tytule ogłoszenia.", kontrolka: nazwa });
  const poleWykluczen = pole({ id: "edytor-wykluczenia", etykieta: "Pomiń wersje", podpowiedz: "Słowa po przecinku. Ogłoszenia z nimi zostaną odrzucone.", kontrolka: wykluczenia });
  const poleNotatki = pole({ id: "edytor-opis", etykieta: "Notatka (opcjonalnie)", podpowiedz: "Pokaże się pod nazwą modelu.", kontrolka: notatka });

  const gotowe = el(
    "div",
    { class: "okno__gotowe", role: "group", "aria-label": "Gotowe słowa do pominięcia" },
    GOTOWE_WYKLUCZENIA.map((slowo) =>
      el(
        "button",
        {
          type: "button",
          class: "przycisk przycisk--maly",
          "aria-pressed": "false",
          "data-slowo": slowo,
          onClick: (z) => {
            const obecne = slowa(wykluczenia.value);
            const nowe = obecne.includes(slowo) ? obecne.filter((s) => s !== slowo) : [...obecne, slowo];
            wykluczenia.value = nowe.join(", ");
            z.currentTarget.setAttribute("aria-pressed", String(nowe.includes(slowo)));
          },
        },
        slowo,
      ),
    ),
  );
  wykluczenia.addEventListener("input", () => {
    const obecne = slowa(wykluczenia.value);
    for (const przycisk of gotowe.children) przycisk.setAttribute("aria-pressed", String(obecne.includes(przycisk.dataset.slowo)));
  });

  const forma = el(
    "form",
    { class: "okno__forma", novalidate: true },
    el(
      "header",
      { class: "okno__naglowek" },
      el("button", { type: "button", class: "przycisk przycisk--maly", onClick: () => zamknij() }, ikona("X"), "Zamknij"),
      el("h2", { id: "okno-tytul" }, "Własny model"),
    ),
    el("p", { class: "podpowiedz" }, "Dodaj model spoza katalogu. Szatnia będzie szukać ogłoszeń z jego nazwą i od razu odrzuci wersje dziecięce oraz inne nawierzchnie tej marki."),
    bladOgolny,
    poleMarki.element,
    poleNowejMarki.element,
    poleModelu.element,
    poleWykluczen.element,
    gotowe,
    el(
      "label",
      { class: "przelacznik", for: "edytor-hala" },
      hala,
      el("span", {}, "Tylko wersje halowe", el("span", { class: "przelacznik__opis" }, "Odrzuca ogłoszenia bez IC, IN, IT albo słowa „halówki” w tytule. Ma znaczenie dla Nike, Adidas i Puma.")),
    ),
    poleNotatki.element,
    el("footer", { class: "okno__stopka" }, wyslij),
    el("section", { class: "okno__wlasne", "aria-labelledby": "okno-wlasne-tytul" }, el("h3", { id: "okno-wlasne-tytul" }, "Twoje modele"), listaWlasnych),
  );
  okno.append(forma);
  document.body.append(okno);

  function opcjeMarek() {
    wyczysc(wyborMarki, katalog.marki.map((m) => el("option", { value: m.id }, m.nazwa)), el("option", { value: INNA_MARKA }, "Inna marka…"));
  }

  function pokazNowaMarke() {
    poleNowejMarki.element.hidden = wyborMarki.value !== INNA_MARKA;
  }
  wyborMarki.addEventListener("change", pokazNowaMarke);

  function rysujWlasne() {
    const wlasne = katalog.marki.flatMap((m) => m.modele.filter((mo) => mo.wlasny).map((mo) => ({ marka: m, model: mo })));
    if (!wlasne.length) {
      wyczysc(listaWlasnych, el("li", { class: "podpowiedz" }, "Nie masz jeszcze własnych modeli. Pierwszy dodasz formularzem powyżej."));
      return;
    }
    wyczysc(
      listaWlasnych,
      wlasne.map(({ marka, model }) => {
        const usun = el("button", { type: "button", class: "przycisk przycisk--maly", "aria-label": `Usuń ${model.nazwa}` }, ikona("Trash2"), "Usuń");
        let zegar = null;
        usun.addEventListener("click", async () => {
          if (usun.dataset.potwierdz !== "true") {
            usun.dataset.potwierdz = "true";
            usun.setAttribute("aria-label", `Potwierdź usunięcie ${model.nazwa}`);
            usun.lastChild.textContent = "Na pewno?";
            zegar = setTimeout(() => {
              usun.dataset.potwierdz = "false";
              usun.setAttribute("aria-label", `Usuń ${model.nazwa}`);
              usun.lastChild.textContent = "Usuń";
            }, CZAS_POTWIERDZENIA);
            return;
          }
          clearTimeout(zegar);
          try {
            await api.usunWlasny(marka.id, model.id);
            await naZmiane({ usuniety: { marka: marka.id, model: model.id } });
            powiadom(`Usunięto ${model.nazwa}.`);
            odswiez();
          } catch (blad) {
            powiadom(`Nie udało się usunąć: ${blad.message}.`, { rodzaj: "blad" });
          }
        });
        return el("li", { class: "okno__wlasny" }, el("span", {}, model.nazwa, model.opis_wykluczen && el("span", { class: "podpowiedz" }, model.opis_wykluczen)), usun);
      }),
    );
  }

  function odswiez() {
    opcjeMarek();
    rysujWlasne();
  }

  function sprawdz() {
    const bledy = [];
    const marka = wyborMarki.value === INNA_MARKA ? nowaMarka.value.trim() : wyborMarki.value;
    const model = nazwa.value.trim();
    const lista = slowa(wykluczenia.value);
    const oznacz = (p, kontrolka, tekst) => {
      p.pokazBlad(tekst);
      if (tekst) bledy.push(kontrolka);
    };
    oznacz(poleNowejMarki, nowaMarka, wyborMarki.value === INNA_MARKA && (marka.length < 2 || !WZOR_NAZWY.test(marka)) ? "Wpisz nazwę marki z co najmniej 2 znaków, same litery, cyfry i spacje." : "");
    oznacz(poleModelu, nazwa, model.length < 2 || !WZOR_NAZWY.test(model) ? "Wpisz nazwę modelu z co najmniej 2 znaków, np. Top Flex. Dozwolone litery, cyfry, spacje i - . + /" : "");
    const zle = lista.filter((s) => s.length > 30 || !WZOR_SLOWA.test(s));
    oznacz(poleWykluczen, wykluczenia, zle.length ? `Popraw: ${zle.join(", ")}. Same litery, cyfry i spacje, do 30 znaków.` : lista.length > 15 ? "Najwyżej 15 słów." : "");
    return { bledy, dane: { marka, model, wykluczenia: lista, opis: notatka.value.trim(), wymagaj_oznaczenia_hali: hala.checked } };
  }

  forma.addEventListener("submit", async (zdarzenie) => {
    zdarzenie.preventDefault();
    bladOgolny.hidden = true;
    const { bledy, dane } = sprawdz();
    if (bledy.length) {
      bledy[0].focus();
      return;
    }
    if (wyslij.getAttribute("aria-disabled") === "true") return;
    wyslij.setAttribute("aria-disabled", "true");
    etykietaWyslij.textContent = "Dodaję…";
    try {
      const wynik = await api.dodajWlasny(dane);
      await naZmiane({ dodany: wynik });
      powiadom(`Dodano ${dane.model}. Możesz go od razu wyszukać.`);
      forma.reset();
      zamknij();
    } catch (blad) {
      wyczysc(bladOgolny, el("p", { class: "blad-stan__tytul" }, ikona("CircleAlert"), "Nie udało się dodać modelu"), el("p", {}, `${blad.message}. Zmień nazwę albo spróbuj ponownie.`));
      bladOgolny.hidden = false;
    } finally {
      wyslij.removeAttribute("aria-disabled");
      etykietaWyslij.textContent = "Dodaj model";
    }
  });

  function zamknij() {
    okno.close();
  }

  okno.addEventListener("close", () => wstrzymajPrzewijanie(false));

  return {
    otworz() {
      odswiez();
      wyborMarki.value = pobierz().marka || katalog.marki[0]?.id;
      pokazNowaMarke();
      for (const p of [poleNowejMarki, poleModelu, poleWykluczen]) p.pokazBlad("");
      bladOgolny.hidden = true;
      wstrzymajPrzewijanie(true);
      okno.showModal();
      nazwa.focus();
    },
    odswiez,
  };
}
