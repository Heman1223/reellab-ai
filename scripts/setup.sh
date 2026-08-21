#!/usr/bin/env bash
#
# ReelLab — one-time setup.
#
#   bash scripts/setup.sh
#
# Installs all three apps' dependencies and creates .env from the template.
# Safe to re-run. Windows users: run this from Git Bash, or follow the manual
# steps in the root README.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

info() { printf '\033[36m›\033[0m %s\n' "$1"; }
warn() { printf '\033[33m!\033[0m %s\n' "$1"; }

# --- .env --------------------------------------------------------------------
if [ -f .env ]; then
  info ".env already exists — leaving it alone."
else
  cp .env.example .env
  info "Created .env from .env.example."
  warn "AI_PROVIDER is 'mock'. Everything runs on fixtures until you set a real key."
fi

mkdir -p uploads logs

# --- backend -----------------------------------------------------------------
info "Installing backend dependencies…"
(cd backend && npm install --no-audit --no-fund)

# --- frontend ----------------------------------------------------------------
info "Installing frontend dependencies…"
(cd frontend && npm install --no-audit --no-fund)

# --- ai ----------------------------------------------------------------------
PYTHON_BIN="${PYTHON_BIN:-python3}"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || PYTHON_BIN=python

info "Setting up the AI service virtualenv…"
(
  cd ai
  [ -d .venv ] || "$PYTHON_BIN" -m venv .venv

  # venv layout differs between Windows and everything else.
  if [ -x .venv/bin/python ]; then
    VENV_PY=.venv/bin/python
  else
    VENV_PY=.venv/Scripts/python.exe
  fi

  "$VENV_PY" -m pip install --upgrade pip --quiet
  "$VENV_PY" -m pip install -r requirements.txt
)

# --- optional tooling --------------------------------------------------------
command -v ffmpeg >/dev/null 2>&1 \
  || warn "FFmpeg not found. Video analysis needs it — install before working on ai/video_analysis/."

command -v mongod >/dev/null 2>&1 \
  || warn "MongoDB not found locally. The backend starts anyway and falls back to an in-process store."

printf '\n\033[32m✓\033[0m Setup complete.\n\n'
printf 'Start everything:   bash scripts/dev.sh\n'
printf 'Or one at a time:   cd backend && npm run dev\n'
printf '                    cd frontend && npm run dev\n'
printf '                    cd ai && uvicorn main:app --reload --port 8000\n\n'
