import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "tests",
  timeout: 60000,
  workers: 3,
  fullyParallel: true,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:5190",
    trace: "retain-on-failure",
    launchOptions: { args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] },
  },
  projects: [
    { name: "komputer", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } },
    { name: "telefon", use: { ...devices["Pixel 7"] } },
  ],
  webServer: [
    {
      command: ".venv/bin/python serwer.py",
      cwd: "..",
      url: "http://127.0.0.1:8765/api/zdrowie",
      reuseExistingServer: true,
    },
    {
      command: "npm run dev",
      url: "http://127.0.0.1:5190",
      reuseExistingServer: true,
    },
  ],
});
