#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"

if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3.11)"
else
  echo "Python 3.11+ not found. Create .venv or install python3.11 first." >&2
  exit 1
fi

export FRONTEND_STATIC_ENABLED=false

cd "${BACKEND_DIR}"
exec "${PYTHON_BIN}" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
