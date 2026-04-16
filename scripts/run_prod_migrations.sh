#!/usr/bin/env bash
# run_prod_migrations.sh — manually apply outstanding Alembic migrations to prod.
#
# Usage (from repo root, with prod DATABASE_URL exported):
#
#   export DATABASE_URL="postgresql+asyncpg://listingjet:<pass>@<rds-host>:5432/listingjet"
#   export DATABASE_URL_SYNC="postgresql://listingjet:<pass>@<rds-host>:5432/listingjet"
#   bash scripts/run_prod_migrations.sh
#
# Alternatively, trigger via ECS Exec (no direct DB access needed):
#
#   CLUSTER=listingjet
#   TASK_ID=$(aws ecs list-tasks --cluster $CLUSTER --service-name listingjet-api \
#               --query 'taskArns[0]' --output text | awk -F/ '{print $NF}')
#   aws ecs execute-command --cluster $CLUSTER --task $TASK_ID \
#     --container listingjet-api --interactive \
#     --command "alembic upgrade head"
#
# Or trigger the CI migrate step directly:
#   gh workflow run deploy.yml --ref main
#
set -euo pipefail

# ── Pre-flight checks ─────────────────────────────────────────────────────────

if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL is not set."
    echo "Export the production DATABASE_URL before running this script."
    exit 1
fi

echo "==================================================================="
echo " LaunchLens / ListingJet — Production Migration Runner"
echo "==================================================================="
echo ""
echo "Target DB: $(echo "$DATABASE_URL" | sed -E 's|postgresql(\+asyncpg)?://[^@]+@||')"
echo ""

# ── Show current revision ─────────────────────────────────────────────────────

echo "--- Current alembic revision on prod ---"
alembic current
echo ""

# ── Show pending migrations ───────────────────────────────────────────────────

echo "--- Pending migrations (current → head) ---"
alembic history -r current:head
echo ""

# ── Confirm before applying ───────────────────────────────────────────────────

if [ "${AUTO_APPROVE:-}" != "1" ]; then
    read -r -p "Apply all pending migrations to PRODUCTION? [y/N] " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

# ── Run upgrade ───────────────────────────────────────────────────────────────

echo ""
echo "--- Running: alembic upgrade head ---"
alembic upgrade head

# ── Verify ───────────────────────────────────────────────────────────────────

echo ""
echo "--- Verification: alembic current ---"
alembic current

echo ""
echo "==================================================================="
echo " Migrations complete."
echo "==================================================================="
