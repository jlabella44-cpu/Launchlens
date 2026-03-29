# ListingJet — Project Overview for LLM Sessions

**Tagline:** "From raw listing media to launch-ready marketing in minutes."

ListingJet is a multi-tenant real estate listing media SaaS. Photographers and agents upload raw photos; a 15-agent AI pipeline curates, scores, packages, and delivers MLS-compliant bundles, branded content, AI descriptions, social captions, floor plan 3D scenes, and cinematic video tours. The frontend is a 3D interactive Next.js app.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, PostgreSQL 16 |
| Orchestration | Temporal (durable workflow + activities) |
| Cache | Redis 7 (rate limiting, SSE pub/sub) |
| Storage | AWS S3 (boto3) |
| Auth | JWT (PyJWT), bcrypt |
| Payments | Stripe (checkout, portal, webhooks) |
| AI Vision | Google Cloud Vision API (tier-1), OpenAI GPT-4V (tier-2) |
| AI Content | Anthropic Claude 3 |
| AI Video | Kling AI |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4, React Three Fiber |
| Observability | OpenTelemetry (OTLP), CloudWatch metrics (`services/metrics.py`), Sentry |
| Testing | pytest-asyncio (270+ tests, all passing) |
| CI/CD | GitHub Actions (lint, test, docker build) |

---

## Repository Layout

