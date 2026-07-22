/**
 * playwright.config.ts — configuração canônica validador-vic
 * Copiado por install-in-app.sh · spec 034
 *
 * BASE_URL default = localhost dev. Override com env var:
 *   BASE_URL=https://educahubplay-omega.vercel.app pnpm playwright test
 */
import { defineConfig, devices } from "@playwright/test";

const BASE_URL = process.env.BASE_URL ?? "http://localhost:3000";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [
    ["html", { open: "never" }],
    ["json", { outputFile: "playwright-report/results.json" }],
    ["list"],
  ],
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile-chrome", use: { ...devices["Pixel 7"] } },
    // { name: "webkit", use: { ...devices["Desktop Safari"] } },  // habilitar se relevante
  ],
  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.05,  // 5% pixel diff tolerado
    },
  },
});
