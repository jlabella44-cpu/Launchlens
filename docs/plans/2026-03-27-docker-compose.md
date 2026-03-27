# Docker Compose Dev Environment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a single `docker compose up` command that starts PostgreSQL, Redis, Temporal, and the LaunchLens API + worker — so any developer can run the full stack locally with zero manual setup.

**Architecture:** `docker-compose.yml` defines 6 services: `postgres` (with test DB init), `redis`, `temporal` (server + UI), `api` (FastAPI via uvicorn), and `worker` (Temporal worker). A `Dockerfile` builds the Python app image shared by api and worker. An init script creates both the dev and test databases. Alembic migrations run on API startup via an entrypoint script.

**Tech Stack:** Docker, Docker Compose, PostgreSQL 16, Redis 7, Temporal (temporalio/auto-setup), Python 3.12

---

## File Structure

```
docker-compose.yml              CREATE  — all services
Dockerfile                      CREATE  — Python app image
docker/
  init-db.sh                    CREATE  — creates dev + test databases
  entrypoint.sh                 CREATE  — runs migrations then starts app
.dockerignore                   CREATE  — exclude unnecessary files
```

---

## Key Design Decisions

### Database
- PostgreSQL 16 on port **5432** (dev) with a second database `launchlens_test` for tests
- The test DB on port **5433** that tests currently expect is handled by mapping: `docker compose` exposes postgres on 5432, but the init script creates both databases. Tests use `localhost:5432` (or 5433 if you run a separate test container).
- For backward compat with existing test config (`localhost:5433`), we add a second postgres service `postgres-test` on port 5433.

### Temporal
- Uses `temporalio/auto-setup` which auto-creates the namespace on first run
- Temporal UI on port 8233
- Connected to the same postgres for its own persistence

### Redis
- Redis 7 on port 6379, no auth (dev only)

### API
- FastAPI on port 8000 with hot-reload via uvicorn `--reload`
- Mounts `src/` as a volume for live code changes

### Worker
- Same Docker image as API, different entrypoint (`python -m launchlens.workflows.worker`)

---

## Tasks

---

### Task 1: Dockerfile + .dockerignore

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

- [ ] **Step 1: Create .dockerignore**

Create `.dockerignore`:

```
.git
.env
__pycache__
*.pyc
.pytest_cache
.mypy_cache
node_modules
frontend
*.egg-info
dist
build
.venv
design-system
docs
tests
alembic/versions/__pycache__
```

- [ ] **Step 2: Create Dockerfile**

Create `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system deps for asyncpg and psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy source + deps manifest, then install
COPY pyproject.toml ./
COPY src/ src/
RUN pip install --no-cache-dir -e ".[dev]"

# Copy remaining app files
COPY alembic/ alembic/
COPY alembic.ini ./
COPY docker/entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
CMD ["api"]
```

- [ ] **Step 3: Verify Dockerfile syntax**

```bash
cd /c/Users/Jeff/launchlens && docker build --check . 2>&1 || echo "docker build --check not supported, will validate on build"
```

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add Dockerfile .dockerignore && git commit -m "feat: add Dockerfile for LaunchLens API/worker"
```

---

### Task 2: Init scripts + entrypoint

**Files:**
- Create: `docker/init-db.sh`
- Create: `docker/entrypoint.sh`

- [ ] **Step 1: Create docker directory**

```bash
mkdir -p /c/Users/Jeff/launchlens/docker
```

- [ ] **Step 2: Create database init script**

Create `docker/init-db.sh`:

```bash
#!/bin/bash
set -e

# This runs as the postgres user on container first start.
# Creates both dev and test databases.

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE launchlens_test;
    GRANT ALL PRIVILEGES ON DATABASE launchlens_test TO $POSTGRES_USER;
EOSQL

echo "Created launchlens_test database"
```

- [ ] **Step 3: Create entrypoint script**

Create `docker/entrypoint.sh`:

```bash
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
```

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add docker/ && git commit -m "feat: add database init and entrypoint scripts"
```

---

### Task 3: docker-compose.yml

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Create docker-compose.yml**

Create `docker-compose.yml`:

