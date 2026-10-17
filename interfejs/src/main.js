import "@fontsource-variable/dm-sans";
import "./style/tokeny.css";
import "./style/baza.css";
import "./style/uklad.css";
import "./style/komponenty.css";
import "./style/strony.css";

import * as api from "./api.js";
import { el, wyczysc } from "./dom.js";
import { edytorModelu } from "./edytor.js";
import { ikona, wstawIkony } from "./ikony.js";
import { krokFiltry } from "./kroki/filtry.js";
import { krokMarka } from "./kroki/marka.js";
import { krokModel } from "./kroki/model.js";
import { krokRozmiar } from "./kroki/rozmiar.js";
import { pasek } from "./pasek.js";
import { postep } from "./postep.js";
import { ograniczonyRuch, odslonyKrokow, odswiezWyzwalacze, podepnijKotwice, sledzKroki, uruchomPrzewijanie, wejscieHero } from "./ruch.js";
import { scena } from "./scena.js";
import { pobierz, subskrybuj, zmien } from "./stan.js";

const $ = (id) => document.getElementById(id);

function ustawStatus(stan, tekst) {
  const status = $("status-api");
  status.dataset.stan = stan;
  status.querySelector(".status-api__tekst").textContent = tekst;
}

function uporzadkujStan(katalog) {
  const stan = pobierz();
  const marka = katalog.marki.find((m) => m.id === stan.marka);
  const model = marka?.modele.find((m) => m.id === stan.model);
  zmien({
    marka: marka ? marka.id : null,
    model: model ? model.id : null,
    rozmiary: katalog.rozmiary.filter((r) => stan.rozmiary.includes(r)),
    maxCena: typeof stan.maxCena === "number" && stan.maxCena > 0 ? stan.maxCena : null,
  });
}

function pokazLiczby(katalog) {
  $("liczba-marek").textContent = katalog.marki.length;
  $("liczba-modeli").textContent = katalog.marki.reduce((suma, m) => suma + m.modele.length, 0);
  $("zakres-rozmiarow").textContent = `${katalog.rozmiary[0]}–${katalog.rozmiary.at(-1)}`;
  $("hero-liczby").hidden = false;
}

function szyna() {
  const linki = [...document.querySelectorAll(".szyna a")];
  const gotowe = (stan) => ({
    marka: Boolean(stan.marka),
    model: Boolean(stan.model),
    rozmiar: stan.rozmiary.length > 0,
    filtry: Boolean(stan.marka && stan.model && stan.rozmiary.length) && stan.maxCena !== "blad",
  });
  const oznacz = (stan) => {
    const g = gotowe(stan);
    for (const link of linki) link.dataset.gotowe = String(g[link.dataset.krok]);
  };
  let aktualny = null;
  sledzKroki((krok, aktywny) => {
    if (!aktywny && krok !== aktualny) return;
    aktualny = aktywny ? krok : null;
    for (const link of linki) {
      if (link.dataset.krok === aktualny) link.setAttribute("aria-current", "step");
      else link.removeAttribute("aria-current");
    }
  });
  oznacz(pobierz());
  subskrybuj(oznacz);
}

function webglDostepny() {
  try {
    const plotno = document.createElement("canvas");
    return Boolean(plotno.getContext("webgl2") || plotno.getContext("webgl"));
  } catch {
    return false;
  }
}

async function scenaTrojwymiarowa(katalog) {
  const kontener = document.querySelector(".scena");
  if (ograniczonyRuch() || !webglDostepny()) {
    kontener.dataset.tryb = "2d";
    return;
  }
  try {
    const { uruchomScene3d } = await import("./scena3d/index.js");
    uruchomScene3d(kontener, katalog);
    odswiezWyzwalacze();
  } catch {
    kontener.dataset.tryb = "2d";
  }
}

