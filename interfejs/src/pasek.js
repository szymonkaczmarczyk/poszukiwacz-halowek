import { gsap } from "gsap";
import { Flip } from "gsap/Flip";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { el, wyczysc, zl } from "./dom.js";
import { ikona } from "./ikony.js";
import { pobierz, subskrybuj } from "./stan.js";
import { ograniczonyRuch, przewin, sledzHero, sprezyna } from "./ruch.js";

gsap.registerPlugin(Flip, ScrollTrigger);

const MAC = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);

export function brakujace(stan) {
  const braki = [];
  if (!stan.marka) braki.push({ tekst: "Wybierz markę", cel: "#krok-marka" });
  else if (!stan.model) braki.push({ tekst: "Wybierz model", cel: "#krok-model" });
  if (!stan.rozmiary.length) braki.push({ tekst: "Zaznacz rozmiar", cel: "#krok-rozmiar" });
  if (stan.maxCena === "blad") braki.push({ tekst: "Popraw maksymalną cenę", cel: "#krok-filtry" });
  return braki;
}

export function pasek({ element, wybor, brak, przycisk, skrot, kotwica }, katalog, naStart) {
  let trwa = false;
  let zadokowany = false;
  let naHero = true;
  const domPoczatkowy = element.parentNode;
  const nastepnyPoczatkowy = element.nextSibling;

  function dopasujKotwice() {
    kotwica.style.minHeight = `${element.offsetHeight}px`;
  }

  function dokuj(tak) {
    if (zadokowany === tak) return;
    zadokowany = tak;
    const stan = Flip.getState(element);
    element.classList.add("pasek--przenoszony");
    if (tak) kotwica.append(element);
    else domPoczatkowy.insertBefore(element, nastepnyPoczatkowy);
    element.classList.toggle("pasek--zadokowany", tak);
    element.classList.toggle("pasek--widoczny", tak || !naHero);
    const koniec = () => element.classList.remove("pasek--przenoszony");
    if (ograniczonyRuch()) {
      koniec();
      return;
    }
    Flip.from(stan, { duration: 0.6, ease: "power3.inOut", onComplete: koniec, onInterrupt: koniec });
  }
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
  sledzHero((wHero) => {
    naHero = wHero;
    if (!zadokowany) element.classList.toggle("pasek--widoczny", !wHero);
  });
  dopasujKotwice();
  new ResizeObserver(() => {
    if (!zadokowany) dopasujKotwice();
  }).observe(element);
  ScrollTrigger.create({
    trigger: kotwica,
    start: "bottom bottom-=12",
    onEnter: () => dokuj(true),
    onLeaveBack: () => dokuj(false),
  });
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
