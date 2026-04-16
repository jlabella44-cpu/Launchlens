#!/bin/bash
set -e

# Parse DB host/port from DATABASE_URL or fall back to 'postgres:5432'
DB_HOST=${DB_HOST:-postgres}
DB_PORT=${DB_PORT:-5432}

if [ -n "$DATABASE_URL" ]; then
    DB_HOST=$(echo "$DATABASE_URL" | sed -E 's|.*@([^:/]+).*|\1|')
    DB_PORT=$(echo "$DATABASE_URL" | sed -E 's|.*:([0-9]+)/.*|\1|' | grep -E '^[0-9]+$' || echo "5432")
fi

echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
RETRIES=0
MAX_RETRIES=30
until python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('$DB_HOST',$DB_PORT)); s.close()" 2>/dev/null; do
    RETRIES=$((RETRIES + 1))
    if [ $RETRIES -ge $MAX_RETRIES ]; then
        echo "PostgreSQL not available after $MAX_RETRIES attempts, starting anyway..."
        break
    fi
    sleep 1
    echo "Waiting for PostgreSQL... ($RETRIES/$MAX_RETRIES)"
done
echo "PostgreSQL check complete"

# Use PORT env var if set (Railway sets this), otherwise 8000
PORT=${PORT:-8000}

case "${1:-api}" in
    migrate)
        # Dedicated migration command — used by the CI deploy job (ECS run-task)
        # and for manual one-shot runs. Exits with alembic's exit code so the
        # caller can detect failures.
        echo "Running Alembic migrations..."
        alembic current
        alembic upgrade head
        echo "Migration complete. Current revision:"
        alembic current
        ;;
    api)
        # Safety-net: apply any outstanding migrations before starting the API.
        # The primary migration path is the 'migrate' ECS task in the deploy
        # pipeline; this catch-up is a last resort and warns on failure rather
        # than blocking startup so that rollbacks can still serve traffic.
        echo "Running Alembic migrations (startup catch-up)..."
        alembic upgrade head || echo "WARNING: Alembic migration failed — check deploy logs"
        echo "Starting API on port $PORT..."
        exec uvicorn listingjet.main:app --host 0.0.0.0 --port "$PORT"
        ;;
    worker)
        echo "Starting Temporal worker..."
        exec python -m listingjet.workflows.worker
        ;;
    test)
        echo "Running tests..."
        exec pytest "$@"
        ;;
    *)
        exec "$@"
        ;;
esac