```
src/listingjet/
  main.py                    FastAPI app factory (create_app, lifespan, router mounts)
  config.py                  Settings (pydantic-settings, .env)
  database.py                SQLAlchemy engine, AsyncSessionLocal, get_db (sets RLS), get_db_admin
  temporal_client.py         TemporalClient singleton (start_pipeline, signal_review)
  telemetry.py               init_tracing() (OTel TracerProvider + OTLP), agent_span() context manager

  models/
    base.py                  TenantScopedModel (id UUID, tenant_id UUID, created_at)
    tenant.py                Tenant (name, plan, stripe_customer_id, stripe_subscription_id, webhook_url, credit_balance)
    user.py                  User (email, password_hash, name, role: UserRole enum)
    listing.py               Listing (address, metadata_, state: ListingState, lock_owner_id, mls_bundle_path, marketing_bundle_path, is_demo, demo_expires_at)
    asset.py                 Asset (listing_id, file_path, file_hash, state, required_for_mls)
    credit_transaction.py    CreditTransaction (tenant_id, amount, balance_after, transaction_type, reason, metadata_)
    social_content.py        SocialContent (listing_id, platform, caption, hashtags, cta)
    vision_result.py         VisionResult (asset_id, tier, room_label, quality_score, commercial_score, hero_candidate)
    package_selection.py     PackageSelection (listing_id, asset_id, channel, position, composite_score)
    event.py                 Event (event_type, payload, tenant_id, listing_id)
    outbox.py                Outbox (event_id, delivered_at)
    learning_weight.py       LearningWeight (tenant_id, room_label, weight)
    brand_kit.py             BrandKit (logo_url, primary_color, secondary_color, font)
    compliance_event.py      ComplianceEvent (asset_id, issue_type, severity)
    label_mapping.py         LabelMapping (raw_label, canonical_label)
    performance_event.py     PerformanceEvent (listing_id, metric_name, value)
    prompt_version.py        PromptVersion (agent_name, version, prompt_text)
    dollhouse_scene.py       DollhouseScene (listing_id, scene_json)
    video_asset.py           VideoAsset (listing_id, video_url, duration_seconds, chapter_markers)
    api_key.py               ApiKey (tenant_id, key_hash, name, last_used_at)

  agents/
    base.py                  BaseAgent ABC: agent_name, execute(), instrumented_execute() [wraps with OTel span + StepTimer]
    ingestion.py             IngestionAgent: dedup by file_hash, S3 upload
    vision.py                VisionAgent: run_tier1 (Google Vision), run_tier2 (GPT-4V top 20), cost tracking
    coverage.py              CoverageAgent: check REQUIRED_SHOTS coverage
    packaging.py             PackagingAgent: composite score, select top 25, → AWAITING_REVIEW
    content.py               ContentAgent: dual-tone descriptions (mls_safe + marketing) via Claude, FHA filter
    brand.py                 BrandAgent: template render → S3 flyer
    learning.py              LearningAgent: read override events, update per-tenant weights
    distribution.py          DistributionAgent: → DELIVERED, emit pipeline.completed
    social_content.py        SocialContentAgent: IG + FB captions via Claude, FHA filtered (Pro+ only)
    mls_export.py            MLSExportAgent: dual ZIP bundles
    photo_compliance.py      PhotoComplianceAgent: detect people/signs/branding in photos
    floorplan.py             FloorplanAgent: GPT-4V → dollhouse JSON
    video.py                 VideoAgent: Kling AI clips → stitched video
    chapter.py               ChapterAgent: GPT-4V keyframes → chapter markers
    social_cuts.py           SocialCutAgent: platform-specific video clips
    video_prompts.py         Room prompts, camera controls, clip transitions

  activities/
    pipeline.py              13 @activity.defn wrappers, all call agent.instrumented_execute()

  workflows/
    listing_pipeline.py      ListingPipeline: Phase 1 (→ AWAITING_REVIEW) → wait signal → Phase 2 (→ DELIVERED)
    worker.py                Temporal worker, init_tracing(), TracingInterceptor wiring

  services/
    auth.py                  hash_password, verify_password, create_access_token, decode_token
    billing.py               BillingService: Stripe customer, checkout, portal, webhook, resolve_plan
    events.py                emit_event() writes Event + Outbox in caller's transaction
    fha_filter.py            fha_check(): 8 FHA regex patterns
    weight_manager.py        WeightManager: blend, score, apply_update
    plan_limits.py           PLAN_LIMITS dict, check_listing_quota, check_asset_quota
    storage.py               StorageService: S3 upload/download/presigned URL
    rate_limiter.py          Redis token bucket rate limiter
    outbox_poller.py         OutboxPoller: polls outbox, delivers to webhook URLs
    metrics.py               track_step_duration, record_step_failure, record_provider_call, record_cost, record_review_turnaround, StepTimer, PROVIDER_COSTS

  monitoring/
    __init__.py              Sentry init (uses settings.sentry_dsn), init_tracing() call

  providers/
    base.py                  VisionProvider, LLMProvider, TemplateProvider ABCs; VisionLabel dataclass
    factory.py               get_vision_provider, get_llm_provider, get_template_provider (USE_MOCK_PROVIDERS flag)
    mock.py                  MockVisionProvider, MockLLMProvider, MockTemplateProvider
    google_vision.py         GoogleVisionProvider + record_provider_call("google_vision", ...)
    openai_vision.py         OpenAIVisionProvider (GPT-4V) + record_provider_call("openai_gpt4v", ...)
    claude.py                ClaudeProvider (Anthropic) + record_provider_call("claude", ...)

  api/
    auth.py                  POST /auth/register, POST /auth/login, GET /auth/me
    listings.py              POST/GET /listings, GET/PATCH /listings/{id}, assets, package, review, approve, export, SSE
    assets.py                GET /assets
    demo.py                  POST /demo/upload, GET /demo/{id}, POST /demo/{id}/claim
    billing.py               POST /billing/checkout, GET /billing/status, POST /billing/portal, POST /billing/webhook
    admin.py                 Tenant CRUD, user management, platform stats, credit management, revenue analytics
    deps.py                  get_current_user, require_admin, get_current_tenant, get_db, get_db_admin
    schemas/
      auth.py                RegisterRequest, LoginRequest, TokenResponse
      listings.py            CreateListingRequest, ListingResponse, etc.
      assets.py              AssetInput, CreateAssetsRequest, AssetResponse
      billing.py             CheckoutRequest/Response, BillingStatusResponse
      admin.py               TenantResponse, TenantDetailResponse, CreditTransactionResponse, TenantCreditsResponse, AdjustCreditsRequest, CreditSummaryResponse, RevenueBreakdownResponse
      demo.py                DemoUploadRequest/Response, DemoViewResponse

  middleware/
    tenant.py                TenantMiddleware: JWT decode → request.state.tenant_id; _PUBLIC_PATHS skip list

alembic/versions/
  001_initial_schema.py      tables + RLS policies
  002_outbox_add_tenant_listing_delivered.py
  003_users_add_password_hash.py
  004_tenant_stripe_fields.py
  005_social_content_export_demo.py
  006_dollhouse_scenes.py
  007_video_assets.py
  008_tenant_webhook_url.py
  009_api_keys.py
  010_credit_transactions.py credit_transactions table + tenants.credit_balance

tests/
  conftest.py                test_engine (NullPool, port 5433), db_session, async_client
  test_agents/               agent unit tests + E2E pipeline smoke
  test_api/                  auth, billing, listings, assets, admin, plan_limits, admin_credits
  test_middleware/           tenant middleware
  test_providers/            mock, factory, storage, rate_limiter, vision providers
  test_services/             events, outbox, fha_filter, weight_manager
  test_workflows/            listing_pipeline, activities, worker
  test_monitoring/           telemetry, pipeline_metrics, instrumented_execute

frontend/src/
  app/
    page.tsx                 Landing page (3D FloatingHouse)
    auth/page.tsx            Login / Register
    listings/page.tsx        Listings dashboard
    listings/[id]/page.tsx   Listing detail (PhotoOrbit, pipeline state, review actions)
    listings/[id]/export/page.tsx  MLS/Marketing ZIP download
    demo/page.tsx            Demo dropzone (no auth)
    demo/[id]/page.tsx       Demo result viewer + claim CTA
    pricing/page.tsx         Plan comparison + upgrade CTAs
    billing/page.tsx         Current plan, usage bars, Stripe portal, invoices
    admin/page.tsx           Admin dashboard: stats, tenant table, credit management
  components/
    layout/nav.tsx           Responsive nav (hamburger on mobile, links on desktop)
    layout/protected-route.tsx  Auth guard
    ui/glass-card.tsx        Glassmorphism card (optional 3D tilt)
    ui/button.tsx            Spring-animated button (min-h-[44px] for touch)
    ui/plan-badge.tsx        Inline upgrade badge for gated features
    listings/listing-card.tsx  3D tilt listing card
    listings/social-preview.tsx  Social caption preview with plan badge
    3d/floating-house.tsx    Three.js R3F scene (landing)
    3d/photo-orbit.tsx       3D photo carousel
    3d/pipeline-visualizer.tsx  State machine 3D visualization
  contexts/
    auth-context.tsx         AuthProvider + useAuth() hook
    plan-context.tsx         PlanProvider + usePlan() + PLAN_LIMITS + isFeatureGated()
  lib/
    api-client.ts            All API calls (auth, listings, billing, admin, demo)
    types.ts                 TypeScript types for all API responses
```

