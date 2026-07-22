# 04 · Metodologia — quando fazer o quê, o que conta como evidência

Ferramentas instaladas ≠ app validado. A validação vem do **processo de uso**. Este documento é o "manual do médico" — qual exame pedir em qual situação e o que o resultado significa.

## Princípio fundador

**"Objetivo fechado" só existe quando existe evidência independente.** Não basta:
- ✋ Você rodar Playwright local uma vez
- ✋ Sentry não ter erros nas primeiras 24h
- ✋ Você clicar "funcionou pra mim"

Evidência aceita:
- ✅ CI verde em 3 runs consecutivos independentes
- ✅ Nightly Browser-Use sem bug novo em 7 dias
- ✅ Zero errors no Sentry em N usuários reais (não zero em 0 usuários)
- ✅ PostHog session replay confirma golden path completa em 5 sessions distintas
- ✅ CodeRabbit passou todos os PRs sem block em janela de 7 dias

## Ciclo canônico de uso

### Ciclo A — Deploy de feature nova

```
1. Você escreve código
2. abre PR
3. camada 5 (CodeRabbit) revisa auto        ← MTTR bug semântico: 5min
4. camada 4 (Playwright + axe + Schemathesis) roda auto   ← MTTR bug regressão: 15min
5. você merge se tudo verde
6. deploy prod auto (Vercel)
7. camada 6 (Sentry + PostHog) começa a observar em prod
8. camada 2 (Browser-Use nightly) valida amanhã 04:00 BRT
```

Evidências geradas:
- CodeRabbit thread no PR (permanent record)
- Playwright report HTML no workflow artifact
- Sentry + PostHog dashboards (primeiras 24h)
- Nightly Browser-Use report JSON (dia seguinte)

### Ciclo B — Bug reportado por usuário real

```
1. Sentry alerta                                              ← T+0
2. Você abre PostHog session replay do mesmo user_id           ← T+2min
3. Reproduz bug local no dev                                   ← T+5min
4. Invoca Claude Code + Playwright MCP: "gera regression test  ← T+10min
   pro cenário do Sentry event #xxx"
5. Playwright MCP gera .spec.ts que falha reproduzindo bug     ← T+15min
6. Você corrige código
7. Roda .spec.ts → verde                                       ← T+30min
8. PR → CodeRabbit + camada 4 rodam                            ← T+45min
9. Merge → deploy → prod
10. Sentry para de receber esse erro                           ← evidência
```

**MTTR alvo: <2h do usuário reportar ao fix em prod.** Sem session replay, MTTR sobe pra 6-24h (dev adivinhando).

### Ciclo C — Nightly autônomo (independente de dev)

```
04:00 BRT · GH Actions dispara
├── Browser-Use ataca cada app do apps.yaml
├── Schemathesis fuzza cada openapi.json
├── Bruno roda smoke tests
└── Consolida relatório

Se bug novo detectado → cria issue GitHub auto
Se erro Sentry novo desde ontem → cria issue GitHub auto
Se PostHog session recording com error → linka no issue

Você acorda, vê issues criadas de madrugada.
```

Evidência gerada: **issues automatizadas com anexos JSON/screenshot** — não é palpite, é replayable.

## O que fazer em cada situação

### "Acabei uma feature nova. Como sei que ela funciona?"

Ordem canônica:
1. **Ciclo A** completo — PR + CodeRabbit + Playwright CI verdes
2. Escreva **1 teste Playwright cobrindo golden path** da feature (senão nightly Browser-Use não sabe testar)
3. Nightly do dia seguinte: se Browser-Use não achou nada + Sentry silencioso → **evidência primária**
4. 7 dias sem regressão em qualquer camada → **evidência secundária de estabilidade**

### "Refactorei algo. Quebrei?"

Ordem canônica:
1. Playwright suite completa passa local (`pnpm playwright test`)
2. PR → CodeRabbit + Playwright CI
3. Deploy → Sentry 24h em silêncio nas rotas afetadas
4. Compara PostHog "eventos por rota" com semana anterior — se despencou 50%, feature pode ter quebrado silencioso

### "Vou lançar pra usuários reais pela primeira vez"

Ordem canônica:
1. Baseline Sentry + PostHog vazio (sem contaminação)
2. Nightly Browser-Use rodou 3 vezes seguidas sem novo bug
3. TestSprite (bootstrap) rodou uma vez — se compra os $69/mês, roda até nightly Browser-Use validar sozinho
4. **Você navega o app manualmente 30min** — nada substitui isso pra sanity check
5. Beta com 5-10 usuários conhecidos primeiro (não abre pra público)
6. Monitorar Sentry + PostHog por 48h antes de escalar

### "Bug esporádico que não consigo reproduzir"

Ordem canônica:
1. PostHog session replay → filtra por session que teve error
2. Reproduz o cenário exato
3. Se ainda não reproduz local: gera Playwright test com Playwright MCP consumindo breadcrumbs Sentry como contexto
4. Test que reproduz é a evidência — ele fica na suite permanente

## O que conta como "não validado"

Zero desses cenários passa validação:
- ❌ CI verde em 1 run só (pode ser sorte)
- ❌ Sentry silencioso em 0 usuários (não observou nada porque não teve ninguém)
- ❌ "Eu cliquei e funcionou" sem replay gravado
- ❌ Playwright test cobrindo só o happy path
- ❌ Cobertura de teste alta (linhas cobertas) sem testar interação real

## Ritmo semanal recomendado

| Dia | Atividade | Duração |
|---|---|---|
| Segunda | Revisar nightly reports do fim-de-semana | 15min |
| Diariamente | Verificar Sentry + PostHog dashboard antes de codar | 5min |
| Sexta | Rodar `run-all.sh --app X` completo local em cada app | 30min |
| Sexta | Revisar CodeRabbit summary da semana | 10min |
| 1x/mês | Baseline visual (aprovar snapshots que mudaram) | 30min |
| 1x/mês | Auditar apps.yaml (rotas novas cadastradas?) | 10min |

## Escalação — quando parar de confiar

Sinais de que o pipeline está degradando:
- Nightly Browser-Use passa >70% do tempo sem achar nada em 30 dias → objetivo muito genérico, refinar
- Sentry recebe erros mas ninguém trata > 7 dias → alerts mal configurados
- PostHog storage baixo mas free tier estourando → filtrar sessions bot antes de gravar
- Playwright suite roda >20min em CI → dividir em shards paralelas
- CodeRabbit vira ruído (>10 comentários por PR) → refinar `.coderabbit.yml`

Cada um tem seção de fix em `docs/06-custos-e-limites.md`.
