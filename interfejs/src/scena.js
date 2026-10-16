import { gsap } from "gsap";
import { pobierz, subskrybuj } from "./stan.js";
import { ograniczonyRuch } from "./ruch.js";

export function scena(katalog) {
  const korzen = document.querySelector(".scena");
  const marka = document.getElementById("scena-marka");
  const model = document.getElementById("scena-model");
  const rozmiar = document.getElementById("scena-rozmiar");

  function ustaw(stan, animuj) {
    const znaleziona = katalog.marki.find((m) => m.id === stan.marka);
    const znaleziony = znaleziona?.modele.find((m) => m.id === stan.model);
    const zmiany = () => {
      marka.textContent = znaleziona ? znaleziona.nazwa : "Szatnia";
      model.textContent = znaleziony ? znaleziony.nazwa : znaleziona ? "Wybierz model" : "Wybierz but";
      rozmiar.textContent = stan.rozmiary.length ? `rozm. ${stan.rozmiary.join(", ")}` : "";
      korzen.dataset.wybrany = String(Boolean(znaleziony));
    };
    if (!animuj || ograniczonyRuch()) {
      zmiany();
      return;
    }
    gsap.to([marka, model], {
      opacity: 0,
      y: -8,
      duration: 0.18,
      ease: "power1.in",
      onComplete: () => {
        zmiany();
        gsap.fromTo([marka, model], { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out", stagger: 0.05 });
      },
    });
    gsap.fromTo(".scena__but", { rotate: -3, y: -6 }, { rotate: 0, y: 0, duration: 0.9, ease: "elastic.out(1, 0.5)" });
  }

  ustaw(pobierz(), false);
  subskrybuj((stan, poprzedni) => {
    if (stan.marka !== poprzedni.marka || stan.model !== poprzedni.model) ustaw(stan, true);
    else if (stan.rozmiary !== poprzedni.rozmiary) ustaw(stan, false);
  });
}
