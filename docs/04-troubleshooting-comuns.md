# 04 · Troubleshooting comuns

Bugs reais encontrados durante uso do validador-vic + como diagnosticar.

## axe-runner reporta 0 violations mas UI tem problemas

**Sintoma:** `axe-runner.py --url URL` retorna GO com 0 violations, mas visualmente o layout está errado.

**Causas comuns:**

1. **Filtro `--tags` muito restritivo** — default v1 era `wcag2aa,wcag21aa` filtrando pra 6 rules. Fix aplicado 2026-07-28 spec 054: default vazio (todas 90+ rules axe). Verificar via `passes_count` — se ≤ 10 no output, axe rodou parcial.

2. **Screenshot capturado antes da hidratação client-side** — Next.js SSR retorna wrapper vazio, componentes React ainda não montaram. Fix: `page.wait_for_selector('main') + wait_for_timeout(3000)` no runner.

3. **Contrast rules ficam em `incomplete`** — axe não decide contraste sozinho em texto sobre imagem/canvas. Usar Lighthouse (que calcula pixel-por-pixel) pra pegar contraste real. Camada 7c.

4. **axe não detecta problemas de DESIGN** (hierarquia visual pobre, densidade, delight) — só WCAG. Reclamação subjetiva de "legibilidade" vai além do escopo axe. Precisa juiz humano OR LLM-as-judge (ReLook pattern) OR screenshot manual review.

## Lighthouse falha com CHROME_PATH not set

**Sintoma:** `Runtime error: The CHROME_PATH environment variable must be set`

**Fix:** exportar Chromium do Playwright (mais estável):
```bash
export CHROME_PATH=$(find ~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome -executable 2>/dev/null | sort -V | tail -1)
```

Ou já está embutido no `lighthouse-runner.sh` (fix automático desde spec 054).

## Browser-Use retorna 403 PERMISSION_DENIED (Gemini)

**Sintoma:** logs mostram `403 Your project has been denied access` em TODAS as keys Gemini.

**Causa:** Google AI Studio bloqueou o projeto. Não é bug código.

**Fix:** operador (Felipe) renova/reativa keys em https://aistudio.google.com/apikey. Alternativa: usar Groq (`GROQ_KEYS` env) — o `browser-use-runner.py` já tem fallback multi-provider.

## Vercel serve 2 deploys diferentes no mesmo push

**Sintoma:** `git push origin main` deploya em 2 URLs Vercel — `app.vercel.app` e `app-alias.vercel.app` — com bundles diferentes.

**Causa:** repo GitHub linkado a 2 projetos Vercel separados no mesmo team. Vercel escuta o mesmo push e builda 2x com env vars possivelmente diferentes.

**Diagnose:**
```bash
cd app-repo
npx vercel inspect app-alias.vercel.app | grep -E "id|url|created"
```

**Fix:** consolidar 1 projeto Vercel. Deletar duplicado no dashboard (`vercel.com/team/settings`).

## Vercel prod deploy não atualiza pós push

**Sintoma:** commit + push + Vercel build success MAS URL prod continua servindo bundle antigo.

**Diagnose:** verificar aliases:
```bash
npx vercel alias ls | grep sua-url
```

Se alias apontar pra deployment antigo, promover manualmente:
```bash
npx vercel alias set <deployment-URL> <alias>
```

## Playwright timeout em rota lenta (Blockly, Mafs, PartyKit)

**Sintoma:** `page.goto(URL, wait_until="networkidle", timeout=45000)` timeout em rotas que fazem lazy load pesado.

**Fix:** aumentar timeout OU trocar wait_until:
- `wait_until="load"` — mais permissivo, não espera network idle
- `wait_until="domcontentloaded"` — mais rápido, só HTML

Ou aguardar seletor específico do componente lazy:
```python
page.wait_for_selector('canvas.blocklyMainBackground', timeout=15000)
```

## Screenshots idênticos byte-a-byte apesar de código mudou

**Sintoma:** `page.screenshot()` gera PNG com mesmo tamanho/MD5 depois de fix aplicado.

**Causas:**

1. **Vercel CDN cache** — asset servido do edge antigo. Fix: cache-bust via query string `?v=xyz`.
2. **Playwright browser cache** — mesma sessão puxa cache. Fix: `browser.new_context()` sem preserved storage.
3. **Deploy não promoveu** — verificar `vercel alias ls`.

## Textura background image invisível mesmo carregando

**Sintoma:** CSS bundle contém `background-image: url(/brand/textures/canvas.png)`, asset HTTP 200, mas fundo aparece liso.

**Causas (cascata comum spec 053 v1→v4):**

1. **Asset PNG errado** — nome sugere creme mas conteúdo é azul/preto. Verificar via `Read` do arquivo.
2. **Elemento filho tem `background-color` cobrindo textura do pai** — ex: `<main class="bg-marca-bege">` cobre `<body class="brand-canvas">`. Fix: aplicar textura no `<main>` OR remover bg-color de main.
3. **Gradient overlay camufla** — `linear-gradient() + url()` empilha gradient POR CIMA da textura. Fix: usar pseudo-elemento `::before` com `opacity` OR remover gradient.

## Aumentar cobertura axe pra rules específicas

Default (todas rules) cobre WCAG 2.1 AA/AAA + best practices. Pra scope mais restrito:

```bash
--tags wcag2a         # só WCAG 2.0 nível A
--tags wcag2aa        # WCAG 2.0 nível AA
--tags wcag21aa       # WCAG 2.1 AA (recomendado default)
--tags best-practice  # apenas best practices (não-WCAG)
--tags ""             # todas rules (default validador-vic)
```
