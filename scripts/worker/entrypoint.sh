#!/usr/bin/env bash
# Worker (Chloe) entrypoint: load Bitwarden session into environment so all processes
# (including agent-invoked shells) see it. Then exec OpenClaw.
set -euo pipefail
BW_ENV="/home/node/.openclaw/secrets/bitwarden.env"
BW_SESSION_FILE="/home/node/.openclaw/secrets/bw-session"
export BITWARDENCLI_APPDATA_DIR="/home/node/.openclaw/bitwarden-cli"
[ -f "$BW_ENV" ] && . "$BW_ENV"
[ -f "$BW_SESSION_FILE" ] && export BW_SESSION=$(cat "$BW_SESSION_FILE")

# QMD SQLite store (~/.openclaw/agents/<id>/qmd/xdg-cache/qmd/); ensure dirs exist on mounted state volume.
AGENTS_BASE=/home/node/.openclaw/agents
mkdir -p "$AGENTS_BASE/main/qmd/xdg-cache/qmd"
if [ -d "$AGENTS_BASE" ]; then
  shopt -s nullglob
  for d in "$AGENTS_BASE"/*/; do
    mkdir -p "${d}qmd/xdg-cache/qmd"
  done
  shopt -u nullglob
fi

exec "$@"
