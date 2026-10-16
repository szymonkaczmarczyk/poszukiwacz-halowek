import { expect, test } from "@playwright/test";

const oferta = (klucz, tytul, suma, grupa, dodatki = {}) => ({
  klucz,
  url: klucz,
  tytul,
  suma_pln: suma,
  zrodlo: dodatki.zrodlo || "Vinted",
  grupa,
  stan: "Dobry",
  zdjecie: "",
  flagi: [],
  ...dodatki,
});

const WYNIKI_41 = {
  rozmiar: "41",
  oferty: [
    oferta("https://www.vinted.pl/items/1", "Joma Top Flex 41 nowe", 150, "pewne", { flagi: ["NOWE"] }),
    oferta("https://www.vinted.pl/items/2", "Joma Top Flex skóra", 99, "rozmiar", { flagi: ["TANIEJ o 20 zł"] }),
    oferta("https://www.olx.pl/d/3", "Halówki Joma 41", 60, "weryfikacja", { zrodlo: "OLX" }),
  ],
  zmiany: { poprzednio: "2026-10-15 20:00", pierwsze: false, nowe: ["https://www.vinted.pl/items/1"], tansze: [{ klucz: "https://www.vinted.pl/items/2", roznica: 20 }], drozsze: [], zniknely: [{ klucz: "x", tytul: "Joma Top Flex stare", zrodlo: "OLX", cena: 80 }] },
  zrodla: [{ nazwa: "Vinted", status: "ok" }, { nazwa: "OLX", status: "podejrzane" }],
  recznie: [{ nazwa: "Allegro", url: "https://allegro.pl/listing?string=joma", opis: "chronione przez DataDome" }],
  wskazowka_zdjec: "napis TOP FLEX z boku",
};

const WYNIKI_42 = { rozmiar: "42", oferty: [oferta("https://www.vinted.pl/items/9", "Joma Top Flex 42", 210, "pewne")], zmiany: { pierwsze: true, nowe: [], tansze: [], drozsze: [], zniknely: [] }, zrodla: [], recznie: [] };

function strumien(zdarzenia) {
  return zdarzenia.map((z, id) => `id: ${id}\nevent: ${z.typ}\ndata: ${JSON.stringify({ id, ...z })}\n\n`).join("");
}

async function przygotuj(page, zdarzenia) {
  await page.route("**/api/wyszukiwania", (route) => route.fulfill({ status: 202, json: { id: "t1", zdarzenia: "/api/wyszukiwania/t1/zdarzenia" } }));
  await page.route("**/api/wyszukiwania/t1/zdarzenia", (route) => route.fulfill({ status: 200, contentType: "text/event-stream", body: strumien(zdarzenia) }));
  await page.goto("/");
  await expect(page.locator("#status-api")).toHaveAttribute("data-stan", "ok");
  await page.locator("#lista-marek").getByRole("radio", { name: /^Joma \d+ model/ }).click();
  await page.locator("#lista-modeli").getByRole("radio", { name: /^Joma Top Flex bez Rebound/ }).click();
}

const PELNE = [
  { typ: "wyszukiwanie_start", dane: { nazwa: "Joma Top Flex", rozmiary: ["41", "42"] } },
  { typ: "start", dane: { rozmiar: "41", zrodla: ["Vinted", "OLX"] } },
  { typ: "zrodlo_koniec", dane: { rozmiar: "41", nazwa: "Vinted", status: "ok", ofert: 2, odczytano: 40, oferty: [] } },
  { typ: "zrodlo_koniec", dane: { rozmiar: "41", nazwa: "OLX", status: "podejrzane", ofert: 1, odczytano: 2, oferty: [] } },
  { typ: "koniec", dane: { rozmiar: "41", wyniki: WYNIKI_41 } },
  { typ: "start", dane: { rozmiar: "42", zrodla: ["Vinted"] } },
  { typ: "koniec", dane: { rozmiar: "42", wyniki: WYNIKI_42 } },
  { typ: "wyszukiwanie_koniec", dane: { stan: "gotowe", czas: 30, gotowe_rozmiary: ["41", "42"] } },
];

test("wyniki są w grupach z oznaczeniami zmian i zakładkami rozmiarów", async ({ page }) => {
  await przygotuj(page, PELNE);
  await page.getByRole("button", { name: "Rozmiar 41" }).click();
  await page.getByRole("button", { name: "Rozmiar 42" }).click();
  await page.getByRole("button", { name: /Szukaj ofert/ }).click();
  await expect(page.locator("#postep-tytul")).toHaveText("Wyniki");
  await expect(page.getByRole("tab")).toHaveCount(2);
  await expect(page.getByRole("tab", { name: /Rozm. 41/ })).toHaveAttribute("aria-selected", "true");
  await expect(page.locator(".grupa-ofert--pewne")).toContainText("Joma Top Flex 41 nowe");
  await expect(page.locator(".grupa-ofert--pewne .znaczek")).toContainText("nowa");
  await expect(page.locator(".grupa-ofert--rozmiar .znaczek")).toContainText("taniej o 20 zł");
  await expect(page.locator(".grupa-ofert--weryfikacja")).toContainText("napis TOP FLEX z boku");
  await expect(page.locator(".zmiany")).toContainText("1 nowa");
  await expect(page.locator(".zmiany")).toContainText("1 zniknęła");
  await expect(page.locator(".wyniki .blad-stan")).toContainText("OLX");
  await expect(page.locator(".recznie")).toContainText("Allegro");
  await page.getByLabel("Kolejność").selectOption("cena-");
  await page.getByLabel("Źródło").selectOption("Vinted");
  await expect(page.locator(".oferta")).toHaveCount(2);
  await expect(page.locator(".narzedzia__licznik")).toHaveText("Pokazuję 2 z 3 ofert.");
  await page.getByRole("tab", { name: /Rozm. 42/ }).click();
  await expect(page.locator(".zmiany")).toContainText("Pierwsze sprawdzenie w rozmiarze 42");
  await expect(page.locator(".oferta")).toHaveCount(1);
});