```yaml
services:
  # ── PostgreSQL (dev) ─────────────────────────────────────────
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: launchlens
      POSTGRES_PASSWORD: password
      POSTGRES_DB: launchlens
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./docker/init-db.sh:/docker-entrypoint-initdb.d/init-db.sh
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U launchlens"]
      interval: 5s
      timeout: 5s
      retries: 5

  # ── PostgreSQL (test — port 5433 for backward compat) ───────
  postgres-test:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: launchlens
      POSTGRES_PASSWORD: password
      POSTGRES_DB: launchlens_test
    ports:
      - "5433:5432"
    volumes:
      - pgdata_test:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U launchlens"]
      interval: 5s
      timeout: 5s
      retries: 5

  # ── Redis ────────────────────────────────────────────────────
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  # ── Temporal ─────────────────────────────────────────────────
  temporal:
    image: temporalio/auto-setup:latest
    environment:
      - DB=postgresql
      - DB_PORT=5432
      - POSTGRES_USER=launchlens
      - POSTGRES_PWD=password
      - POSTGRES_SEEDS=postgres
      - DYNAMIC_CONFIG_FILE_PATH=config/dynamicconfig/development-sql.yaml
    ports:
      - "7233:7233"
    depends_on:
      postgres:
        condition: service_healthy

  # ── Temporal UI ──────────────────────────────────────────────
  temporal-ui:
    image: temporalio/ui:latest
    environment:
      - TEMPORAL_ADDRESS=temporal:7233
      - TEMPORAL_CORS_ORIGINS=http://localhost:3000
    ports:
      - "8233:8080"
    depends_on:
      - temporal

  # ── LaunchLens API ───────────────────────────────────────────
  api:
    build: .
    command: api
    environment:
      - DATABASE_URL=postgresql+asyncpg://launchlens:password@postgres:5432/launchlens
      - DATABASE_URL_SYNC=postgresql://launchlens:password@postgres:5432/launchlens
      - JWT_SECRET=docker-dev-secret-change-in-production-xxxxx
      - TEMPORAL_HOST=temporal:7233
      - REDIS_URL=redis://redis:6379/0
      - APP_ENV=development
      - USE_MOCK_PROVIDERS=true
    ports:
      - "8000:8000"
    volumes:
      - ./src:/app/src
      - ./alembic:/app/alembic
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      temporal:
        condition: service_started

  # ── LaunchLens Temporal Worker ───────────────────────────────
  worker:
    build: .
    command: worker
    environment:
      - DATABASE_URL=postgresql+asyncpg://launchlens:password@postgres:5432/launchlens
      - DATABASE_URL_SYNC=postgresql://launchlens:password@postgres:5432/launchlens
      - JWT_SECRET=docker-dev-secret-change-in-production-xxxxx
      - TEMPORAL_HOST=temporal:7233
      - REDIS_URL=redis://redis:6379/0
      - APP_ENV=development
      - USE_MOCK_PROVIDERS=true
    volumes:
      - ./src:/app/src
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      temporal:
        condition: service_started

volumes:
  pgdata:
  pgdata_test:
```

- [ ] **Step 2: Validate compose file**

```bash
cd /c/Users/Jeff/launchlens && docker compose config --quiet 2>&1 && echo "Valid" || echo "Invalid"
```

- [ ] **Step 3: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add docker-compose.yml && git commit -m "feat: add docker-compose with Postgres, Redis, Temporal, API, and worker"
```

---

### Task 4: Smoke test + documentation + tag

**Files:**
- Modify: `.env.example` (add docker note)

- [ ] **Step 1: Test docker compose starts**

```bash
cd /c/Users/Jeff/launchlens && docker compose up -d postgres postgres-test redis 2>&1 | tail -10
```

Wait for healthy:
```bash
cd /c/Users/Jeff/launchlens && docker compose ps 2>&1
```

- [ ] **Step 2: Verify test DB is accessible on port 5433**

```bash
cd /c/Users/Jeff/launchlens && docker compose exec postgres-test pg_isready -U launchlens 2>&1
```

- [ ] **Step 3: Run Alembic migrations against the test DB**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && DATABASE_URL_SYNC="postgresql://launchlens:password@localhost:5433/launchlens_test" "$PYTHON" -m alembic upgrade head 2>&1 | tail -10
```

- [ ] **Step 4: Run the full test suite**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest --tb=short -q 2>&1 | tail -15
```
Expected: All DB-dependent tests should now PASS with the test container running.

- [ ] **Step 5: Bring up the full stack**

```bash
cd /c/Users/Jeff/launchlens && docker compose up -d 2>&1 | tail -15
```

Verify API is responding:
```bash
curl -s http://localhost:8000/health 2>&1
```
Expected: `{"status":"ok"}`

- [ ] **Step 6: Bring everything down**

```bash
cd /c/Users/Jeff/launchlens && docker compose down 2>&1
```

- [ ] **Step 7: Commit and tag**

```bash
cd /c/Users/Jeff/launchlens && git add .env.example && git commit --allow-empty -m "feat: docker compose dev environment verified" && git tag v0.8.1-docker-compose && echo "Tagged v0.8.1-docker-compose"
```

---

## Quick Reference

```bash
# Start everything
docker compose up -d

# Start just infra (for local Python dev)
docker compose up -d postgres postgres-test redis temporal temporal-ui

# View logs
docker compose logs -f api worker

# Run tests (with test DB running)
docker compose up -d postgres-test
pytest --tb=short -q

# Reset databases
docker compose down -v
docker compose up -d

# Temporal UI
open http://localhost:8233
```

---

## NOT in scope

- Production Docker setup (multi-stage build, non-root user, health endpoints)
- CI/CD Docker images
- Kubernetes / ECS deployment manifests
- SSL/TLS termination
- Database backups
- Log aggregation (ELK/Loki)
- S3 local mock (LocalStack) — deferred; `USE_MOCK_PROVIDERS=true` handles this

## What already exists

- `.env.example` with all env vars documented
- `alembic/` with 4 migrations (001–004)
- `src/launchlens/main.py` — FastAPI app
- `src/launchlens/workflows/worker.py` — Temporal worker entry point
- Tests expect PostgreSQL on `localhost:5433` for test DB
