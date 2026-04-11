#!/usr/bin/env bash
set -euo pipefail

ENV_FILE=${ENV_FILE:-/etc/openclaw/stack.env}
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
STACK_DIR=${STACK_DIR:-$SCRIPT_DIR}
COMPOSE_FILE=${COMPOSE_FILE:-$STACK_DIR/compose.yml}
[ -f "$ENV_FILE" ] && INSTANCE=$(grep -E '^INSTANCE=' "$ENV_FILE" | cut -d= -f2- | tr -d '"' | head -1)
INSTANCE=${INSTANCE:-op-and-chloe}

cd "$STACK_DIR"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck source=/dev/null
  . "$ENV_FILE" 2>/dev/null || true
  set +a
fi

case "${SITES_ENABLED:-disabled}" in
  enabled|ENABLE|Enabled|true|TRUE|True|1|yes|YES|Yes|on|ON|On) SITES_ENABLED=enabled ;;
  *) SITES_ENABLED=disabled ;;
esac

mkdir -p \
  "${OPENCLAW_WORKSPACE_DIR:-/var/lib/openclaw/chloe/workspace}/sites" \
  "${OPENCLAW_SITES_PROXY_CONFIG_DIR:-/etc/openclaw/sites-proxy}" \
  "${OPENCLAW_SITES_PROXY_DATA_DIR:-/var/lib/openclaw/sites-proxy/data}" \
  "${OPENCLAW_SITES_PROXY_STORAGE_DIR:-/var/lib/openclaw/sites-proxy/config}"
: > "${OPENCLAW_SITES_PROXY_CONFIG_DIR:-/etc/openclaw/sites-proxy}/sites.generated.caddy"

echo "[start] syncing core instructions into workspaces"
bash "$STACK_DIR/scripts/host/sync-workspaces.sh"

echo "[start] building guard and worker images (openclaw-guard-tools:local, openclaw-worker-tools:local)"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build openclaw-guard openclaw-gateway

echo "[start] pulling images (browser)"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" pull browser

if [ "$SITES_ENABLED" = "enabled" ]; then
  echo "[start] pulling images (site proxy, sites reconciler)"
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" --profile sites pull site-proxy sites-reconciler
fi

echo "[start] bringing stack up"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d browser openclaw-guard openclaw-gateway

if [ "$SITES_ENABLED" = "enabled" ]; then
  echo "[start] enabling sites publishing services"
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" --profile sites up -d site-proxy sites-reconciler
else
  echo "[start] ensuring sites publishing services are disabled"
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" --profile sites stop site-proxy sites-reconciler >/dev/null 2>&1 || true
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" --profile sites rm -f site-proxy sites-reconciler >/dev/null 2>&1 || true
fi

echo "[start] container status"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" --profile sites ps

echo "[start] warming up browser/CDP"
sleep 10

# Refresh worker state with current browser container CDP URL so Chloe's browser tool works
if docker ps -q -f "name=${INSTANCE:-op-and-chloe}-browser" | grep -q . 2>/dev/null; then
  echo "[start] updating webtop CDP URL in worker state"
  STACK_DIR="$STACK_DIR" ENV_FILE="$ENV_FILE" bash "$STACK_DIR/scripts/host/update-webtop-cdp-url.sh" 2>/dev/null || true
fi

echo "[start] waiting for gateways to listen (guard 18790, worker 18789)..."
max=120
for i in $(seq 1 "$max"); do
  w="$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 2 http://127.0.0.1:18789/ 2>/dev/null || echo 000)"
  g="$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 2 http://127.0.0.1:18790/ 2>/dev/null || echo 000)"
  if [ "$w" = "200" ] && [ "$g" = "200" ]; then
    echo "[start] gateways ready after ${i}s"
    break
  fi
  [ "$i" -eq "$max" ] && { echo "[start] WARN: gateways not ready after ${max}s; Tailscale serve may 502 until they are up"; break; }
  sleep 1
done

if tailscale status >/dev/null 2>&1; then
  echo "[start] applying Tailscale serve (Guard, Worker, Webtop)"
  bash "$STACK_DIR/scripts/host/apply-tailscale-serve.sh" 2>/dev/null || true
fi
echo "[start] healthcheck"
STACK_DIR="$STACK_DIR" ENV_FILE="$ENV_FILE" "$STACK_DIR/healthcheck.sh"
