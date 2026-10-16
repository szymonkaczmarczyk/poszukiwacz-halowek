import { el, odmiana, wyczysc, zl } from "./dom.js";
import { ikona } from "./ikony.js";
import { pojawienie, przewin } from "./ruch.js";

const NA_STRONE = 12;
const GRUPY = [
  { id: "pewne", tytul: "Potwierdzony rozmiar", opis: "Model i rozmiar się zgadzają." },
  { id: "rozmiar", tytul: "Rozmiar do sprawdzenia", opis: "Model się zgadza, ale ogłoszenie nie podaje rozmiaru jednoznacznie. Zapytaj sprzedającego." },
  { id: "weryfikacja", tytul: "Model do sprawdzenia na zdjęciu", opis: "Buty tej marki w Twoim rozmiarze, ale bez nazwy modelu w tytule." },
];
const SORTOWANIE = {
  cena: (a, b) => a.suma_pln - b.suma_pln,
  "cena-": (a, b) => b.suma_pln - a.suma_pln,
  zrodlo: (a, b) => a.zrodlo.localeCompare(b.zrodlo, "pl") || a.suma_pln - b.suma_pln,
};
const ZNAKI_WALUT = { EUR: "€", GBP: "£", USD: "$" };

export function bezpiecznyAdres(adres) {
  try {
    const url = new URL(adres);
    return url.protocol === "https:" || url.protocol === "http:" ? url.href : null;
  } catch {
    return null;
  }
}

function znaczekFlagi(flaga) {
  if (flaga === "NOWE") return el("li", { class: "znaczek znaczek--sukces" }, ikona("Sparkles"), "nowa");
  if (flaga.startsWith("TANIEJ")) return el("li", { class: "znaczek znaczek--sukces" }, ikona("TrendingDown"), flaga.toLowerCase());
  return el("li", { class: "znaczek znaczek--ostrzezenie" }, ikona("TrendingUp"), flaga);
}

function kartaOferty(oferta, naUkryj) {
  const adres = bezpiecznyAdres(oferta.url);
  const zdjecie = bezpiecznyAdres(oferta.zdjecie);
  const meta = [oferta.zrodlo, oferta.stan, oferta.lokalizacja].filter(Boolean).join(" · ");
  const dostawa =
    oferta.dostawa_pln === null || oferta.dostawa_pln === undefined
      ? oferta.wysylka || "koszt dostawy nieznany"
      : `w tym dostawa ${oferta.dostawa_szacunkowa ? "~" : ""}${zl(oferta.dostawa_pln)}${oferta.dostawa_szacunkowa ? " (szac.)" : ""}`;
  const waluta = oferta.waluta && oferta.waluta !== "PLN" ? `${oferta.cena.toFixed(2).replace(".", ",")} ${ZNAKI_WALUT[oferta.waluta] || oferta.waluta}` : null;
  const znaczki = [
    ...(oferta.flagi || []).map(znaczekFlagi),
    oferta.wskazowka && el("li", { class: "znaczek" }, oferta.wskazowka),
    oferta.uwagi && el("li", { class: "znaczek" }, oferta.uwagi),
  ].filter(Boolean);
  const tytul = adres
    ? el("a", { class: "oferta__link", href: adres, target: "_blank", rel: "noopener noreferrer" }, oferta.tytul)
    : oferta.tytul;
  return el(
    "article",
    { class: `oferta oferta--${oferta.grupa}`, "data-klucz": oferta.klucz },
    zdjecie
      ? el("img", { class: "oferta__zdjecie", src: zdjecie, alt: `Zdjęcie z oferty: ${oferta.tytul}`, loading: "lazy", decoding: "async", referrerpolicy: "no-referrer", width: 96, height: 96 })
      : el("span", { class: "oferta__zdjecie oferta__zdjecie--brak", "aria-hidden": "true" }),
    el(
      "div",
      { class: "oferta__tresc" },
      el("h4", { class: "oferta__tytul" }, tytul),
      el("p", { class: "oferta__meta" }, meta),
      znaczki.length > 0 && el("ul", { class: "znaczki", "aria-label": "Oznaczenia oferty" }, znaczki),
    ),
    el(
      "div",
      { class: "oferta__prawa" },
      el("span", { class: "oferta__cena" }, `${oferta.dostawa_szacunkowa ? "~" : ""}${zl(oferta.suma_pln)}`),
      el("span", { class: "oferta__dostawa" }, waluta ? `${waluta} · ${dostawa}` : dostawa),
      el(
        "button",
        { type: "button", class: "przycisk przycisk--maly oferta__ukryj", "aria-label": `Ukryj ofertę: ${oferta.tytul}`, onClick: () => naUkryj(oferta) },
        ikona("EyeOff"),
        el("span", { "aria-hidden": "true" }, "Ukryj"),
      ),
    ),
  );
}

