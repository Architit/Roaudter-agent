#!/usr/bin/env bash
set -euo pipefail

REPO="${1:-$(pwd)}"
cd "$REPO"

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

# ONTOLOGICAL SAFETY CHECK (ANGEL GUARD)
if [[ -f "IDENTITY.md" ]]; then
  ID=$(grep "System ID:" IDENTITY.md | cut -d'#' -f3 | xargs)
  echo "[ANGEL GUARD] Fixating Identity: $ID"
else
  echo "[ANGEL GUARD] ERROR: IDENTITY.md not fixated. HALTING."
  exit 1
fi


PY="$REPO/.venv/bin/python"
PIP="$REPO/.venv/bin/pip"

"$PY" -m pip install -U pip

if [[ -f "requirements-dev.txt" ]]; then
  "$PIP" install -r requirements-dev.txt
elif [[ -f "requirements.txt" ]]; then
  "$PIP" install -r requirements.txt
elif [[ -f "pyproject.toml" ]]; then
  "$PIP" install -e .
else
  echo "[devkit] WARN: no requirements*.txt or pyproject.toml found"
fi

echo "[devkit] OK: $PY"
