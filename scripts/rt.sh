#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_ROOT="${ECO_WORK_ROOT:-$(cd "$SCRIPT_DIR/../../../../.." && pwd)}"
LAM_DIR="${LAM_DIR:-$WORK_ROOT/LAM}"
RO_DIR="${RO_DIR:-$WORK_ROOT/Roaudter-agent}"

# ensure editable install is active (no-op if already)
cd "$RO_DIR"
pip install -e . >/dev/null

# run tests from LAM
cd "$LAM_DIR"
TMPDIR=/tmp TEMP=/tmp TMP=/tmp bash scripts/lam_env.sh pytest -q -k "${1:-roaudter}"
