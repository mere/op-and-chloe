#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
STACK_DIR=${STACK_DIR:-$SCRIPT_DIR}
ENV_FILE=${ENV_FILE:-/etc/openclaw/stack.env}

# Use same INSTANCE as docker compose (from env file)
if [ -f "$ENV_FILE" ]; then
  export INSTANCE=$(grep -E '^INSTANCE=' "$ENV_FILE" | cut -d= -f2- | tr -d '"' | head -1)
fi
export INSTANCE=${INSTANCE:-op-and-chloe}

bash "$STACK_DIR/scripts/host/stack-health.sh"

echo

echo "== watchdog timer =="
systemctl is-enabled openclaw-cdp-watchdog.timer >/dev/null 2>&1 && systemctl is-active openclaw-cdp-watchdog.timer >/dev/null 2>&1 \
  && echo "openclaw-cdp-watchdog.timer: enabled+active" \
  || echo "openclaw-cdp-watchdog.timer: not enabled/active"

echo

echo "== daily backups =="
if [ -f /etc/cron.d/openclaw-daily-backup ]; then
  echo "openclaw-daily-backup: enabled"
else
  echo "openclaw-daily-backup: disabled"
fi
if [ -f "$ENV_FILE" ]; then
  retention=$(grep -E '^DAILY_BACKUPS_RETENTION_COUNT=' "$ENV_FILE" | cut -d= -f2- | tr -d '"' | head -1)
  retention=${retention:-30}
  echo "openclaw-daily-backup retention: $retention"
fi

echo

echo "== sites publishing =="
if [ -f "$ENV_FILE" ]; then
  sites_enabled=$(grep -E '^SITES_ENABLED=' "$ENV_FILE" | cut -d= -f2- | tr -d '"' | head -1)
  sites_domain=$(grep -E '^SITES_BASE_DOMAIN=' "$ENV_FILE" | cut -d= -f2- | tr -d '"' | head -1)
  sites_enabled=${sites_enabled:-disabled}
  if [ "$sites_enabled" = "enabled" ]; then
    echo "sites publishing: enabled"
    echo "sites base domain: ${sites_domain:-<not set>}"
  else
    echo "sites publishing: disabled"
  fi
fi
