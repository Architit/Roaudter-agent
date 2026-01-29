#!/usr/bin/env bash
set -euo pipefail

LAM_DIR="/mnt/c/Users/lkise/OneDrive/Documenten/GitHub/LAM"
RO_DIR="/home/architit/work/Roaudter-agent"

# ensure editable install is active (no-op if already)
cd "$RO_DIR"
pip install -e . >/dev/null

# run tests from LAM
cd "$LAM_DIR"
TMPDIR=/tmp TEMP=/tmp TMP=/tmp bash scripts/lam_env.sh pytest -q -k "${1:-roaudter}"
