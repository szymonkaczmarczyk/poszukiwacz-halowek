const KLUCZ = "szatnia-wybor";

const POCZATKOWY = {
  marka: null,
  model: null,
  rozmiary: [],
  maxCena: null,
  tylkoPewne: false,
  odswiez: false,
  pominieteZrodla: [],
};

const sluchacze = new Set();
let stan = { ...POCZATKOWY, ...wczytaj(), ...zAdresu() };

function wczytaj() {
  try {
    const zapisany = JSON.parse(localStorage.getItem(KLUCZ) || "{}");
    return Object.fromEntries(Object.entries(zapisany).filter(([klucz]) => klucz in POCZATKOWY));
  } catch {
    return {};
  }
}

function zAdresu() {
  const parametry = new URLSearchParams(location.search);
  const wynik = {};
  if (parametry.get("marka")) wynik.marka = parametry.get("marka");
  if (parametry.get("model")) wynik.model = parametry.get("model");
  if (parametry.get("marka") && !parametry.get("model")) wynik.model = null;
  if (parametry.get("rozmiar")) wynik.rozmiary = parametry.get("rozmiar").split(",").filter(Boolean);
  return wynik;
}

function zapiszWAdresie() {
  const parametry = new URLSearchParams();
  if (stan.marka) parametry.set("marka", stan.marka);
  if (stan.model) parametry.set("model", stan.model);
  if (stan.rozmiary.length) parametry.set("rozmiar", stan.rozmiary.join(","));
  const zapytanie = parametry.toString();
  const adres = `${location.pathname}${zapytanie ? `?${zapytanie}` : ""}${location.hash}`;
  if (adres !== `${location.pathname}${location.search}${location.hash}`) history.replaceState(null, "", adres);
}

function zapisz() {
  try {
    localStorage.setItem(KLUCZ, JSON.stringify(stan));
  } catch {}
}

export function pobierz() {
  return stan;
}

export function zmien(zmiany) {
  const poprzedni = stan;
  stan = { ...stan, ...zmiany };
  zapisz();
  zapiszWAdresie();
  for (const sluchacz of sluchacze) sluchacz(stan, poprzedni);
}

export function subskrybuj(sluchacz) {
  sluchacze.add(sluchacz);
  return () => sluchacze.delete(sluchacz);
}
