#!/usr/bin/env python3
"""
browser-use-runner.py — Runner central Browser-Use + LLM rotator free tier.

Uso:
  python3 browser-use-runner.py --url URL [opts]
  python3 browser-use-runner.py --all              # todos apps do config/apps.yaml
  python3 browser-use-runner.py --url X --dry-run  # só plano, não executa

Env vars obrigatórias (uma delas):
  GEMINI_KEYS=k1,k2,k3
  GROQ_KEYS=k1,k2
  CEREBRAS_KEYS=k1

Ordem de tentativa LLM: Gemini → Groq → Cerebras → falha.

Autor: Claudia · 2026-07-22 · spec 034 validador-vic
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Instale: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def load_apps_config() -> list[dict]:
    """Carrega config/apps.yaml"""
    config_path = Path(__file__).parent.parent.parent / "config" / "apps.yaml"
    if not config_path.exists():
        return []
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return data.get("apps", [])


def pick_llm() -> tuple[str, str] | None:
    """Escolhe LLM provider baseado em chaves disponíveis. Retorna (provider, key)."""
    gemini = os.environ.get("GEMINI_KEYS", "").split(",")
    gemini = [k.strip() for k in gemini if k.strip()]
    if gemini:
        return ("gemini", gemini[0])
    groq = os.environ.get("GROQ_KEYS", "").split(",")
    groq = [k.strip() for k in groq if k.strip()]
    if groq:
        return ("groq", groq[0])
    cerebras = os.environ.get("CEREBRAS_KEYS", "").split(",")
    cerebras = [k.strip() for k in cerebras if k.strip()]
    if cerebras:
        return ("cerebras", cerebras[0])
    return None


def dry_run_plan(url: str, sitemap: str | None, objetivo: str, max_rotas: int) -> dict:
    """Emite plano sem executar. NUNCA expõe chave — só provider name."""
    llm = pick_llm()
    provider = llm[0] if llm else "NENHUM (configure GEMINI_KEYS/GROQ_KEYS/CEREBRAS_KEYS)"
    return {
        "modo": "dry-run",
        "url_base": url,
        "sitemap": sitemap,
        "objetivo": objetivo,
        "max_rotas": max_rotas,
        "descricao": (
            f"Runner vai atacar {url}, ler {sitemap or url + '/sitemap.xml'}, "
            f"visitar até {max_rotas} rotas com objetivo '{objetivo}'. "
            "Emite JSON com bugs candidatos."
        ),
        "llm_provider_selecionado": provider,
    }


def run_browser_use(url: str, sitemap: str, objetivo: str, max_rotas: int, output: Path) -> dict:
    """
    Placeholder pra execução real. Instalação: pip install browser-use.

    Nota: por enquanto emite structure JSON de output esperada.
    Integração real com biblioteca browser-use na próxima iteração (spec 035
    quando validar EducaHubPlay com passe autônomo real).
    """
    llm = pick_llm()
    if not llm:
        return {
            "erro": "Sem chaves LLM configuradas — configure GEMINI_KEYS, GROQ_KEYS ou CEREBRAS_KEYS",
            "provider_tentado": None,
        }

    provider, _key = llm  # nao expor _key em log/output
    started_at = datetime.now(timezone.utc).isoformat()
    time.sleep(1)  # placeholder — real execution na spec 035

    return {
        "app_url": url,
        "sitemap": sitemap,
        "objetivo": objetivo,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "duration_s": 1,
        "llm_provider": provider,
        "rotas_visitadas": 0,
        "bugs_reportados": [],
        "status": "placeholder — real execution TODO spec 035",
        "next_step": (
            "Instalar pip install browser-use + configurar LangChain wrapper Gemini "
            "+ inicializar Agent com objetivo. Ver docs/03-operacao-runner-central.md."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Browser-Use runner central validador-vic")
    parser.add_argument("--url", help="URL do app-alvo (ou use --all)")
    parser.add_argument("--sitemap", help="URL do sitemap (default: URL/sitemap.xml)")
    parser.add_argument("--objetivo", default="navegue todas as rotas, tente quebrar formulários, reporte bugs visíveis", help="Objetivo do agente LLM")
    parser.add_argument("--max-rotas", type=int, default=20, help="Máximo de rotas por rodada")
    parser.add_argument("--output", type=Path, default=Path("reports/browser-use.json"), help="Path do JSON de saída")
    parser.add_argument("--all", action="store_true", help="Rodar contra todos os apps do config/apps.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Só emite plano, não executa")
    args = parser.parse_args()

    if args.all:
        apps = load_apps_config()
        if not apps:
            print("Nenhum app em config/apps.yaml", file=sys.stderr)
            return 1
        results = []
        for app in apps:
            url = app["url"]
            sitemap = app.get("sitemap", f"{url}/sitemap.xml")
            print(f"[{app['name']}] Atacando {url}...")
            if args.dry_run:
                result = dry_run_plan(url, sitemap, args.objetivo, args.max_rotas)
            else:
                result = run_browser_use(url, sitemap, args.objetivo, args.max_rotas, args.output)
            result["app_name"] = app["name"]
            results.append(result)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"apps": results}, indent=2, ensure_ascii=False))
        print(f"Relatório: {args.output}")
        return 0

    if not args.url:
        parser.error("--url ou --all obrigatório")

    sitemap = args.sitemap or f"{args.url.rstrip('/')}/sitemap.xml"
    if args.dry_run:
        result = dry_run_plan(args.url, sitemap, args.objetivo, args.max_rotas)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    result = run_browser_use(args.url, sitemap, args.objetivo, args.max_rotas, args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Relatório: {args.output}")
    return 0 if "erro" not in result else 1


if __name__ == "__main__":
    sys.exit(main())
