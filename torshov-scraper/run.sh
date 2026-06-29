#!/usr/bin/env bash
set -euo pipefail

JSON="$(curl -sSL http://supervisor/addons/self/info || true)"

PRODUCT_ID="$(echo "$JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["options"]["product_id"])' 2>/dev/null || echo "50368")"
URL="$(echo "$JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["options"]["url"])' 2>/dev/null || echo "")"
POLL_INTERVAL="$(echo "$JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["options"]["poll_interval"])' 2>/dev/null || echo "300")"

export PRODUCT_ID="${PRODUCT_ID}"
export URL="${URL:-https://www.torshovsport.no/fotball/supporterutstyr/landslag/norge/nike-norge-herrelandslaget-vm-2026-fotballdrakt-hjemme}"
export POLL_INTERVAL="${POLL_INTERVAL}"

mkdir -p /data

exec python3 /app/scraper.py
