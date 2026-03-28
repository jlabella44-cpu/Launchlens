# App-Side Monitoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add full observability to LaunchLens — CloudWatch metrics, Sentry error tracking, request metrics middleware, and a deep health check endpoint.

**Architecture:** A `monitoring/` package initializes Sentry and provides a CloudWatch metrics helper. A `RequestMetricsMiddleware` records latency, count, and error rate per endpoint. A `@time_metric` decorator times pipeline stages. Deep health checks verify DB, Redis, and Temporal connectivity. All wired into the existing FastAPI app via `init_monitoring()`.

**Tech Stack:** sentry-sdk[fastapi], boto3 (CloudWatch), redis, temporalio, pytest

---

## File Structure

```
src/launchlens/
  monitoring/
    __init__.py              CREATE — init_monitoring(app) entry point
    sentry.py                CREATE — Sentry SDK init
    metrics.py               CREATE — CloudWatch metric helpers (emit_metric, time_metric)
    middleware.py             CREATE — RequestMetricsMiddleware

  api/
    health.py                CREATE — deep health check endpoint (extracted from main.py)

  config.py                  MODIFY — add sentry_dsn, environment fields
  main.py                    MODIFY — wire monitoring, extract health to router

tests/
  test_monitoring/
    test_metrics.py          CREATE
    test_middleware.py        CREATE
    test_health.py           CREATE
    test_sentry.py           CREATE
```

---

## Tasks

---

### Task 1: Config fields + Sentry init

**Files:**
- Modify: `src/launchlens/config.py`
- Create: `src/launchlens/monitoring/__init__.py`
- Create: `src/launchlens/monitoring/sentry.py`
- Create: `tests/test_monitoring/test_sentry.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_monitoring/__init__.py` (empty) and `tests/test_monitoring/test_sentry.py`:

```python
# tests/test_monitoring/test_sentry.py
from unittest.mock import patch, MagicMock


def test_init_sentry_with_dsn():
    from launchlens.monitoring.sentry import init_sentry
    with patch("launchlens.monitoring.sentry.sentry_sdk") as mock_sdk:
        init_sentry(dsn="https://test@sentry.io/123", environment="production", release="abc123")
        mock_sdk.init.assert_called_once()
        call_kwargs = mock_sdk.init.call_args[1]
        assert call_kwargs["dsn"] == "https://test@sentry.io/123"
        assert call_kwargs["environment"] == "production"
        assert call_kwargs["release"] == "abc123"


def test_init_sentry_skips_without_dsn():
    from launchlens.monitoring.sentry import init_sentry
    with patch("launchlens.monitoring.sentry.sentry_sdk") as mock_sdk:
        init_sentry(dsn="", environment="development", release="")
        mock_sdk.init.assert_not_called()


def test_monitoring_init_exists():
    from launchlens.monitoring import init_monitoring
    assert callable(init_monitoring)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_monitoring/test_sentry.py -v 2>&1 | tail -10
```

- [ ] **Step 3: Add config fields**

In `src/launchlens/config.py`, add after the `aws_region` field:

```python
    # Monitoring
    sentry_dsn: str = ""
    environment: str = "development"
    git_sha: str = ""
```

- [ ] **Step 4: Create Sentry module**

Create `src/launchlens/monitoring/sentry.py`:

```python
"""Sentry SDK initialization for error tracking."""

import logging

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

logger = logging.getLogger(__name__)


def init_sentry(dsn: str, environment: str, release: str) -> None:
    """Initialize Sentry SDK. No-op if dsn is empty."""
    if not dsn:
        logger.info("Sentry DSN not configured, skipping initialization")
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=0.1,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
        ],
    )
    logger.info("Sentry initialized for environment=%s release=%s", environment, release)
```

- [ ] **Step 5: Create monitoring __init__**

Create `src/launchlens/monitoring/__init__.py`:

