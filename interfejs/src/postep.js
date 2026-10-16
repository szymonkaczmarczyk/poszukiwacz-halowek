import * as api from "./api.js";
import { el, odmiana, wyczysc, zl } from "./dom.js";
import { ikona } from "./ikony.js";
import { powiadom } from "./powiadomienia.js";
import { pojawienie, przewin } from "./ruch.js";
import { widokWynikow } from "./wyniki.js";

const IKONA_STANU = {
  czeka: "Clock",
  trwa: "LoaderCircle",
  ok: "CircleCheck",
  wstrzymane: "Pause",
  podejrzane: "TriangleAlert",
  "błąd": "CircleX",
  przerwane: "Square",
};
const OPIS_STANU = {
  wstrzymane: "wstrzymane",
  podejrzane: "podejrzanie mało",
  "błąd": "błąd",
  przerwane: "przerwane",
};

function ogloszZdarzenie(zdarzenie) {
  document.dispatchEvent(new CustomEvent("szatnia:wyszukiwanie", { detail: zdarzenie }));
}

export function postep({ sekcja, tytul, numer, opis, zrodla, wyniki, przerwij, pasekPostepu }, { naKoniec }) {
  let pozycje = new Map();
  let zakonczone = true;
  let identyfikator = null;
  let rozmiaryRazem = 1;
  let gotoweRozmiary = 0;
  let zamknijStrumien = null;

  const widok = widokWynikow(wyniki, { naUkryj: ukryjOferte });

  async function ukryjOferte(oferta, cofnijWidok) {
    try {
      await api.ukryj(oferta.url);
      powiadom(`Ukryto: ${oferta.tytul}`, {
        akcja: {
          etykieta: "Cofnij",
          wykonaj: async () => {
            try {
              await api.przywroc(oferta.url);
              cofnijWidok();
            } catch (blad) {
              powiadom(`Nie udało się przywrócić oferty: ${blad.message}.`, { rodzaj: "blad" });
            }
          },
        },
      });
    } catch (blad) {
      cofnijWidok();
      powiadom(`Nie udało się ukryć oferty: ${blad.message}. Spróbuj jeszcze raz.`, { rodzaj: "blad" });
    }
  }

  function ustawPasek() {
    const wszystkie = [...pozycje.values()];
    const skonczone = wszystkie.filter((p) => !["czeka", "trwa"].includes(p.dataset.stan)).length;
    const czesc = wszystkie.length ? skonczone / wszystkie.length : 0;
    const procent = Math.round(((gotoweRozmiary + (zakonczone ? 0 : czesc)) / rozmiaryRazem) * 100);
    const wartosc = zakonczone ? 100 : Math.min(99, procent);
    pasekPostepu.setAttribute("aria-valuenow", String(wartosc));
    pasekPostepu.style.setProperty("--postep", String(wartosc / 100));
  }

  function ustawZrodlo(nazwa, stan, tekst) {
    const pozycja = pozycje.get(nazwa);
    if (!pozycja) return;
    pozycja.dataset.stan = stan;
    pozycja.firstChild.replaceWith(ikona(IKONA_STANU[stan] || "Clock"));
    if (tekst !== undefined) pozycja.querySelector(".zrodlo__stan").textContent = tekst;
    ustawPasek();
  }

  function obsluz(zdarzenie) {
    const { typ, dane } = zdarzenie;
    ogloszZdarzenie(zdarzenie);
    if (typ === "wyszukiwanie_start") {
      rozmiaryRazem = dane.rozmiary.length;
      opis.textContent = `Szukam: ${dane.nazwa}, ${odmiana(dane.rozmiary.length, "rozmiar", "rozmiary", "rozmiary")} ${dane.rozmiary.join(", ")}. Zapytania idą powoli, żeby sklepy nas nie blokowały.`;
    } else if (typ === "start") {
      numer.textContent = rozmiaryRazem > 1 ? `Rozmiar ${dane.rozmiar} · ${gotoweRozmiary + 1} z ${rozmiaryRazem}` : `Rozmiar ${dane.rozmiar}`;
      pozycje = new Map(
        dane.zrodla.map((nazwa) => [
          nazwa,
          el("li", { class: "zrodlo", "data-stan": "czeka" }, ikona("Clock"), el("span", { class: "zrodlo__nazwa" }, nazwa), el("span", { class: "zrodlo__stan" }, "czeka")),
        ]),
      );
      wyczysc(zrodla, [...pozycje.values()]);
      pojawienie([...zrodla.children]);
      widok.rozmiar(dane.rozmiar);
      ustawPasek();
    } else if (typ === "zrodlo_start") {
      ustawZrodlo(dane.zrodlo, "trwa", "sprawdzam…");
    } else if (typ === "zrodlo_koniec") {
      const tekst = dane.status === "ok" ? `${dane.ofert} z ${dane.odczytano} pasuje` : OPIS_STANU[dane.status] || dane.status;
      ustawZrodlo(dane.nazwa, dane.status, tekst);
      widok.podglad(dane.rozmiar, dane.oferty || []);
    } else if (typ === "koniec") {
      gotoweRozmiary += 1;
      widok.koniec(dane.rozmiar, dane.wyniki || {});
      ustawPasek();
    } else if (typ === "przerywanie") {
      przerwij.setAttribute("aria-disabled", "true");
      opis.textContent = "Przerywam. Kończę bieżące zapytania i zapisuję to, co już znalazłem…";
    } else if (typ === "blad") {
      wyniki.prepend(
        el("div", { class: "blad-stan", role: "alert" }, el("p", { class: "blad-stan__tytul" }, ikona("CircleAlert"), "Wyszukiwanie przerwane"), el("p", {}, `${dane.komunikat}. Zmień źródła albo spróbuj ponownie za chwilę.`)),
      );
    } else if (typ === "wyszukiwanie_koniec") {
      zakoncz(dane);
    }
  }

  function zakoncz(dane) {
    if (zakonczone) return;
    zakonczone = true;
    zamknijStrumien?.();
    przerwij.hidden = true;
    widok.zakoncz();
    ustawPasek();
    const oferty = widok.wszystkie();
    const najtansza = oferty.sort((a, b) => a.suma_pln - b.suma_pln)[0];
    const czas = dane.czas ? `w ${Math.round(dane.czas)} s` : "";
    if (dane.stan === "gotowe") {
      numer.textContent = "Gotowe";
      tytul.textContent = "Wyniki";
      opis.textContent = najtansza ? `Gotowe ${czas}. Najtańsza oferta: ${zl(najtansza.suma_pln)} (${najtansza.zrodlo}).` : `Gotowe ${czas}, ale nic nie pasuje.`;
    } else if (dane.stan === "przerwane") {
      numer.textContent = "Przerwane";
      tytul.textContent = "Wyniki częściowe";
      opis.textContent = oferty.length ? `Przerwano ${czas}. Pokazuję ${oferty.length} ${odmiana(oferty.length, "ofertę", "oferty", "ofert")} ze źródeł, które zdążyły odpowiedzieć.` : "Przerwano, zanim jakiekolwiek źródło skończyło.";
    } else {
      numer.textContent = "Przerwane";
      tytul.textContent = "Wyszukiwanie przerwane";
    }
    naKoniec(dane.stan);
  }

  async function zadajPrzerwanie() {
    if (zakonczone || !identyfikator || przerwij.getAttribute("aria-disabled") === "true") return;
    przerwij.setAttribute("aria-disabled", "true");
    try {
      await api.przerwij(identyfikator);
    } catch (blad) {
      if (blad.status !== 409) {
        przerwij.removeAttribute("aria-disabled");
        powiadom(`Nie udało się przerwać: ${blad.message}.`, { rodzaj: "blad" });
      }
    }
  }

  przerwij.addEventListener("click", zadajPrzerwanie);
  document.addEventListener("keydown", (zdarzenie) => {
    if (zdarzenie.key === "Escape" && !zakonczone) zadajPrzerwanie();
  });

  function niepowodzenie(tekst) {
    zakonczone = false;
    zakoncz({ stan: "blad" });
    opis.textContent = tekst;
  }

  return {
    async uruchom(stan) {
      zakonczone = false;
      identyfikator = null;
      gotoweRozmiary = 0;
      rozmiaryRazem = stan.rozmiary.length;
      pozycje = new Map();
      sekcja.hidden = false;
      numer.textContent = "Wyszukiwanie";
      tytul.textContent = "Szukam ofert";
      opis.textContent = "Uruchamiam wyszukiwanie…";
      przerwij.hidden = false;
      przerwij.removeAttribute("aria-disabled");
      wyczysc(zrodla);
      widok.reset();
      ustawPasek();
      przewin(sekcja);
      const zapytanie = {
        marka: stan.marka,
        model: stan.model,
        rozmiary: stan.rozmiary,
        tylko_pewne: stan.tylkoPewne,
        odswiez: stan.odswiez,
      };
      if (typeof stan.maxCena === "number") zapytanie.max_cena = stan.maxCena;
      try {
        if (stan.pominieteZrodla.length) {
          const wszystkie = await api.zrodla(stan.marka, stan.model);
          zapytanie.zrodla = wszystkie.filter((z) => z.dostepne && !stan.pominieteZrodla.includes(z.nazwa)).map((z) => z.nazwa);
          if (!zapytanie.zrodla.length) {
            niepowodzenie("Wszystkie źródła są odznaczone. Włącz co najmniej jedno w kroku Filtry.");
            return;
          }
        }
        const odpowiedz = await api.startWyszukiwania(zapytanie);
        identyfikator = odpowiedz.id;
        zamknijStrumien = api.sluchajZdarzen(odpowiedz.zdarzenia, obsluz, () => {
          if (!zakonczone) niepowodzenie("Utracono połączenie z serwerem. Wyniki zapisane do tej pory są w katalogu wyniki/.");
        });
      } catch (blad) {
        niepowodzenie(blad.status === 409 ? "Trwa już inne wyszukiwanie. Poczekaj, aż się skończy." : `Nie udało się wystartować: ${blad.message}.`);
      }
    },
  };
}
