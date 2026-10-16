import { expect, test } from "@playwright/test";

async function przygotujKatalog(page) {
  const stan = { dodany: false, wyslane: null, usunieto: null };
  await page.route("**/api/katalog", async (route) => {
    const katalog = await (await route.fetch()).json();
    if (stan.dodany) {
      katalog.marki.find((m) => m.id === "joma").modele.push({ id: "top-flex-2402", nazwa: "Joma Top Flex 2402", model: "Top Flex 2402", opis_wykluczen: "bez: jr, rebound", wskazowka_zdjec: "", model3d: null, wlasny: true });
    }
    await route.fulfill({ json: katalog });
  });
  await page.route("**/api/wlasne", async (route) => {
    stan.wyslane = route.request().postDataJSON();
    stan.dodany = true;
    await route.fulfill({ status: 201, json: { marka: "joma", model: "top-flex-2402" } });
  });
  await page.route("**/api/wlasne/joma/top-flex-2402", async (route) => {
    stan.usunieto = route.request().method();
    stan.dodany = false;
    await route.fulfill({ status: 204, body: "" });
  });
  return stan;
}

test("własny model: walidacja, dodanie, wybór i usunięcie z potwierdzeniem", async ({ page }) => {
  const stan = await przygotujKatalog(page);
  await page.goto("/");
  await expect(page.locator("#status-api")).toHaveAttribute("data-stan", "ok");
  await page.locator("#lista-marek").getByRole("radio", { name: /^Joma \d+ model/ }).click();
  await page.getByRole("button", { name: "Dodaj własny model" }).click();
  const okno = page.getByRole("dialog", { name: "Własny model" });
  await expect(okno).toBeVisible();
  await expect(okno.getByLabel("Marka")).toHaveValue("joma");
  await okno.getByRole("button", { name: "Dodaj model" }).click();
  await expect(okno.locator("#edytor-model-blad")).toContainText("Wpisz nazwę modelu");
  await expect(okno.getByLabel("Nazwa modelu")).toBeFocused();
  await okno.getByLabel("Nazwa modelu").fill("Top Flex 2402");
  await okno.getByLabel("Pomiń wersje").fill("rebound, (a|b)");
  await okno.getByRole("button", { name: "Dodaj model" }).click();
  await expect(okno.locator("#edytor-wykluczenia-blad")).toContainText("Popraw: (a|b)");
  await okno.getByLabel("Pomiń wersje").fill("rebound");
  await okno.getByRole("button", { name: "jr", exact: true }).click();
  await expect(okno.getByLabel("Pomiń wersje")).toHaveValue("rebound, jr");
  await okno.getByRole("button", { name: "Dodaj model" }).click();
  await expect(okno).toBeHidden();
  expect(stan.wyslane).toEqual({ marka: "joma", model: "Top Flex 2402", wykluczenia: ["rebound", "jr"], opis: "", wymagaj_oznaczenia_hali: true });
  const karta = page.locator("#lista-modeli").getByRole("radio", { name: /Joma Top Flex 2402/ });
  await expect(karta).toHaveAttribute("aria-checked", "true");
  await expect(karta).toContainText("własny model");
  await expect(page.locator(".powiadomienie")).toContainText("Dodano Top Flex 2402");
  await expect(page.locator("#pasek-wybor")).toContainText("Joma Top Flex 2402");

  await page.getByRole("button", { name: "Dodaj własny model" }).click();
  const usun = okno.getByRole("button", { name: "Usuń Joma Top Flex 2402" });
  await usun.click();
  await expect(okno.getByRole("button", { name: "Potwierdź usunięcie Joma Top Flex 2402" })).toBeVisible();
  expect(stan.usunieto).toBeNull();
  await okno.getByRole("button", { name: "Potwierdź usunięcie Joma Top Flex 2402" }).click();
  await expect(okno.locator(".okno__lista")).toContainText("Nie masz jeszcze własnych modeli");
  expect(stan.usunieto).toBe("DELETE");
  await okno.getByRole("button", { name: "Zamknij" }).click();
  await expect(page.locator("#lista-modeli").getByRole("radio", { name: /Joma Top Flex 2402/ })).toHaveCount(0);
  await expect(page.locator("#pasek-brak")).toContainText("Wybierz model");
});

test("nowa marka wymaga nazwy", async ({ page }) => {
  await przygotujKatalog(page);
  await page.goto("/");
  await expect(page.locator("#status-api")).toHaveAttribute("data-stan", "ok");
  await page.getByRole("button", { name: "Dodaj własny model" }).click();
  const okno = page.getByRole("dialog", { name: "Własny model" });
  await expect(okno.getByLabel("Nazwa nowej marki")).toBeHidden();
  await okno.getByLabel("Marka").selectOption("__inna__");
  await expect(okno.getByLabel("Nazwa nowej marki")).toBeVisible();
  await okno.getByLabel("Nazwa modelu").fill("Precision");
  await okno.getByRole("button", { name: "Dodaj model" }).click();
  await expect(okno.locator("#edytor-nowa-marka-blad")).toContainText("Wpisz nazwę marki");
  await page.keyboard.press("Escape");
  await expect(okno).toBeHidden();
});
