/**
 * mvp_bridge.ts — snippet DEV-ONLY pra colar em lib/firebase.ts (ou equivalente)
 * Spec 055 · Padrão Dora 2026-08-03 (mvp-fundacao-app commit db38a83)
 *
 * Expõe `window.__mvp_bridge = { app, auth, db }` gated por env DEV pra Playwright
 * autenticar sincrono via `signInWithCustomToken(window.__mvp_bridge.auth, token)`
 * em localhost. Nunca vaza pra produção (Next.js/Vite/react-scripts strippam o
 * branch em production build via dead code elimination).
 *
 * Como aplicar:
 *   1. Abra seu módulo de init do Firebase (`lib/firebase.ts`, `src/firebase.ts` etc)
 *   2. No FIM do módulo (depois de `app`, `auth`, `db` já criados), cole o bloco
 *      apropriado abaixo (Next.js / Vite / react-scripts)
 *   3. Rebuilda seu dev server, confirme no DevTools console: `!!window.__mvp_bridge`
 *   4. Em prod: `curl https://APP.vercel.app | grep __mvp_bridge` → 0 matches
 *
 * SEGURANÇA: se você ver __mvp_bridge exposto em produção, é BUG — não é feature.
 * Ele expõe o Firebase Auth handle do usuário logado a qualquer script na página
 * (XSS trivial). Verifique que o gate `NODE_ENV === "development"` está intacto
 * e que seu bundler está removendo o branch em prod build.
 */

// ─── Next.js (App Router / Pages Router) ─────────────────────────────────────
// Cole no fim de `lib/firebase.ts`:

if (process.env.NODE_ENV === "development" && typeof window !== "undefined") {
  ;(window as unknown as { __mvp_bridge: { app: unknown; auth: unknown; db: unknown } }).__mvp_bridge = {
    app,   // FirebaseApp
    auth,  // Auth
    db,    // Firestore
  }
}

// ─── Vite (mvp-fundacao-app padrão original Dora) ────────────────────────────
// Cole no fim de `src/lib/firebase.ts`:

// if (import.meta.env.DEV && typeof window !== "undefined") {
//   ;(window as unknown as { __mvp_bridge: any }).__mvp_bridge = { app, auth, db }
// }

// ─── react-scripts (CRA) ─────────────────────────────────────────────────────
// Cole após init do Firebase em `src/api/firebase.ts` (ou equivalente):

// if (process.env.NODE_ENV === "development" && typeof window !== "undefined") {
//   (window as any).__mvp_bridge = { app, auth, db };
// }

// ─── Verificação pós-instalação ──────────────────────────────────────────────
// Dev (localhost):
//   1. Abra o app em localhost
//   2. DevTools → Console → digite: window.__mvp_bridge
//   3. Deve retornar { app, auth, db }
//
// Prod:
//   1. curl https://SEU_APP.vercel.app | grep __mvp_bridge → 0 matches
//   2. Se retornar match, seu bundler NÃO está strippando dead code.
//      Verifique tsconfig.json e configuração de production build.
