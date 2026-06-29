#!/usr/bin/env bash
set -euo pipefail

JSON="$(curl -sSL http://supervisor/addons/self/info || true)"

opt() { echo "$JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['options'].get('$1',''))" 2>/dev/null || true; }

export PRODUCT_ID="$(opt product_id)"
export URL="${URL:-https://www.torshovsport.no/fotball/supporterutstyr/landslag/norge/nike-norge-herrelandslaget-vm-2026-fotballdrakt-hjemme}"
export POLL_INTERVAL="$(opt poll_interval)"

export SMTP_HOST="$(opt smtp_host)"
export SMTP_PORT="$(opt smtp_port)"
export SMTP_USER="$(opt smtp_user)"
export SMTP_PASS="$(opt smtp_pass)"
export SMTP_FROM="$(opt smtp_from)"
export SMTP_TO="$(opt smtp_to)"
TLS="$(opt smtp_tls)"
export SMTP_TLS="${TLS:-1}"

mkdir -p /data

exec python3 /app/scraper.py
