export class BladApi extends Error {
  constructor(komunikat, status = 0) {
    super(komunikat);
    this.status = status;
  }
}

async function zapytanie(adres, opcje = {}) {
  let odpowiedz;
  try {
    odpowiedz = await fetch(adres, { headers: { Accept: "application/json", ...opcje.headers }, ...opcje });
  } catch {
    throw new BladApi("serwer nie odpowiada");
  }
  const dane = await odpowiedz.json().catch(() => ({}));
  if (!odpowiedz.ok) {
    const szczegol = typeof dane.detail === "string" ? dane.detail : "nieprawidłowe dane";
    throw new BladApi(szczegol, odpowiedz.status);
  }
  return dane;
}

export function katalog() {
  return zapytanie("/api/katalog");
}

export function zrodla(marka, model) {
  return zapytanie(`/api/katalog/${encodeURIComponent(marka)}/${encodeURIComponent(model)}/zrodla`);
}

export function startWyszukiwania(dane) {
  return zapytanie("/api/wyszukiwania", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dane),
  });
}

export function przerwij(id) {
  return zapytanie(`/api/wyszukiwania/${encodeURIComponent(id)}/przerwij`, { method: "POST" });
}

function wyslijAdres(adres, url) {
  return zapytanie(adres, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url }) });
}

export function ukryj(url) {
  return wyslijAdres("/api/ukryte", url);
}

export function przywroc(url) {
  return wyslijAdres("/api/ukryte/przywroc", url);
}

export function dodajWlasny(dane) {
  return zapytanie("/api/wlasne", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(dane) });
}

export async function usunWlasny(marka, model) {
  let odpowiedz;
  try {
    odpowiedz = await fetch(`/api/wlasne/${encodeURIComponent(marka)}/${encodeURIComponent(model)}`, { method: "DELETE" });
  } catch {
    throw new BladApi("serwer nie odpowiada");
  }
  if (!odpowiedz.ok) {
    const dane = await odpowiedz.json().catch(() => ({}));
    throw new BladApi(typeof dane.detail === "string" ? dane.detail : "nie udało się usunąć", odpowiedz.status);
  }
}

export const TYPY_ZDARZEN = ["wyszukiwanie_start", "start", "zrodlo_start", "log", "zrodlo_koniec", "koniec", "blad", "przerywanie", "wyszukiwanie_koniec"];

export function sluchajZdarzen(adres, obsluz, przyBledzie) {
  const zrodlo = new EventSource(adres);
  for (const typ of TYPY_ZDARZEN) {
    zrodlo.addEventListener(typ, (wiadomosc) => {
      const zdarzenie = JSON.parse(wiadomosc.data);
      obsluz(zdarzenie);
      if (typ === "wyszukiwanie_koniec") zrodlo.close();
    });
  }
  zrodlo.onerror = () => {
    if (zrodlo.readyState === EventSource.CLOSED) przyBledzie();
  };
  return () => zrodlo.close();
}
