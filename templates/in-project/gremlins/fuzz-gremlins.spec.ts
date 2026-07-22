/**
 * fuzz-gremlins.spec.ts — monkey testing via gremlins.js dentro do Playwright
 * Copiado por install-in-app.sh · spec 034 validador-vic
 *
 * Roda 3min de chaos random em cada rota crítica, captura console errors.
 * Use com moderação — não roda a cada PR, só nightly OU on-demand.
 */
import { test, expect } from "@playwright/test";

const ROTAS_A_ATACAR = [
  "/",
  // adicione as rotas do app:
];

const DURACAO_MS = 60000;  // 60s por rota (reduzir se longo demais)

test.describe.serial("fuzz — Gremlins.js", () => {
  for (const rota of ROTAS_A_ATACAR) {
    test(`monkey chaos em ${rota}`, async ({ page }) => {
      test.setTimeout(DURACAO_MS + 30000);

      const consoleErrors: string[] = [];
      page.on("console", (msg) => {
        if (msg.type() === "error") consoleErrors.push(msg.text());
      });

      await page.goto(rota);

      // Injeta gremlins.js via CDN + roda
      await page.addScriptTag({
        url: "https://unpkg.com/gremlins.js/dist/gremlins.min.js",
      });

      await page.evaluate((duration) => {
        // @ts-expect-error injetado
        return gremlins.createHorde({
          species: [
            // @ts-expect-error
            gremlins.species.clicker(),
            // @ts-expect-error
            gremlins.species.toucher(),
            // @ts-expect-error
            gremlins.species.formFiller(),
            // @ts-expect-error
            gremlins.species.scroller(),
            // @ts-expect-error
            gremlins.species.typer(),
          ],
          mogwais: [
            // @ts-expect-error
            gremlins.mogwais.alert(),
            // @ts-expect-error
            gremlins.mogwais.gizmo(),
          ],
          strategies: [
            // @ts-expect-error
            gremlins.strategies.distribution({ delay: 100 }),
          ],
        }).unleash({ nb: Math.floor(duration / 100) });
      }, DURACAO_MS);

      await page.waitForTimeout(DURACAO_MS);

      // Falha SO se console errors > 5 (permite alguns fantasmas de dev warnings)
      expect(consoleErrors.length, `console.error(s):\n${consoleErrors.join("\n")}`).toBeLessThan(5);
    });
  }
});
