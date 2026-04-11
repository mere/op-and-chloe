#!/bin/sh
# Run sites reconcile in a fresh Python process each cycle so updates to
# reconcile_sites.py on the mounted repo are picked up without recreating the container.
set -eu
INTERVAL="${SITES_RECONCILE_INTERVAL:-5}"
BASE_DOMAIN="${SITES_BASE_DOMAIN:-}"
while true; do
  python3 /opt/op-and-chloe/scripts/sites/reconcile_sites.py \
    --workspace /srv/chloe-workspace \
    --output /etc/openclaw/sites.generated.caddy \
    --interval 0 \
    --base-domain "$BASE_DOMAIN"
  sleep "$INTERVAL"
done
