# validador-vic

**Pipeline de validação usuário autônoma — plug-and-play, portátil, 100% grátis.**

Verify · Instrument · Cover

---

## O que é

`validador-vic` é o **runner central** de um pipeline de 6 camadas que valida aplicações web sem overlap — cada camada mata um tipo distinto de bug. Nasce da necessidade de garantir que features entreguem código funcional pro usuário final, não só código que passa `pnpm build`.

Aplicações-alvo (MVP): `EducaHubPlay`, `XequeMath`, `HQ-Lab`, `Lab Games`, `InovaEDUCACAO Landing`.

## Como funciona

3 padrões de integração combinados:

| Padrão | Vive onde | Ferramentas | Papel |
|---|---|---|---|
| **In-project** | Repo do app-alvo (devDep npm) | Playwright, @axe-core/playwright, Gremlins.js, Sentry SDK, PostHog SDK | Testa código do app; instalado localmente |
| **External runner** | ESTE repo (`validador-vic`) | Browser-Use, Schemathesis, Bruno CLI | Ataca a URL do app; não precisa acesso ao código |
| **SaaS observing** | Servidor externo (Sentry/PostHog/CodeRabbit/TestSprite) | — | Observa e reporta; conta única por serviço |

## Pipeline 6-camadas

```
Camada 1 · Discovery (sitemap + openapi)                    ← in-project
Camada 2 · Autonomous LLM (Browser-Use + TestSprite)        ← runner + SaaS
Camada 3 · Fuzzing (Gremlins.js + fast-check)               ← in-project
Camada 4 · E2E determinístico (Playwright + axe + toHaveScreenshot + Schemathesis + Bruno) ← in-project + runner
Camada 5 · Code review AI (CodeRabbit)                      ← SaaS
Camada 6 · Produção (Sentry + PostHog)                      ← in-project SDK + SaaS
```

Detalhes: [docs/00-arquitetura.md](docs/00-arquitetura.md)

## Quick-start

### Se você quer INSTALAR o pipeline num app-alvo

```bash
# clone este repo
git clone https://github.com/mvpconsultorialtda/validador-vic.git
cd validador-vic

# instala libs in-project + templates no app-alvo (interativo)
bash scripts/install-in-app.sh --target ~/repositorios/educahubplay
```

Depois disso, o app-alvo tem Playwright + axe + Gremlins + Sentry SDK + PostHog SDK configurados. Ver [docs/01-instalacao-em-aplicacoes.md](docs/01-instalacao-em-aplicacoes.md).

### Se você quer USAR o pipeline no app já instrumentado

**Do lado do app (in-project):**
```bash
cd ~/repositorios/educahubplay
pnpm test:e2e         # roda Playwright + axe
pnpm test:fuzz        # roda Gremlins.js dentro Playwright
```

**Do lado daqui (runner central):**
```bash
cd ~/repositorios/validador-vic
python3 scripts/runners/browser-use-runner.py --url https://educahubplay-omega.vercel.app
bash scripts/runners/schemathesis-runner.sh --spec https://educahubplay-omega.vercel.app/openapi.json
```

Detalhes: [docs/02-operacao-in-project.md](docs/02-operacao-in-project.md) e [docs/03-operacao-runner-central.md](docs/03-operacao-runner-central.md).

## Custo total

**$0/mês permanente** enquanto abaixo dos free tiers:
- LLMs: Gemini + Groq + Cerebras rotacionados (>3M tokens/dia grátis)
- Sentry Cloud Dev: 5k errors/mês grátis
- PostHog Cloud: 5k session recordings/mês grátis
- CodeRabbit: unlimited public repos + 200 private reviews/mês grátis
- TestSprite: free tier (side projects)
- GitHub Actions: 2000 min/mês grátis (repo privado) OR ilimitado (repo público)

Detalhes: [docs/06-custos-e-limites.md](docs/06-custos-e-limites.md)

## Portabilidade

Este repo roda em:
- **VPS Hostinger** (fase 2 — self-host GlitchTip/Bugsink quando SaaS estourarem)
- **Máquina local** (dev)
- **GitHub Actions runner** (padrão nightly)
- **Docker Compose** (opcional, isolamento)

Detalhes: [docs/05-portabilidade.md](docs/05-portabilidade.md)

## Metodologia de uso

Não é "instalei, esqueci". Existe processo claro pra **obter evidência de que o app está validado**:

1. Instalação (playbook A)
2. Configuração de SaaS (Sentry + PostHog + CodeRabbit + TestSprite)
3. Baseline manual (5 golden path tests escritos por você)
4. Nightly autônomo ligado (Browser-Use + Schemathesis via GH Actions)
5. Ciclo bug: Sentry alerta → PostHog replay → Playwright regression test → PR → fix

Detalhes: [docs/04-metodologia-evidencias.md](docs/04-metodologia-evidencias.md)

## Índice de documentação

- [00-arquitetura.md](docs/00-arquitetura.md) — pipeline 6-camadas, fluxo de dados, sem overlap
- [01-instalacao-em-aplicacoes.md](docs/01-instalacao-em-aplicacoes.md) — playbook A: como instalar in-project
- [02-operacao-in-project.md](docs/02-operacao-in-project.md) — playbook B: operar libs dentro do app
- [03-operacao-runner-central.md](docs/03-operacao-runner-central.md) — playbook C: operar runner central
- [04-metodologia-evidencias.md](docs/04-metodologia-evidencias.md) — quando fazer o quê, o que conta como evidência
- [05-portabilidade.md](docs/05-portabilidade.md) — VPS, máquina local, Docker
- [06-custos-e-limites.md](docs/06-custos-e-limites.md) — free tiers, quando cada um estoura, plano migração

## Origem

Criado em 2026-07-22 por Claudia (agente MVP) após decisão coletiva com Felipe.

Base de decisão: `agente_claudia/docs/pesquisa/2026-07-22-frameworks-comparativo-cruzado.md` (5106 palavras, 26 repos com stats reais, 11 SaaS com preço confirmado).

Spec canônica: `agente_claudia/specs/034-validador-vic-repo-portatil/`.
