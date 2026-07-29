#!/usr/bin/env bash
# lighthouse-runner.sh — Camada 7c do validador-vic · Performance + A11y + SEO + Best Practices
# Uso: ./scripts/runners/lighthouse-runner.sh --url URL --output PATH
# Autor: Claudia · 2026-07-28 · spec 054

set -euo pipefail

URL=""
OUTPUT="reports/lighthouse.json"
LH_THRESHOLD_PERF="${LH_THRESHOLD_PERF:-80}"
LH_THRESHOLD_A11Y="${LH_THRESHOLD_A11Y:-90}"
LH_THRESHOLD_BP="${LH_THRESHOLD_BP:-90}"
LH_THRESHOLD_SEO="${LH_THRESHOLD_SEO:-95}"
LH_THRESHOLD_LCP_MS="${LH_THRESHOLD_LCP_MS:-2500}"
LH_THRESHOLD_CLS="${LH_THRESHOLD_CLS:-0.1}"
LH_THRESHOLD_TBT_MS="${LH_THRESHOLD_TBT_MS:-200}"

while [[ $# -gt 0 ]]; do
  case $1 in
    --url) URL="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    *) echo "arg desconhecido: $1" >&2; exit 1 ;;
  esac
done

[[ -z "$URL" ]] && { echo "precisa --url URL" >&2; exit 1; }

mkdir -p "$(dirname "$OUTPUT")"

# CHROME_PATH — usar Chromium do Playwright (mais estável no ambiente)
if [[ -z "${CHROME_PATH:-}" ]]; then
  export CHROME_PATH=$(find ~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome -executable 2>/dev/null | sort -V | tail -1)
fi
[[ -z "$CHROME_PATH" ]] && { echo "[lh] Chromium não encontrado. Rode: python -m playwright install chromium" >&2; exit 1; }

lighthouse "$URL" \
  --output=json \
  --output-path="$OUTPUT.full" \
  --chrome-flags="--headless --no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage" \
  --only-categories=performance,accessibility,best-practices,seo \
  --preset=desktop \
  --quiet 2>&1 | tail -3 || true

[[ ! -s "$OUTPUT.full" ]] && { echo "[lh] Lighthouse não gerou output" >&2; exit 1; }

python3 - <<PYEOF
import json, sys
d = json.load(open("$OUTPUT.full"))
cat = d.get("categories", {})
audits = d.get("audits", {})

def score(k):
    s = cat.get(k, {}).get("score")
    return round(s * 100) if s is not None else None

def metric(k):
    return audits.get(k, {}).get("numericValue")

scores = {
    "performance": score("performance"),
    "accessibility": score("accessibility"),
    "best-practices": score("best-practices"),
    "seo": score("seo"),
}
metrics = {
    "LCP_ms": metric("largest-contentful-paint"),
    "CLS": metric("cumulative-layout-shift"),
    "TBT_ms": metric("total-blocking-time"),
    "FCP_ms": metric("first-contentful-paint"),
    "TTI_ms": metric("interactive"),
    "SI_ms": metric("speed-index"),
}
thresholds = {
    "performance": $LH_THRESHOLD_PERF, "accessibility": $LH_THRESHOLD_A11Y,
    "best-practices": $LH_THRESHOLD_BP, "seo": $LH_THRESHOLD_SEO,
    "LCP_ms": $LH_THRESHOLD_LCP_MS, "CLS": $LH_THRESHOLD_CLS, "TBT_ms": $LH_THRESHOLD_TBT_MS,
}
reasons = []
for k in ["performance", "accessibility", "best-practices", "seo"]:
    v = scores.get(k)
    if v is not None and v < thresholds[k]:
        reasons.append(f"{k}: {v} < {thresholds[k]}")
for k in ["LCP_ms", "TBT_ms"]:
    v = metrics.get(k)
    if v is not None and v > thresholds[k]:
        reasons.append(f"{k}: {round(v)} > {thresholds[k]}")
v = metrics.get("CLS")
if v is not None and v > thresholds["CLS"]:
    reasons.append(f"CLS: {v:.3f} > {thresholds['CLS']}")

verdict = "GO" if not reasons else "NO-GO"
result = {
    "url": "$URL",
    "timestamp": d.get("fetchTime"),
    "lighthouse_version": d.get("lighthouseVersion"),
    "scores": scores,
    "metrics": metrics,
    "thresholds": thresholds,
    "verdict": verdict,
    "reasons": reasons,
}
json.dump(result, open("$OUTPUT", "w"), indent=2, ensure_ascii=False)
print(f"  [{verdict}] $URL")
print(f"    scores: {scores}")
lcp = metrics['LCP_ms'] and round(metrics['LCP_ms'])
tbt = metrics['TBT_ms'] and round(metrics['TBT_ms'])
print(f"    metrics: LCP={lcp}ms CLS={metrics['CLS']:.3f} TBT={tbt}ms" if metrics['CLS'] is not None else f"    metrics: LCP={lcp}ms TBT={tbt}ms")
if reasons: print(f"    reasons: {', '.join(reasons)}")
PYEOF

rm -f "$OUTPUT.full"
echo "[lh] output: $OUTPUT"
