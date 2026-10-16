import { el, grupaRadio, ustawRovingTabindex, wyczysc } from "../dom.js";
import { ikona } from "../ikony.js";
import { pobierz, subskrybuj, zmien } from "../stan.js";
import { pojawienie, przewin, sprezyna } from "../ruch.js";
import { opcjaWyboru, pokazDalej, przyciskDalej, zaznacz } from "./wspolne.js";

function najczestszyOpis(modele) {
  const liczniki = new Map();
  for (const m of modele) liczniki.set(m.opis_wykluczen, (liczniki.get(m.opis_wykluczen) || 0) + 1);
  const [opis, ile] = [...liczniki].sort((a, b) => b[1] - a[1])[0] || [];
  return ile > 1 ? opis : "";
}

export function krokModel(sekcja, kontener, opisKroku, katalog) {
  const domyslnyOpis = opisKroku.textContent;
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
      opisKroku.textContent = domyslnyOpis;
      wyczysc(kontener, pustyStan());
      return;
    }
    const wspolnyOpis = najczestszyOpis(znaleziona.modele);
    opisKroku.textContent = wspolnyOpis ? `${domyslnyOpis} Dla ${znaleziona.nazwa}: ${wspolnyOpis}.` : domyslnyOpis;
    wyczysc(
      kontener,
      znaleziona.modele.map((m) =>
        opcjaWyboru({
          wartosc: m.id,
          zaznaczona: m.id === model,
          naWybor: wybierz,
          nazwa: m.nazwa,
          meta: [m.wlasny && "własny model", m.opis_wykluczen !== wspolnyOpis && m.opis_wykluczen].filter(Boolean).join(" · "),
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
