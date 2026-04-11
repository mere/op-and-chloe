#!/usr/bin/env bash
set -euo pipefail

INSTANCE=${INSTANCE:-op-and-chloe}
GW_CONTAINER=${GW_CONTAINER:-${INSTANCE}-openclaw-gateway}
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
STACK_DIR=${STACK_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}
ENV_FILE=${ENV_FILE:-/etc/openclaw/stack.env}

printf "== containers ==\n"
docker ps --format "{{.Names}}\t{{.Status}}\t{{.Image}}" \
  | awk "BEGIN{print \"NAME\\tSTATUS\\tIMAGE\"} /^${INSTANCE}-/{print}"

echo
printf "== gateway port mapping ==\n"
docker port "$GW_CONTAINER" 18789/tcp 2>/dev/null || echo "(no port mapping found)"

echo
printf "== CDP smoke test ==\n"
bash "$STACK_DIR/scripts/host/cdp-smoke-test.sh"

echo
printf "== network/security checks ==\n"
if tailscale status >/dev/null 2>&1; then
  echo "✅ Tailscale - Running"
else
  echo "⚠️  Tailscale - Not running"
fi

if [ -f "$ENV_FILE" ]; then
  SITES_ENABLED=$(grep -E '^SITES_ENABLED=' "$ENV_FILE" | cut -d= -f2- | tr -d '"' | head -1)
  SITES_BASE_DOMAIN=$(grep -E '^SITES_BASE_DOMAIN=' "$ENV_FILE" | cut -d= -f2- | tr -d '"' | head -1)
  if [ "${SITES_ENABLED:-disabled}" != "enabled" ]; then
    echo "⚪ Sites publishing - disabled"
  elif [ -n "${SITES_BASE_DOMAIN:-}" ]; then
    echo "✅ Sites base domain - ${SITES_BASE_DOMAIN}"
  else
    echo "⚪ Sites base domain - not configured"
  fi
fi

echo
printf "== recent gateway logs (tail) ==\n"
docker logs "$GW_CONTAINER" --tail=20
