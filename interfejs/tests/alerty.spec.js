import { expect, test } from "@playwright/test";

const WYNIKI = { rozmiar: "41", oferty: [{ klucz: "https://www.vinted.pl/items/1", url: "https://www.vinted.pl/items/1", tytul: "Joma Top Flex 41", suma_pln: 150, zrodlo: "Vinted", grupa: "pewne", flagi: [] }], zmiany: { pierwsze: true, nowe: [], tansze: [], drozsze: [], zniknely: [] }, zrodla: [], recznie: [] };
const ZDARZENIA = [
  { typ: "wyszukiwanie_start", dane: { nazwa: "Joma Top Flex", rozmiary: ["41"] } },
  { typ: "start", dane: { rozmiar: "41", zrodla: ["Vinted"] } },
  { typ: "zrodlo_koniec", dane: { rozmiar: "41", nazwa: "Vinted", status: "ok", ofert: 1, odczytano: 10, oferty: [] } },
  { typ: "koniec", dane: { rozmiar: "41", wyniki: WYNIKI } },
  { typ: "wyszukiwanie_koniec", dane: { stan: "gotowe", czas: 12, gotowe_rozmiary: ["41"] } },
];

const ALERT_Z_TRAFIENIAMI = {
  id: "a1",
  marka: "joma",
  model: "top-flex",
  nazwa: "Joma Top Flex",
  rozmiar: "42",
  max_cena: 300,
  tylko_pewne: false,
  utworzono: "2026-10-20 18:00",
  sprawdzono: "2026-10-21 15:00",
  stan: "ok",
  nowych: 1,
  trafienia: [
    { typ: "tansza", klucz: "https://www.vinted.pl/items/7", url: "https://www.vinted.pl/items/7", tytul: "Joma Top Flex 42 skóra", zrodlo: "Vinted", cena: 180, roznica: 40, kiedy: "2026-10-21 15:00" },
    { typ: "nowa", klucz: "https://www.olx.pl/d/8", url: "https://www.olx.pl/d/8", tytul: "Halówki Joma Top Flex", zrodlo: "OLX", cena: 210, roznica: null, kiedy: "2026-10-21 09:00" },
  ],
};
const ALERT_CZEKA = { ...ALERT_Z_TRAFIENIAMI, id: "a2", nazwa: "Nike Gato", marka: "nike", model: "gato", rozmiar: "43", max_cena: null, sprawdzono: null, stan: "czeka na pierwsze sprawdzenie", nowych: 0, trafienia: [] };
const LISTA = { alerty: [ALERT_Z_TRAFIENIAMI, ALERT_CZEKA], godziny: [9, 15, 21], harmonogram: false, kanaly: { mac: true, telegram: false } };

function strumien(zdarzenia) {
  return zdarzenia.map((z, id) => `id: ${id}\nevent: ${z.typ}\ndata: ${JSON.stringify({ id, ...z })}\n\n`).join("");
}

async function szukaj(page, zalogowany) {
  const zapisane = [];
  await page.route("**/api/admin", (route) => route.fulfill({ json: { zalogowany, skonfigurowany: true } }));
  await page.route("**/api/alerty", (route) => {
    if (route.request().method() === "POST") {
      zapisane.push(route.request().postDataJSON());
      return route.fulfill({ status: 201, json: { dodane: [{ ...ALERT_CZEKA, rozmiar: "41" }], pominiete: [], godziny: [9, 15, 21] } });
    }
    return route.fulfill({ json: LISTA });
  });
  await page.route("**/api/wyszukiwania", (route) => route.fulfill({ status: 202, json: { id: "t1", zdarzenia: "/api/wyszukiwania/t1/zdarzenia" } }));
  await page.route("**/api/wyszukiwania/t1/zdarzenia", (route) => route.fulfill({ status: 200, contentType: "text/event-stream", body: strumien(ZDARZENIA) }));
  await page.goto("/");
  await expect(page.locator("#status-api")).toHaveAttribute("data-stan", "ok");
  await page.locator("#lista-marek").getByRole("radio", { name: /^Joma \d+ model/ }).click();
  await page.locator("#lista-modeli").getByRole("radio", { name: "Joma Top Flex", exact: true }).click();
  await page.getByRole("button", { name: "Rozmiar 41" }).click();
  await page.getByRole("button", { name: /Szukaj ofert/ }).click();
  await expect(page.locator("#postep-tytul")).toHaveText("Wyniki");
  return zapisane;
}

