/**
 * smoke.spec.ts — testes canônicos golden path
 * Copiado por install-in-app.sh · spec 034 validador-vic
 *
 * Customize os testes pra golden path REAL do seu app.
 */
import { test, expect } from "@playwright/test";

test.describe("smoke — golden path", () => {
  test("home renderiza sem erro", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/./);  // qualquer título válido
  });

  test("home visual baseline", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveScreenshot("home.png", { fullPage: false });
  });

  test("sitemap.xml responde 200", async ({ request }) => {
    const response = await request.get("/sitemap.xml");
    expect(response.status()).toBe(200);
  });

  // Adicione mais smoke tests:
  // test("login → dashboard funciona", async ({ page }) => { ... });
});
