#!/bin/bash
set -e

# Wait for postgres to be ready
echo "Waiting for PostgreSQL..."
until python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('postgres',5432)); s.close()" 2>/dev/null; do
    sleep 1
    echo "Waiting for PostgreSQL..."
done
echo "PostgreSQL is ready"

# Run migrations
echo "Running Alembic migrations..."
alembic upgrade head

case "$1" in
    api)
        echo "Starting LaunchLens API on port 8000..."
        exec uvicorn launchlens.main:app --host 0.0.0.0 --port 8000 --reload
        ;;
    worker)
        echo "Starting Temporal worker..."
        exec python -m launchlens.workflows.worker
        ;;
    test)
        echo "Running tests..."
        exec pytest "$@"
        ;;
    *)
        exec "$@"
        ;;
esac
