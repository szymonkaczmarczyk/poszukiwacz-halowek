import { expect, test } from "@playwright/test";

test("scena 3D zastępuje rysunek i reaguje na wybór marki", async ({ page }) => {
  const bledy = [];
  page.on("pageerror", (blad) => bledy.push(blad.message));
  await page.goto("/");
  const scena = page.locator(".scena");
  await expect(scena).toHaveAttribute("data-tryb", "3d", { timeout: 15000 });
  await expect(page.locator(".scena__plotno")).toHaveCount(1);
  await expect(page.locator(".scena__but")).toBeHidden();
  await page.locator("#lista-marek").getByRole("radio", { name: /^Nike \d+ model/ }).click();
  await expect(page.locator("#scena-marka")).toHaveText("Nike");
  const wymiary = await page.locator(".scena__plotno").evaluate((plotno) => [plotno.width, plotno.height]);
  expect(wymiary[0]).toBeGreaterThan(100);
  expect(wymiary[1]).toBeGreaterThan(100);
  expect(bledy).toEqual([]);
});

test("ograniczony ruch zostawia rysunek 2D bez WebGL", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.locator(".scena")).toHaveAttribute("data-tryb", "2d");
  await expect(page.locator(".scena__plotno")).toHaveCount(0);
  await expect(page.locator(".scena__but")).toBeVisible();
});

test("brak WebGL zostawia rysunek 2D", async ({ page }) => {
  await page.addInitScript(() => {
    const oryginal = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (typ, ...reszta) {
      return /webgl/.test(typ) ? null : oryginal.call(this, typ, ...reszta);
    };
  });
  await page.goto("/");
  await expect(page.locator(".scena")).toHaveAttribute("data-tryb", "2d");
  await expect(page.locator(".scena__but")).toBeVisible();
});

async function podepnijModel3d(page, odpowiedz) {
  await page.route("**/api/katalog", async (route) => {
    const katalog = await (await route.fetch()).json();
    const joma = katalog.marki.find((m) => m.id === "joma");
    joma.modele.find((m) => m.id === "top-flex").model3d = "/modele/testowy.glb";
    await route.fulfill({ json: katalog });
  });
  await page.route("**/modele/testowy.glb", odpowiedz);
}

test("model z plikiem GLB pokazuje prawdziwy but, inny wraca do stylizowanego", async ({ page }) => {
  const bledy = [];
  page.on("pageerror", (blad) => bledy.push(blad.message));
  await podepnijModel3d(page, (route) => route.fulfill({ path: "tests/zasoby/but-testowy.glb", contentType: "model/gltf-binary" }));
  await page.goto("/");
  const scena = page.locator(".scena");
  await expect(scena).toHaveAttribute("data-tryb", "3d", { timeout: 15000 });
  await expect(scena).toHaveAttribute("data-model3d", "stylizowany");
  await page.locator("#lista-marek").getByRole("radio", { name: /^Joma \d+ model/ }).click();
  await page.locator("#lista-modeli").getByRole("radio", { name: /^Joma Top Flex bez Rebound/ }).click();
  await expect(scena).toHaveAttribute("data-model3d", "prawdziwy", { timeout: 15000 });
  await page.locator("#lista-modeli").getByRole("radio", { name: /^Joma Mundial/ }).click();
  await expect(scena).toHaveAttribute("data-model3d", "stylizowany");
  expect(bledy).toEqual([]);
});

test("uszkodzony plik GLB zostawia stylizowany but", async ({ page }) => {
  await podepnijModel3d(page, (route) => route.fulfill({ body: "to nie jest glb", contentType: "model/gltf-binary" }));
  await page.goto("/");
  const scena = page.locator(".scena");
  await expect(scena).toHaveAttribute("data-tryb", "3d", { timeout: 15000 });
  await page.locator("#lista-marek").getByRole("radio", { name: /^Joma \d+ model/ }).click();
  await page.locator("#lista-modeli").getByRole("radio", { name: /^Joma Top Flex bez Rebound/ }).click();
  await expect(scena).toHaveAttribute("data-model3d", "stylizowany", { timeout: 15000 });
});
