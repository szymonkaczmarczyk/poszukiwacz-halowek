import { gsap } from "gsap";
import { el } from "./dom.js";
import { ikona } from "./ikony.js";
import { ograniczonyRuch } from "./ruch.js";

const CZAS_WIDOCZNOSCI = 6500;

export function powiadom(tekst, { rodzaj = "info", akcja = null } = {}) {
  const region = document.getElementById("powiadomienia");
  let zegar = null;

  function zamknij() {
    clearTimeout(zegar);
    if (!wpis.isConnected) return;
    if (ograniczonyRuch()) {
      wpis.remove();
      return;
    }
    gsap.to(wpis, { y: 12, opacity: 0, duration: 0.18, ease: "power1.in", onComplete: () => wpis.remove() });
  }

  const wpis = el(
    "div",
    { class: `powiadomienie powiadomienie--${rodzaj}`, role: rodzaj === "blad" ? "alert" : "status" },
    ikona(rodzaj === "blad" ? "CircleAlert" : "CircleCheck"),
    el("span", { class: "powiadomienie__tekst" }, tekst),
    akcja &&
      el(
        "button",
        {
          type: "button",
          class: "powiadomienie__akcja",
          onClick: () => {
            zamknij();
            akcja.wykonaj();
          },
        },
        akcja.etykieta,
      ),
  );
  region.append(wpis);
  if (!ograniczonyRuch()) gsap.from(wpis, { y: 16, opacity: 0, duration: 0.32, ease: "power3.out" });
  zegar = setTimeout(zamknij, CZAS_WIDOCZNOSCI);
  wpis.addEventListener("pointerenter", () => clearTimeout(zegar));
  wpis.addEventListener("pointerleave", () => {
    zegar = setTimeout(zamknij, CZAS_WIDOCZNOSCI / 2);
  });
  return zamknij;
}
