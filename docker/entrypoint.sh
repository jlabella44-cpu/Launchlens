#!/bin/bash
set -e

# Parse DB host/port from DATABASE_URL or fall back to 'postgres:5432'
DB_HOST=${DB_HOST:-postgres}
DB_PORT=${DB_PORT:-5432}

if [ -n "$DATABASE_URL" ]; then
    # Extract host:port from postgresql+asyncpg://user:pass@host:port/db
    DB_HOST=$(echo "$DATABASE_URL" | sed -E 's|.*@([^:/]+).*|\1|')
    DB_PORT=$(echo "$DATABASE_URL" | sed -E 's|.*:([0-9]+)/.*|\1|' | grep -E '^[0-9]+$' || echo "5432")
fi

echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
until python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('$DB_HOST',$DB_PORT)); s.close()" 2>/dev/null; do
    sleep 1
    echo "Waiting for PostgreSQL..."
done
echo "PostgreSQL is ready"

# Run migrations
echo "Running Alembic migrations..."
alembic upgrade head

# Use PORT env var if set (Railway sets this), otherwise 8000
PORT=${PORT:-8000}

case "$1" in
    api)
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
