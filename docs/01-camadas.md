# 01 · Camadas do pipeline validador-vic

Pipeline de 7 camadas · cada uma mata **1 tipo distinto de bug** · nenhuma refaz o trabalho da outra.

## Overview

| # | Camada | Tipo de bug alvo | Onde vive | Trigger |
|---|---|---|---|---|
| 1 | **Discovery** | Rota nova em prod sem cobertura | in-project (`sitemap.ts`) + runner (`discover-routes.py`) | build success |
| 2 | **Autonomous LLM** | Interação emergente não imaginada | runner (Browser-Use + rotator LLM) | nightly / pre-merge |
| 3 | **Fuzzing** | Input não antecipado, race condition | in-project (Gremlins.js + fast-check) | CI rápido |
| 4 | **E2E determinístico** | Regressão em PR não relacionado | in-project (Playwright + axe helper) | CI obrigatório |
| 5 | **Code review AI** | Bug semântico que passa build/lint/E2E | SaaS (CodeRabbit) | pre-merge |
| 6 | **Produção observe** | Bug que escapou tudo e usuário real achou | in-project SDK (Sentry + PostHog) | runtime prod |
| 7 | **A11y + Visual + Perf** ⭐ **NOVA spec 054** | Regressão visual/legibilidade/performance/acessibilidade | runner (axe-runner + Playwright screenshots + Unlighthouse) | pre-merge + baseline diff |

## Detalhamento Camada 7 (nova)

### 7a · Accessibility (axe-core)

Rodar `scripts/runners/axe-runner.py --url URL` em cada rota.

Output: JSON estruturado com violations por WCAG rule + impact (critical/serious/moderate/minor).

Threshold GO/NO-GO padrão:
- `critical: 0` — bloqueia deploy
- `serious: 0` — bloqueia deploy
- `moderate: ≤ 5` — warning
- `minor: ≤ 15` — informativo

### 7b · Visual Regression (Playwright toHaveScreenshot)

Playwright nativo — `expect(page).toHaveScreenshot('slug.png', { maxDiffPixels: 100, fullPage: true })`.

Baseline em git commit direto (`__screenshots__/`). Migrar pra Cloudflare R2 quando repo ficar >500MB.

### 7c · Performance + SEO (Unlighthouse)

Unlighthouse crawla site inteiro rodando Lighthouse em cada rota descoberta.

Thresholds:

| Categoria | GO | Bloqueio NO-GO |
|---|---|---|
| Performance | ≥ 80 | < 75 (ou regressão >-5 vs último) |
| Accessibility | ≥ 90 | < 90 absoluto |
| Best Practices | ≥ 90 | < 85 |
| SEO | ≥ 95 | < 95 absoluto |
| LCP | ≤ 2.5s | > 4.0s |
| CLS | ≤ 0.1 | > 0.25 |
| TBT | ≤ 200ms | > 600ms |

## Como as camadas se combinam

```
Cam 1 sitemap.xml + discover-routes → Cam 2 Browser-Use ataca as URLs descobertas
Cam 1 sitemap → Cam 7 (axe + Playwright + Unlighthouse) auditam cada rota
Cam 3 Gremlins captura erros runtime → Cam 6 Sentry recebe → dev vê breadcrumbs
Cam 4 Playwright pass/fail → CI bloqueia PR se falhar
Cam 5 CodeRabbit comenta PR antes de merge
Cam 6 bug prod → volta pra Cam 4 (novo teste E2E) OU Cam 7 (novo baseline visual)
```

## Aplicação em app novo (Next.js)

Ver `02-instalacao-projeto-novo.md`.

## Loop canônico pra mudança visual

Ver `03-loop-canonico-mudanca-visual.md`. **Regra dura:** nunca reportar "OK" sem screenshot lido pelo próprio agente. Grep de CSS não conta.
