# Templates in-project

Arquivos canônicos pra copiar pro app-alvo durante instalação (playbook A).

Uso automatizado: `bash scripts/install-in-app.sh --target /path/to/app`.

Uso manual: `cp -r templates/in-project/{ferramenta}/* /path/to/app/`.

## Estrutura

| Pasta | Conteúdo | Onde vai no app-alvo |
|---|---|---|
| `playwright/` | playwright.config.ts + tests/smoke + tsconfig test | raiz + `tests/` |
| `axe/` | tests/a11y.spec.ts | `tests/` |
| `gremlins/` | tests/fuzz-gremlins.spec.ts + gremlins helpers | `tests/` |
| `sentry/` | sentry.client.config.ts + sentry.server.config.ts + instrumentation.ts | raiz |
| `posthog/` | PostHogProvider.tsx | `app/components/` |
| `github-actions/` | `.github/workflows/validator-ci.yml` | `.github/workflows/` |

## Regra de convivência

Templates são **ponto de partida**, não gospel. Depois de instalar você customiza. Novos testes você escreve manualmente OU via Claude Code + Playwright MCP.

Se o app-alvo já tem `playwright.config.ts`, o script `install-in-app.sh` NÃO sobrescreve (usa `cp -n`). Você merge manual.
