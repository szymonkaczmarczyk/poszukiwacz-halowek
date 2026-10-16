import { expect, test } from "@playwright/test";

const ZDARZENIA = [
  { typ: "wyszukiwanie_start", dane: { nazwa: "Joma Top Flex", rozmiary: ["41"] } },
  { typ: "start", dane: { rozmiar: "41", zrodla: ["Vinted", "R-GOL"] } },
  { typ: "zrodlo_start", dane: { rozmiar: "41", zrodlo: "Vinted" } },
  { typ: "zrodlo_start", dane: { rozmiar: "41", zrodlo: "R-GOL" } },
  {
    typ: "zrodlo_koniec",
    dane: {
      rozmiar: "41",
      nazwa: "R-GOL",
      status: "ok",
      ofert: 1,
      odczytano: 100,
      oferty: [{ klucz: "https://www.r-gol.com/pl/a", url: "https://www.r-gol.com/pl/a", tytul: "Joma Top Flex 2401 IN", suma_pln: 289.99, zrodlo: "R-GOL", grupa: "pewne", stan: "nowe", zdjecie: "" }],
    },
  },
  {
    typ: "zrodlo_koniec",
    dane: {
      rozmiar: "41",
      nazwa: "Vinted",
      status: "wstrzymane",
      ofert: 1,
      odczytano: 20,
      oferty: [{ klucz: "https://www.vinted.pl/items/1", url: "https://www.vinted.pl/items/1", tytul: "Halówki Joma Top Flex 41", suma_pln: 120.5, zrodlo: "Vinted", grupa: "rozmiar", stan: "Dobry", zdjecie: "javascript:alert(1)", dostawa_szacunkowa: true }],
    },
  },
  { typ: "wyszukiwanie_koniec", dane: { stan: "gotowe", czas: 12.4, gotowe_rozmiary: ["41"] } },
];

const marka = (page, nazwa) => page.locator("#lista-marek").getByRole("radio", { name: new RegExp(`^${nazwa} \\d+ model`) });

function strumien(zdarzenia) {
  return zdarzenia.map((z, id) => `id: ${id}\nevent: ${z.typ}\ndata: ${JSON.stringify({ id, ...z })}\n\n`).join("");
}

async function wybierzJomeTopFlex(page) {
  await page.goto("/");
  await expect(page.locator("#status-api")).toHaveAttribute("data-stan", "ok");
  await marka(page, "Joma").click();
  await page.locator("#lista-modeli").getByRole("radio", { name: /^Joma Top Flex bez Rebound/ }).click();
  await page.getByRole("button", { name: "Rozmiar 41" }).click();
}

test("strona startowa pokazuje dane z katalogu i CTA", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Szatnia/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Halówki w Twoim rozmiarze, od najtańszej oferty");
  await expect(page.locator("#liczba-marek")).toHaveText("6");
  await expect(page.locator("#liczba-modeli")).toHaveText("36");
  await expect(page.locator("#zakres-rozmiarow")).toHaveText("38–46");
  await expect(page.getByRole("link", { name: "Wybierz but" })).toBeVisible();
  await expect(page.getByRole("radio")).toHaveCount(6);
});

test("pusty stan modelu prowadzi do wyboru marki", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#lista-modeli .pusty-stan")).toContainText("Najpierw wybierz markę");
  await expect(page.locator("#lista-zrodel")).toContainText("Wybierz markę i model");
});

test("wybór marki, modelu i rozmiaru trafia do podsumowania i zostaje po odświeżeniu", async ({ page }) => {
  await wybierzJomeTopFlex(page);
  await page.getByRole("button", { name: "Rozmiar 42" }).click();
  await expect(marka(page, "Joma")).toHaveAttribute("aria-checked", "true");
  await expect(page.locator("#rozmiar-podpowiedz")).toContainText("Wybrane: 41, 42");
  await expect(page.locator("#pasek-wybor")).toContainText("Joma Top Flex");
  await expect(page.locator("#pasek-wybor")).toContainText("rozm. 41, 42");
  await expect(page.locator("#szukaj")).toHaveAttribute("aria-disabled", "false");
  await expect(page.locator("#zrodla-licznik")).toContainText("Włączone");
  await page.reload();
  await expect(page.locator("#pasek-wybor")).toContainText("Joma Top Flex");
  await expect(page.getByRole("button", { name: "Rozmiar 42" })).toHaveAttribute("aria-pressed", "true");
});

test("strzałki zmieniają markę w grupie radiowej", async ({ page, isMobile }) => {
  test.skip(isMobile, "klawiatura tylko na komputerze");
  await page.goto("/");
  await marka(page, "Joma").click();
  await page.keyboard.press("ArrowRight");
  await expect(marka(page, "Mizuno")).toHaveAttribute("aria-checked", "true");
  await expect(marka(page, "Mizuno")).toBeFocused();
  await expect(page.locator("#lista-modeli")).toContainText("Mizuno Morelia Sala");
});