function bladSerwera(blad, ponow) {
  ustawStatus("blad", "Serwer nie odpowiada");
  const lista = $("lista-marek");
  lista.removeAttribute("aria-busy");
  wyczysc(
    lista,
    el(
      "div",
      { class: "blad-stan", role: "alert" },
      el("p", { class: "blad-stan__tytul" }, ikona("CircleAlert"), "Nie mogę połączyć się z serwerem Szatni"),
      el("p", {}, "Uruchom go w katalogu projektu poleceniem ", el("code", {}, "py serwer.py"), `, a potem spróbuj ponownie. Szczegóły: ${blad.message}.`),
      el("button", { type: "button", class: "przycisk przycisk--maly", onClick: ponow }, ikona("RefreshCw"), "Spróbuj ponownie"),
    ),
  );
}

function szkieletMarek() {
  wyczysc($("lista-marek"), Array.from({ length: 6 }, () => el("div", { class: "szkielet", "aria-hidden": "true" })));
}

async function wczytajKatalog() {
  ustawStatus("trwa", "Łączę z serwerem…");
  szkieletMarek();
  try {
    const katalog = await api.katalog();
    ustawStatus("ok", "Serwer działa");
    return katalog;
  } catch (blad) {
    bladSerwera(blad, uruchom);
    return null;
  }
}

async function uruchom() {
  const katalog = await wczytajKatalog();
  if (!katalog) return;
  uporzadkujStan(katalog);
  pokazLiczby(katalog);

  const marki = krokMarka($("krok-marka"), $("lista-marek"), katalog);
  const modele = krokModel($("krok-model"), $("lista-modeli"), katalog);
  const edytor = edytorModelu(katalog, {
    naZmiane: async ({ dodany, usuniety }) => {
      const nowy = await api.katalog();
      katalog.marki.splice(0, katalog.marki.length, ...nowy.marki);
      marki.odswiez();
      modele.odswiez();
      pokazLiczby(katalog);
      const stan = pobierz();
      if (dodany) zmien({ marka: dodany.marka, model: dodany.model });
      else if (usuniety && !katalog.marki.some((m) => m.id === stan.marka)) zmien({ marka: null, model: null });
      else if (usuniety && stan.marka === usuniety.marka && stan.model === usuniety.model) zmien({ model: null });
    },
  });
  api
    .stanAdmina()
    .then(({ zalogowany }) => {
      if (!zalogowany) return;
      $("lista-modeli").after(
        el("button", { type: "button", class: "przycisk przycisk--maly krok__wlasny", onClick: () => edytor.otworz() }, ikona("Plus"), "Dodaj własny model"),
      );
    })
    .catch(() => null);
  krokRozmiar($("krok-rozmiar"), $("lista-rozmiarow"), $("rozmiar-podpowiedz"), katalog.rozmiary);
  krokFiltry($("filtry"));
  scena(katalog);
  szyna();

  const sterowanie = pasek(
    { element: $("pasek"), wybor: $("pasek-wybor"), brak: $("pasek-brak"), przycisk: $("szukaj"), skrot: $("skrot"), kotwica: $("pasek-kotwica") },
    katalog,
    (stan) => {
      sterowanie.ustawTrwa(true);
      ustawStatus("trwa", "Szukam…");
      wyszukiwanie.uruchom(stan);
      odswiezWyzwalacze();
    },
  );
  const wyszukiwanie = postep(
    { sekcja: $("postep"), tytul: $("postep-tytul"), numer: $("postep-nr"), opis: $("postep-opis"), zrodla: $("zrodla-postep"), wyniki: $("wyniki"), przerwij: $("przerwij"), pasekPostepu: $("pasek-postepu") },
    {
      naKoniec: (stan) => {
        sterowanie.ustawTrwa(false);
        ustawStatus(stan === "blad" ? "blad" : "ok", stan === "blad" ? "Wyszukiwanie przerwane" : "Serwer działa");
        odswiezWyzwalacze();
      },
    },
  );

  wstawIkony();
  odslonyKrokow();
  odswiezWyzwalacze();
  scenaTrojwymiarowa(katalog);
}

wstawIkony();
uruchomPrzewijanie();
podepnijKotwice();
wejscieHero();
uruchom();