test("ukrycie oferty można cofnąć", async ({ page }) => {
  const wywolania = [];
  await page.route("**/api/ukryte", (route) => {
    wywolania.push(["ukryj", route.request().postDataJSON().url]);
    return route.fulfill({ json: { ukryto: true } });
  });
  await page.route("**/api/ukryte/przywroc", (route) => {
    wywolania.push(["przywroc", route.request().postDataJSON().url]);
    return route.fulfill({ json: { przywrocono: true } });
  });
  await przygotuj(page, PELNE);
  await page.getByRole("button", { name: "Rozmiar 41" }).click();
  await page.getByRole("button", { name: /Szukaj ofert/ }).click();
  await expect(page.locator(".oferta")).toHaveCount(3);
  await page.getByRole("button", { name: "Ukryj ofertę: Joma Top Flex skóra" }).click();
  await expect(page.locator(".oferta")).toHaveCount(2);
  await expect(page.locator(".powiadomienie")).toContainText("Ukryto: Joma Top Flex skóra");
  await page.getByRole("button", { name: "Cofnij" }).click();
  await expect(page.locator(".oferta")).toHaveCount(3);
  expect(wywolania).toEqual([
    ["ukryj", "https://www.vinted.pl/items/2"],
    ["przywroc", "https://www.vinted.pl/items/2"],
  ]);
});

test("przerwanie wysyła żądanie i pokazuje wyniki częściowe", async ({ page }) => {
  let przerwano = false;
  await page.route("**/api/wyszukiwania/t1/przerwij", (route) => {
    przerwano = true;
    return route.fulfill({ status: 202, json: { id: "t1", stan: "trwa" } });
  });
  const zdarzenia = [
    { typ: "wyszukiwanie_start", dane: { nazwa: "Joma Top Flex", rozmiary: ["41"] } },
    { typ: "start", dane: { rozmiar: "41", zrodla: ["Vinted", "OLX"] } },
    { typ: "zrodlo_start", dane: { rozmiar: "41", zrodlo: "OLX" } },
  ];
  await page.route("**/api/wyszukiwania", (route) => route.fulfill({ status: 202, json: { id: "t1", zdarzenia: "/api/wyszukiwania/t1/zdarzenia" } }));
  let wywolanieStrumienia = 0;
  await page.route("**/api/wyszukiwania/t1/zdarzenia", (route) => {
    wywolanieStrumienia += 1;
    const dalej = przerwano
      ? [
          { typ: "przerywanie", dane: {} },
          { typ: "zrodlo_koniec", dane: { rozmiar: "41", nazwa: "OLX", status: "przerwane", ofert: 0, odczytano: 0, oferty: [] } },
          { typ: "koniec", dane: { rozmiar: "41", przerwane: true, wyniki: { ...WYNIKI_41, oferty: WYNIKI_41.oferty.slice(0, 1) } } },
          { typ: "wyszukiwanie_koniec", dane: { stan: "przerwane", czas: 9 } },
        ]
      : [];
    const wszystkie = [...zdarzenia, ...dalej];
    const od = Number(route.request().headers()["last-event-id"] ?? -1) + 1;
    const body = wszystkie.slice(od).map((z, i) => `id: ${od + i}\nevent: ${z.typ}\ndata: ${JSON.stringify({ id: od + i, ...z })}\nretry: 200\n\n`).join("");
    return route.fulfill({ status: 200, contentType: "text/event-stream", body });
  });
  await page.goto("/");
  await expect(page.locator("#status-api")).toHaveAttribute("data-stan", "ok");
  await page.locator("#lista-marek").getByRole("radio", { name: /^Joma \d+ model/ }).click();
  await page.locator("#lista-modeli").getByRole("radio", { name: /^Joma Top Flex bez Rebound/ }).click();
  await page.getByRole("button", { name: "Rozmiar 41" }).click();
  await page.getByRole("button", { name: /Szukaj ofert/ }).click();
  await expect(page.locator('.zrodlo[data-stan="trwa"]')).toContainText("OLX");
  await page.getByRole("button", { name: /Przerwij szukanie/ }).click();
  expect(przerwano).toBe(true);
  await expect(page.locator("#postep-tytul")).toHaveText("Wyniki częściowe", { timeout: 10000 });
  await expect(page.locator('.zrodlo[data-stan="przerwane"]')).toContainText("OLX");
  await expect(page.locator(".oferta")).toHaveCount(1);
  await expect(page.getByRole("button", { name: /Przerwij szukanie/ })).toBeHidden();
  expect(wywolanieStrumienia).toBeGreaterThan(1);
});
