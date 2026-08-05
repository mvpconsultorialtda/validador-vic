/**
 * widget-feedback.spec.ts — validação E2E do widget de feedback v1.4.0
 * Spec 055 · validador-vic pipeline widget · 2026-08-04
 *
 * Requer:
 *   1. Dev server local rodando (`pnpm dev` ou `npm start`) na porta esperada
 *   2. Bridge dev `window.__mvp_bridge` presente em lib/firebase.ts (padrão Dora)
 *   3. Custom token de test user em env FIREBASE_TEST_CUSTOM_TOKEN
 *   4. Endpoint VPS `/api/feedback-upload` respondendo (mvp-agentes.duckdns.org)
 *
 * 3 fluxos validados:
 *   A. Texto-only
 *   B. Texto + upload de arquivo (mp3 fake 32KB)
 *   C. Texto + gravação nativa (skip se MediaRecorder não suportado)
 *
 * Regra Zero B: 2x consecutivas OK = validado.
 *
 * Customize:
 *   - ROUTE_WITH_WIDGET — rota onde o widget aparece
 *   - VPS_UPLOAD_URL se diferente do default
 *   - FIREBASE_TEST_CUSTOM_TOKEN gerado via Firebase Admin SDK antes do teste
 */
import { test, expect, Page } from "@playwright/test";
import { readFileSync } from "fs";
import { join } from "path";

const ROUTE_WITH_WIDGET = process.env.WIDGET_ROUTE || "/";
const VPS_UPLOAD_URL =
  process.env.VPS_UPLOAD_URL || "https://mvp-agentes.duckdns.org/api/feedback-upload";
const CUSTOM_TOKEN = process.env.FIREBASE_TEST_CUSTOM_TOKEN || "";

// Fixture: 32KB fake mp3 gerado uma vez
const FAKE_MP3 = Buffer.concat([
  Buffer.from([0xff, 0xfb, 0x90, 0x00]), // header MP3 frame
  Buffer.alloc(32 * 1024 - 4, 0),
]);

async function authViaBridge(page: Page) {
  test.skip(!CUSTOM_TOKEN, "FIREBASE_TEST_CUSTOM_TOKEN não setado — pula test");

  await page.goto("/");
  await page.waitForFunction(() => !!(window as any).__mvp_bridge?.auth, null, { timeout: 15000 });

  const result = await page.evaluate(
    async ({ token }) => {
      try {
        const { signInWithCustomToken } = await import(
          "https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js"
        );
        // @ts-ignore
        const auth = (window as any).__mvp_bridge.auth;
        const cred = await signInWithCustomToken(auth, token);
        return { ok: true, uid: cred.user.uid, email: cred.user.email };
      } catch (e: any) {
        return { ok: false, err: String(e && e.message ? e.message : e) };
      }
    },
    { token: CUSTOM_TOKEN }
  );

  expect(result.ok, `auth via bridge falhou: ${JSON.stringify(result)}`).toBe(true);
}

async function openWidget(page: Page) {
  await page.goto(ROUTE_WITH_WIDGET);

  // Widget é Web Component <mvp-feedback-widget> — precisa penetrar shadow DOM
  const trigger = page.locator("mvp-feedback-widget").locator("#trigger");
  await expect(trigger).toBeVisible({ timeout: 5000 });
  await trigger.click();
}

async function fillTextFields(page: Page, comment: string, rating: number) {
  const widget = page.locator("mvp-feedback-widget");

  // Rating
  await widget.locator(`.star[data-v="${rating}"]`).click();

  // Comment
  await widget.locator("#comment").fill(comment);
}

async function submit(page: Page) {
  const widget = page.locator("mvp-feedback-widget");
  await widget.locator("#submit-btn").click();
}

async function waitSuccessToast(page: Page) {
  const toast = page.locator("mvp-feedback-widget").locator("#toast.success");
  await expect(toast).toBeVisible({ timeout: 30000 });
}

test.describe("widget-feedback v1.4.0 — 3 fluxos", () => {
  test.beforeEach(async ({ page }) => {
    await authViaBridge(page);
  });

  test("A — texto-only submete e recebe toast success", async ({ page }) => {
    await openWidget(page);
    await fillTextFields(page, "E2E teste A — texto only", 4);
    await submit(page);
    await waitSuccessToast(page);
  });

  test("B — texto + upload arquivo mp3", async ({ page }) => {
    await openWidget(page);
    await fillTextFields(page, "E2E teste B — com upload mp3", 3);

    const fileInput = page.locator("mvp-feedback-widget").locator("#file-input");
    await fileInput.setInputFiles({
      name: "test-audio.mp3",
      mimeType: "audio/mpeg",
      buffer: FAKE_MP3,
    });

    // Confirma que apareceu na lista
    const list = page.locator("mvp-feedback-widget").locator(".attached-list .attached-item");
    await expect(list).toHaveCount(1);

    await submit(page);
    await waitSuccessToast(page);
  });

  test("C — gravação nativa (skip se MediaRecorder ausente)", async ({ page }) => {
    await openWidget(page);

    const recordBtn = page.locator("mvp-feedback-widget").locator("#record-btn");
    const isHidden = await recordBtn.evaluate((el) => (el as HTMLElement).style.display === "none");
    test.skip(isHidden, "MediaRecorder não suportado nesse browser — pula");

    await fillTextFields(page, "E2E teste C — com gravação nativa", 5);

    // Grant permissão de mic
    await page.context().grantPermissions(["microphone"]);
    await recordBtn.click();
    await page.waitForTimeout(3000); // grava 3s
    await recordBtn.click(); // para

    // Confirma que gravação apareceu
    const list = page.locator("mvp-feedback-widget").locator(".attached-list .attached-item");
    await expect(list).toHaveCount(1);

    await submit(page);
    await waitSuccessToast(page);
  });
});
