# 00 · Arquitetura

## Pipeline 6-camadas sem overlap

Cada camada mata **1 tipo distinto de bug**. Nenhuma refaz o trabalho da outra. Isso é o princípio fundador — sem ele, você duplica esforço e cria falso senso de segurança.

```
┌─────────────────────────────────────────────────────────────────┐
│  CAMADA 1 · DISCOVERY (build-time, determinístico)              │
│  Mata: rota nova entra em prod sem cobertura                    │
│  Produz: sitemap.xml + openapi.json                             │
└──────────────────────┬──────────────────────────────────────────┘
                       │ (URLs + endpoints)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  CAMADA 2 · AUTONOMOUS LLM (pre-merge OR nightly)               │
│  Mata: bug de interação emergente que humano não imaginou       │
│  Produz: relatório bugs JSON + scripts Playwright candidatos    │
└──────────────────────┬──────────────────────────────────────────┘
                       │ (bugs achados)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  CAMADA 3 · FUZZING (CI, rápido)                                │
│  Mata: input não antecipado, race condition, form quebra        │
│  Produz: console.error capturados + Sentry breadcrumbs          │
└──────────────────────┬──────────────────────────────────────────┘
                       │ (erros runtime)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  CAMADA 4 · E2E DETERMINÍSTICO (CI, obrigatório)                │
│  Mata: regressão em PR não relacionado                          │
│  Produz: pass/fail binário + baseline screenshots + a11y report │
└──────────────────────┬──────────────────────────────────────────┘
                       │ (report PR)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  CAMADA 5 · CODE REVIEW AI (pre-merge)                          │
│  Mata: bug semântico que build/lint/E2E passa mas está errado   │
│  Produz: comentários inline PR + block em críticos              │
└──────────────────────┬──────────────────────────────────────────┘
                       │ (merge ou volta)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  CAMADA 6 · PRODUÇÃO OBSERVE (runtime)                          │
│  Mata: bug que escapou tudo e usuário real encontrou            │
│  Produz: Sentry error + PostHog session replay + logs           │
└──────────────────────┬──────────────────────────────────────────┘
                       │ (bug escapou → volta pro início)
                       ▼
                    LOOP → gera novo teste E2E em camada 4
```

## Onde cada ferramenta vive (3 padrões de integração)

### Padrão A · IN-PROJECT (devDep no repo do app)

Vive dentro do repo do app-alvo. Roda no CI do próprio app.

- `sitemap.ts` (código Next.js)
- `next-openapi-gen` (devDep)
- `@playwright/test` (devDep)
- `@axe-core/playwright` (devDep)
- `gremlins.js` (devDep)
- `fast-check` (devDep)
- `msw` (devDep)
- `@sentry/nextjs` (dep + snippet layout.tsx)
- `posthog-js` (dep + snippet layout.tsx)

**Consequência:** cada app instala separadamente. 5 apps = 5x instalação.

### Padrão B · EXTERNAL RUNNER (repo `validador-vic` — este)

Vive num repo separado. Roda em máquina/CI própria. Só precisa da URL do app.

- **Browser-Use** — script Python, `scripts/runners/browser-use-runner.py`
- **Playwright MCP** — roda no Claude Code local
- **Schemathesis** — CLI Python, `scripts/runners/schemathesis-runner.sh`
- **Bruno CLI** — `bruno-collections/{app}/` versionadas neste repo

**Consequência:** 1 repo central valida todos os apps.

### Padrão C · SAAS OBSERVING (gerenciado por terceiro)

Você não gerencia infra. SDK no app (padrão A) envia dados pra dashboard SaaS.

- **Sentry Cloud** — DSN no `.env` do app
- **PostHog Cloud** — API key no `.env` do app
- **CodeRabbit** — GitHub App instalada 1x na organização, cobre todos os repos
- **TestSprite** — SaaS externo, aponta pra URL do app

**Consequência:** setup ~5min por SaaS. 1 conta por serviço.

## Fluxo de dados entre camadas

| De | Pra | Formato | Trigger |
|---|---|---|---|
| Cam 1 sitemap.ts | Cam 2 Browser-Use | `sitemap.xml` (URLs) | build success |
| Cam 1 next-openapi-gen | Cam 4 Schemathesis | `openapi.json` | build success |
| Cam 2 Browser-Use | Cam 4 Playwright | JSON `{bug, url, steps, screenshot}` | nightly cron OR pre-merge |
| Cam 2 Playwright MCP | Cam 4 Playwright | `.spec.ts` gerado | Claude Code invocado |
| Cam 3 Gremlins.js | Cam 6 Sentry | `Sentry.captureException()` | run in Playwright wrapper |
| Cam 4 Playwright | GitHub Actions | pass/fail exit code | push/PR |
| Cam 5 CodeRabbit | GitHub PR | comentários inline | PR aberto |
| Cam 6 Sentry | Cam 6 PostHog | link user_id no evento | error captured |
| Cam 6 PostHog | dev (dashboard) | session replay | ver bug reportado |
| Cam 6 → Cam 4 | Playwright novo `.spec.ts` | Claude Code + MCP consome breadcrumbs | bug reproduzido |

## Regra crítica de composição

- Libs que testam **código INTERNO do app** (Playwright + axe + Gremlins + SDKs) → **in-project**
- Runners que **batem na URL externamente** (Browser-Use + Schemathesis + Bruno) → **runner central**
- Observadores **externos por design** (Sentry + PostHog + CodeRabbit + TestSprite) → **SaaS**

Isso evita:
- Duplicação de Browser-Use em cada app (economia de config)
- Bruno collections espalhadas (versionamento único)
- Playwright fora do repo (perda de localidade cognitiva — teste tem que morar perto do código)
- SDKs Sentry/PostHog fora do bundle (não conseguem monitorar runtime)

## Aplicação nas 5 plataformas MVP

Cada app instrumentado do mesmo jeito:

| Plataforma | In-project instalado | SaaS DSN Sentry | SaaS PostHog | URL config runner |
|---|---|---|---|---|
| EducaHubPlay | ✅ | `educahubplay@sentry.io` | `educahubplay@posthog.com` | `educahubplay-omega.vercel.app` |
| XequeMath | ✅ | `xequemath@sentry.io` | `xequemath@posthog.com` | `xequemath.vercel.app` |
| HQ-Lab | ✅ | `hqlab@sentry.io` | `hqlab@posthog.com` | `hq-lab.vercel.app` |
| Lab Games | ✅ | `labgames@sentry.io` | `labgames@posthog.com` | `lab-games.vercel.app` |
| InovaEDUCACAO Landing | ✅ | `inovaeducacao@sentry.io` | `inovaeducacao@posthog.com` | (URL a definir) |

Config no `config/apps.yaml` deste repo lista todas.
