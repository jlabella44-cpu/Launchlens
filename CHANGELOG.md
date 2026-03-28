# Changelog

All notable changes to LaunchLens are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added
- OpenTelemetry tracing spans wired into all 15 agents via `BaseAgent.instrumented_execute()`
- CloudWatch-style pipeline metrics: step duration, step failures, provider call success/failure, per-step costs
- Review turnaround time metric recorded on `POST /listings/{id}/approve`
- Temporal `TracingInterceptor` wired into workflow worker for distributed trace propagation
- `StepTimer` context manager for consistent duration recording
- Sentry integration: `sentry_dsn` and `git_sha` config fields, SDK initialized in monitoring module

### Fixed
- `config.py` was missing `sentry_dsn` and `git_sha` fields — monitoring module used fragile `getattr()` fallbacks
- `sentry-sdk`, `opentelemetry-api/sdk`, and `opentelemetry-exporter-otlp-proto-grpc` missing from `pyproject.toml`
- `tests/test_monitoring/__init__.py` missing — caused test discovery failure
- `.env.production.example` had redundant `ENVIRONMENT=production` (config uses `APP_ENV`)

---

## [1.2.0] — 2026-03-28

### Added
- **Credit system**: `CreditTransaction` model with signed `amount`, `balance_after`, `transaction_type` (purchase / usage / admin_adjustment / expiration / bonus)
- Denormalized `credit_balance` column on `Tenant` for fast reads
- Alembic migration 010: `credit_transactions` table + composite index + `tenants.credit_balance`
- `GET /admin/tenants/{id}/credits` — credit balance + paginated transaction history
- `POST /admin/tenants/{id}/credits/adjust` — manual credit adjustment with negative-balance guard and full audit trail (emits `credits.admin_adjustment` event)
- `GET /admin/credits/summary` — platform-wide credit stats (outstanding, purchased/used/adjusted this month, tenant count)
- `GET /admin/analytics/revenue` — subscription count, credit purchase totals, top-10 tenants by usage, avg credits per listing
- Admin frontend dashboard at `/admin`: platform stats, tenant table with credit balances sortable by name/plan/credits, credit adjustment form, transaction history
- `credit_balance` field exposed on `TenantResponse` and `TenantDetailResponse`
- 10 new integration tests for all credit endpoints

---

## [1.1.0] — 2026-03-27

### Added
- **Mobile responsiveness**: responsive layout across all pages (375px+), hamburger navigation drawer, `hidden lg:block` for 3D components on small screens
- Touch targets: all buttons `min-h-[44px]`, `touch-action: manipulation` globally
- `PlanContext` + `usePlan()` hook for frontend plan-gating
- `PlanBadge` component to surface upgrade prompts inline (e.g., Social Content feature)
- Billing page (`/billing`): current plan card, usage bars, Stripe portal link, invoice table
- Webhook plan resolution fix: `checkout.session.completed` now resolves plan from Stripe line items, falls back to subscription retrieval — was always hard-coding "pro"
- Alembic migration 009: API keys table

### Fixed
- Billing webhook always setting `tenant.plan = "pro"` regardless of purchased price ID

---

## [1.0.1] — 2026-03-27

### Added
- Frontend remaining pages: demo dropzone landing (`/demo`), demo result viewer (`/demo/[id]`), export download with MLS/Marketing toggle (`/listings/[id]/export`), social media preview cards, pricing page with Media OS copy
- Video player with chapter timeline on listing detail page
- Webhook delivery service with retry logic and signature validation
- Tenant webhook URL support: `PATCH /admin/tenants/{id}` accepts `webhook_url`; `POST /admin/tenants/{id}/test-webhook` sends test event
- Alembic migration 008: `tenants.webhook_url` column

---

## [1.0.0] — 2026-03-27

### Added
- Full interactive frontend: Next.js 16, React 19, TypeScript, Tailwind CSS 4
- 3D components: `FloatingHouse` (landing), `PhotoOrbit` (listing detail carousel), `PipelineVisualizer` (state machine visualization) — React Three Fiber
- Glassmorphism design system (GlassCard, animated Button, spring-based transitions)
- All frontend pages: auth (login/register), listings dashboard, listing detail, 3D scene wrappers
- Framer Motion page transitions and stagger animations

---

## [0.9.2] — 2026-03-27

### Added
- **Video pipeline**: `VideoAgent` (Kling AI image-to-video, photo selection, clip generation, stitching), `ChapterAgent` (GPT-4V keyframe analysis → chapter markers), `SocialCutAgent` (platform clips for IG/TikTok/FB/YT Shorts)
- Kling AI provider (`KLING_ACCESS_KEY`, `KLING_SECRET_KEY`, `KLING_API_BASE_URL`)
- `video_assets` table (migration 007), `video_score_floor`/`video_max_photos`/`video_clip_duration` config
- Video API endpoints wired into Temporal Phase 2
- 16 new tests

---

## [0.9.1] — 2026-03-27

### Added
- **FloorplanAgent**: GPT-4V analyzes floorplan photos → structured room/wall/door JSON for 3D dollhouse rendering
- Dollhouse scenes table (migration 006), `GET /listings/{id}/dollhouse` endpoint
- `PhotoComplianceAgent`: detects compliance issues (people, signs, branding) in photos
- 8 new tests

---

## [0.9.0] — 2026-03-27 — Listing Media OS

