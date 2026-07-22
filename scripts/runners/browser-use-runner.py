#!/usr/bin/env python3
"""
browser-use-runner.py — Runner central Browser-Use REAL + LLM rotator multi-key.

Uso:
  python3 browser-use-runner.py --url URL [opts]
  python3 browser-use-runner.py --all              # todos apps do config/apps.yaml
  python3 browser-use-runner.py --url X --dry-run  # só plano, não executa

Env vars:
  GEMINI_KEYS=k1,k2,k3,k4,k5   (recomendado - rotator round-robin)
  GEMINI_API_KEY=k1            (fallback single-key)
  GROQ_KEYS=k1,k2              (secondary provider)
  GROQ_API_KEY=k1              (fallback)
  CEREBRAS_KEYS=k1             (tertiary)

Rotator: round-robin Gemini. Em 429/quota, avança pra próxima key.
Se todas Gemini esgotadas, tenta Groq → Cerebras.

Autor: Claudia · 2026-07-22 · spec 034/035/038 validador-vic
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Instale: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Instale: pip install requests", file=sys.stderr)
    sys.exit(1)


def load_apps_config() -> list[dict]:
    """Carrega config/apps.yaml"""
    config_path = Path(__file__).parent.parent.parent / "config" / "apps.yaml"
    if not config_path.exists():
        return []
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return data.get("apps", [])


def collect_keys() -> dict[str, list[str]]:
    """Coleta TODAS as chaves disponíveis por provider."""
    result = {"gemini": [], "groq": [], "cerebras": []}

    gemini = os.environ.get("GEMINI_KEYS", "").split(",")
    gemini = [k.strip() for k in gemini if k.strip()]
    if not gemini:
        single = os.environ.get("GEMINI_API_KEY", "").strip()
        if single:
            gemini = [single]
    result["gemini"] = gemini

    groq = os.environ.get("GROQ_KEYS", "").split(",")
    groq = [k.strip() for k in groq if k.strip()]
    if not groq:
        single_groq = os.environ.get("GROQ_API_KEY", "").strip()
        if single_groq:
            groq = [single_groq]
    result["groq"] = groq

    cerebras = os.environ.get("CEREBRAS_KEYS", "").split(",")
    cerebras = [k.strip() for k in cerebras if k.strip()]
    result["cerebras"] = cerebras

    return result


class KeyRotator:
    """Rotator round-robin de chaves LLM. Avança automaticamente em 429/quota."""
    def __init__(self, keys_by_provider: dict[str, list[str]]):
        self.keys = keys_by_provider
        self.idx = {p: 0 for p in keys_by_provider}
        self.exhausted = {p: set() for p in keys_by_provider}

    def next_key(self, provider: str = "gemini") -> tuple[str, str] | None:
        """Retorna próxima (provider, key). None se todas esgotadas."""
        keys = self.keys.get(provider, [])
        if not keys:
            for p in ("gemini", "groq", "cerebras"):
                if p != provider and self.keys.get(p):
                    return self.next_key(p)
            return None

        for _ in range(len(keys)):
            i = self.idx[provider] % len(keys)
            self.idx[provider] += 1
            if i not in self.exhausted[provider]:
                return (provider, keys[i])
        # Todas exhausted deste provider — tenta fallback
        for p in ("gemini", "groq", "cerebras"):
            if p != provider and self.keys.get(p):
                return self.next_key(p)
        return None

    def mark_exhausted(self, provider: str, key: str) -> None:
        """Marca chave como esgotada (429/quota)."""
        keys = self.keys.get(provider, [])
        for i, k in enumerate(keys):
            if k == key:
                self.exhausted[provider].add(i)
                break

    def summary(self) -> dict:
        return {
            "gemini_keys": len(self.keys.get("gemini", [])),
            "groq_keys": len(self.keys.get("groq", [])),
            "cerebras_keys": len(self.keys.get("cerebras", [])),
            "total_keys": sum(len(v) for v in self.keys.values()),
        }


def pick_llm() -> tuple[str, str] | None:
    """Compat: primeira chave disponível. Backend de dry_run_plan."""
    keys = collect_keys()
    for provider in ("gemini", "groq", "cerebras"):
        if keys[provider]:
            return (provider, keys[provider][0])
    return None


def fetch_sitemap_urls(sitemap_url: str, base_url: str, max_urls: int = 50) -> list[str]:
    """Puxa URLs de sitemap.xml. Fallback: só a URL base."""
    try:
        r = requests.get(sitemap_url, timeout=15)
        if r.status_code != 200:
            return [base_url]
        root = ET.fromstring(r.text)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [loc.text for loc in root.findall(".//sm:loc", ns)]
        if not urls:
            urls = [loc.text for loc in root.findall(".//loc")]
        return urls[:max_urls] if urls else [base_url]
    except Exception as err:
        print(f"[fetch_sitemap] falhou: {err}", file=sys.stderr)
        return [base_url]


def dry_run_plan(url: str, sitemap: str | None, objetivo: str, max_rotas: int) -> dict:
    """Emite plano sem executar. NUNCA expõe chave — só provider name + count."""
    keys = collect_keys()
    sitemap_url = sitemap or f"{url.rstrip('/')}/sitemap.xml"
    urls_sample = fetch_sitemap_urls(sitemap_url, url, max_urls=max_rotas)
    return {
        "modo": "dry-run",
        "url_base": url,
        "sitemap": sitemap_url,
        "objetivo": objetivo,
        "max_rotas": max_rotas,
        "rotas_descobertas": len(urls_sample),
        "primeiras_5_rotas": urls_sample[:5],
        "rotator_ativo": True,
        "gemini_keys": len(keys["gemini"]),
        "groq_keys": len(keys["groq"]),
        "cerebras_keys": len(keys["cerebras"]),
        "total_keys": sum(len(v) for v in keys.values()),
        "descricao": (
            f"Runner vai atacar {url}, ler {sitemap_url}, "
            f"visitar até {max_rotas} rotas com objetivo '{objetivo}'. "
            "Rotator multi-key ativo. Emite JSON com bugs candidatos."
        ),
    }


async def run_browser_use_real(url: str, sitemap: str, objetivo: str, max_rotas: int) -> dict:
    """Execução REAL Browser-Use por rota. Com rotator multi-key."""
    from browser_use import Agent, ChatGoogle
    from browser_use.browser import BrowserSession, BrowserProfile

    keys = collect_keys()
    rotator = KeyRotator(keys)
    summary = rotator.summary()
    if summary["total_keys"] == 0:
        return {"erro": "Sem chaves LLM (GEMINI_KEYS/GROQ_KEYS/CEREBRAS_KEYS/GEMINI_API_KEY/GROQ_API_KEY)"}

    browser_profile = BrowserProfile(
        headless=True,
        chromium_sandbox=False,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
    )
    urls = fetch_sitemap_urls(sitemap, url, max_urls=max_rotas)
    urls_atacar = urls[:max_rotas]

    started_at = datetime.now(timezone.utc).isoformat()
    t0 = time.time()
    bugs_reportados = []
    rotas_visitadas = 0
    retries_count = 0
    keys_used = set()

    for rota_url in urls_atacar:
        print(f"  → atacando {rota_url}", file=sys.stderr)
        task = (
            f"Vá para a URL {rota_url} e faça o seguinte: {objetivo}. "
            "Reporte em texto claro qualquer bug visível, erro de layout, "
            "botão que não funciona, formulário quebrado, texto que não faz sentido, "
            "ou qualquer coisa que pareça errado. Se tudo estiver OK, diga 'OK: nenhum bug visível'."
        )

        # Retry loop com key rotation em 429/quota
        max_key_tries = 5
        succeeded = False
        for attempt in range(max_key_tries):
            llm_pair = rotator.next_key("gemini")
            if not llm_pair:
                bugs_reportados.append({
                    "url": rota_url,
                    "descricao": "[runner] todas as chaves LLM esgotadas",
                    "tipo": "quota-esgotada",
                    "detectado_em": datetime.now(timezone.utc).isoformat(),
                })
                break
            provider, key = llm_pair
            keys_used.add(f"{provider}:{key[:8]}...")
            llm = ChatGoogle(model="gemini-2.5-flash", api_key=key)
            try:
                browser_session = BrowserSession(browser_profile=browser_profile)
                agent = Agent(task=task, llm=llm, browser_session=browser_session)
                result = await agent.run(max_steps=8)
                rotas_visitadas += 1
                final_answer = str(result.final_result()) if hasattr(result, "final_result") else str(result)
                if "OK: nenhum bug" not in final_answer[:80]:
                    bugs_reportados.append({
                        "url": rota_url,
                        "descricao": final_answer[:1500],
                        "detectado_em": datetime.now(timezone.utc).isoformat(),
                        "key_prefixo": f"{provider}:{key[:8]}...",
                    })
                succeeded = True
                time.sleep(2)
                break
            except Exception as err:
                err_str = str(err)
                is_quota = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "rate limit" in err_str.lower() or "quota" in err_str.lower()
                if is_quota:
                    rotator.mark_exhausted(provider, key)
                    retries_count += 1
                    print(f"    ⟳ 429 na key {key[:8]}...; tentando próxima (attempt {attempt+1}/{max_key_tries})", file=sys.stderr)
                    continue
                else:
                    print(f"    ✗ erro em {rota_url}: {err_str[:200]}", file=sys.stderr)
                    bugs_reportados.append({
                        "url": rota_url,
                        "descricao": f"[erro executando agent] {err_str[:800]}",
                        "detectado_em": datetime.now(timezone.utc).isoformat(),
                        "tipo": "erro-runner",
                    })
                    break

        if not succeeded and attempt == max_key_tries - 1:
            print(f"    ✗ esgotou {max_key_tries} tentativas em {rota_url}", file=sys.stderr)

    return {
        "app_url": url,
        "sitemap": sitemap,
        "objetivo": objetivo,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "duration_s": int(time.time() - t0),
        "rotator_ativo": True,
        "keys_summary": summary,
        "keys_usadas_count": len(keys_used),
        "retries_count": retries_count,
        "rotas_descobertas_no_sitemap": len(urls),
        "rotas_visitadas": rotas_visitadas,
        "bugs_reportados": bugs_reportados,
        "total_bugs": len(bugs_reportados),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Browser-Use runner central validador-vic")
    parser.add_argument("--url", help="URL do app-alvo (ou use --all)")
    parser.add_argument("--sitemap", help="URL do sitemap (default: URL/sitemap.xml)")
    parser.add_argument("--objetivo", default="navegue a página, tente clicar botões visíveis e reportar problemas de UX ou erros visíveis", help="Objetivo do agente LLM")
    parser.add_argument("--max-rotas", type=int, default=5, help="Máximo de rotas por rodada (padrão MVP: 5)")
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
            print(f"[{app['name']}] Atacando {url}...", file=sys.stderr)
            if args.dry_run:
                result = dry_run_plan(url, sitemap, args.objetivo, args.max_rotas)
            else:
                result = asyncio.run(run_browser_use_real(url, sitemap, args.objetivo, args.max_rotas))
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

    result = asyncio.run(run_browser_use_real(args.url, sitemap, args.objetivo, args.max_rotas))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Relatório: {args.output}")
    print(f"Total bugs candidatos: {result.get('total_bugs', 0)}")
    return 0 if "erro" not in result else 1


if __name__ == "__main__":
    sys.exit(main())
