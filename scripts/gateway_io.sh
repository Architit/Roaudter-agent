#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_NAME="$(basename "$ROOT")"

GATEWAY_GITHUB_REMOTE="${GATEWAY_GITHUB_REMOTE:-origin}"
GATEWAY_ONEDRIVE_ROOT="${GATEWAY_ONEDRIVE_ROOT:-}"
GATEWAY_GWORKSPACE_ROOT="${GATEWAY_GWORKSPACE_ROOT:-}"
GATEWAY_EXPORT_DIR="${GATEWAY_EXPORT_DIR:-$ROOT/.gateway/export}"
GATEWAY_IMPORT_DIR="${GATEWAY_IMPORT_DIR:-$ROOT/.gateway/import}"
GATEWAY_STAGE_DIR="${GATEWAY_STAGE_DIR:-$ROOT/.gateway/import_staging}"

log() { echo "[$(date -Iseconds)] $*"; }

validate_archive_paths() {
  local archive="$1"
  local entry
  while IFS= read -r entry; do
    [[ -z "$entry" ]] && continue
    if [[ "$entry" == /* ]]; then
      log "import:fail unsafe_path absolute entry=$entry"
      return 1
    fi
    if [[ "$entry" == ".." || "$entry" == ../* || "$entry" == */.. || "$entry" == */../* ]]; then
      log "import:fail unsafe_path traversal entry=$entry"
      return 1
    fi
  done < <(tar -tzf "$archive")
}


verify_github() {
  if git -C "$ROOT" remote get-url "$GATEWAY_GITHUB_REMOTE" >/dev/null 2>&1; then
    log "github:ok remote=$GATEWAY_GITHUB_REMOTE"
  else
    log "github:fail remote_not_found remote=$GATEWAY_GITHUB_REMOTE"
    return 1
  fi
}

verify_onedrive() {
  if [[ -z "$GATEWAY_ONEDRIVE_ROOT" ]]; then
    log "onedrive:warn env_not_set GATEWAY_ONEDRIVE_ROOT"
    return 2
  fi
  if [[ -d "$GATEWAY_ONEDRIVE_ROOT" ]]; then
    log "onedrive:ok path=$GATEWAY_ONEDRIVE_ROOT"
  else
    log "onedrive:fail path_missing path=$GATEWAY_ONEDRIVE_ROOT"
    return 1
  fi
}

verify_gworkspace() {
  if [[ -z "$GATEWAY_GWORKSPACE_ROOT" ]]; then
    log "gworkspace:warn env_not_set GATEWAY_GWORKSPACE_ROOT"
    return 2
  fi
  if [[ -d "$GATEWAY_GWORKSPACE_ROOT" ]]; then
    log "gworkspace:ok path=$GATEWAY_GWORKSPACE_ROOT"
  else
    log "gworkspace:fail path_missing path=$GATEWAY_GWORKSPACE_ROOT"
    return 1
  fi
}

do_export() {
  mkdir -p "$GATEWAY_EXPORT_DIR"
  ts="$(date +%Y%m%d_%H%M%S)"
  archive="$GATEWAY_EXPORT_DIR/${REPO_NAME}_${ts}.tgz"
  tar --exclude='.git' --exclude='.venv' --exclude='__pycache__' -czf "$archive" -C "$ROOT" .
  log "export:ok archive=$archive"
}

do_import() {
  local archive="${1:-}"
  if [[ -z "$archive" ]]; then
    log "import:fail missing_archive_argument"
    return 1
  fi
  if [[ ! -f "$archive" ]]; then
    log "import:fail archive_not_found path=$archive"
    return 1
  fi
  mkdir -p "$GATEWAY_IMPORT_DIR" "$GATEWAY_STAGE_DIR"
  cp -f "$archive" "$GATEWAY_IMPORT_DIR/"
  find "$GATEWAY_STAGE_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
  validate_archive_paths "$archive"
  tar -xzf "$archive" -C "$GATEWAY_STAGE_DIR" --no-same-owner --no-same-permissions
  log "import:ok staged_at=$GATEWAY_STAGE_DIR archive=$(basename "$archive")"
}

cmd="${1:-verify}"
case "$cmd" in
  verify)
    rc=0
    verify_github || rc=1
    verify_onedrive || rc=1
    verify_gworkspace || rc=1
    exit "$rc"
    ;;
  export)
    do_export
    ;;
  import)
    do_import "${2:-}"
    ;;
  *)
    echo "Usage: $0 [verify|export|import <archive>]"
    exit 2
    ;;
esac
