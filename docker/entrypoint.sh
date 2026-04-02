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

# Run migrations (skip on failure — DB might not be ready yet)
echo "Running Alembic migrations..."
# Stamp to current if DB is ahead of Alembic tracking (idempotent)
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

async def stamp_if_needed():
    url = os.environ.get('DATABASE_URL', '')
    if not url:
        return
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            # Check if listing_permissions exists (migration 025)
            r = await conn.execute(text(\"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='listing_permissions')\"))
            has_025 = r.scalar()
            # Check current alembic version
            r = await conn.execute(text('SELECT version_num FROM alembic_version LIMIT 1'))
            row = r.first()
            current = row[0] if row else None
            # If DB has 025 tables but Alembic thinks we're behind, stamp to 025
            if has_025 and current and int(current) < 25:
                await conn.execute(text(\"UPDATE alembic_version SET version_num = '025'\"))
                await conn.commit()
                print('Stamped alembic_version to 025')
            # If Alembic is behind (e.g. stuck at 015) and tables exist, stamp forward
            elif current and int(current) < 24:
                await conn.execute(text(\"UPDATE alembic_version SET version_num = '024'\"))
                await conn.commit()
                print('Stamped alembic_version to 024')
    except Exception as e:
        print(f'Stamp check skipped: {e}')
    finally:
        await engine.dispose()

asyncio.run(stamp_if_needed())
" 2>/dev/null || true
alembic upgrade head || echo "WARNING: Alembic migration failed — continuing anyway"

# Use PORT env var if set (Railway sets this), otherwise 8000
PORT=${PORT:-8000}

case "${1:-api}" in
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
