export function el(tag, atrybuty = {}, ...dzieci) {
  const element = document.createElement(tag);
  for (const [klucz, wartosc] of Object.entries(atrybuty)) {
    if (wartosc === null || wartosc === undefined || wartosc === false) continue;
    if (klucz.startsWith("on") && typeof wartosc === "function") {
      element.addEventListener(klucz.slice(2).toLowerCase(), wartosc);
    } else if (klucz === "class") {
      element.className = wartosc;
    } else {
      element.setAttribute(klucz, wartosc === true ? "" : String(wartosc));
    }
  }
  dodaj(element, dzieci);
  return element;
}

function dodaj(element, dzieci) {
  for (const dziecko of dzieci.flat()) {
    if (dziecko === null || dziecko === undefined || dziecko === false) continue;
    element.append(dziecko instanceof Node ? dziecko : document.createTextNode(String(dziecko)));
  }
}

export function wyczysc(element, ...dzieci) {
  element.replaceChildren();
  dodaj(element, dzieci);
}

export function grupaRadio(kontener, wybierz) {
  kontener.addEventListener("keydown", (zdarzenie) => {
    const kierunek = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[zdarzenie.key];
    if (!kierunek) return;
    const opcje = [...kontener.querySelectorAll('[role="radio"]')];
    const obecna = opcje.indexOf(document.activeElement);
    if (obecna === -1) return;
    zdarzenie.preventDefault();
    const nastepna = opcje[(obecna + kierunek + opcje.length) % opcje.length];
    nastepna.focus();
    wybierz(nastepna.dataset.wartosc);
  });
}

export function ustawRovingTabindex(kontener) {
  const opcje = [...kontener.querySelectorAll('[role="radio"]')];
  const zaznaczona = opcje.find((o) => o.getAttribute("aria-checked") === "true") || opcje[0];
  for (const opcja of opcje) opcja.tabIndex = opcja === zaznaczona ? 0 : -1;
}

export function zl(kwota) {
  return new Intl.NumberFormat("pl-PL", { style: "currency", currency: "PLN", maximumFractionDigits: kwota % 1 ? 2 : 0 }).format(kwota);
}

export function odmiana(liczba, jeden, kilka, wiele) {
  if (liczba === 1) return jeden;
  const reszta10 = liczba % 10;
  const reszta100 = liczba % 100;
  return reszta10 >= 2 && reszta10 <= 4 && (reszta100 < 12 || reszta100 > 14) ? kilka : wiele;
}
