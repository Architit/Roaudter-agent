#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_ROOT="${ECO_WORK_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
LAM_DIR="${LAM_DIR:-$WORK_ROOT/LAM}"

cd "$LAM_DIR"
TMPDIR=/tmp TEMP=/tmp TMP=/tmp bash scripts/lam_env.sh pytest -q "$@"