function blokZmian(rozmiar, zmiany, liczbaOfert) {
  if (!zmiany) return null;
  if (zmiany.pierwsze) {
    return el("div", { class: "zmiany" }, el("p", {}, `Pierwsze sprawdzenie w rozmiarze ${rozmiar}. Następnym razem pokażę tu nowe oferty, tańsze i te, które zniknęły.`));
  }
  const pozycje = [
    [zmiany.nowe.length, "Sparkles", "znaczek--sukces", odmiana(zmiany.nowe.length, "nowa", "nowe", "nowych")],
    [zmiany.tansze.length, "TrendingDown", "znaczek--sukces", odmiana(zmiany.tansze.length, "tańsza", "tańsze", "tańszych")],
    [zmiany.drozsze.length, "TrendingUp", "znaczek--ostrzezenie", odmiana(zmiany.drozsze.length, "droższa", "droższe", "droższych")],
    [zmiany.zniknely.length, "Minus", "", odmiana(zmiany.zniknely.length, "zniknęła", "zniknęły", "zniknęło")],
  ].filter(([liczba]) => liczba > 0);
  const kiedy = zmiany.poprzednio ? ` (${zmiany.poprzednio})` : "";
  return el(
    "div",
    { class: "zmiany" },
    el("h3", { class: "zmiany__tytul" }, `Od ostatniego sprawdzenia${kiedy}`),
    pozycje.length
      ? el("ul", { class: "znaczki" }, pozycje.map(([liczba, nazwa, klasa, opis]) => el("li", { class: `znaczek ${klasa}` }, ikona(nazwa), `${liczba} ${opis}`)))
      : el("p", {}, `Bez zmian. Te same ${liczbaOfert} ${odmiana(liczbaOfert, "oferta", "oferty", "ofert")} co ostatnio.`),
    zmiany.zniknely.length > 0 &&
      el(
        "details",
        { class: "zmiany__szczegoly" },
        el("summary", {}, "Pokaż oferty, które zniknęły"),
        el(
          "ul",
          {},
          zmiany.zniknely.map((z) => el("li", {}, `${z.tytul} · ${z.zrodlo}${z.cena ? ` · ostatnio ${zl(z.cena)}` : ""}`)),
        ),
      ),
  );
}

function alarmZrodel(zrodla) {
  const problemy = (zrodla || []).filter((z) => z.status === "podejrzane" || z.status === "błąd");
  if (!problemy.length) return null;
  return el(
    "div",
    { class: "blad-stan", role: "alert" },
    el("p", { class: "blad-stan__tytul" }, ikona("TriangleAlert"), `${problemy.length} ${odmiana(problemy.length, "źródło mogło", "źródła mogły", "źródeł mogło")} przestać działać`),
    el("p", {}, `${problemy.map((z) => z.nazwa).join(", ")}. Brak wyników z tych stron nie znaczy, że nie ma butów. Strona mogła zmienić wygląd.`),
  );
}

function linkiReczne(recznie) {
  if (!recznie?.length) return null;
  return el(
    "div",
    { class: "recznie" },
    el("h3", {}, "Sprawdź też ręcznie"),
    el("p", { class: "podpowiedz" }, "Te strony blokują automaty, więc otwórz je sam. Linki są już ułożone pod Twój model i rozmiar."),
    el(
      "ul",
      { class: "recznie__lista" },
      recznie
        .filter((r) => bezpiecznyAdres(r.url))
        .map((r) =>
          el(
            "li",
            {},
            el("a", { href: bezpiecznyAdres(r.url), target: "_blank", rel: "noopener noreferrer", class: "recznie__link" }, r.nazwa, ikona("ExternalLink")),
            el("span", { class: "podpowiedz" }, r.opis),
          ),
        ),
    ),
  );
}

