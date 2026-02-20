#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

export PYTEST_ADDOPTS="${PYTEST_ADDOPTS:--p no:cacheprovider}"

PYTEST_BIN="${PYTEST_BIN:-$ROOT_DIR/.venv/bin/pytest}"

if [[ ! -x "$PYTEST_BIN" ]]; then
  echo "[test-entrypoint] pytest not found at $PYTEST_BIN"
  echo "[test-entrypoint] create env: python -m venv .venv && .venv/bin/pip install -e '.[test]'"
  exit 2
fi

run_pytest_allow_empty() {
  if "$PYTEST_BIN" "$@"; then
    return 0
  fi
  local rc=$?
  if [[ $rc -eq 5 ]]; then
    return 0
  fi
  return "$rc"
}

case "${1:---all}" in
  --all)
    "$PYTEST_BIN" -q tests
    ;;
  --integration)
    run_pytest_allow_empty -q tests -m "integration"
    ;;
  --unit-only)
    run_pytest_allow_empty -q tests -m "not integration"
    ;;
  --ci)
    "$PYTEST_BIN" -q tests --maxfail=1
    ;;
  *)
    echo "usage: $0 [--all|--unit-only|--integration|--ci]"
    exit 2
    ;;
esac
