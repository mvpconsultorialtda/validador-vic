/**
 * a11y.spec.ts — WCAG 2.2 audit via @axe-core/playwright
 * Copiado por install-in-app.sh · spec 034 validador-vic
 */
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const ROTAS_CRITICAS = [
  "/",
  // adicione as rotas críticas do app aqui:
  // "/login",
  // "/dashboard",
];

test.describe("a11y — WCAG 2.2", () => {
  for (const rota of ROTAS_CRITICAS) {
    test(`rota ${rota} sem violações críticas`, async ({ page }) => {
      await page.goto(rota);
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
        .analyze();

      // Falha só em critical + serious (moderate/minor viram warning)
      const bloqueantes = results.violations.filter(
        (v) => v.impact === "critical" || v.impact === "serious",
      );
      expect(bloqueantes, JSON.stringify(bloqueantes, null, 2)).toEqual([]);
    });
  }
});