export function widokWynikow(kontener, { naUkryj }) {
  const rozmiary = new Map();
  const ukryte = new Set();
  const filtry = { zrodlo: "", sort: "cena", tylkoPewne: false };
  const limity = {};
  let aktywny = null;
  let trwa = false;

  const zakladki = el("div", { class: "zakladki", role: "tablist", "aria-label": "Rozmiary" });
  const alarm = el("div");
  const zmiany = el("div");
  const wyborZrodla = el("select", { id: "filtr-zrodla", name: "filtr-zrodla", onChange: (z) => ustawFiltr("zrodlo", z.target.value) });
  const sortowanie = el(
    "select",
    { id: "sortowanie", name: "sortowanie", onChange: (z) => ustawFiltr("sort", z.target.value) },
    el("option", { value: "cena" }, "od najtańszych"),
    el("option", { value: "cena-" }, "od najdroższych"),
    el("option", { value: "zrodlo" }, "według źródła"),
  );
  const licznik = el("p", { class: "podpowiedz narzedzia__licznik", "aria-live": "polite" });
  const narzedzia = el(
    "div",
    { class: "narzedzia" },
    el("label", { class: "narzedzia__pole", for: "filtr-zrodla" }, "Źródło", wyborZrodla),
    el("label", { class: "narzedzia__pole", for: "sortowanie" }, "Kolejność", sortowanie),
    el(
      "label",
      { class: "przelacznik", for: "filtr-pewne" },
      el("input", { type: "checkbox", id: "filtr-pewne", onChange: (z) => ustawFiltr("tylkoPewne", z.target.checked) }),
      el("span", {}, "Tylko potwierdzony rozmiar"),
    ),
    licznik,
  );
  const grupy = el("div", { class: "grupy" });
  const recznie = el("div");
  const panel = el("div", { class: "wyniki__panel", role: "tabpanel", id: "panel-wynikow" }, alarm, zmiany, narzedzia, grupy, recznie);

  function ustawFiltr(klucz, wartosc) {
    filtry[klucz] = wartosc;
    rysuj();
  }

  function biezacy() {
    return rozmiary.get(aktywny);
  }

  function widoczne(dane) {
    return [...dane.oferty.values()].filter((o) => !ukryte.has(o.klucz));
  }

  function rysujZakladki() {
    zakladki.hidden = rozmiary.size < 2;
    wyczysc(
      zakladki,
      [...rozmiary.entries()].map(([rozmiar, dane]) =>
        el(
          "button",
          {
            type: "button",
            role: "tab",
            class: "zakladka",
            id: `zakladka-${rozmiar}`,
            "aria-selected": String(rozmiar === aktywny),
            "aria-controls": "panel-wynikow",
            tabindex: rozmiar === aktywny ? "0" : "-1",
            onClick: () => {
              aktywny = rozmiar;
              rysuj();
            },
          },
          `Rozm. ${rozmiar}`,
          el("span", { class: "zakladka__liczba" }, dane.koniec ? widoczne(dane).length : "…"),
        ),
      ),
    );
    panel.setAttribute("aria-labelledby", aktywny ? `zakladka-${aktywny}` : "postep-tytul");
  }

  function rysujNarzedzia(lista) {
    const zrodla = [...new Set(lista.map((o) => o.zrodlo))].sort((a, b) => a.localeCompare(b, "pl"));
    if (filtry.zrodlo && !zrodla.includes(filtry.zrodlo)) filtry.zrodlo = "";
    wyczysc(wyborZrodla, el("option", { value: "" }, "wszystkie"), zrodla.map((z) => el("option", { value: z }, z)));
    wyborZrodla.value = filtry.zrodlo;
    narzedzia.hidden = lista.length === 0;
  }

  function pustyStan(dane) {
    if (!dane.koniec) return el("div", { class: "pusty-stan" }, el("p", {}, "Oferty pojawią się tutaj, gdy pierwsze źródło skończy sprawdzanie."));
    return el(
      "div",
      { class: "pusty-stan" },
      el("p", {}, `Nie znalazłem ofert w rozmiarze ${aktywny}. Spróbuj sąsiedniego rozmiaru, wyłącz limit ceny albo filtr potwierdzonego rozmiaru.`),
      el("button", { type: "button", class: "przycisk przycisk--maly", onClick: () => przewin("#krok-rozmiar") }, "Zmień rozmiar", ikona("ArrowRight")),
    );
  }

  function rysujGrupy(dane, lista) {
    const przed = new Set([...grupy.querySelectorAll("[data-klucz]")].map((e) => e.dataset.klucz));
    const przefiltrowane = lista
      .filter((o) => !filtry.zrodlo || o.zrodlo === filtry.zrodlo)
      .filter((o) => !filtry.tylkoPewne || o.grupa === "pewne")
      .sort(SORTOWANIE[filtry.sort]);
    const ileOfert = przefiltrowane.length;
    licznik.textContent = lista.length ? `Pokazuję ${ileOfert} z ${lista.length} ${odmiana(lista.length, "oferty", "ofert", "ofert")}.` : "";
    if (!lista.length) {
      wyczysc(grupy, pustyStan(dane));
      return;
    }
    if (!ileOfert) {
      wyczysc(grupy, el("div", { class: "pusty-stan" }, el("p", {}, "Żadna oferta nie pasuje do wybranych filtrów. Zmień źródło albo wyłącz filtr potwierdzonego rozmiaru.")));
      return;
    }
    wyczysc(
      grupy,
      GRUPY.map((grupa) => {
        const wGrupie = przefiltrowane.filter((o) => o.grupa === grupa.id);
        if (!wGrupie.length) return null;
        const klucz = `${aktywny}|${grupa.id}`;
        const limit = limity[klucz] || NA_STRONE;
        const reszta = wGrupie.length - limit;
        const opis = grupa.id === "weryfikacja" && dane.wskazowkaZdjec ? `${grupa.opis} Jak rozpoznać: ${dane.wskazowkaZdjec}.` : grupa.opis;
        return el(
          "section",
          { class: `grupa-ofert grupa-ofert--${grupa.id}`, "aria-labelledby": `grupa-${grupa.id}` },
          el("h3", { id: `grupa-${grupa.id}`, class: "grupa-ofert__tytul" }, grupa.tytul, el("span", { class: "grupa-ofert__liczba" }, wGrupie.length)),
          el("p", { class: "podpowiedz" }, opis),
          el("div", { class: "grupa-ofert__lista" }, wGrupie.slice(0, limit).map((o) => kartaOferty(o, ukryj))),
          reszta > 0 &&
            el(
              "button",
              {
                type: "button",
                class: "przycisk przycisk--maly grupa-ofert__wiecej",
                onClick: () => {
                  limity[klucz] = limit + NA_STRONE;
                  rysuj();
                },
              },
              `Pokaż kolejne ${Math.min(reszta, NA_STRONE)} (zostało ${reszta})`,
            ),
        );
      }),
    );
    pojawienie([...grupy.querySelectorAll("[data-klucz]")].filter((e) => !przed.has(e.dataset.klucz)));
  }

  function rysuj() {
    const dane = biezacy();
    if (!dane) {
      wyczysc(kontener);
      return;
    }
    if (!panel.isConnected) wyczysc(kontener, zakladki, panel);
    const lista = widoczne(dane);
    rysujZakladki();
    wyczysc(alarm, alarmZrodel(dane.zrodla));
    wyczysc(zmiany, blokZmian(aktywny, dane.zmiany, lista.length));
    rysujNarzedzia(lista);
    rysujGrupy(dane, lista);
    wyczysc(recznie, dane.koniec && !trwa ? linkiReczne(dane.recznie) : null);
  }

  function ukryj(oferta) {
    ukryte.add(oferta.klucz);
    const karta = grupy.querySelector(`[data-klucz="${CSS.escape(oferta.klucz)}"]`);
    const nastepna = karta?.nextElementSibling?.querySelector(".oferta__ukryj") || karta?.previousElementSibling?.querySelector(".oferta__ukryj");
    rysuj();
    (nastepna?.isConnected ? nastepna : document.getElementById("postep-tytul")).focus({ preventScroll: true });
    naUkryj(oferta, () => {
      ukryte.delete(oferta.klucz);
      rysuj();
    });
  }

  zakladki.addEventListener("keydown", (zdarzenie) => {
    const kierunek = { ArrowRight: 1, ArrowLeft: -1 }[zdarzenie.key];
    if (!kierunek) return;
    const klucze = [...rozmiary.keys()];
    aktywny = klucze[(klucze.indexOf(aktywny) + kierunek + klucze.length) % klucze.length];
    rysuj();
    document.getElementById(`zakladka-${aktywny}`)?.focus();
  });

  return {
    reset() {
      rozmiary.clear();
      for (const klucz of Object.keys(limity)) delete limity[klucz];
      aktywny = null;
      trwa = true;
      wyczysc(kontener);
    },
    rozmiar(rozmiar) {
      if (!rozmiary.has(rozmiar)) rozmiary.set(rozmiar, { oferty: new Map(), koniec: false });
      if (!aktywny) aktywny = rozmiar;
      rysuj();
    },
    podglad(rozmiar, oferty) {
      const dane = rozmiary.get(rozmiar);
      if (!dane || dane.koniec) return;
      for (const oferta of oferty) dane.oferty.set(oferta.klucz, oferta);
      if (rozmiar === aktywny) rysuj();
      else rysujZakladki();
    },
    koniec(rozmiar, wyniki) {
      const dane = rozmiary.get(rozmiar) || { oferty: new Map() };
      dane.oferty = new Map((wyniki.oferty || []).map((o) => [o.klucz, o]));
      Object.assign(dane, { koniec: true, zmiany: wyniki.zmiany, zrodla: wyniki.zrodla, recznie: wyniki.recznie, wskazowkaZdjec: wyniki.wskazowka_zdjec });
      rozmiary.set(rozmiar, dane);
      rysuj();
    },
    zakoncz() {
      trwa = false;
      rysuj();
    },
    wszystkie() {
      return [...rozmiary.values()].flatMap((d) => widoczne(d));
    },
  };
}
