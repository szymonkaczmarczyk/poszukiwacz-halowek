import { el, wyczysc, zl } from "./dom.js";
import { ikona } from "./ikony.js";
import { pobierz, subskrybuj } from "./stan.js";
import { przewin, sledzHero, sprezyna } from "./ruch.js";

const MAC = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);

export function brakujace(stan) {
  const braki = [];
  if (!stan.marka) braki.push({ tekst: "Wybierz markę", cel: "#krok-marka" });
  else if (!stan.model) braki.push({ tekst: "Wybierz model", cel: "#krok-model" });
  if (!stan.rozmiary.length) braki.push({ tekst: "Zaznacz rozmiar", cel: "#krok-rozmiar" });
  if (stan.maxCena === "blad") braki.push({ tekst: "Popraw maksymalną cenę", cel: "#krok-filtry" });
  return braki;
}

export function pasek({ element, wybor, brak, przycisk, skrot }, katalog, naStart) {
  let trwa = false;
  skrot.textContent = MAC ? "⌘\u00a0↵" : "Ctrl\u00a0↵";

  function opis(stan) {
    const marka = katalog.marki.find((m) => m.id === stan.marka);
    const model = marka?.modele.find((m) => m.id === stan.model);
    const szczegoly = [];
    if (stan.rozmiary.length) szczegoly.push(`rozm. ${stan.rozmiary.join(", ")}`);
    if (typeof stan.maxCena === "number") szczegoly.push(`do ${zl(stan.maxCena)}`);
    if (stan.tylkoPewne) szczegoly.push("tylko pewne");
    if (stan.pominieteZrodla.length) szczegoly.push(`bez ${stan.pominieteZrodla.length} źródeł`);
    return [
      el("span", { class: "pasek__model" }, model ? model.nazwa : marka ? marka.nazwa : "Nic jeszcze nie wybrano"),
      szczegoly.length > 0 && el("span", { class: "pasek__szczegol" }, szczegoly.join(" · ")),
    ];
  }

  function odswiez() {
    const stan = pobierz();
    const braki = brakujace(stan);
    wyczysc(wybor, opis(stan));
    wyczysc(brak, braki.length ? [ikona("TriangleAlert"), braki.map((b) => b.tekst).join(", ")] : []);
    const zablokowany = trwa || braki.length > 0;
    przycisk.setAttribute("aria-disabled", String(zablokowany));
    if (braki.length) przycisk.setAttribute("aria-describedby", "pasek-brak");
    else przycisk.removeAttribute("aria-describedby");
  }

  function uruchom() {
    if (trwa) return;
    const braki = brakujace(pobierz());
    if (braki.length) {
      sprezyna(brak);
      przewin(braki[0].cel);
      return;
    }
    naStart(pobierz());
  }

  przycisk.addEventListener("click", uruchom);
  document.addEventListener("keydown", (zdarzenie) => {
    if (zdarzenie.key === "Enter" && (zdarzenie.ctrlKey || zdarzenie.metaKey)) {
      zdarzenie.preventDefault();
      uruchom();
    }
  });
  sledzHero((naHero) => element.classList.toggle("pasek--widoczny", !naHero));
  subskrybuj(odswiez);
  odswiez();

  return {
    ustawTrwa(wartosc) {
      trwa = wartosc;
      przycisk.dataset.trwa = String(wartosc);
      odswiez();
    },
    pokaz() {
      element.classList.add("pasek--widoczny");
    },
  };
}
