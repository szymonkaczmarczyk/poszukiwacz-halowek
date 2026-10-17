import { el, grupaRadio, ustawRovingTabindex, wyczysc } from "../dom.js";
import { ikona } from "../ikony.js";
import { pobierz, subskrybuj, zmien } from "../stan.js";
import { pojawienie, przewin, sprezyna } from "../ruch.js";
import { opcjaWyboru, pokazDalej, przyciskDalej, zaznacz } from "./wspolne.js";

export function krokModel(sekcja, kontener, katalog) {
  const dalej = przyciskDalej("Dalej: rozmiar", "#krok-rozmiar");
  sekcja.append(dalej);

  function wybierz(id) {
    if (id === pobierz().model) return;
    zmien({ model: id });
  }

  function pustyStan() {
    return el(
      "div",
      { class: "pusty-stan" },
      el("p", {}, "Najpierw wybierz markę. Pokażę tu jej modele z opisem, czego program nie bierze pod uwagę."),
      el("button", { type: "button", class: "przycisk przycisk--maly", onClick: () => przewin("#krok-marka") }, "Wybierz markę", ikona("ArrowRight")),
    );
  }

  function render() {
    const { marka, model } = pobierz();
    const znaleziona = katalog.marki.find((m) => m.id === marka);
    pokazDalej(dalej, Boolean(model));
    if (!znaleziona) {
      wyczysc(kontener, pustyStan());
      return;
    }
    wyczysc(
      kontener,
      znaleziona.modele.map((m) =>
        opcjaWyboru({
          wartosc: m.id,
          zaznaczona: m.id === model,
          naWybor: wybierz,
          nazwa: m.nazwa,
        }),
      ),
    );
    ustawRovingTabindex(kontener);
    pojawienie([...kontener.children]);
  }

  grupaRadio(kontener, wybierz);
  render();

  subskrybuj((stan, poprzedni) => {
    if (stan.marka !== poprzedni.marka) {
      render();
      return;
    }
    if (stan.model !== poprzedni.model) {
      zaznacz(kontener, stan.model);
      ustawRovingTabindex(kontener);
      pokazDalej(dalej, Boolean(stan.model));
      sprezyna(kontener.querySelector('[aria-checked="true"]'));
    }
  });

  return { odswiez: render };
}
