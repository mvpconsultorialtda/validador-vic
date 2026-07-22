# 05 · Portabilidade — VPS / máquina local / Docker / GH Actions

Este repo roda em **qualquer ambiente Unix com Python 3.11+, Node 20+ e Docker opcional**. Sem lock-in.

## Ambientes suportados

### GitHub Actions (padrão nightly)

Workflow `.github/workflows/nightly-validate.yml` roda em runner Microsoft grátis. Zero setup.

Requer secrets configurados em `Settings → Secrets and variables → Actions`:
- `GEMINI_KEYS`
- `GROQ_KEYS`
- `CEREBRAS_KEYS`
- `SENTRY_AUTH_TOKEN` (opcional — só se upload de source maps)

### VPS Hostinger (fase 2 — self-host)

Quando SaaS free tiers estourarem, migrar:

**Sentry → GlitchTip self-host:**
```bash
ssh vps-mvp
docker-compose -f /opt/glitchtip/docker-compose.yml up -d
# ~2GB RAM, 1 container + Postgres + Redis/Valkey
# DSN muda de sentry.io pra glitchtip.mvpconsultoria.com
```

**PostHog Cloud → OpenReplay self-host:**
```bash
ssh vps-mvp
docker-compose -f /opt/openreplay/docker-compose.yml up -d
# ~4GB RAM + storage bruto de videos
```

**Runner central (Browser-Use nightly):**
```bash
ssh vps-mvp
git clone https://github.com/mvpconsultorialtda/validador-vic.git
cd validador-vic
cp .env.example .env
# preencher chaves
sudo tee /etc/cron.d/validador-vic <<EOF
0 4 * * * claude cd /home/claude/validador-vic && bash scripts/nightly.sh
EOF
```

### Máquina local (dev)

```bash
git clone https://github.com/mvpconsultorialtda/validador-vic.git
cd validador-vic
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# preenche chaves
python3 scripts/runners/browser-use-runner.py --url https://X --dry-run  # sanity
```

Sem GitHub Actions dispondo, roda manualmente OR configura `crontab -e` local.

### Docker Compose (opcional, isolamento)

`docker-compose.yml` (template incluído):

```yaml
version: '3.8'
services:
  runner:
    build: .
    env_file: .env
    volumes:
      - ./reports:/app/reports
    command: python3 scripts/runners/browser-use-runner.py --all
```

Rodar:
```bash
docker-compose up
```

Vantagens Docker:
- Isolamento total do sistema hospedeiro
- Mesmo Chromium version em qualquer máquina
- Fácil migrar entre VPS

Desvantagens:
- +2GB imagem Docker
- Overhead ~5% CPU

## Requisitos mínimos

| Ambiente | CPU | RAM | Disco | Rede |
|---|---|---|---|---|
| GH Actions | runner MS default (2 vCPU) | 7GB | 14GB | ilimitado |
| VPS Hostinger nightly | 1 vCPU | 1.5GB | 5GB | ilimitado |
| Local dev | qualquer | 2GB livres | 500MB | qualquer |
| Docker | 2 vCPU | 2GB | 3GB imagem + reports | qualquer |

## Portabilidade de dados

Nenhum dado sensível fica em disco local. Estrutura:

```
validador-vic/
├── reports/                 ← gitignored, JSONs de saída
├── .venv/                   ← gitignored
├── .env                     ← gitignored (secrets)
├── bruno-collections/
│   └── */environments/*.local.bru   ← gitignored (tokens dev)
└── (resto tudo committed)
```

Backup: 
- Reports podem ser descartados (rodada nova regenera)
- Secrets ficam em GH Actions vars OR VPS `.env` — backup pessoal
- Colecões Bruno versionadas no git — clonagem restaura

## Migração entre ambientes

De GH Actions para VPS:
```bash
# no VPS
git clone https://github.com/mvpconsultorialtda/validador-vic.git
# copiar .env do local
scp .env vps-mvp:/opt/validador-vic/.env
# testar
ssh vps-mvp "cd /opt/validador-vic && python3 scripts/runners/browser-use-runner.py --url https://educahubplay-omega.vercel.app --dry-run"
# ativar cron
```

De VPS pra Docker:
```bash
docker-compose up -d
```

De Docker de volta pra GH Actions:
- Nada muda no repo — só desligar cron VPS
- GH Actions continua rodando o mesmo workflow

## Sem lock-in de serviços

Se qualquer SaaS abaixo mudar política ou preço, você tem substituto:

| Se cair… | Substitui por… |
|---|---|
| Gemini free tier | Groq / Cerebras / OpenRouter free |
| Sentry Cloud free | GlitchTip / Bugsink self-host VPS |
| PostHog Cloud free | OpenReplay self-host VPS |
| CodeRabbit | Ellipsis (só GitHub) |
| TestSprite | Browser-Use continua rodando |
| GitHub Actions | VPS cron |
