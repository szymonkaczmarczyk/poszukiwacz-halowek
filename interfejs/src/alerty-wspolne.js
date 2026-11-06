import * as api from "./api.js";
import { el, odmiana } from "./dom.js";
import { ikona } from "./ikony.js";

export function opisGodzin(godziny) {
  const nazwy = godziny.map((g) => `${g}:00`);
  return nazwy.length > 1 ? `${nazwy.slice(0, -1).join(", ")} i ${nazwy.at(-1)}` : nazwy.join("");
}

export function nastepneSprawdzenie(godziny, teraz = new Date()) {
  const dzis = godziny.find((g) => g > teraz.getHours());
  return dzis === undefined ? `jutro o ${godziny[0]}:00` : `dziś o ${dzis}:00`;
}

export function liczbaNowych(alerty) {
  return alerty.reduce((suma, alert) => suma + alert.nowych, 0);
}

export function dzwonekAlertow() {
  const kropka = el("span", { class: "dzwonek__kropka", "aria-hidden": "true", hidden: true });
  const link = el("a", { class: "przycisk przycisk--maly dzwonek", href: "/alerty.html", "aria-label": "Alerty o ofertach" }, ikona("Bell"), el("span", { class: "dzwonek__tekst" }, "Alerty"), kropka);

  async function odswiez() {
    try {
      const { alerty } = await api.alerty();
      const nowych = liczbaNowych(alerty);
      kropka.hidden = nowych === 0;
      link.setAttribute("aria-label", nowych ? `Alerty o ofertach, ${nowych} ${odmiana(nowych, "nowa zmiana", "nowe zmiany", "nowych zmian")}` : "Alerty o ofertach");
    } catch {
      kropka.hidden = true;
    }
  }

  return { element: link, odswiez };
}
