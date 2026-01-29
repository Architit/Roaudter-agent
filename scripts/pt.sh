#!/usr/bin/env bash
set -euo pipefail

LAM_DIR="/mnt/c/Users/lkise/OneDrive/Documenten/GitHub/LAM"

cd "$LAM_DIR"
TMPDIR=/tmp TEMP=/tmp TMP=/tmp bash scripts/lam_env.sh pytest -q "$@"
