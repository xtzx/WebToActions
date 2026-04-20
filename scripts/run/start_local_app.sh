#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"
APP_HOST="${APP_HOST:-127.0.0.1}"
APP_PORT="${APP_PORT:-8000}"

if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3.11)"
else
  echo "Python 3.11+ not found. Create .venv or install python3.11 first." >&2
  exit 1
fi

cd "${FRONTEND_DIR}"
npm run build

export FRONTEND_STATIC_ENABLED=true
export FRONTEND_DIST_DIR="${FRONTEND_DIR}/dist"

cd "${BACKEND_DIR}"
exec "${PYTHON_BIN}" -m uvicorn app.main:app --host "${APP_HOST}" --port "${APP_PORT}"
