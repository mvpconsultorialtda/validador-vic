#!/usr/bin/env python3
"""
discover-routes.py — descoberta DETERMINÍSTICA de rotas de um app Next.js.

Faz 3 coisas cruzando código estático (sem LLM, sem navegação, 100% reproduzível):

  1. Varre `app/**/page.tsx` → rotas EXISTENTES no filesystem (verdade absoluta)
  2. Grep `href="/X"` + `router.push("/X"|/`X`)` → rotas REFERENCIADAS por botões/links
  3. Cruza:
     - INTERSEÇÃO: rotas existem E referenciadas (OK)
     - ÓRFÃS: existem mas nada aponta (rota criada e esquecida)
     - LINKS MORTOS: referenciadas mas rota não existe (BUG 404 pro usuário)

Emite JSON estruturado. Falha com exit 1 se detectar link morto.

Uso:
  python3 discover-routes.py --target ~/repositorios/educahubplay
  python3 discover-routes.py --target ~/repositorios/educahubplay --json
  python3 discover-routes.py --target ~/repositorios/educahubplay --fail-on-dead

Suporta: Next.js 13+ App Router (app/**/page.tsx). Next.js Pages Router (pages/**)
não suportado — se você tiver, avise.

Substitui o sitemap.ts manual — descobre TODA rota que existe ou é referenciada,
sem depender de humano lembrar de atualizar array.

Autor: Claudia · 2026-07-24 · spec 043 validador-vic
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Regex compilados
RE_LINK_HREF = re.compile(r'href=["\']([^"\']+)["\']')
RE_ROUTER_PUSH_STRING = re.compile(r'router\.push\(\s*["\']([^"\']+)["\']')
RE_ROUTER_PUSH_TEMPLATE = re.compile(r'router\.push\(\s*`([^`]+)`')
RE_REDIRECT = re.compile(r'redirect\(\s*["\']([^"\']+)["\']')


def is_internal_route(url: str) -> bool:
    """Filtra apenas rotas internas do app (não externas, não anchor, não asset)."""
    if not url.startswith("/"):
        return False
    if url.startswith("//"):  # protocol-relative
        return False
    if url.startswith("/_next") or url.startswith("/api/"):
        return False
    if "#" in url:
        url = url.split("#")[0]
    if url.startswith("/") and any(url.endswith(ext) for ext in (".ico", ".png", ".jpg", ".svg", ".woff", ".woff2", ".css", ".js")):
        return False
    return True


def normalize_route(url: str) -> str:
    """Remove querystring + trailing slash. Substitui template literals ${x} por [param]."""
    # Remove querystring
    if "?" in url:
        url = url.split("?")[0]
    # Remove trailing slash (exceto root)
    if url != "/" and url.endswith("/"):
        url = url.rstrip("/")
    # Template literals viram placeholder
    url = re.sub(r"\$\{[^}]+\}", "[param]", url)
    return url


def find_page_routes(app_dir: Path) -> set[str]:
    """
    Scan app/**/page.tsx (App Router). Cada page.tsx = 1 rota.
    Exemplos:
      app/page.tsx           → "/"
      app/quiz/page.tsx      → "/quiz"
      app/quiz/[quizId]/page.tsx → "/quiz/[param]"
    """
    routes = set()
    for page in app_dir.rglob("page.tsx"):
        rel = page.relative_to(app_dir).parent
        parts = rel.parts
        # Segmentos dinâmicos [x] viram [param] pra bater com references
        parts = tuple(re.sub(r"\[([^\]]+)\]", "[param]", p) for p in parts)
        # Ignora rotas em route groups (parênteses)
        parts = tuple(p for p in parts if not (p.startswith("(") and p.endswith(")")))
        route = "/" + "/".join(parts) if parts else "/"
        route = normalize_route(route)
        routes.add(route)
    return routes


def find_referenced_routes(target_dir: Path) -> dict[str, list[str]]:
    """
    Grep todos `href="/X"` + `router.push("/X"|/`X`)` + `redirect("/X")` no repo.
    Retorna dict {rota: [arquivo:linha, ...]}.
    """
    references: dict[str, list[str]] = {}
    scan_dirs = ["app", "components", "lib", "hooks", "src", "pages"]
    for d in scan_dirs:
        dir_path = target_dir / d
        if not dir_path.exists():
            continue
        for tsx in list(dir_path.rglob("*.tsx")) + list(dir_path.rglob("*.ts")):
            try:
                content = tsx.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for line_num, line in enumerate(content.split("\n"), 1):
                for regex in (RE_LINK_HREF, RE_ROUTER_PUSH_STRING, RE_ROUTER_PUSH_TEMPLATE, RE_REDIRECT):
                    for match in regex.finditer(line):
                        url = match.group(1)
                        if not is_internal_route(url):
                            continue
                        norm = normalize_route(url)
                        references.setdefault(norm, []).append(
                            f"{tsx.relative_to(target_dir)}:{line_num}"
                        )
    return references


def cross_analysis(existing: set[str], referenced: dict[str, list[str]]) -> dict:
    """Cruza existentes vs referenciadas. Categoriza."""
    referenced_set = set(referenced.keys())

    intersection = existing & referenced_set
    orfas = existing - referenced_set
    links_mortos = referenced_set - existing

    return {
        "total_existentes": len(existing),
        "total_referenciadas": len(referenced_set),
        "ok_intersection": sorted(intersection),
        "orfas_existem_sem_referencia": sorted(orfas),
        "links_mortos_referenciadas_sem_rota": [
            {"rota": rota, "referenciada_em": referenced[rota][:5]}
            for rota in sorted(links_mortos)
        ],
        "total_links_mortos": len(links_mortos),
    }


def print_human(result: dict, target: Path) -> None:
    print(f"\n=== DISCOVERY DETERMINÍSTICO — {target.name} ===")
    print(f"Rotas existentes (app/**/page.tsx):  {result['total_existentes']}")
    print(f"Rotas referenciadas (Link/push/redirect): {result['total_referenciadas']}")
    print(f"Links mortos (BUG 404 pro usuário):  {result['total_links_mortos']}\n")

    if result["links_mortos_referenciadas_sem_rota"]:
        print("🚨 LINKS MORTOS — arrumar urgente:")
        for lm in result["links_mortos_referenciadas_sem_rota"]:
            refs = ", ".join(lm["referenciada_em"][:3])
            print(f"  ❌ {lm['rota']:35s}  ← {refs}")
        print()

    if result["orfas_existem_sem_referencia"]:
        print("⚠️  Rotas ÓRFÃS (existem mas nada aponta — possível dead code):")
        for r in result["orfas_existem_sem_referencia"]:
            print(f"  ⚠  {r}")
        print()

    print(f"✅ OK ({len(result['ok_intersection'])} rotas existem + referenciadas):")
    for r in result["ok_intersection"]:
        print(f"  ✓ {r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover rotas determinístico Next.js")
    parser.add_argument("--target", type=Path, required=True, help="Path do repo app-alvo")
    parser.add_argument("--json", action="store_true", help="Output JSON em vez de humano")
    parser.add_argument("--fail-on-dead", action="store_true", help="Exit 1 se detectar link morto")
    parser.add_argument("--output", type=Path, help="Salvar JSON em arquivo")
    args = parser.parse_args()

    target = args.target.resolve()
    app_dir = target / "app"
    if not app_dir.exists():
        print(f"ERRO: {app_dir} não existe (não é Next.js App Router?)", file=sys.stderr)
        return 2

    existing = find_page_routes(app_dir)
    referenced = find_referenced_routes(target)
    result = cross_analysis(existing, referenced)
    result["target"] = str(target)

    if args.output:
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"JSON salvo em: {args.output}", file=sys.stderr)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_human(result, target)

    if args.fail_on_dead and result["total_links_mortos"] > 0:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
