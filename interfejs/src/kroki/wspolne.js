import { el } from "../dom.js";
import { ikona } from "../ikony.js";
import { pojawienie, przewin } from "../ruch.js";

export function przyciskDalej(etykieta, cel) {
  return el(
    "button",
    { type: "button", class: "przycisk krok__dalej", onClick: () => przewin(cel) },
    etykieta,
    ikona("ArrowDown"),
  );
}

export function opcjaWyboru({ wartosc, zaznaczona, naWybor, poczatek, nazwa, meta }) {
  return el(
    "button",
    {
      type: "button",
      role: "radio",
      class: "wybor",
      "aria-checked": String(zaznaczona),
      "data-wartosc": wartosc,
      onClick: () => naWybor(wartosc),
    },
    poczatek,
    el("span", { class: "wybor__tresc" }, el("span", { class: "wybor__nazwa" }, nazwa), meta && el("span", { class: "wybor__meta" }, meta)),
    el("span", { class: "wybor__znak", "aria-hidden": "true" }, ikona("Check")),
  );
}

export function zaznacz(kontener, wartosc) {
  for (const opcja of kontener.querySelectorAll('[role="radio"]')) {
    const zaznaczona = opcja.dataset.wartosc === wartosc;
    opcja.setAttribute("aria-checked", String(zaznaczona));
  }
}

export function pokazDalej(przycisk, widoczny) {
  const zmiana = przycisk.hidden === widoczny;
  przycisk.hidden = !widoczny;
  if (zmiana && widoczny) pojawienie([przycisk]);
}
