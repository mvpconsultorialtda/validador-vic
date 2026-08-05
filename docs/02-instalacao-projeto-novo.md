# 02 · Instalação em projeto novo

Passo-a-passo pra ativar o pipeline validador-vic em um app novo (Next.js/Vue/Svelte/qualquer web).

## Pré-requisitos

- Node.js 18+ (pra Playwright + Lighthouse)
- Python 3.10+ (pra runners Python)
- Chromium (via Playwright)
- Repo Git conectado a plataforma de deploy (Vercel/Netlify/Cloudflare Pages)

## Setup do validador-vic (1x por ambiente)

```bash
# Clonar
git clone https://github.com/mvpconsultorialtda/validador-vic
cd validador-vic

# Python venv + deps
python3 -m venv .venv
.venv/bin/pip install axe-playwright-python playwright pyyaml requests browser-use langchain-google-genai langchain-groq
.venv/bin/python -m playwright install chromium

# Lighthouse global (Node)
npm install -g lighthouse
# OU: usar via npx sem install (mais lento)

# Env vars pros LLM providers (Camada 2 Browser-Use)
export GEMINI_KEYS="k1,k2,k3"  # rotator round-robin
export GROQ_KEYS="k1,k2"       # fallback
```

## Configurar app-alvo

Editar `config/apps.yaml`:

```yaml
apps:
  - name: educahubplay
    url: https://educahubplay.vercel.app
    sitemap: https://educahubplay.vercel.app/sitemap.xml
    repo_github: mvpconsultorialtda/educahubplay
    thresholds:
      axe_critical: 0
      axe_serious: 0
      lh_performance: 80
      lh_accessibility: 90
```

## Aplicação por camada

### Camada 1 · Discovery (in-project OU runner)

**In-project** (dentro do app-alvo — recomendado pra Next.js):

```typescript
// app/sitemap.ts
import { MetadataRoute } from 'next'
export default function sitemap(): MetadataRoute.Sitemap {
  const base = 'https://seu-app.vercel.app'
  return [
    { url: `${base}/`, priority: 1 },
    { url: `${base}/quiz`, priority: 0.8 },
    // ... todas rotas conhecidas
  ]
}
```

**Runner deterministic** (roda no `validador-vic` — pega o que sitemap esquece):

```bash
python3 scripts/discover-routes.py --url https://seu-app.vercel.app
```

### Camada 2 · Autonomous LLM (Browser-Use)

```bash
.venv/bin/python scripts/runners/browser-use-runner.py \
  --url https://seu-app.vercel.app \
  --objetivo "explore /login, /dashboard, /perfil. reporte qualquer erro visual, rota 404, botao sem reacao" \
  --max-rotas 5 \
  --output reports/browser-use.json
```

Requer `GEMINI_KEYS` ou `GROQ_KEYS` env.

### Camada 4 · E2E determinístico (in-project)

Instalar no app-alvo:

```bash
cd seu-app
pnpm add -D @playwright/test @axe-core/playwright
```

Criar teste `tests/e2e/smoke.spec.ts`:

```typescript
import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('landing sem violations a11y críticas', async ({ page }) => {
  await page.goto('/')
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2aa', 'wcag21aa'])
    .analyze()
  const critical = results.violations.filter(v => v.impact === 'critical')
  expect(critical).toHaveLength(0)
})
```

### Camada 7a · A11y externo (validador-vic runner)

```bash
# Rota individual
.venv/bin/python scripts/runners/axe-runner.py \
  --url https://seu-app.vercel.app/cruzadinha/biologia \
  --output reports/axe-cruzadinha-bio.json

# Batch sitemap
.venv/bin/python scripts/runners/axe-runner.py \
  --sitemap https://seu-app.vercel.app/sitemap.xml \
  --output reports/axe-audit/ \
  --max-rotas 30 \
  --threshold-critical 0 --threshold-serious 0
```

### Camada 7c · Performance + SEO (Lighthouse)

```bash
# Uma rota
./scripts/runners/lighthouse-runner.sh \
  --url https://seu-app.vercel.app/ \
  --output reports/lh-landing.json

# Custom thresholds
LH_THRESHOLD_PERF=90 LH_THRESHOLD_LCP_MS=2000 \
  ./scripts/runners/lighthouse-runner.sh --url URL --output OUT
```

## CI integration (GitHub Actions exemplo)

```yaml
# .github/workflows/validador.yml
on: [pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          repository: mvpconsultorialtda/validador-vic
          path: validador-vic

      - uses: actions/setup-python@v5
      - uses: actions/setup-node@v4

      - run: |
          cd validador-vic
          python -m venv .venv
          .venv/bin/pip install axe-playwright-python playwright
          .venv/bin/python -m playwright install chromium
          npm install -g lighthouse

      - run: |
          cd validador-vic
          .venv/bin/python scripts/runners/axe-runner.py \
            --sitemap ${{ vars.PR_PREVIEW_URL }}/sitemap.xml \
            --output reports/axe/ --max-rotas 20

      - run: |
          ./validador-vic/scripts/runners/lighthouse-runner.sh \
            --url ${{ vars.PR_PREVIEW_URL }} \
            --output reports/lh-landing.json

      - uses: actions/upload-artifact@v4
        with:
          name: audit-reports
          path: reports/
```

## Cross-repo — orquestrando N apps de 1 vez

Ver `05-cross-repo-orchestration.md`.

## Troubleshooting

Ver `04-troubleshooting-comuns.md`.
