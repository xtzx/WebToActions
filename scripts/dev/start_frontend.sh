#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/frontend"

cd "${FRONTEND_DIR}"
echo "Starting frontend dev server on http://127.0.0.1:5173 (split dev mode)..."
exec npm run dev -- --host 127.0.0.1 --port 5173