```python
"""Monitoring package — initializes all observability components."""

import logging

from fastapi import FastAPI

from launchlens.config import settings
from launchlens.monitoring.sentry import init_sentry

logger = logging.getLogger(__name__)


def init_monitoring(app: FastAPI) -> None:
    """Initialize all monitoring: Sentry, metrics middleware."""
    init_sentry(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=settings.git_sha,
    )
    logger.info("Monitoring initialized")
```

- [ ] **Step 6: Add sentry-sdk dependency**

In `pyproject.toml`, add to the `dependencies` list:

```
    "sentry-sdk[fastapi]>=2.0",
```

- [ ] **Step 7: Run test**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_monitoring/test_sentry.py -v 2>&1 | tail -10
```

- [ ] **Step 8: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/monitoring/ src/launchlens/config.py pyproject.toml tests/test_monitoring/ && git commit -m "feat: add Sentry integration and monitoring package"
```

---

### Task 2: CloudWatch metrics helper

**Files:**
- Create: `src/launchlens/monitoring/metrics.py`
- Create: `tests/test_monitoring/test_metrics.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_monitoring/test_metrics.py`:

```python
# tests/test_monitoring/test_metrics.py
import asyncio
from unittest.mock import patch, MagicMock
import pytest


def test_emit_metric_calls_cloudwatch():
    from launchlens.monitoring.metrics import emit_metric
    mock_client = MagicMock()
    with patch("launchlens.monitoring.metrics._get_cloudwatch_client", return_value=mock_client):
        emit_metric("RequestCount", 1, unit="Count", dimensions={"endpoint": "/health"})
        mock_client.put_metric_data.assert_called_once()
        call_args = mock_client.put_metric_data.call_args[1]
        assert call_args["Namespace"] == "LaunchLens"
        metric = call_args["MetricData"][0]
        assert metric["MetricName"] == "RequestCount"
        assert metric["Value"] == 1


def test_emit_metric_noop_in_development():
    from launchlens.monitoring.metrics import emit_metric
    with patch("launchlens.monitoring.metrics.settings") as mock_settings:
        mock_settings.environment = "development"
        # Should not raise, just no-op
        emit_metric("RequestCount", 1)


def test_time_metric_decorator():
    from launchlens.monitoring.metrics import time_metric

    @time_metric("TestDuration")
    async def slow_function():
        await asyncio.sleep(0.01)
        return "done"

    with patch("launchlens.monitoring.metrics.emit_metric") as mock_emit:
        result = asyncio.get_event_loop().run_until_complete(slow_function())
        assert result == "done"
        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        assert call_args[0][0] == "TestDuration"
        assert call_args[0][1] >= 10  # at least 10ms
```

- [ ] **Step 2: Implement metrics module**

Create `src/launchlens/monitoring/metrics.py`:

```python
"""CloudWatch custom metrics helpers."""

import functools
import logging
import time

import boto3

from launchlens.config import settings

logger = logging.getLogger(__name__)

_cloudwatch_client = None


def _get_cloudwatch_client():
    global _cloudwatch_client
    if _cloudwatch_client is None:
        _cloudwatch_client = boto3.client("cloudwatch", region_name=settings.aws_region)
    return _cloudwatch_client


def emit_metric(
    name: str,
    value: float,
    unit: str = "None",
    dimensions: dict[str, str] | None = None,
) -> None:
    """Emit a CloudWatch custom metric. No-op in development."""
    if settings.environment == "development":
        return

    try:
        cw_dimensions = [{"Name": k, "Value": v} for k, v in (dimensions or {}).items()]
        _get_cloudwatch_client().put_metric_data(
            Namespace="LaunchLens",
            MetricData=[
                {
                    "MetricName": name,
                    "Value": value,
                    "Unit": unit,
                    "Dimensions": cw_dimensions,
                }
            ],
        )
    except Exception:
        logger.exception("Failed to emit metric %s", name)


def time_metric(metric_name: str, dimensions: dict[str, str] | None = None):
    """Decorator that times an async function and emits the duration as a metric."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                return await func(*args, **kwargs)
            finally:
                duration_ms = (time.monotonic() - start) * 1000
                emit_metric(metric_name, duration_ms, unit="Milliseconds", dimensions=dimensions)
        return wrapper
    return decorator
```

