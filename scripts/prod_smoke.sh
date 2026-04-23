#!/usr/bin/env bash
# Post-deploy smoke test for ListingJet prod.
#
# Usage:
#   scripts/prod_smoke.sh                        # hits https://api.listingjet.ai
#   PROD_URL=https://api.example.com scripts/prod_smoke.sh
#
# What it checks:
#   1. /health — returns 200 (API + DB liveness)
#   2. /health/deep — returns 200 (DB + Redis + Temporal reachable)
#   3. Anonymous POST /demo/upload — happy path, no auth, creates a demo
#      listing with a single sample asset. Validates the ingestion path
#      end-to-end.
#
# Exit 0 on all green; exit 1 at first failure.
# Designed for CI hook after deploy.yml, or operator run after a manual
# cdk deploy.

set -euo pipefail

PROD_URL="${PROD_URL:-https://api.listingjet.ai}"
CURL="curl --silent --show-error --fail --max-time 15"

info() { printf '[INFO] %s\n' "$*"; }
pass() { printf '[PASS] %s\n' "$*"; }
fail() { printf '[FAIL] %s\n' "$*" >&2; exit 1; }

info "Smoke target: $PROD_URL"

# 1. /health
info "1/3 /health"
$CURL -o /dev/null "$PROD_URL/health" || fail "GET /health"
pass "/health 200"

# 2. /health/deep
info "2/3 /health/deep"
$CURL -o /dev/null "$PROD_URL/health/deep" || fail "GET /health/deep"
pass "/health/deep 200"

# 3. Anonymous demo upload
info "3/3 POST /demo/upload"
DEMO_PAYLOAD='{"file_paths": ["s3://smoke/sample.jpg"]}'

# Capture the response so we can sanity-check the listing id came back
RESP=$(curl --silent --show-error --fail --max-time 30 \
  -H 'Content-Type: application/json' \
  -d "$DEMO_PAYLOAD" \
  "$PROD_URL/demo/upload") || fail "POST /demo/upload"

if printf '%s' "$RESP" | grep -q '"id"\|"demo_id"\|"listing_id"'; then
    pass "/demo/upload 200 (listing id returned)"
else
    fail "/demo/upload response missing id: $RESP"
fi

printf '\n[OK] prod smoke green\n'
