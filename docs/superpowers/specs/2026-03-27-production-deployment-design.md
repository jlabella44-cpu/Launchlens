# Production Deployment & Monitoring — Design Spec

**Date:** 2026-03-27
**Scope:** AWS ECS Fargate deployment + full observability (logging, metrics, error tracking, alerting)
**Target:** Solo/beta launch

---

## Overview

Deploy LaunchLens to AWS using ECS Fargate with full observability. Infrastructure defined in AWS CDK (Python). CI/CD via GitHub Actions. Monitoring via CloudWatch + Sentry.

---

## Deployment Architecture

### Services (ECS Fargate)

| Service | Image | CPU | Memory | Count |
|---------|-------|-----|--------|-------|
| API | launchlens-api | 0.5 vCPU | 1 GB | 1 |
| Worker | launchlens-worker | 0.5 vCPU | 1 GB | 1 |
| Temporal | temporalio/auto-setup | 0.5 vCPU | 1 GB | 1 |

### Data Stores

| Service | Type | Size |
|---------|------|------|
| PostgreSQL | RDS db.t4g.micro | 20 GB, single-AZ |
| Redis | ElastiCache cache.t4g.micro | single node |
| S3 | Already in use | existing bucket |

### Networking

- **VPC** with 2 public subnets (ALB) + 2 private subnets (services, databases)
- **ALB** with HTTPS termination (ACM certificate)
- **Security groups:** ALB → API (port 8000), API/Worker → RDS (5432), API/Worker → Redis (6379), API/Worker → Temporal (7233)
- No public internet access for services (NAT Gateway for outbound — Kling API, S3, Sentry)

### Secrets

AWS Secrets Manager for:
- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `KLING_ACCESS_KEY` / `KLING_SECRET_KEY`
- `GOOGLE_VISION_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `SENTRY_DSN`

### Container Registry

ECR repositories: `launchlens-api`, `launchlens-worker`

---

## Monitoring & Observability

### Structured Logging

- **Library:** `structlog` with JSON formatter
- **Output:** stdout → CloudWatch Logs (ECS handles log driver)
- **Fields on every line:** timestamp, level, request_id, tenant_id, event
- **Log groups:** `/launchlens/api`, `/launchlens/worker`, `/launchlens/temporal`
- **Retention:** 30 days

### Metrics (CloudWatch Custom Metrics)

Namespace: `LaunchLens`

| Metric | Dimensions | Unit |
|--------|-----------|------|
| `RequestLatency` | endpoint | Milliseconds |
| `RequestCount` | endpoint, status_code | Count |
| `ErrorCount` | endpoint | Count |
| `PipelineStageDuration` | stage (ingestion, vision, packaging, etc.) | Seconds |
| `KlingApiLatency` | — | Milliseconds |
| `KlingApiErrors` | — | Count |
| `ActiveListings` | — | Count |

Implementation: lightweight middleware for request metrics, decorator for pipeline stage timing, explicit calls in KlingProvider.

### Error Tracking (Sentry)

- **SDK:** `sentry-sdk[fastapi]`
- **Integration:** FastAPI ASGI middleware
- **Captures:** unhandled exceptions, request context (URL, method, user_id, tenant_id)
- **Release:** tagged with git SHA from `GIT_SHA` env var
- **Environment:** `production` / `staging`
- **Sample rate:** 1.0 (capture all errors at beta scale)

### Alerting (CloudWatch Alarms → SNS → Email)

| Alarm | Condition | Period |
|-------|-----------|--------|
| API Unhealthy | ALB target health check fails | 1 min, 2 consecutive |
| High Error Rate | ErrorCount / RequestCount > 5% | 5 min |
| High Latency | p95 RequestLatency > 5000ms | 5 min |
| ECS Task Stopped | RunningTaskCount < 1 | 1 min |
| RDS Storage | FreeStorageSpace < 4 GB | 5 min |
| RDS CPU | CPUUtilization > 80% | 5 min |

SNS topic: `launchlens-alerts` → email subscription (configured at deploy time)

### Health Endpoints

- `GET /health` — existing, returns `{"status": "ok"}`
- `GET /health/deep` — new, checks:
  - Database: `SELECT 1`
  - Redis: `PING`
  - Temporal: connection check
  - Returns `{"status": "ok", "database": "ok", "redis": "ok", "temporal": "ok"}` or 503 with failing component

---

## Infrastructure as Code (AWS CDK)

### File Structure

```
infra/
  app.py                  — CDK app entry, instantiates all stacks
  stacks/
    network.py            — VPC, subnets, NAT Gateway, security groups
    database.py           — RDS PostgreSQL, ElastiCache Redis
    services.py           — ECS cluster, task definitions, ALB, ECR repos
    monitoring.py         — CloudWatch dashboard, alarms, SNS topic
    ci.py                 — IAM role for GitHub Actions OIDC
  cdk.json
  requirements.txt
```

### Stack Dependencies

```
network → database → services → monitoring
                  → ci (parallel with services)
```

---

## CI/CD Pipeline (GitHub Actions)

### Workflow: `.github/workflows/deploy.yml`

Trigger: push to `main`

Steps:
1. Run tests (`pytest`)
2. Build Docker image (multi-stage: builder + runtime)
3. Push to ECR
4. Run Alembic migrations (one-off ECS task)
5. Update ECS services (rolling deploy)
6. Notify Sentry of new release
7. Smoke test: `curl https://api.launchlens.com/health/deep`

### Dockerfile Updates

- Multi-stage build (builder installs deps, runtime copies only what's needed)
- Non-root user (`launchlens`)
- Health check: `CMD curl -f http://localhost:8000/health || exit 1`

---

## App-Side Changes

### New Files

```
src/launchlens/monitoring/
  __init__.py             — init_monitoring(app) entry point
  logging.py              — structlog configuration (JSON, request_id binding)
  metrics.py              — CloudWatch metric helpers (emit_metric, time_metric decorator)
  sentry.py               — Sentry SDK init with FastAPI integration
  middleware.py            — RequestMetricsMiddleware (latency, count, errors per endpoint)

src/launchlens/api/health.py  — deep health check endpoint
```

### Modified Files

- `src/launchlens/main.py` — call `init_monitoring(app)` in lifespan
- `src/launchlens/config.py` — add `sentry_dsn`, `aws_region`, `environment` fields
- `Dockerfile` — multi-stage build, non-root user, health check
- `.github/workflows/deploy.yml` — new workflow

### New Dependencies

- `structlog`
- `sentry-sdk[fastapi]`
- `boto3` (already present for S3)

---

## Not In Scope

- Auto-scaling (single task per service for beta)
- Multi-AZ RDS (upgrade when paying customers exist)
- CDN / CloudFront (use S3 presigned URLs for now)
- Custom domain setup (can be added to ALB later)
- Staging environment (deploy to production directly for beta)
- Terraform (using CDK instead)
