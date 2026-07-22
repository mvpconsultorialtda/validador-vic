# 03 · Operação runner central — Playbook C

Como operar as ferramentas **daqui do repo validador-vic** apontando pros apps-alvo.

## Browser-Use — exploração autônoma LLM

Script `scripts/runners/browser-use-runner.py`.

### Preparação

```bash
cd validador-vic
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Chaves LLM grátis em `.env`:

```env
GEMINI_KEYS=key1,key2,key3          # https://aistudio.google.com/apikey
GROQ_KEYS=gsk_xxx                    # https://console.groq.com
CEREBRAS_KEYS=csk-xxx                # https://cloud.cerebras.ai
```

### Rodar contra 1 app

```bash
python3 scripts/runners/browser-use-runner.py \
  --url https://educahubplay-omega.vercel.app \
  --sitemap https://educahubplay-omega.vercel.app/sitemap.xml \
  --objetivo "navegue todas as rotas, tente quebrar formulários, reporte bugs visíveis" \
  --max-rotas 20 \
  --output relatorio-educahubplay.json
```

Ao terminar (~15min), emite JSON tipo:

```json
{
  "app": "educahubplay",
  "started_at": "2026-07-22T04:00:00Z",
  "duration_s": 892,
  "rotas_visitadas": 20,
  "bugs_reportados": [
    {
      "url": "/duelo/xxxxxxxx-fake",
      "categoria": "error-handling",
      "severidade": "media",
      "descricao": "Rota mostra 'Carregando duelo…' indefinidamente ao invés de 404 quando duelId inválido",
      "steps": ["...", "..."],
      "screenshot_base64": "..."
    }
  ]
}
```

### Rodar contra todos os apps

```bash
python3 scripts/runners/browser-use-runner.py --all
```

Lê `config/apps.yaml`, roda sequencial (paraliza se `--parallel 3`).

### Dry-run

```bash
python3 scripts/runners/browser-use-runner.py --url https://xxx --dry-run
```

Não executa — só emite plano de ataque (quais rotas, quais objetivos, ordem).

## Schemathesis — fuzzing OpenAPI

Script `scripts/runners/schemathesis-runner.sh`.

```bash
bash scripts/runners/schemathesis-runner.sh \
  --spec https://educahubplay-omega.vercel.app/openapi.json \
  --base-url https://educahubplay-omega.vercel.app \
  --output relatorio-schemathesis-educahubplay.json
```

Roda property-based fuzzing contra cada endpoint definido no OpenAPI:
- Gera inputs random válidos por schema
- Verifica que status codes batem com spec
- Detecta 500 escondido, campos aceitos indevidamente, etc.

Auth Firebase: usar `--header "Authorization: Bearer $DEV_TOKEN"`.

## Bruno CLI — explorar APIs manualmente

Colecões em `bruno-collections/{app}/`. Exemplo:

```
bruno-collections/
  educahubplay/
    environments/
      prod.bru
      dev.bru
      dev.local.bru       ← gitignored, tokens
    api/
      chat/POST-chat.bru
      duelos/POST-criar.bru
      ...
```

Rodar:

```bash
cd bruno-collections/educahubplay
bruno run api/chat/POST-chat.bru --env dev
```

Ou tudo:

```bash
bruno run . --env dev
```

Bruno Desktop app (GUI): abre a pasta `bruno-collections/educahubplay/` — usa a mesma versão.

## Playwright MCP — dentro do Claude Code

Não roda daqui. Roda no seu Claude Code local com plugin instalado:

```
No Claude Code:
/plugin install playwright-mcp
```

Depois qualquer conversa pode invocar:

```
Cria teste Playwright pra fluxo X. Navegue no app https://educahubplay-omega.vercel.app.
```

Playwright MCP + Claude Code navegam ao vivo, coletam seletores, geram `.spec.ts`.

Output vai pro repo do app (não daqui) — via git.

## TestSprite — bootstrap opcional

Dashboard TestSprite: https://testsprite.com

Add project → paste URL → TestSprite roda auto. Não precisa código daqui — é 100% SaaS.

Free tier útil pra:
- Rodar em paralelo com Browser-Use nos primeiros 30 dias
- Comparar quais bugs cada um pega

Se TestSprite pega ≥3 bugs que Browser-Use não pega → paga $69/mês, mantém ambos.

## GitHub Actions — nightly automatizado

`.github/workflows/nightly-validate.yml` roda cron 04:00 BRT (07:00 UTC):

```yaml
on:
  schedule:
    - cron: '0 7 * * *'   # 04:00 BRT
  workflow_dispatch:       # trigger manual OK
```

Jobs:
1. `browser-use-all-apps` — matriz por app do `apps.yaml`
2. `schemathesis-all-apps` — matriz por app
3. `bruno-smoke-tests` — coleção de smoke por app
4. `consolidate-report` — merge JSONs em relatório diário
5. `notify` — cria issue GitHub OR envia Slack (opcional)

Ver:

```bash
gh workflow view nightly-validate.yml
gh run list --workflow=nightly-validate.yml
```

## Rodar tudo de uma vez local

```bash
bash scripts/run-all.sh --app educahubplay
```

Executa Browser-Use + Schemathesis + Bruno em sequência local. ~30min por app.

## Anti-padrões

- ❌ Rodar Browser-Use sem `--max-rotas` (roda em todas as 47 rotas + subrotas = LLM quota estourada)
- ❌ Commitar `.env` (secrets vazam)
- ❌ Commitar `.venv/` (bloat repo)
- ❌ Objetivo Browser-Use vago tipo "teste" (LLM entra em loop → custo)
- ❌ Rodar Schemathesis contra `--base-url` de produção sem auth adequada (pode disparar side effects)
