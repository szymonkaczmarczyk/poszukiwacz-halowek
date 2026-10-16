import { el, odmiana, wyczysc } from "../dom.js";
import { pobierz, subskrybuj, zmien } from "../stan.js";
import { sprezyna } from "../ruch.js";
import { pokazDalej, przyciskDalej } from "./wspolne.js";

export function krokRozmiar(sekcja, kontener, podpowiedz, rozmiary) {
  const dalej = przyciskDalej("Dalej: filtry", "#krok-filtry");
  sekcja.append(dalej);

  function przelacz(rozmiar) {
    const wybrane = new Set(pobierz().rozmiary);
    if (wybrane.has(rozmiar)) wybrane.delete(rozmiar);
    else wybrane.add(rozmiar);
    zmien({ rozmiary: rozmiary.filter((r) => wybrane.has(r)) });
  }

  wyczysc(
    kontener,
    rozmiary.map((rozmiar) =>
      el(
        "button",
        {
          type: "button",
          class: "rozmiar",
          "aria-pressed": String(pobierz().rozmiary.includes(rozmiar)),
          "aria-label": `Rozmiar ${rozmiar}`,
          "data-wartosc": rozmiar,
          onClick: () => przelacz(rozmiar),
        },
        el("span", { class: "rozmiar__liczba", "aria-hidden": "true" }, rozmiar),
        el("span", { class: "rozmiar__eu", "aria-hidden": "true" }, "EU"),
      ),
    ),
  );

  function opisz(wybrane) {
    pokazDalej(dalej, Boolean(wybrane.length));
    if (!wybrane.length) {
      podpowiedz.textContent = "Zaznacz co najmniej jeden rozmiar.";
      return;
    }
    const lista = wybrane.join(", ");
    const czas = wybrane.length > 1 ? " Każdy rozmiar to osobne przejście, więc szukanie potrwa dłużej." : "";
    podpowiedz.textContent = `Wybrane: ${lista} (${wybrane.length} ${odmiana(wybrane.length, "rozmiar", "rozmiary", "rozmiarów")}).${czas}`;
  }

  opisz(pobierz().rozmiary);
  subskrybuj((stan, poprzedni) => {
    if (stan.rozmiary === poprzedni.rozmiary) return;
    for (const przycisk of kontener.children) {
      const wcisniety = stan.rozmiary.includes(przycisk.dataset.wartosc);
      if (przycisk.getAttribute("aria-pressed") !== String(wcisniety)) {
        przycisk.setAttribute("aria-pressed", String(wcisniety));
        sprezyna(przycisk);
      }
    }
    opisz(stan.rozmiary);
  });
}
