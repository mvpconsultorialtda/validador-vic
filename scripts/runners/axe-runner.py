#!/usr/bin/env python3
"""
axe-runner.py — Camada 7 do validador-vic · Accessibility scanner via axe-core.

Uso:
  python3 scripts/runners/axe-runner.py --url URL [opts]
  python3 scripts/runners/axe-runner.py --url URL --output reports/axe.json
  python3 scripts/runners/axe-runner.py --sitemap URL --output reports/axe/ (multi-rota)

Deps (instalar em .venv):
  pip install axe-playwright-python playwright
  python -m playwright install chromium

Output JSON estruturado por rota:
  {
    "url": "...",
    "timestamp": "...",
    "violations": [ {id, impact, description, help_url, nodes: []} ],
    "passes": N,
    "incomplete": N,
    "inapplicable": N,
    "score_summary": {
      "total_violations": N,
      "by_impact": {"critical": N, "serious": N, "moderate": N, "minor": N}
    }
  }

Threshold GO/NO-GO padrão (configurável via env AXE_THRESHOLD_CRITICAL / SERIOUS):
  critical=0 · serious=0 · moderate<=5 · minor<=15

Autor: Claudia · 2026-07-28 · spec 054 validador-vic HUB CENTRAL
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlparse
import xml.etree.ElementTree as ET


def run_axe_on_url(url: str, tags: list[str] | None = None) -> dict:
    """Roda axe contra 1 URL. Retorna dict com violations + summary."""
    try:
        from playwright.sync_api import sync_playwright
        from axe_playwright_python.sync_playwright import Axe
    except ImportError as e:
        print(f"[erro] Faltam deps. Rode: pip install axe-playwright-python playwright && python -m playwright install chromium\n{e}", file=sys.stderr)
        sys.exit(2)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=45000)
            # Aguarda hidratação client-side (Next.js SSR → CSR)
            page.wait_for_selector("main, body > div", timeout=15000)
            page.wait_for_timeout(3000)  # buffer pra client components montarem
            try:
                page.wait_for_function("document.fonts && document.fonts.ready", timeout=5000)
            except Exception:
                pass  # não bloqueia se fonts.ready timeoutar
        except Exception as e:
            print(f"[warn] navigation error em {url}: {e}", file=sys.stderr)

        axe = Axe()
        if tags:
            results = axe.run(page, context=None, options={"runOnly": {"type": "tag", "values": tags}})
        else:
            results = axe.run(page)
        raw = results.response
        browser.close()

    violations = raw.get("violations", [])
    passes = raw.get("passes", [])
    incomplete = raw.get("incomplete", [])
    inapplicable = raw.get("inapplicable", [])

    by_impact = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
    for v in violations:
        impact = v.get("impact") or "minor"
        by_impact[impact] = by_impact.get(impact, 0) + 1

    return {
        "url": url,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "violations": [
            {
                "id": v.get("id"),
                "impact": v.get("impact"),
                "description": v.get("description"),
                "help_url": v.get("helpUrl"),
                "nodes_count": len(v.get("nodes", [])),
                "nodes_sample": [
                    {"html": n.get("html", "")[:200], "target": n.get("target")}
                    for n in v.get("nodes", [])[:3]
                ],
            }
            for v in violations
        ],
        "passes_count": len(passes),
        "incomplete_count": len(incomplete),
        "inapplicable_count": len(inapplicable),
        "score_summary": {
            "total_violations": len(violations),
            "by_impact": by_impact,
        },
    }


def parse_sitemap(sitemap_url: str) -> list[str]:
    """Extrai URLs de sitemap.xml."""
    try:
        with urlopen(sitemap_url, timeout=15) as resp:
            data = resp.read()
        root = ET.fromstring(data)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        return [loc.text for loc in root.findall(".//sm:loc", ns) if loc.text]
    except Exception as e:
        print(f"[warn] sitemap parse falhou ({sitemap_url}): {e}", file=sys.stderr)
        return []


def check_thresholds(report: dict, thresholds: dict) -> tuple[bool, list[str]]:
    """Retorna (passa_go, motivos_falha)."""
    by_impact = report["score_summary"]["by_impact"]
    reasons = []
    for level, limit in thresholds.items():
        actual = by_impact.get(level, 0)
        if actual > limit:
            reasons.append(f"{level}: {actual} > {limit}")
    return (len(reasons) == 0), reasons


def main():
    parser = argparse.ArgumentParser(description="axe-core runner via Playwright Python")
    parser.add_argument("--url", help="URL única pra auditar")
    parser.add_argument("--sitemap", help="URL sitemap.xml — audita todas rotas")
    parser.add_argument("--output", default="reports/axe.json", help="Path output (arquivo se --url, pasta se --sitemap)")
    parser.add_argument("--tags", default="", help="Tags axe (vazio=todas rules; ex: 'wcag2aa,wcag21aa' filtra)")
    parser.add_argument("--threshold-critical", type=int, default=0)
    parser.add_argument("--threshold-serious", type=int, default=0)
    parser.add_argument("--threshold-moderate", type=int, default=5)
    parser.add_argument("--threshold-minor", type=int, default=15)
    parser.add_argument("--max-rotas", type=int, default=30, help="Limite rotas em modo --sitemap")
    args = parser.parse_args()

    if not args.url and not args.sitemap:
        print("Precisa --url OU --sitemap", file=sys.stderr)
        sys.exit(1)

    thresholds = {
        "critical": args.threshold_critical,
        "serious": args.threshold_serious,
        "moderate": args.threshold_moderate,
        "minor": args.threshold_minor,
    }
    tags = args.tags.split(",") if args.tags else None

    if args.url:
        print(f"[axe] rodando em {args.url}...")
        report = run_axe_on_url(args.url, tags=tags)
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        passed, reasons = check_thresholds(report, thresholds)
        print(f"[axe] output: {out_path}")
        print(f"[axe] violations: {report['score_summary']['total_violations']} · by_impact: {report['score_summary']['by_impact']}")
        print(f"[axe] verdict: {'GO' if passed else 'NO-GO — ' + ', '.join(reasons)}")
        sys.exit(0 if passed else 1)

    # Modo sitemap
    urls = parse_sitemap(args.sitemap)[: args.max_rotas]
    if not urls:
        print(f"[axe] sitemap sem URLs válidas", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    for url in urls:
        slug = urlparse(url).path.strip("/").replace("/", "_") or "root"
        try:
            report = run_axe_on_url(url, tags=tags)
            report_path = out_dir / f"axe-{slug}.json"
            report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            passed, reasons = check_thresholds(report, thresholds)
            summaries.append({
                "url": url,
                "slug": slug,
                "total_violations": report["score_summary"]["total_violations"],
                "by_impact": report["score_summary"]["by_impact"],
                "verdict": "GO" if passed else "NO-GO",
                "reasons": reasons,
                "report": str(report_path),
            })
            print(f"  [{summaries[-1]['verdict']}] {url} · violations={report['score_summary']['total_violations']}")
        except Exception as e:
            print(f"  [ERROR] {url} · {e}", file=sys.stderr)
            summaries.append({"url": url, "slug": slug, "error": str(e), "verdict": "ERROR"})

    summary_path = out_dir / "_summary.json"
    summary_path.write_text(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sitemap": args.sitemap,
        "thresholds": thresholds,
        "tags": tags,
        "total_urls": len(urls),
        "results": summaries,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[axe] summary: {summary_path}")

    fails = sum(1 for s in summaries if s.get("verdict") != "GO")
    print(f"[axe] total: {len(summaries)} · GO: {sum(1 for s in summaries if s.get('verdict') == 'GO')} · NO-GO/ERROR: {fails}")
    sys.exit(0 if fails == 0 else 1)


if __name__ == "__main__":
    main()
