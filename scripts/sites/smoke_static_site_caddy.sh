#!/bin/sh
# Verify generated Caddy site blocks: extensionless /blog and /blog/ return 200 when
# blog.html exists at site root (mirrors the sites proxy container layout).
set -eu
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
TMP="$(mktemp -d)"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

mkdir -p "$TMP/root" "$TMP/registry"
echo '<html><body>blog</body></html>' >"$TMP/root/blog.html"
echo '<html><body>home</body></html>' >"$TMP/root/index.html"

SITE_BLOCK="$(
  SCRIPT_DIR="$SCRIPT_DIR" python3 <<'PY'
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ["SCRIPT_DIR"])
import reconcile_sites  # noqa: E402

site = reconcile_sites.PublishedSite(
    name="t",
    subdomain="h",
    domain="h.example.com",
    root=Path("/srv/root"),
    basicauth=None,
)
print(reconcile_sites.render_sites([site], [], "example.com"))
PY
)"
printf '%s\n' "$SITE_BLOCK" >"$TMP/registry/sites.generated.raw"
# Use internal TLS so the smoke test does not hit public ACME for example.com.
awk '
  /^h\.example\.com \{/ { print; print "  tls internal"; next }
  { print }
' "$TMP/registry/sites.generated.raw" >"$TMP/registry/sites.generated.caddy"

cat >"$TMP/Caddyfile" <<'EOF'
import /etc/caddy/sites-registry/sites.generated.caddy
EOF

docker rm -f opch-smoke-caddy >/dev/null 2>&1 || true
docker run -d --name opch-smoke-caddy -p 127.0.0.1:29777:443 \
  -p 127.0.0.1:29778:9080 \
  -v "$TMP/Caddyfile:/etc/caddy/Caddyfile:ro" \
  -v "$TMP/registry:/etc/caddy/sites-registry:ro" \
  -v "$TMP/root:/srv/root:ro" \
  caddy:2 >/dev/null

ok=0
i=0
while [ "$i" -lt 30 ]; do
  if curl -fsSk -o /dev/null --resolve "h.example.com:29777:127.0.0.1" "https://h.example.com:29777/" 2>/dev/null; then
    ok=1
    break
  fi
  i=$((i + 1))
  sleep 0.2
done
if [ "$ok" != 1 ]; then
  echo "smoke: Caddy did not become ready on :29777 (HTTPS)" >&2
  docker logs opch-smoke-caddy 2>&1 | tail -30 >&2 || true
  docker rm -f opch-smoke-caddy >/dev/null 2>&1 || true
  exit 1
fi

fail=0
for path in /blog /blog/; do
  code="$(
    curl -sSk -o /dev/null -w '%{http_code}' \
      --resolve "h.example.com:29777:127.0.0.1" \
      "https://h.example.com:29777${path}"
  )"
  if [ "$code" != "200" ]; then
    echo "smoke: GET ${path} expected 200, got ${code}" >&2
    fail=1
  fi
done
docker rm -f opch-smoke-caddy >/dev/null 2>&1 || true

if [ "$fail" != 0 ]; then
  exit 1
fi
echo "smoke_static_site_caddy: ok (/blog and /blog/ -> 200)"