- [ ] **Step 3: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_monitoring/test_metrics.py -v 2>&1 | tail -10
```

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/monitoring/metrics.py tests/test_monitoring/test_metrics.py && git commit -m "feat: add CloudWatch metrics helper and time_metric decorator"
```

---

### Task 3: Request metrics middleware

**Files:**
- Create: `src/launchlens/monitoring/middleware.py`
- Create: `tests/test_monitoring/test_middleware.py`
- Modify: `src/launchlens/monitoring/__init__.py`
- Modify: `src/launchlens/main.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_monitoring/test_middleware.py`:

```python
# tests/test_monitoring/test_middleware.py
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_request_metrics_middleware_emits_metrics(async_client: AsyncClient):
    """Middleware should emit RequestLatency and RequestCount metrics."""
    with patch("launchlens.monitoring.middleware.emit_metric") as mock_emit:
        resp = await async_client.get("/health")
        assert resp.status_code == 200

        # Should have been called for latency and count
        metric_names = [call.args[0] for call in mock_emit.call_args_list]
        assert "RequestLatency" in metric_names
        assert "RequestCount" in metric_names


@pytest.mark.asyncio
async def test_request_metrics_tracks_errors(async_client: AsyncClient):
    """Middleware should emit ErrorCount for 4xx/5xx responses."""
    with patch("launchlens.monitoring.middleware.emit_metric") as mock_emit:
        # Hit a nonexistent route to get a 404
        resp = await async_client.get("/nonexistent-route-xyz")

        error_calls = [c for c in mock_emit.call_args_list if c.args[0] == "ErrorCount"]
        if resp.status_code >= 400:
            assert len(error_calls) >= 1
```

- [ ] **Step 2: Implement middleware**

Create `src/launchlens/monitoring/middleware.py`:

```python
"""Request metrics middleware — records latency, count, and errors per endpoint."""

import logging
import time

from fastapi import Request
from starlette.responses import Response

from launchlens.monitoring.metrics import emit_metric

logger = logging.getLogger(__name__)


class RequestMetricsMiddleware:
    """Emits CloudWatch metrics for every request: latency, count, errors."""

    async def __call__(self, request: Request, call_next) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000

        endpoint = request.url.path
        status = str(response.status_code)

        emit_metric(
            "RequestLatency",
            duration_ms,
            unit="Milliseconds",
            dimensions={"endpoint": endpoint},
        )
        emit_metric(
            "RequestCount",
            1,
            unit="Count",
            dimensions={"endpoint": endpoint, "status_code": status},
        )

        if response.status_code >= 400:
            emit_metric(
                "ErrorCount",
                1,
                unit="Count",
                dimensions={"endpoint": endpoint},
            )

        return response
```

- [ ] **Step 3: Wire middleware into monitoring init**

Update `src/launchlens/monitoring/__init__.py`:

```python
"""Monitoring package — initializes all observability components."""

import logging

from fastapi import FastAPI

from launchlens.config import settings
from launchlens.monitoring.sentry import init_sentry
from launchlens.monitoring.middleware import RequestMetricsMiddleware

logger = logging.getLogger(__name__)


def init_monitoring(app: FastAPI) -> None:
    """Initialize all monitoring: Sentry, request metrics middleware."""
    init_sentry(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=settings.git_sha,
    )

    app.middleware("http")(RequestMetricsMiddleware())

    logger.info("Monitoring initialized")
```

- [ ] **Step 4: Wire into main.py**

In `src/launchlens/main.py`, add import at the top:

```python
from launchlens.monitoring import init_monitoring
```

