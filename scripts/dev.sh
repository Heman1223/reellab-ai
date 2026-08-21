#!/usr/bin/env bash
#
# ReelLab — run all three services.
#
#   bash scripts/dev.sh
#
# Backend on :4000, AI on :8000, frontend on :5173. Ctrl-C stops all three.
# Logs are interleaved; for readable output while debugging one service, run
# that service in its own terminal instead.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  printf '\033[33m!\033[0m No .env found. Run: bash scripts/setup.sh\n'
  exit 1
fi

# Locate the AI virtualenv, whichever layout it has.
if [ -x ai/.venv/bin/python ]; then
  VENV_PY="$ROOT/ai/.venv/bin/python"
elif [ -x ai/.venv/Scripts/python.exe ]; then
  VENV_PY="$ROOT/ai/.venv/Scripts/python.exe"
else
  printf '\033[33m!\033[0m No AI virtualenv. Run: bash scripts/setup.sh\n'
  exit 1
fi

PIDS=()

cleanup() {
  printf '\n\033[36m›\033[0m Stopping…\n'
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

printf '\033[36m›\033[0m AI service      → http://localhost:8000\n'
(cd ai && "$VENV_PY" -m uvicorn main:app --reload --port 8000) &
PIDS+=($!)

printf '\033[36m›\033[0m Backend         → http://localhost:4000/api/v1/health\n'
(cd backend && npm run dev) &
PIDS+=($!)

printf '\033[36m›\033[0m Frontend        → http://localhost:5173\n'
(cd frontend && npm run dev) &
PIDS+=($!)

printf '\nAll three running. Ctrl-C to stop.\n\n'
wait
