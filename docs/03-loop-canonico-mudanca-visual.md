# 03 · Loop canônico pra mudança visual

**Origem:** falha sistêmica documentada 2026-07-28 (spec 053 v1→v4) — Claudia empilhou 4 iterações de fix visual reportando "OK" via grep de CSS, mas todas retornavam fundo LISO nos screenshots. Operador Felipe cobrou explícito: "por que você não valida antes de me dizer se deu certo?"

**Fact wiki motivador:** `mvp-wiki/wiki/facts/claudia/2026-07-28-brand-vic-manual-aplicado.md` + `agente_claudia/memory/feedback_validar_visual_antes_de_reportar.md`

## Loop obrigatório (7 passos)

```
1. Fazer mudança código  (edit .tsx/.css/.js)
2. Build local passa      (pnpm build)
3. Commit + push          (git push origin main OU merge branch)
4. Aguardar deploy Vercel (background monitor curl-until-200)
5. Screenshot Playwright  (headless → PNG salvo local)
6. LER o PNG eu mesma     (Read tool — Claude multimodal renderiza)
7. Decisão:
   - Visual OK → reportar 1 vez com screenshot inline
   - Visual NOT OK → iterar SILENCIOSAMENTE (voltar a 1)
```

## Anti-padrões proibidos

- ❌ Reportar "aplicado" após só grep de CSS/HTML no bundle prod
- ❌ Reportar "OK" após só HTTP 200 na rota
- ❌ Reportar "corrigido" após só build passar local
- ❌ Múltiplas iterações "corrigindo" sem screenshot lido entre cada
- ❌ Confessar erro visual e prometer "vou corrigir" sem provar em screenshot
- ❌ Racionalizar arquiteturalmente ("SVG procedural é melhor") sem consultar operador quando ele entregou asset específico

## Anti-padrões complementares (bugs mecânicos)

Cascata típica de bugs UI que só screenshot pega:

1. **Asset errado** — arquivo nome parece certo, conteúdo não é (ex: `canvas.png` = azul, não creme)
2. **Overlay CSS camufla textura** — `background-image: gradient + PNG` — gradient tapa PNG
3. **Elemento filho tem `background-color`** que cobre background do pai (ex: `<main class="bg-marca-bege">` cobre `<body class="brand-canvas">`)
4. **Hidration timing** — screenshot capturado antes de client component montar (esperar `page.wait_for_selector('main') + timeout(3000)`)

Screenshot lê o resultado final — grep vê apenas parte da história.

## Ferramenta padrão (validador-vic)

### Setup 1x (por ambiente)

```bash
cd validador-vic
python3 -m venv .venv
.venv/bin/pip install playwright axe-playwright-python
.venv/bin/python -m playwright install chromium
```

### Executar screenshot loop

```bash
# Screenshot rota individual
.venv/bin/python scripts/runners/screenshot-loop.py \
  --url https://educahubplay.vercel.app/cruzadinha/biologia \
  --output reports/screenshots/2026-07-28-cruzadinha-bio.png

# A11y check da mesma rota
.venv/bin/python scripts/runners/axe-runner.py \
  --url https://educahubplay.vercel.app/cruzadinha/biologia \
  --output reports/axe/2026-07-28-cruzadinha-bio.json
```

### Auditar site inteiro (baseline)

```bash
# Audit axe em todas rotas do sitemap
.venv/bin/python scripts/runners/axe-runner.py \
  --sitemap https://educahubplay.vercel.app/sitemap.xml \
  --output reports/axe-audit-YYYY-MM-DD/ \
  --max-rotas 30

# Diff visual (Playwright screenshot compare)
npx playwright test scripts/runners/visual-regression.spec.ts
```

## Threshold decisão

| Nível | O que faço |
|---|---|
| GO — 0 critical + 0 serious + moderate ≤5 | reporto ao operador com screenshot |
| WARN — critical=0 serious=0 mas moderate 6-15 | reporto + backlog issue |
| NO-GO — qualquer critical OU serious | iterar silenciosamente OU reverter |

## Precedente registrado

Baseline 2026-07-28 EducaHubPlay (16 rotas):
- 8 violations totais (3 critical + 5 moderate + 0 serious/minor)
- Detalhamento em `agente_claudia/docs/audit/2026-07-28-plataforma-baseline-axe/`
- 2 fixes aplicados (plotter labels + programe-o-vic heading-order)
- 3ª critical (Blockly/SurveyJS internals) — bug UPSTREAM, aceito como limitação conhecida

## Regra pessoal registrada (Claudia)

Salva em `agente_claudia/memory/feedback_validar_visual_antes_de_reportar.md`
com metadata `type=feedback` — auto-carrega toda sessão nova.

Toda regressão em bug UI que Felipe cobrar → releitura desta doc + do feedback antes de agir.
