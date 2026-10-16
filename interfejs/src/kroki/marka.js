import { el, grupaRadio, odmiana, ustawRovingTabindex, wyczysc } from "../dom.js";
import { pobierz, subskrybuj, zmien } from "../stan.js";
import { pojawienie, sprezyna } from "../ruch.js";
import { opcjaWyboru, pokazDalej, przyciskDalej, zaznacz } from "./wspolne.js";

export function krokMarka(sekcja, kontener, katalog) {
  const dalej = przyciskDalej("Dalej: model", "#krok-model");
  dalej.hidden = !pobierz().marka;
  sekcja.append(dalej);

  function wybierz(id) {
    if (id === pobierz().marka) return;
    zmien({ marka: id, model: null });
  }

  function rysuj() {
    wyczysc(
      kontener,
      katalog.marki.map((marka) =>
        opcjaWyboru({
          wartosc: marka.id,
          zaznaczona: marka.id === pobierz().marka,
          naWybor: wybierz,
          poczatek: el("span", { class: "monogram", "aria-hidden": "true" }, marka.nazwa.slice(0, 2)),
          nazwa: marka.nazwa,
          meta: `${marka.modele.length} ${odmiana(marka.modele.length, "model", "modele", "modeli")}`,
        }),
      ),
    );
    kontener.removeAttribute("aria-busy");
    ustawRovingTabindex(kontener);
  }

  rysuj();
  grupaRadio(kontener, wybierz);
  pojawienie([...kontener.children]);

  subskrybuj((stan, poprzedni) => {
    if (stan.marka === poprzedni.marka) return;
    zaznacz(kontener, stan.marka);
    ustawRovingTabindex(kontener);
    pokazDalej(dalej, Boolean(stan.marka));
    sprezyna(kontener.querySelector('[aria-checked="true"]'));
  });

  return { odswiez: rysuj };
}