test("zła cena blokuje szukanie i mówi, co poprawić", async ({ page }) => {
  await wybierzJomeTopFlex(page);
  await page.getByLabel("Maksymalna cena z dostawą").fill("-5");
  await expect(page.locator("#max-cena-blad")).toContainText("Wpisz kwotę większą od zera");
  await expect(page.locator("#szukaj")).toHaveAttribute("aria-disabled", "true");
  await expect(page.locator("#pasek-brak")).toContainText("Popraw maksymalną cenę");
  await page.getByRole("button", { name: "do 300 zł" }).click();
  await expect(page.getByLabel("Maksymalna cena z dostawą")).toHaveValue("300");
  await expect(page.locator("#szukaj")).toHaveAttribute("aria-disabled", "false");
  await expect(page.locator("#pasek-wybor")).toContainText("do 300 zł");
});

test("wyszukiwanie pokazuje postęp źródeł i oferty od najtańszej", async ({ page }) => {
  let wyslane;
  await page.route("**/api/wyszukiwania", async (route) => {
    wyslane = route.request().postDataJSON();
    await route.fulfill({ status: 202, json: { id: "test", zdarzenia: "/api/wyszukiwania/test/zdarzenia" } });
  });
  await page.route("**/api/wyszukiwania/test/zdarzenia", (route) => route.fulfill({ status: 200, contentType: "text/event-stream", body: strumien(ZDARZENIA) }));
  await wybierzJomeTopFlex(page);
  await page.getByRole("button", { name: /Szukaj ofert/ }).click();
  expect(wyslane).toEqual({ marka: "joma", model: "top-flex", rozmiary: ["41"], tylko_pewne: false, odswiez: false });
  await expect(page.locator("#postep-opis")).toContainText("Najtańsza oferta");
  await expect(page.locator('.zrodlo[data-stan="ok"]')).toContainText("R-GOL");
  await expect(page.locator('.zrodlo[data-stan="wstrzymane"]')).toContainText("Vinted");
  const oferty = page.locator(".oferta");
  await expect(oferty).toHaveCount(2);
  await expect(page.locator(".grupa-ofert--pewne .oferta")).toContainText("289,99 zł");
  await expect(page.locator(".grupa-ofert--rozmiar .oferta")).toContainText("~120,50 zł");
  await expect(page.locator(".grupa-ofert--rozmiar .oferta__link")).toHaveAttribute("rel", "noopener noreferrer");
  await expect(page.locator(".grupa-ofert--rozmiar img")).toHaveCount(0);
  await expect(page.locator("#szukaj")).toHaveAttribute("aria-disabled", "false");
});

test("skrót klawiszowy uruchamia szukanie", async ({ page, isMobile }) => {
  test.skip(isMobile, "klawiatura tylko na komputerze");
  let wywolano = false;
  await page.route("**/api/wyszukiwania", (route) => {
    wywolano = true;
    return route.fulfill({ status: 409, json: { detail: "trwa już inne wyszukiwanie" } });
  });
  await wybierzJomeTopFlex(page);
  await page.keyboard.press("ControlOrMeta+Enter");
  await expect(page.locator("#postep-opis")).toContainText("Trwa już inne wyszukiwanie");
  expect(wywolano).toBe(true);
});

test("brak serwera pokazuje instrukcję i ponowienie", async ({ page }) => {
  await page.route("**/api/katalog", (route) => route.abort());
  await page.goto("/");
  await expect(page.locator("#status-api")).toHaveAttribute("data-stan", "blad");
  await expect(page.locator("#lista-marek .blad-stan")).toContainText("py serwer.py");
  await page.unroute("**/api/katalog");
  await page.getByRole("button", { name: "Spróbuj ponownie" }).click();
  await expect(marka(page, "Munich")).toBeVisible();
});

test("ograniczony ruch wyłącza płynne przewijanie, układ bez poziomego scrolla", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-ruch", "ograniczony");
  const nadmiar = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(nadmiar).toBeLessThanOrEqual(0);
});

test("adres URL otwiera wybrany model i rozmiary, a zmiany trafiają do adresu", async ({ page }) => {
  await page.goto("/?marka=nike&model=tiempo&rozmiar=44,43");
  await expect(page.locator("#status-api")).toHaveAttribute("data-stan", "ok");
  await expect(page.locator("#pasek-wybor")).toContainText("Nike Tiempo IC");
  await expect(page.locator("#pasek-wybor")).toContainText("rozm. 43, 44");
  await page.getByRole("button", { name: "Rozmiar 45" }).click();
  await expect(page).toHaveURL(/marka=nike&model=tiempo&rozmiar=43%2C44%2C45/);
  await page.getByRole("link", { name: "Wybierz but" }).click();
  await expect(page).toHaveURL(/\?marka=nike.*#krok-marka$/);
});

test("nieznany model z adresu nie jest wybierany", async ({ page }) => {
  await page.goto("/?marka=nike&model=nie-ma-takiego&rozmiar=99");
  await expect(page.locator("#status-api")).toHaveAttribute("data-stan", "ok");
  await expect(page.locator("#pasek-brak")).toContainText("Wybierz model");
  await expect(page.locator("#pasek-brak")).toContainText("Zaznacz rozmiar");
});
