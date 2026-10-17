import "./strona.js";
import * as api from "./api.js";
import { wyczysc } from "./dom.js";
import { ikona } from "./ikony.js";

const forma = document.getElementById("logowanie");
const haslo = document.getElementById("haslo");
const blad = document.getElementById("haslo-blad");
const przycisk = document.getElementById("zaloguj");
const zalogowany = document.getElementById("zalogowany");

function pokazBlad(tekst) {
  if (!tekst) {
    blad.hidden = true;
    haslo.removeAttribute("aria-invalid");
    return;
  }
  wyczysc(blad, ikona("CircleAlert"), tekst);
  blad.hidden = false;
  haslo.setAttribute("aria-invalid", "true");
  haslo.focus();
}

function ustawZalogowany(stan) {
  forma.hidden = stan;
  zalogowany.hidden = !stan;
}

forma.addEventListener("submit", async (zdarzenie) => {
  zdarzenie.preventDefault();
  if (!haslo.value) {
    pokazBlad("Wpisz hasło administratora.");
    return;
  }
  if (przycisk.getAttribute("aria-disabled") === "true") return;
  przycisk.setAttribute("aria-disabled", "true");
  przycisk.textContent = "Loguję…";
  try {
    await api.zalogujAdmina(haslo.value);
    pokazBlad("");
    haslo.value = "";
    ustawZalogowany(true);
  } catch (e) {
    const komunikaty = {
      401: "Nieprawidłowe hasło. Sprawdź wielkość liter i spróbuj ponownie.",
      429: "Za dużo prób. Odczekaj 15 minut i spróbuj ponownie.",
      503: "Hasło nie jest jeszcze ustawione. W katalogu projektu uruchom: py serwer.py --ustaw-haslo",
    };
    pokazBlad(komunikaty[e.status] || `Nie udało się zalogować: ${e.message}.`);
  } finally {
    przycisk.removeAttribute("aria-disabled");
    przycisk.textContent = "Zaloguj się";
  }
});

document.getElementById("wyloguj").addEventListener("click", async () => {
  await api.wylogujAdmina().catch(() => null);
  ustawZalogowany(false);
  haslo.focus();
});

api.stanAdmina().then((stan) => ustawZalogowany(stan.zalogowany)).catch(() => ustawZalogowany(false));
