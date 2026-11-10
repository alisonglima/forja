#!/usr/bin/env bash
# Instala o Forja direto no sistema (sem Docker). Requer Python 3.9+, ffmpeg e Node 20+.
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ERRO: $PYTHON nao encontrado. Instale Python 3.9+." >&2
  exit 2
fi
if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  echo "ERRO: ffmpeg/ffprobe nao encontrados. Instale antes de continuar." >&2
  exit 2
fi
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "ERRO: Node.js/npm 20+ nao encontrados. Instale antes de continuar." >&2
  exit 2
fi

"$PYTHON" -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test]"

(
  cd remotion-template
  npm install --no-audit --no-fund
  npx remotion browser ensure
)

python -m forja --json doctor
