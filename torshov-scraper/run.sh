#!/usr/bin/env bash
set -euo pipefail

JSON="$(curl -sSL http://supervisor/addons/self/info || true)"

opt() { echo "$JSON" | python3 -c "import sys,json; v=json.load(sys.stdin)['data']['options'].get('$1',''); print(v)" 2>/dev/null || true; }

export PRODUCT_ID="$(opt product_id)"
export URL="${URL:-https://www.torshovsport.no/fotball/supporterutstyr/landslag/norge/nike-norge-herrelandslaget-vm-2026-fotballdrakt-hjemme}"
export POLL_INTERVAL="$(opt poll_interval)"

SMTP_HOST_VAL="$(opt smtp_host)"
SMTP_PORT_VAL="$(opt smtp_port)"
SMTP_USER_VAL="$(opt smtp_user)"
SMTP_PASS_VAL="$(opt smtp_pass)"
SMTP_FROM_VAL="$(opt smtp_from)"
SMTP_TO_VAL="$(opt smtp_to)"
TLS_VAL="$(opt smtp_tls)"

[ -n "$SMTP_HOST_VAL" ] && export SMTP_HOST="$SMTP_HOST_VAL"
[ -n "$SMTP_PORT_VAL" ] && export SMTP_PORT="$SMTP_PORT_VAL"
[ -n "$SMTP_USER_VAL" ] && export SMTP_USER="$SMTP_USER_VAL"
[ -n "$SMTP_PASS_VAL" ] && export SMTP_PASS="$SMTP_PASS_VAL"
[ -n "$SMTP_FROM_VAL" ] && export SMTP_FROM="$SMTP_FROM_VAL"
[ -n "$SMTP_TO_VAL" ] && export SMTP_TO="$SMTP_TO_VAL"
[ -n "$TLS_VAL" ] && export SMTP_TLS="$TLS_VAL"

mkdir -p /data

exec python3 /app/scraper.py
