#!/bin/bash
set -e

# Wait for postgres to be ready
echo "Waiting for PostgreSQL..."
while ! python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect(('postgres', 5432))
    s.close()
    exit(0)
except:
    exit(1)
" 2>/dev/null; do
    sleep 1
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
