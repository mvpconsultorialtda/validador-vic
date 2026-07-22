# 01 · Instalação em aplicações-alvo — Playbook A

Como instalar as libs **in-project** e configurar SaaS **observing** num app-alvo (EducaHubPlay, XequeMath, etc).

## Pré-requisitos no app-alvo

- Next.js 14+ (App Router preferencialmente) OU Vite + React
- Node 20+
- pnpm/npm/yarn
- Repo git configurado

## Método automatizado (recomendado)

```bash
# no repo validador-vic
bash scripts/install-in-app.sh --target ~/repositorios/educahubplay
```

Script interativo pergunta:
1. Qual framework? (Next.js App Router / Next.js Pages / Vite React)
2. Instalar Playwright? (Y/n)
3. Instalar Sentry SDK? (Y/n — cola DSN depois)
4. Instalar PostHog SDK? (Y/n — cola API key depois)
5. Copiar templates? (Y/n)
6. Adicionar `.github/workflows/validator-ci.yml`? (Y/n)

Ao final: app-alvo tem `package.json` atualizado + arquivos copiados + `.env.example` atualizado + `pnpm install` rodado.

## Método manual (se quiser controle passo a passo)

### 1. Libs in-project (devDep)

```bash
cd ~/repositorios/educahubplay
pnpm add -D @playwright/test @axe-core/playwright gremlins.js fast-check msw
pnpm add -D next-openapi-gen
pnpm add @sentry/nextjs posthog-js
```

### 2. Copiar templates

```bash
cp -r ~/repositorios/validador-vic/templates/in-project/playwright/* .
cp -r ~/repositorios/validador-vic/templates/in-project/axe/* .
cp -r ~/repositorios/validador-vic/templates/in-project/gremlins/* .
cp -r ~/repositorios/validador-vic/templates/in-project/sentry/* .
cp -r ~/repositorios/validador-vic/templates/in-project/posthog/* .
cp -r ~/repositorios/validador-vic/templates/in-project/github-actions/.github .
```

### 3. Configurar env vars

Adicionar em `.env.local` (dev) e Vercel dashboard (prod):

```env
NEXT_PUBLIC_SENTRY_DSN=https://xxx@yyy.ingest.sentry.io/zzz
SENTRY_AUTH_TOKEN=sntrys_xxx   # só CI, não expor
NEXT_PUBLIC_POSTHOG_KEY=phc_xxx
NEXT_PUBLIC_POSTHOG_HOST=https://us.i.posthog.com
```

### 4. Instrumentar

`app/layout.tsx` — adicionar PostHogProvider e Sentry init (templates já contém código).

`instrumentation.ts` — Sentry captureRequestError (template).

`playwright.config.ts` — config canônico (template).

### 5. Rodar sanity check

```bash
pnpm playwright test --list          # confirma 3-5 testes template listados
pnpm playwright test tests/smoke     # deve passar
```

### 6. Registrar no runner central

Editar `config/apps.yaml` do validador-vic:

```yaml
apps:
  - name: educahubplay
    url: https://educahubplay-omega.vercel.app
    sitemap: /sitemap.xml
    openapi: /openapi.json
    playwright_ci: true
    sentry_org: mvpconsultoria
    sentry_project: educahubplay
```

Commit no validador-vic. Nightly runner passa a atacar esse app.

## Configurar SaaS observing

### Sentry Cloud (5min)

1. Criar conta grátis em https://sentry.io
2. New Project → Next.js
3. Copiar DSN
4. Colar em `NEXT_PUBLIC_SENTRY_DSN` do app-alvo
5. Deploy pra Vercel — erros começam a chegar

Free tier: 5000 errors/mês + 50 replays/mês + 30 dias retenção + 1 user.

### PostHog Cloud (5min)

1. Criar conta grátis em https://posthog.com
2. New Project → Web
3. Copiar API key + Host (US region padrão)
4. Colar em `NEXT_PUBLIC_POSTHOG_KEY` e `NEXT_PUBLIC_POSTHOG_HOST` do app-alvo
5. Deploy pra Vercel — sessions começam a gravar

Free tier: 5000 recordings/mês + 100k errors/mês + 1M events/mês.

### CodeRabbit (2min)

1. Ir em https://coderabbit.ai
2. Sign in com GitHub
3. Install app na organização `mvpconsultorialtda`
4. Configure repos → selecionar `educahubplay`, `xequemath`, `hq-lab`, etc
5. Próximo PR ativa automaticamente

Free tier: unlimited public repos + 200 private reviews/mês.

### TestSprite (opcional bootstrap 30 dias)

1. https://testsprite.com — sign in com GitHub
2. Add project → paste URL app-alvo
3. TestSprite scan roda auto
4. Se free tier útil → paga $69/mês. Se não → cancela sem custo.

## Checklist pós-instalação

- [ ] `pnpm playwright test --list` mostra 3+ testes template
- [ ] `pnpm build` continua passando (SDKs não quebraram build)
- [ ] Sentry recebeu evento test (via `Sentry.captureMessage("test")`)
- [ ] PostHog dashboard mostra "1 user online" após você visitar
- [ ] CodeRabbit comentou no PR mais recente
- [ ] `config/apps.yaml` do validador-vic tem entrada nova
- [ ] Commit no app-alvo + push