Add this line inside `create_app()`, after the middleware stack and before `app.include_router(...)`:

```python
    init_monitoring(app)
```

- [ ] **Step 5: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_monitoring/ -v 2>&1 | tail -15
```

- [ ] **Step 6: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/monitoring/ src/launchlens/main.py tests/test_monitoring/test_middleware.py && git commit -m "feat: add RequestMetricsMiddleware with CloudWatch latency/count/error metrics"
```

---

### Task 4: Deep health check endpoint

**Files:**
- Create: `src/launchlens/api/health.py`
- Create: `tests/test_monitoring/test_health.py`
- Modify: `src/launchlens/main.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_monitoring/test_health.py`:

```python
# tests/test_monitoring/test_health.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(async_client: AsyncClient):
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "checks" in data


@pytest.mark.asyncio
async def test_deep_health_returns_component_status(async_client: AsyncClient):
    resp = await async_client.get("/health/deep")
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "database" in data
    assert "redis" in data
    assert "temporal" in data
    assert "status" in data


@pytest.mark.asyncio
async def test_deep_health_database_ok(async_client: AsyncClient):
    """Test DB should be reachable via the test conftest setup."""
    resp = await async_client.get("/health/deep")
    data = resp.json()
    assert data["database"] == "ok"
```

- [ ] **Step 2: Create health router**

Create `src/launchlens/api/health.py`:

```python
"""Health check endpoints."""

import logging

import redis.asyncio as aioredis
import sqlalchemy
from fastapi import APIRouter
from starlette.responses import JSONResponse

from launchlens.config import settings
from launchlens.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Basic health check — tests DB connectivity."""
    checks = {"api": "ok"}

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(sqlalchemy.text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "ok" if all_ok else "degraded", "checks": checks}


@router.get("/health/deep")
async def deep_health():
    """Deep health check — verifies DB, Redis, and Temporal connectivity."""
    components = {}

    # Database
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(sqlalchemy.text("SELECT 1"))
        components["database"] = "ok"
    except Exception as e:
        logger.warning("Health check: database failed: %s", e)
        components["database"] = f"error: {e}"

    # Redis
    try:
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
        components["redis"] = "ok"
    except Exception as e:
        logger.warning("Health check: redis failed: %s", e)
        components["redis"] = f"error: {e}"

    # Temporal
    try:
        from temporalio.client import Client
        client = await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)
        await client.service_client.check_health()
        components["temporal"] = "ok"
    except Exception as e:
        logger.warning("Health check: temporal failed: %s", e)
        components["temporal"] = f"error: {e}"

    all_ok = all(v == "ok" for v in components.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if all_ok else "degraded", **components},
    )
```

- [ ] **Step 3: Wire into main.py**

In `src/launchlens/main.py`:

1. Add import: `from launchlens.api import health`
2. Replace the inline `/health` endpoint with a router include. Remove the `@app.get("/health")` block (lines 53-67) and add:

```python
    app.include_router(health.router)
```

Add it after the other `app.include_router(...)` calls.

- [ ] **Step 4: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_monitoring/test_health.py -v 2>&1 | tail -10
```

- [ ] **Step 5: Run full test suite**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest --tb=short -q 2>&1 | tail -5
```

- [ ] **Step 6: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/api/health.py src/launchlens/main.py tests/test_monitoring/test_health.py && git commit -m "feat: add deep health check endpoint (/health/deep) with DB, Redis, Temporal checks"
```

---

### Task 5: Production Dockerfile + deploy workflow

**Files:**
- Modify: `Dockerfile`
- Create: `.github/workflows/deploy.yml`
- Create: `.env.production.example`

- [ ] **Step 1: Update Dockerfile for production**

Replace `Dockerfile` with:

```dockerfile
# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src/ src/
RUN pip install --no-cache-dir -e .

# Runtime stage
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN useradd --create-home --shell /bin/bash launchlens
USER launchlens

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

