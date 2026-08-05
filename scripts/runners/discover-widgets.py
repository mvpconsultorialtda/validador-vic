#!/usr/bin/env python3
"""
discover-widgets.py — descoberta DETERMINÍSTICA do widget-feedback.js
em um app Next.js / React.

Faz 4 coisas cruzando código estático (sem LLM, sem navegação):

  1. Localiza `public/widget-feedback.js` (arquivo canônico)
  2. Extrai versão via regex `Versao: X.Y.Z` no header
  3. Localiza referências ao script (`<script src=".../widget-feedback.js">`) em:
     - `app/layout.tsx` (Next.js App Router)
     - `pages/_app.tsx` / `pages/_document.tsx` (Next.js Pages Router)
     - `src/App.tsx` / `src/index.tsx` (react-scripts)
     - `public/index.html`
     - qualquer `.html` no repo
  4. Valida `data-project="X"` no script — deve estar presente e não vazio

Emite JSON estruturado. Falha com exit 1 se:
  - widget ausente
  - data-project ausente/vazio
  - versão abaixo de min_version (se passada)

Uso:
  python3 discover-widgets.py --target ~/repositorios/educahubplay
  python3 discover-widgets.py --target ~/repositorios/xequemath --json
  python3 discover-widgets.py --target ~/repositorios/hq-lab --min-version 1.4.0 --fail-on-missing

Autor: Claudia · 2026-08-04 · spec 055 validador-vic pipeline widget
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ─── Regex ────────────────────────────────────────────────────────────────
RE_VERSION = re.compile(r"Versao:\s*(\d+\.\d+\.\d+)", re.IGNORECASE)
RE_SCRIPT_TAG = re.compile(
    r'<script[^>]*src=["\'][^"\']*widget-feedback\.js[^"\']*["\'][^>]*>',
    re.IGNORECASE,
)
RE_DATA_PROJECT = re.compile(r'data-project=["\']([^"\']+)["\']')


def find_widget_file(target: Path) -> Path | None:
    """Localiza public/widget-feedback.js. Retorna None se não existe."""
    candidates = [
        target / "public" / "widget-feedback.js",
        target / "static" / "widget-feedback.js",
        target / "assets" / "widget-feedback.js",
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            return p
    return None


def extract_version(widget_path: Path) -> str | None:
    """Extrai `Versao: X.Y.Z` do header. Retorna None se não achou."""
    try:
        head = widget_path.read_text(encoding="utf-8", errors="replace")[:2000]
    except Exception:
        return None
    m = RE_VERSION.search(head)
    return m.group(1) if m else None


def find_script_references(target: Path) -> list[dict]:
    """Grep `<script src=".../widget-feedback.js">` em layouts + htmls.

    Retorna lista de {file, line, tag, data_project}.
    """
    references = []
    scan_globs = [
        "app/layout.tsx", "app/layout.js", "app/layout.jsx",
        "pages/_app.tsx", "pages/_app.js",
        "pages/_document.tsx", "pages/_document.js",
        "src/App.tsx", "src/App.js", "src/App.jsx",
        "src/index.tsx", "src/index.js",
        "public/index.html", "index.html",
    ]

    files_to_check: set[Path] = set()
    for g in scan_globs:
        p = target / g
        if p.exists():
            files_to_check.add(p)

    # Adiciona qualquer .html na raiz + public/
    for base in [target, target / "public"]:
        if base.exists():
            for html in base.glob("*.html"):
                files_to_check.add(html)

    for f in files_to_check:
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for line_num, line in enumerate(content.split("\n"), 1):
            for match in RE_SCRIPT_TAG.finditer(line):
                tag = match.group(0)
                dp = RE_DATA_PROJECT.search(tag)
                references.append({
                    "file": str(f.relative_to(target)),
                    "line": line_num,
                    "tag": tag[:200],
                    "data_project": dp.group(1) if dp else None,
                })

    return references


def parse_semver(v: str) -> tuple[int, int, int] | None:
    try:
        parts = v.split(".")
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        return None


def cross_analysis(
    widget_path: Path | None,
    version: str | None,
    references: list[dict],
    min_version: str | None,
) -> dict:
    """Cruza estado: widget presente? versão OK? referências corretas?"""
    result: dict = {
        "widget_present": widget_path is not None,
        "widget_path": str(widget_path) if widget_path else None,
        "widget_version": version,
        "references_count": len(references),
        "references": references,
        "issues": [],
    }

    if widget_path is None:
        result["issues"].append({"code": "widget_missing", "detail": "public/widget-feedback.js não existe"})
        return result

    if version is None:
        result["issues"].append({"code": "version_unreadable", "detail": "regex `Versao: X.Y.Z` não bateu no header"})

    if min_version and version:
        mv = parse_semver(min_version)
        cv = parse_semver(version)
        if mv and cv and cv < mv:
            result["issues"].append({
                "code": "version_below_min",
                "detail": f"widget está em {version}, mínimo exigido {min_version}",
            })

    if not references:
        result["issues"].append({
            "code": "no_references",
            "detail": "widget existe mas nenhum layout/html referencia — nunca carrega",
        })
    else:
        for ref in references:
            if not ref["data_project"]:
                result["issues"].append({
                    "code": "missing_data_project",
                    "detail": f"{ref['file']}:{ref['line']} — <script> sem data-project (grava em 'unknown')",
                })

    return result


def print_human(result: dict, target: Path) -> None:
    print(f"\n=== DISCOVER-WIDGETS — {target.name} ===")
    print(f"widget presente: {'✅' if result['widget_present'] else '❌'}")
    print(f"widget path:     {result['widget_path'] or '(none)'}")
    print(f"versão:          {result['widget_version'] or '(desconhecida)'}")
    print(f"referências:     {result['references_count']}")

    if result["references"]:
        print("\n  Referências encontradas:")
        for ref in result["references"]:
            dp = ref["data_project"] or "❌ (missing)"
            print(f"  ✓ {ref['file']}:{ref['line']}  data-project={dp}")

    if result["issues"]:
        print("\n🚨 ISSUES:")
        for iss in result["issues"]:
            print(f"  ❌ [{iss['code']}] {iss['detail']}")
    else:
        print("\n✅ Sem issues.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Descoberta determinística de widget-feedback")
    parser.add_argument("--target", type=Path, required=True, help="Path do repo app-alvo")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--min-version", type=str, help="Falha se widget < min_version (SemVer)")
    parser.add_argument("--fail-on-missing", action="store_true", help="Exit 1 se qualquer issue")
    parser.add_argument("--output", type=Path, help="Salvar JSON em arquivo")
    args = parser.parse_args()

    target = args.target.resolve()
    if not target.exists():
        print(f"ERRO: {target} não existe", file=sys.stderr)
        return 2

    widget_path = find_widget_file(target)
    version = extract_version(widget_path) if widget_path else None
    references = find_script_references(target)
    result = cross_analysis(widget_path, version, references, args.min_version)
    result["target"] = str(target)

    if args.output:
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"JSON salvo em: {args.output}", file=sys.stderr)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_human(result, target)

    if args.fail_on_missing and result["issues"]:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
