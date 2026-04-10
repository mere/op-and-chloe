#!/usr/bin/env bash
set -euo pipefail

ENV_FILE=${ENV_FILE:-/etc/openclaw/stack.env}
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
STACK_DIR=${STACK_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}
FORCE_RUN=0

for arg in "$@"; do
  case "$arg" in
    --force) FORCE_RUN=1 ;;
    *)
      echo "[backup] unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck source=/dev/null
  . "$ENV_FILE" 2>/dev/null || true
  set +a
fi

default_backup_dir(){
  local parent base
  parent=$(dirname "$STACK_DIR")
  base=$(basename "$STACK_DIR")
  echo "$parent/backups/$base"
}

DAILY_BACKUPS_ENABLED=${DAILY_BACKUPS_ENABLED:-disabled}
DAILY_BACKUPS_DIR=${DAILY_BACKUPS_DIR:-$(default_backup_dir)}
DAILY_BACKUPS_RETENTION_COUNT=${DAILY_BACKUPS_RETENTION_COUNT:-30}
OPENCLAW_STATE_DIR=${OPENCLAW_STATE_DIR:-/var/lib/openclaw/chloe/state}
OPENCLAW_WORKSPACE_DIR=${OPENCLAW_WORKSPACE_DIR:-/var/lib/openclaw/chloe/workspace}
OPENCLAW_ETC_DIR=${OPENCLAW_ETC_DIR:-$(dirname "$ENV_FILE")}

if [ "$FORCE_RUN" -ne 1 ] && [ "$DAILY_BACKUPS_ENABLED" != "enabled" ]; then
  echo "[backup] daily backups disabled"
  exit 0
fi

case "$DAILY_BACKUPS_RETENTION_COUNT" in
  ''|*[!0-9]*)
    echo "[backup] DAILY_BACKUPS_RETENTION_COUNT must be a non-negative integer" >&2
    exit 1
    ;;
esac

mkdir -p "$DAILY_BACKUPS_DIR"

backup_dir_real=$(readlink -f "$DAILY_BACKUPS_DIR" 2>/dev/null || echo "$DAILY_BACKUPS_DIR")
state_dir_real=$(readlink -f "$OPENCLAW_STATE_DIR" 2>/dev/null || echo "$OPENCLAW_STATE_DIR")
workspace_dir_real=$(readlink -f "$OPENCLAW_WORKSPACE_DIR" 2>/dev/null || echo "$OPENCLAW_WORKSPACE_DIR")
etc_dir_real=$(readlink -f "$OPENCLAW_ETC_DIR" 2>/dev/null || echo "$OPENCLAW_ETC_DIR")
case "$backup_dir_real" in
  "$state_dir_real"|"$state_dir_real"/*|"$workspace_dir_real"|"$workspace_dir_real"/*|"$etc_dir_real"|"$etc_dir_real"/*)
    echo "[backup] backup directory must live outside Chloe state/workspace and /etc/openclaw" >&2
    exit 1
    ;;
esac

for source_dir in "$OPENCLAW_ETC_DIR" "$OPENCLAW_STATE_DIR" "$OPENCLAW_WORKSPACE_DIR"; do
  if [ ! -d "$source_dir" ]; then
    echo "[backup] missing source directory: $source_dir" >&2
    exit 1
  fi
done

timestamp=$(date -u +"%Y%m%dT%H%M%SZ")
archive_name="openclaw-backup-${timestamp}.tar.gz"
archive_path="$DAILY_BACKUPS_DIR/$archive_name"

tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT
tmp_archive_path="$tmp_dir/$archive_name"

cat > "$tmp_dir/manifest.txt" <<EOF
created_at_utc=$timestamp
stack_dir=$STACK_DIR
env_file=$ENV_FILE
openclaw_etc_dir=$OPENCLAW_ETC_DIR
openclaw_state_dir=$OPENCLAW_STATE_DIR
openclaw_workspace_dir=$OPENCLAW_WORKSPACE_DIR
EOF

echo "[backup] writing $archive_path"
tar -czf "$tmp_archive_path" \
  -C / "${OPENCLAW_ETC_DIR#/}" \
  -C / "${OPENCLAW_STATE_DIR#/}" \
  -C / "${OPENCLAW_WORKSPACE_DIR#/}" \
  -C "$tmp_dir" manifest.txt

mv "$tmp_archive_path" "$archive_path"

if [ "$DAILY_BACKUPS_RETENTION_COUNT" -gt 0 ]; then
  python3 - "$DAILY_BACKUPS_DIR" "$DAILY_BACKUPS_RETENTION_COUNT" <<'PY'
from pathlib import Path
import sys

backup_dir = Path(sys.argv[1])
keep = int(sys.argv[2])
archives = sorted(backup_dir.glob("openclaw-backup-*.tar.gz"))
for path in archives[:-keep]:
    path.unlink(missing_ok=True)
    print(f"[backup] pruned {path}")
PY
fi

echo "[backup] complete: $archive_path"