### Added
- **SocialContentAgent**: Instagram + Facebook captions via Claude with FHA filtering (Pro+ plan only)
- **MLSExportAgent**: dual ZIP bundle export — MLS-unbranded + Marketing-branded
- **ContentAgent dual-tone**: single Claude call returns both `mls_safe` and `marketing` descriptions
- Export endpoint: `GET /listings/{id}/export?mode=mls|marketing` → presigned S3 URL
- Demo pipeline: unauthenticated upload → AI results → register → claim (`POST /demo/upload`, `GET /demo/{id}`, `POST /demo/{id}/claim`)
- Temporal parallel Phase 2: Brand + Social run concurrently after Content
- `social_content`, `demo` tables (migration 005)
- Strategic repositioning: PRD v3 "Listing Media OS"
- 21 new tests

---

## [0.8.3] — 2026-03-27

### Added
- GitHub Actions CI: `lint.yml` (ruff), `test.yml` (pytest with 2 Postgres containers), `docker.yml` (build validation)

---

## [0.8.2] — 2026-03-27

### Added
- Admin dashboard API: `GET /admin/tenants` (list + filter), `GET /admin/tenants/{id}` (detail + counts), `PATCH /admin/tenants/{id}` (update name/plan/webhook), `GET/POST /admin/tenants/{id}/users`, `PATCH /admin/users/{id}/role`, `GET /admin/stats`
- 12 new tests

---

## [0.8.1] — 2026-03-27

### Added
- Docker Compose full dev environment: postgres, postgres-test, redis, temporal, temporal-ui, api, worker
- `docker/entrypoint.sh`: waits for postgres, runs alembic, dispatches `api`/`worker`/`test`
- `docker/init-db.sh`: creates `launchlens_test` database

---

## [0.8.0] — 2026-03-27

### Added
- Plan enforcement: `PLAN_LIMITS` dict (starter/pro/enterprise), `check_listing_quota`, `check_asset_quota`
- Starter: 5 listings/month, 25 assets/listing, no tier-2 vision, no social content
- Pro: 50 listings/month, 50 assets/listing, full pipeline
- Enterprise: 500 listings/month, 100 assets/listing, full pipeline
- SocialContentAgent skipped in workflow for Starter tenants
- 12 new tests

---

## [0.7.0] — 2026-03-27

### Added
- Temporal wiring: `ListingPipeline` workflow (Phase 1 + approve signal + Phase 2), `create_worker()`, activity definitions
- `POST /listings/{id}/assets` triggers Temporal workflow via `TemporalClient`
- `POST /listings/{id}/approve` sends signal to running workflow
- 10 new tests

---

## [0.6.0] — 2026-03-26

### Added
- Full listing API: `POST /listings`, `GET /listings`, `GET /listings/{id}`, `PATCH /listings/{id}`, `POST /listings/{id}/assets`, `GET /listings/{id}/assets`, `GET /listings/{id}/package`, `POST /listings/{id}/review`, `POST /listings/{id}/approve`
- SSE endpoint: `GET /webhook/sse` for real-time pipeline events
- Outbox poller service for reliable event delivery
- 20 new tests

---

## [0.5.0] — 2026-03-26

### Added
- Stripe integration: `BillingService` (customer creation, checkout, portal, webhook handler)
- `POST /billing/checkout`, `GET /billing/status`, `POST /billing/portal`, `POST /billing/webhook`
- Stripe price ID config (`STRIPE_PRICE_STARTER`, `STRIPE_PRICE_PRO`, `STRIPE_PRICE_ENTERPRISE`)
- Tenant stripe fields migration (004)
- 10 new tests

---

## [0.4.0] — 2026-03-26

### Added
- Auth: `POST /auth/register` (creates Tenant + admin User), `POST /auth/login` (JWT), `GET /auth/me`
- `get_current_user`, `require_admin` FastAPI dependencies
- `TenantMiddleware`: JWT decode on every request, sets `request.state.tenant_id`
- bcrypt password hashing, JWT with configurable expiry
- `users` password_hash migration (003)
- 16 new tests

---

## [0.3.0] — 2026-03-25

### Added
- Full 8-agent pipeline: `IngestionAgent`, `VisionAgent` (tier-1 + tier-2), `CoverageAgent`, `PackagingAgent`, `ContentAgent`, `BrandAgent`, `LearningAgent`, `DistributionAgent`
- `BaseAgent` ABC with `AgentContext`, session injection pattern
- Listing state machine: NEW → UPLOADING → ANALYZING → AWAITING_REVIEW → IN_REVIEW → APPROVED → EXPORTING → DELIVERED
- E2E smoke test: full pipeline from ingest to delivery
- ~50 new tests

---

## [0.2.0] — 2026-03-25

### Added
- AI provider abstractions: `VisionProvider`, `LLMProvider`, `TemplateProvider` ABCs
- `GoogleVisionProvider`, `OpenAIVisionProvider` (GPT-4V), `ClaudeProvider`, `MockProviders`
- `StorageService` (S3 upload/download with presigned URLs)
- `RateLimiter` (Redis token bucket)
- `emit_event` + `OutboxPoller` for reliable event delivery
- `WeightManager` for per-tenant learning weights
- ~40 new tests

---

## [0.1.0] — 2026-03-25

### Added
- Project scaffold: FastAPI app, SQLAlchemy 2.0 async engine, Alembic
- Initial schema (migration 001): all tables + Row-Level Security policies
- `TenantScopedModel` base, `Tenant`, `User`, `Listing`, `Asset`, `Event`, `Outbox` models
- pydantic-settings config, JWT auth skeleton
- ~20 initial tests