COPY alembic/ alembic/
COPY alembic.ini ./
COPY docker/entrypoint.sh ./entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["./entrypoint.sh"]
CMD ["api"]
```

- [ ] **Step 2: Create deploy workflow**

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  AWS_REGION: us-east-1
  ECR_REPO_API: launchlens-api
  ECR_REPO_WORKER: launchlens-worker
  ECS_CLUSTER: launchlens
  ECS_SERVICE_API: launchlens-api
  ECS_SERVICE_WORKER: launchlens-worker

permissions:
  id-token: write
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: launchlens
          POSTGRES_PASSWORD: password
          POSTGRES_DB: launchlens_test
        ports: ["5433:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      DATABASE_URL: "postgresql+asyncpg://launchlens:password@localhost:5433/launchlens_test"
      DATABASE_URL_SYNC: "postgresql://launchlens:password@localhost:5433/launchlens_test"
      JWT_SECRET: "test-secret"
      REDIS_URL: "redis://localhost:6379/0"
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: python -m alembic upgrade head
      - run: python -m pytest --tb=short -q

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to ECR
        id: ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push API image
        env:
          REGISTRY: ${{ steps.ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $REGISTRY/$ECR_REPO_API:$IMAGE_TAG -t $REGISTRY/$ECR_REPO_API:latest .
          docker push $REGISTRY/$ECR_REPO_API:$IMAGE_TAG
          docker push $REGISTRY/$ECR_REPO_API:latest

      - name: Run migrations
        env:
          REGISTRY: ${{ steps.ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          aws ecs run-task \
            --cluster $ECS_CLUSTER \
            --task-definition launchlens-migrate \
            --launch-type FARGATE \
            --network-configuration "$(aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE_API --query 'services[0].networkConfiguration' --output json)" \
            --overrides '{"containerOverrides":[{"name":"migrate","command":["python","-m","alembic","upgrade","head"]}]}'

      - name: Deploy API service
        run: |
          aws ecs update-service --cluster $ECS_CLUSTER --service $ECS_SERVICE_API --force-new-deployment
          aws ecs update-service --cluster $ECS_CLUSTER --service $ECS_SERVICE_WORKER --force-new-deployment

      - name: Notify Sentry
        if: always()
        env:
          SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
        run: |
          curl -sL https://sentry.io/api/0/organizations/${{ secrets.SENTRY_ORG }}/releases/ \
            -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" \
            -H "Content-Type: application/json" \
            -d '{"version":"${{ github.sha }}","projects":["launchlens"]}' || true
```

- [ ] **Step 3: Create env example**

Create `.env.production.example`:

```bash
# App
APP_ENV=production
LOG_LEVEL=INFO
ENVIRONMENT=production
GIT_SHA=  # set by CI

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@rds-host:5432/launchlens
DATABASE_URL_SYNC=postgresql://user:pass@rds-host:5432/launchlens

# Auth
JWT_SECRET=  # generate: python -c "import secrets; print(secrets.token_urlsafe(32))"

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Redis
REDIS_URL=redis://elasticache-host:6379/0

# Temporal
TEMPORAL_HOST=temporal-host:7233

# S3
S3_BUCKET_NAME=launchlens-prod
AWS_REGION=us-east-1

# Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_VISION_API_KEY=...

# Video
KLING_ACCESS_KEY=...
KLING_SECRET_KEY=...

# Monitoring
SENTRY_DSN=https://...@sentry.io/...
```

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add Dockerfile .github/workflows/deploy.yml .env.production.example && git commit -m "feat: production Dockerfile (multi-stage, non-root) + deploy workflow + env example"
```

---

## NOT in scope

- AWS CDK infrastructure stacks (separate plan — requires AWS account setup)
- CloudWatch dashboard creation (done via CDK or console)
- CloudWatch alarms (done via CDK)
- SNS topic setup (done via CDK)
- Custom domain / SSL cert (manual or CDK)
- Auto-scaling rules
