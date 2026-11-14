#!/usr/bin/env bash
# Start backend and frontend together, installing dependencies on first run. Ctrl+C stops both.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/backend/.venv"

if [ ! -x "$VENV/bin/uvicorn" ]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q -r "$ROOT/backend/requirements.txt"
fi

(cd "$ROOT/backend" && exec "$VENV/bin/uvicorn" app.main:app --reload --port 8000) &
BACK=$!
trap 'kill $BACK 2>/dev/null' EXIT

cd "$ROOT/frontend"
[ -d node_modules ] || npm install
npm run dev
