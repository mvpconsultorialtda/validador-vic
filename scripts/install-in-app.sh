#!/usr/bin/env bash
# install-in-app.sh — instala pipeline in-project num app-alvo (interativo)
#
# Uso:
#   bash install-in-app.sh --target ~/repositorios/educahubplay
#   bash install-in-app.sh --help
#
# Autor: Claudia · spec 034 validador-vic

set -euo pipefail

REPO_VIC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --help)
      cat <<EOF
Uso: bash install-in-app.sh --target /path/to/app-repo

Instala interativamente o pipeline validador-vic no repo do app-alvo:
- Playwright + @axe-core/playwright + Gremlins.js + fast-check + msw
- @sentry/nextjs + posthog-js
- next-openapi-gen
- Templates canônicos (playwright.config.ts, tests/, layout snippets)
- .github/workflows/validator-ci.yml
EOF
      exit 0
      ;;
    *) echo "opção desconhecida: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  echo "--target obrigatório. Use --help." >&2
  exit 2
fi

if [[ ! -d "$TARGET" ]]; then
  echo "Diretório $TARGET não existe" >&2
  exit 2
fi

if [[ ! -f "$TARGET/package.json" ]]; then
  echo "$TARGET não é um projeto Node/Next.js (sem package.json)" >&2
  exit 2
fi

cd "$TARGET"
APP_NAME=$(node -p "require('./package.json').name" 2>/dev/null || basename "$TARGET")

echo "════════════════════════════════════════════════════════════"
echo "  validador-vic · install-in-app"
echo "  Target: $TARGET"
echo "  App:    $APP_NAME"
echo "════════════════════════════════════════════════════════════"

read -p "Detectar framework? (Next.js App / Next.js Pages / Vite / outro): " FRAMEWORK
FRAMEWORK=${FRAMEWORK:-"Next.js App"}

ask_confirm() {
  local prompt="$1"
  local default="${2:-Y}"
  read -p "$prompt [${default}/$([[ "$default" = "Y" ]] && echo "n" || echo "y")]: " response
  response=${response:-$default}
  [[ "$response" =~ ^[YySs]$ ]]
}

# Detecta package manager
PM="pnpm"
if [[ -f "yarn.lock" ]]; then PM="yarn"
elif [[ -f "package-lock.json" ]]; then PM="npm"
fi
echo "Package manager detectado: $PM"

INSTALL_PLAYWRIGHT=true
INSTALL_SENTRY=true
INSTALL_POSTHOG=true
INSTALL_TEMPLATES=true
INSTALL_CI=true

ask_confirm "Instalar Playwright + axe + Gremlins?" || INSTALL_PLAYWRIGHT=false
ask_confirm "Instalar Sentry SDK?" || INSTALL_SENTRY=false
ask_confirm "Instalar PostHog SDK?" || INSTALL_POSTHOG=false
ask_confirm "Copiar templates canônicos?" || INSTALL_TEMPLATES=false
ask_confirm "Adicionar .github/workflows/validator-ci.yml?" || INSTALL_CI=false

DEV_DEPS=""
DEPS=""

if $INSTALL_PLAYWRIGHT; then
  DEV_DEPS="$DEV_DEPS @playwright/test @axe-core/playwright gremlins.js fast-check msw"
fi
if $INSTALL_SENTRY; then
  DEPS="$DEPS @sentry/nextjs"
fi
if $INSTALL_POSTHOG; then
  DEPS="$DEPS posthog-js"
fi

# next-openapi-gen só se Next.js
if [[ "$FRAMEWORK" =~ Next ]]; then
  DEV_DEPS="$DEV_DEPS next-openapi-gen"
fi

echo ""
echo "Vai executar:"
[[ -n "$DEPS" ]] && echo "  $PM add $DEPS"
[[ -n "$DEV_DEPS" ]] && echo "  $PM add -D $DEV_DEPS"
echo ""

ask_confirm "Prosseguir?" || exit 0

if [[ -n "$DEPS" ]]; then
  $PM add $DEPS
fi
if [[ -n "$DEV_DEPS" ]]; then
  $PM add -D $DEV_DEPS
fi

if $INSTALL_TEMPLATES; then
  echo "Copiando templates de $REPO_VIC/templates/in-project/..."
  # Playwright config + tests
  if $INSTALL_PLAYWRIGHT; then
    cp -n "$REPO_VIC/templates/in-project/playwright/playwright.config.ts" ./ || echo "  playwright.config.ts já existe (mantido)"
    mkdir -p tests
    cp -rn "$REPO_VIC/templates/in-project/playwright/tests/"* tests/ || echo "  alguns testes já existem"
  fi
  # Axe wrapper
  if $INSTALL_PLAYWRIGHT; then
    cp -n "$REPO_VIC/templates/in-project/axe/a11y.spec.ts" tests/ || echo "  tests/a11y.spec.ts já existe"
  fi
  # Gremlins wrapper
  if $INSTALL_PLAYWRIGHT; then
    cp -n "$REPO_VIC/templates/in-project/gremlins/fuzz-gremlins.spec.ts" tests/ || echo "  tests/fuzz-gremlins.spec.ts já existe"
  fi
  # Sentry
  if $INSTALL_SENTRY; then
    cp -n "$REPO_VIC/templates/in-project/sentry/sentry.client.config.ts" ./ || echo "  sentry.client.config.ts já existe"
    cp -n "$REPO_VIC/templates/in-project/sentry/sentry.server.config.ts" ./ || echo "  sentry.server.config.ts já existe"
    cp -n "$REPO_VIC/templates/in-project/sentry/instrumentation.ts" ./ || echo "  instrumentation.ts já existe"
  fi
  # PostHog
  if $INSTALL_POSTHOG; then
    mkdir -p app/components
    cp -n "$REPO_VIC/templates/in-project/posthog/PostHogProvider.tsx" app/components/ || echo "  PostHogProvider.tsx já existe"
  fi
fi

if $INSTALL_CI; then
  echo "Copiando .github/workflows/validator-ci.yml..."
  mkdir -p .github/workflows
  cp -n "$REPO_VIC/templates/in-project/github-actions/.github/workflows/validator-ci.yml" .github/workflows/ || echo "  já existe"
fi

# Env vars
echo ""
echo "Adicionar em .env.local (dev) e Vercel dashboard (prod):"
[[ "$INSTALL_SENTRY" = true ]] && echo "  NEXT_PUBLIC_SENTRY_DSN=https://xxx@yyy.ingest.sentry.io/zzz"
[[ "$INSTALL_SENTRY" = true ]] && echo "  SENTRY_AUTH_TOKEN=sntrys_xxx"
[[ "$INSTALL_POSTHOG" = true ]] && echo "  NEXT_PUBLIC_POSTHOG_KEY=phc_xxx"
[[ "$INSTALL_POSTHOG" = true ]] && echo "  NEXT_PUBLIC_POSTHOG_HOST=https://us.i.posthog.com"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Instalação completa em $TARGET"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Próximos passos:"
echo "1. Configurar SaaS: Sentry Cloud + PostHog Cloud + CodeRabbit"
echo "2. Preencher .env.local com DSNs/keys"
echo "3. Editar app/layout.tsx pra montar PostHogProvider (ver docs/01)"
echo "4. Rodar: $PM playwright install --with-deps"
echo "5. Rodar: $PM playwright test tests/smoke"
echo "6. Commit + push"
echo "7. Editar $REPO_VIC/config/apps.yaml adicionando este app"
echo ""
echo "Consulte $REPO_VIC/docs/01-instalacao-em-aplicacoes.md pra detalhes."