test("administrator zapisuje wyszukiwanie jako alert", async ({ page }) => {
  const zapisane = await szukaj(page, true);
  const dzwonek = page.getByRole("link", { name: /Alerty o ofertach, 1 nowa zmiana/ });
  await expect(dzwonek).toBeVisible();
  await expect(dzwonek.locator(".dzwonek__kropka")).toBeVisible();
  const przycisk = page.getByRole("button", { name: "Powiadamiaj o nowych i tańszych" });
  await przycisk.click();
  await expect(page.locator(".powiadomienie")).toContainText("Alert zapisany dla rozmiaru 41. Sprawdzam codziennie o 9:00, 15:00 i 21:00");
  await expect(page.getByRole("button", { name: "Alert zapisany" })).toHaveAttribute("aria-disabled", "true");
  expect(zapisane).toEqual([{ marka: "joma", model: "top-flex", rozmiary: ["41"], tylko_pewne: false }]);
});

test("bez logowania nie ma alertów ani dzwonka", async ({ page }) => {
  await szukaj(page, false);
  await expect(page.locator("#zapisz-alert")).toBeHidden();
  await expect(page.locator(".dzwonek")).toHaveCount(0);
});

test("strona alertów pokazuje zmiany, ustawienia i usuwa alert po potwierdzeniu", async ({ page }) => {
  const zadania = [];
  await page.route("**/api/alerty", (route) => route.fulfill({ json: LISTA }));
  await page.route("**/api/alerty/**", (route) => {
    zadania.push(`${route.request().method()} ${new URL(route.request().url()).pathname}`);
    return route.fulfill(route.request().method() === "DELETE" ? { status: 204, body: "" } : { json: { ok: true } });
  });
  await page.goto("/alerty.html");
  await expect(page).toHaveTitle("Alerty o ofertach - Szatnia");
  const karty = page.locator(".alert");
  await expect(karty).toHaveCount(2);
  const pierwsza = karty.first();
  await expect(pierwsza.getByRole("heading")).toHaveText("Joma Top Flexrozmiar 42");
  await expect(pierwsza).toHaveAttribute("data-nowe", "true");
  await expect(pierwsza.locator(".trafienie").first()).toContainText("taniej o 40 zł");
  await expect(pierwsza.locator('.trafienie[data-nowe="true"]')).toHaveCount(1);
  await expect(pierwsza.getByRole("link", { name: "Joma Top Flex 42 skóra" })).toHaveAttribute("href", "https://www.vinted.pl/items/7");
  await expect(pierwsza.getByRole("link", { name: "Szukaj teraz" })).toHaveAttribute("href", "/?marka=joma&model=top-flex&rozmiar=42#krok-filtry");
  await expect(pierwsza.locator(".znaczki").first()).toContainText("do 300 zł");
  await expect(karty.nth(1)).toContainText("Pierwsze sprawdzenie");
  await expect(karty.nth(1)).toContainText("Na razie bez zmian");
  await expect(page.locator(".alerty-ustawienia")).toContainText("Automatyczne sprawdzanie jest wyłączone");
  await expect(page.locator(".alerty-ustawienia")).toContainText("Telegram nie jest ustawiony");
  await expect.poll(() => zadania).toContain("POST /api/alerty/przeczytane");

  const usun = page.getByRole("button", { name: "Usuń alert Nike Gato, rozmiar 43" });
  await usun.click();
  await expect(page.getByRole("button", { name: "Potwierdź: Usuń alert Nike Gato, rozmiar 43" })).toBeVisible();
  await page.getByRole("button", { name: "Potwierdź: Usuń alert Nike Gato, rozmiar 43" }).click();
  await expect(karty).toHaveCount(1);
  await expect(page.locator(".powiadomienie")).toContainText("Usunięto alert: Nike Gato, rozmiar 43.");
  expect(zadania).toContain("DELETE /api/alerty/a2");
});

test("strona alertów bez logowania i bez alertów", async ({ page }) => {
  await page.route("**/api/alerty", (route) => route.fulfill({ status: 401, json: { detail: "tylko administrator ma do tego dostęp" } }));
  await page.goto("/alerty.html");
  await expect(page.getByText("Alerty widzi tylko administrator")).toBeVisible();
  await expect(page.getByRole("link", { name: "Zaloguj się" })).toHaveAttribute("href", "/admin.html");

  await page.unroute("**/api/alerty");
  await page.route("**/api/alerty", (route) => route.fulfill({ json: { ...LISTA, alerty: [], harmonogram: true, kanaly: { mac: true, telegram: true } } }));
  await page.reload();
  await expect(page.getByText("Nie masz jeszcze alertów")).toBeVisible();
  await expect(page.getByRole("link", { name: "Wybierz buty" })).toHaveAttribute("href", "/#krok-marka");
  await expect(page.locator(".alerty-ustawienia")).toContainText("Sprawdzam codziennie o 9:00, 15:00 i 21:00");
  await expect(page.locator(".alerty-ustawienia")).toContainText("Telegram jest podłączony");
});
