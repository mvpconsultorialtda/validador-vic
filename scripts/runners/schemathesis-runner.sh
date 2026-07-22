#!/usr/bin/env bash
# schemathesis-runner.sh — fuzzing OpenAPI contra app-alvo
#
# Uso:
#   bash schemathesis-runner.sh --spec URL_openapi.json [--base-url URL] [--output PATH]
#
# Requer: pip install schemathesis (versão 4+)
# Autor: Claudia · spec 034 validador-vic

set -euo pipefail

SPEC=""
BASE_URL=""
OUTPUT="reports/schemathesis.json"
CHECKS="all"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --spec) SPEC="$2"; shift 2 ;;
    --base-url) BASE_URL="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    --checks) CHECKS="$2"; shift 2 ;;
    --help)
      cat <<EOF
Uso: bash schemathesis-runner.sh --spec URL_openapi.json [opts]

Opções:
  --spec URL          URL do openapi.json (obrigatório)
  --base-url URL      URL base pra requests (default: extraído do spec)
  --output PATH       arquivo JSON de saída (default: reports/schemathesis.json)
  --checks NAMES      checks a rodar (default: all)
EOF
      exit 0
      ;;
    *) echo "opção desconhecida: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$SPEC" ]]; then
  echo "--spec obrigatório" >&2
  exit 2
fi

if ! command -v schemathesis &>/dev/null; then
  echo "Schemathesis não instalado. Rodar: pip install schemathesis" >&2
  exit 3
fi

mkdir -p "$(dirname "$OUTPUT")"

CMD="schemathesis run $SPEC --checks $CHECKS --report $OUTPUT"
if [[ -n "$BASE_URL" ]]; then
  CMD="$CMD --base-url $BASE_URL"
fi

echo "Executando: $CMD"
$CMD || {
  echo "Schemathesis retornou não-zero (bugs esperados). Ver $OUTPUT" >&2
  exit 0  # bugs achados NÃO são erro do script
}

echo "Relatório: $OUTPUT"
