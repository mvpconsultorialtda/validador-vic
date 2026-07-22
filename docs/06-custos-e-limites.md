# 06 · Custos e limites free tiers

Detalhamento de cada free tier, quando estoura, plano de migração.

## Overview

**Custo hoje (MVP academia com 5 apps):** **$0/mês permanente**.

Quando cada free tier estoura → plano de migração pra alternativa também grátis (self-host VPS) OR paga mínima.

## Detalhado por ferramenta

### Gemini API (LLM primário Browser-Use)

- **Tier grátis (2026):** 1500 requests/dia · 1M contexto · Gemini 2.5 Flash
- **Consumo estimado:** Browser-Use uma rodada nightly ~30-50 requests. Nightly em 5 apps × 30 req = 150 req/nightly. Cabe fácil.
- **Quando estoura:** rodadas manuais durante o dia OU >10 apps
- **Migração:** ativar `GROQ_KEYS` no `.env` → rotator troca automaticamente

### Groq API (fallback LLM)

- **Tier grátis:** 100k tokens/dia
- **Migração:** ativar `CEREBRAS_KEYS`

### Cerebras API (segundo fallback LLM)

- **Tier grátis:** 1M tokens/dia
- **Migração:** OpenRouter free pool → chaves rotacionadas anônimas

### Sentry Cloud Dev

- **Tier grátis:** 5000 errors/mês + **50 replays/mês** + 30 dias retenção + 1 user
- **Consumo estimado MVP:** 50-500 errors/mês nos primeiros usuários EducaHubPlay
- **Quando estoura:** ≥500 users ativos OR bug crítico em produção com replay gravando muito
- **Migração:** self-host **GlitchTip** no VPS Hostinger (1 container, ~2GB RAM, sabor Sentry API-compat)

### PostHog Cloud

- **Tier grátis:** 5000 recordings/mês + 100k errors/mês + 1M events/mês
- **Consumo estimado MVP:** ~1000 sessions/mês (usuários casuais EducaHubPlay)
- **Quando estoura:** ≥1500 sessions/mês
- **Migração:** self-host **OpenReplay** no VPS (~4GB RAM, Apache 2.0)

### CodeRabbit

- **Tier grátis:** unlimited public repos + **200 private reviews/mês**
- **Consumo estimado:** ~50-100 PRs/mês nos 5 apps privados
- **Quando estoura:** >200 PRs/mês private (improvável fase MVP)
- **Migração:** Pro $24/dev/mês OR **Ellipsis** flat $20/dev/mês (só GitHub)

### TestSprite

- **Tier grátis:** side projects
- **Consumo:** opcional bootstrap 30 dias
- **Quando pagar:** $69/mês Standard se ROI comprovado
- **Alternativa:** ficar só com Browser-Use (grátis permanente)

### GitHub Actions

- **Tier grátis (repo privado):** 2000 minutos/mês
- **Consumo estimado:** nightly ~15min × 30 dias × 5 apps = 2250 min. **Estouro leve.**
- **Migração:** repo `validador-vic` **público** → GH Actions ilimitado grátis
- **Alternativa:** rodar nightly em VPS cron (~$5/mês VPS já pago)

## Timeline realista de custos

| Fase | Usuários MVP | Ferramentas free tier | Custo mensal |
|---|---|---|---|
| **Mês 1-6** | 0-100 | Tudo | **$0** |
| **Mês 7-12** | 100-500 | Todos exceto Sentry Team ou GlitchTip self-host | **$0-26** |
| **Ano 2** | 500-5000 | Migra Sentry+PostHog pra self-host VPS existente | **$0** (VPS já pago) |
| **Ano 2+** | >5000 | Manter self-host + upgrade Chromatic se Storybook | **$0-179** |

## Anti-padrões custo

- ❌ Rodar Sentry self-host **na fase MVP** (22GB RAM real, 25+ containers — inviável)
- ❌ Pagar $69 TestSprite sem provar ROI em 30 dias
- ❌ CodeRabbit Pro ($24/dev/mês) sem estourar free tier
- ❌ Chromatic paid ($179/mês) sem Storybook ativo

## Regra de decisão pra escalar

**Só pagar quando:**
1. Free tier estourou por 2 meses consecutivos
2. Alternativa self-host requer setup >6h
3. Custo mensal < 1h teu trabalho valorizado

Exemplo: Sentry Team $26/mês vs GlitchTip self-host 6h setup + manutenção mensal 2h.  
Se sua hora vale >$20 → paga Sentry Team.  
Se estás em modo academia sem monetização → GlitchTip.

## Auditoria mensal de custos

Rotina no dia 1 de cada mês:

```bash
bash scripts/audit-costs.sh
```

Emite relatório:
```
Sentry: 3200 / 5000 errors mês (64%)
PostHog: 2100 / 5000 recordings (42%)
CodeRabbit: 87 / 200 reviews (44%)
Gemini: 45k / 45k req/dia (nunca perto)
GH Actions: 1800 / 2000 min (90% ⚠️)
```

Sinais de escalação:
- ≥ 80% em qualquer → mês seguinte prepara migração
- ≥ 95% → migra AGORA

## Total honesto pra você planejar

**Setup inicial:** 6-8h você (playbook A instala em 5 apps) + $0 custo direto.

**Manutenção mensal:** 30-60min (revisar nightly reports, aprovar baselines visuais, cancelar issues resolvidas).

**Custo pra sempre grátis:** $0 enquanto MVP.  
**Custo escalado (5k+ usuários):** $0-50/mês.  
**Custo enterprise (>50k usuários):** $200-500/mês (mas nesse ponto MVP virou negócio, orçamento diferente).
