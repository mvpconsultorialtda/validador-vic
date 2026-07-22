# 02 · Operação in-project — Playbook B

Como operar as libs **dentro do app-alvo** (após instalação via playbook A).

## Playwright — E2E determinístico

### Rodar suite local

```bash
cd ~/repositorios/educahubplay
pnpm playwright test                    # roda tudo
pnpm playwright test tests/smoke        # só smoke
pnpm playwright test --headed           # ver browser
pnpm playwright test --debug            # step-by-step
pnpm playwright show-report             # abre HTML report
```

### Escrever teste novo (via Claude Code + Playwright MCP)

No Claude Code (com Playwright MCP plugin instalado):

```
Cria teste Playwright pra fluxo: login → /quiz → clica primeiro card → responde 5 perguntas → verifica que ranking atualizou.
```

Claude Code + MCP navega o app real, coleta seletores robustos, emite arquivo `.spec.ts` em `tests/`. Você commita.

### Codegen manual (sem LLM)

```bash
pnpm playwright codegen https://educahubplay-omega.vercel.app
```

Grava sessão manual, emite código Playwright — cola em novo `.spec.ts`.

### Baseline visual

```bash
pnpm playwright test --update-snapshots  # aprova baseline nova
pnpm playwright test                     # compara contra baseline
```

Screenshots vão pra `tests/__snapshots__/`. Commita junto com o teste.

## @axe-core/playwright — A11y

Já vem chamado dentro do template Playwright (`tests/a11y.spec.ts`). Rodar:

```bash
pnpm playwright test tests/a11y
```

Ao falhar, emite JSON com violações WCAG 2.2 — cada nó DOM + regra violada. Fix baseia-se no report.

Rodar em produção (não só local):

```bash
BASE_URL=https://educahubplay-omega.vercel.app pnpm playwright test tests/a11y
```

## Gremlins.js — Fuzzing UI dentro do Playwright

Template `tests/fuzz-gremlins.spec.ts` já configurado — roda Gremlins por 3min em cada rota do sitemap.

```bash
pnpm playwright test tests/fuzz-gremlins
```

Ao terminar, Gremlins reporta:
- Nº de "gremlins" simulados (cliques/scrolls/keypress aleatórios)
- Nº de `console.error` capturados
- Screenshot no momento de cada erro

Falhas viram issues automaticamente (workflow GH Actions no template).

## fast-check — Property-based em hooks/reducers

Ficam em `tests/unit/*.test.ts` rodando com Vitest. Exemplo em `lib/quiz-engine/__tests__/scoring.property.test.ts` (template):

```typescript
import fc from 'fast-check';
import { scoreAnswer } from '../scoring';

test('scoreAnswer nunca retorna negativo', () => {
  fc.assert(fc.property(
    fc.record({
      question: fc.record({ points: fc.integer({ min: 0, max: 100 }) }),
      correct: fc.boolean(),
      timeSpent: fc.integer({ min: 0, max: 60000 }),
    }),
    ({ question, correct, timeSpent }) => {
      const score = scoreAnswer(question as any, correct, timeSpent);
      return score >= 0;
    }
  ));
});
```

Rodar:

```bash
pnpm test tests/unit
```

## Sentry SDK — capturar em prod

Sentry SDK captura auto:
- Uncaught exceptions
- Unhandled promise rejections
- Console errors (se configurado)

Capturar manual:

```typescript
import * as Sentry from "@sentry/nextjs";

try {
  // código arriscado
} catch (err) {
  Sentry.captureException(err);
}
```

Ver eventos em https://sentry.io/organizations/{org}/issues/.

Testar setup:

```typescript
Sentry.captureMessage("test do validador-vic");
```

Deve aparecer no dashboard em segundos.

## PostHog SDK — capturar sessions em prod

Provider já configurado no `app/layout.tsx` (template). Automaticamente:
- Grava sessions
- Trackeia pageviews
- Captura clicks + heatmaps

Capturar evento custom:

```typescript
import posthog from 'posthog-js';

posthog.capture('quiz_completed', {
  quiz_id: quiz.id,
  score: totalScore,
  duration_ms: elapsed,
});
```

Ver replays em https://us.posthog.com/project/{id}/replay.

## next-openapi-gen — gerar spec

```bash
pnpm openapi-gen                        # gera public/openapi.json
```

Automatizado no build (script `next build && openapi-gen` no `package.json` template).

Runner central `Schemathesis` puxa esse `openapi.json` via HTTP.

## sitemap.ts — dinâmico

Sitemap fica em `app/sitemap.ts`. Template canônico exporta função async lendo Firestore + estáticos. Ver template.

Testar:

```bash
curl https://educahubplay-omega.vercel.app/sitemap.xml
```

Deve listar todas URLs (rotas estáticas + dinâmicas).

## GitHub Actions — CI

Workflow template `.github/workflows/validator-ci.yml` roda em cada push/PR:

1. `pnpm install`
2. `pnpm build`
3. `pnpm playwright install --with-deps`
4. `pnpm playwright test` (Playwright + axe + Gremlins + property-based)

Report vira comentário no PR. Se falhar, PR block.

## Debug local com dev tools

- Sentry Dev overlay: aparece bottom-right em dev
- PostHog toolbar: aparece se logado
- Playwright inspector: `pnpm playwright test --debug`
- Gremlins visual: `--headed` mostra os cliques aleatórios

## Anti-padrões

- ❌ Rodar Playwright só localmente e não em CI (não pega drift entre máquinas)
- ❌ Ignorar Sentry warnings (source maps upload falho ⇒ stack traces inúteis em prod)
- ❌ Comitar `NEXT_PUBLIC_*` values sensíveis (não é sensível pra SDK, mas verifica)
- ❌ Rodar Gremlins fora de janela dev (3min de chaos random em prod = má ideia)
- ❌ Aprovar baseline visual sem olhar (regressão passa se você `--update-snapshots` cego)