---

## Key Patterns

### Tenant Isolation (RLS)
- PostgreSQL RLS enabled on all tenant-scoped tables (migration 001)
- `get_db` dependency sets `SET LOCAL app.current_tenant = '{tenant_id}'` — **transaction-scoped only, never session-scoped**
- `get_db_admin` skips RLS for cross-tenant admin queries
- `TenantMiddleware` decodes JWT and sets `request.state.tenant_id` on every request

### Agent Pattern
```python
class MyAgent(BaseAgent):
    agent_name = "my_agent"

    async def execute(self, context: AgentContext) -> dict:
        ...
        return {"result": "ok"}
```
- `instrumented_execute(context)` wraps `execute()` with OTel span + `StepTimer`
- All activity functions in `pipeline.py` call `agent.instrumented_execute(context)`
- Provider calls record success/failure via `record_provider_call(provider_name, success)`
- Cost tracking via `record_cost(agent_name, provider_name, call_count)`

### Transaction Pattern
```python
async with (session.begin() if not session.in_transaction() else session.begin_nested()):
    ...
```

### Test DB Override
`conftest.py` overrides `get_db` and `get_db_admin` to use `test_engine` (NullPool, port 5433).

### Credit System
- `CreditTransaction` records every credit event with signed `amount` and denormalized `balance_after`
- `transaction_type`: `purchase` | `usage` | `admin_adjustment` | `expiration` | `bonus`
- `Tenant.credit_balance` is denormalized for fast balance reads (updated atomically with transaction insert)
- Negative balance guard enforced in `POST /admin/tenants/{id}/credits/adjust`
- All adjustments emit a `credits.admin_adjustment` audit event via the outbox

---

## Listing State Machine

```
NEW → UPLOADING → ANALYZING → AWAITING_REVIEW → IN_REVIEW → APPROVED → EXPORTING → DELIVERED
DEMO → (claimed) → UPLOADING → ... (normal flow)
DEMO → (expired) → deleted by cleanup cron
```

- `POST /listings/{id}/assets` → UPLOADING, triggers Temporal pipeline
- Phase 1 finishes → AWAITING_REVIEW
- `POST /listings/{id}/review` → IN_REVIEW (optimistic lock)
- `POST /listings/{id}/approve` → APPROVED, signals Temporal to start Phase 2; records review turnaround metric
- Phase 2: Content → [Brand + Social parallel] → MLS Export → Distribution → DELIVERED
- `GET /listings/{id}/export?mode=mls|marketing` → presigned S3 URL for ZIP

---

## Plan Limits

```python
PLAN_LIMITS = {
    "starter":    {"max_listings_per_month": 5,   "max_assets_per_listing": 25,  "tier2_vision": False, "social_content": False},
    "pro":        {"max_listings_per_month": 50,  "max_assets_per_listing": 50,  "tier2_vision": True,  "social_content": True},
    "enterprise": {"max_listings_per_month": 500, "max_assets_per_listing": 100, "tier2_vision": True,  "social_content": True},
}
```
- SocialContentAgent is skipped in the Temporal workflow for Starter tenants
- Credit purchases are available as add-ons on all plans

---

## Admin API (all require `require_admin`)

| Method | Path | Description |
|--------|------|-------------|
| GET | /admin/tenants | List all tenants |
| GET | /admin/tenants/{id} | Tenant detail (user + listing counts) |
| PATCH | /admin/tenants/{id} | Update name, plan, webhook_url |
| POST | /admin/tenants/{id}/test-webhook | Send test event to tenant webhook |
| GET | /admin/tenants/{id}/users | List users for tenant |
| POST | /admin/tenants/{id}/users | Invite user to tenant |
| PATCH | /admin/users/{id}/role | Change user role |
| GET | /admin/stats | Platform-wide counts |
| GET | /admin/tenants/{id}/credits | Credit balance + transaction history |
| POST | /admin/tenants/{id}/credits/adjust | Manual credit adjustment |
| GET | /admin/credits/summary | Platform credit stats (this month) |
| GET | /admin/analytics/revenue | Revenue breakdown, top tenants by usage |

---

## Observability

- **OTel tracing**: `telemetry.py` — `init_tracing()` sets up `TracerProvider` + OTLP gRPC exporter; `agent_span()` async context manager adds agent_name + listing_id + result fields as span attributes
- **Pipeline metrics**: `services/metrics.py` — `StepTimer` records step duration; `record_step_failure`, `record_provider_call`, `record_cost`, `record_review_turnaround`
- **Temporal**: `TracingInterceptor` from `temporalio.contrib.opentelemetry` wired into both client and worker (gracefully skipped if import fails)
- **Sentry**: initialized in `monitoring/__init__.py` via `settings.sentry_dsn`; `settings.git_sha` used for release tracking

---

## Database Migrations (Alembic)

| Migration | Description |
|-----------|-------------|
| 001 | Initial schema (all core tables) + RLS policies |
| 002 | Outbox: add tenant_id, listing_id, delivered_at |
| 003 | Users: add password_hash |
| 004 | Tenants: stripe_customer_id, stripe_subscription_id |
| 005 | social_content, demo state, export paths |
| 006 | dollhouse_scenes table |
| 007 | video_assets table |
| 008 | tenants.webhook_url |
| 009 | api_keys table |
| 010 | credit_transactions table + tenants.credit_balance |

---

## CI/CD

| Workflow | File | Trigger |
|----------|------|---------|
| Lint | `.github/workflows/lint.yml` | push / PR |
| Test | `.github/workflows/test.yml` | push / PR — 2 Postgres service containers |
| Docker | `.github/workflows/docker.yml` | push to main |

---

## Frontend Architecture

- **Next.js 16** App Router, all pages are server components or `"use client"` client components
- **Design system**: Cinzel (headings), Josefin Sans (body); Primary `#2563EB`, CTA `#F97316`; glassmorphism cards
- **3D**: React Three Fiber components wrapped in `hidden lg:block` for desktop-only rendering
- **Mobile first**: all layouts work at 375px+; hamburger nav at `md:hidden`; `min-h-[44px]` touch targets
- **Auth**: `AuthContext` stores JWT in memory, `ProtectedRoute` wraps all authenticated pages
- **Plan gating**: `PlanContext` fetches billing status on mount; `isFeatureGated(feature)` checks plan limits; `PlanBadge` renders inline upgrade prompt
- **API client**: `frontend/src/lib/api-client.ts` — single export `apiClient` with typed methods for all endpoints

---

## How to Run

```bash
# Infrastructure
docker compose up -d postgres postgres-test redis temporal temporal-ui

# Migrations
python -m alembic upgrade head

# API
uvicorn listingjet.main:app --reload --port 8000

# Worker
python -m listingjet.workflows.worker

# Tests
python -m pytest --tb=short -q

# Frontend
cd frontend && npm run dev
```

Services: API http://localhost:8000 · Swagger http://localhost:8000/docs · Temporal UI http://localhost:8233 · Frontend http://localhost:3000
