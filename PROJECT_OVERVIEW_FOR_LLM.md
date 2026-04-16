# ListingJet — Project Overview for LLM Sessions

**Tagline:** "From raw listing media to launch-ready marketing in minutes."

ListingJet is a multi-tenant real estate listing media SaaS. Photographers and agents upload raw photos; a 20+ agent AI pipeline curates, scores, packages, and delivers MLS-compliant bundles, branded content, AI descriptions, social captions, floor plan 3D scenes, virtual staging, and cinematic video tours. The frontend is a 3D interactive Next.js app with a white-label brokerage deployment option.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, PostgreSQL 16 |
| Orchestration | Temporal (durable workflow + activities) |
| Cache | Redis 7 (rate limiting, SSE pub/sub, auth lockout) |
| Storage | AWS S3 (boto3) — full-res + 1024px proxy pipeline |
| Auth | JWT (PyJWT), bcrypt, httpOnly cookies, Redis-backed blocklist + lockout |
| Payments | Stripe (checkout, portal, webhooks, credit bundles, addons) |
| AI Vision | Google Cloud Vision API (tier-1), Qwen 3.6 Plus / GPT-4V (tier-2) |
| AI Content | Anthropic Claude (default provider via factory) |
| AI Video | Kling AI (clip generation) + FFmpeg (stitching, H.264) |
| Virtual Staging | Pluggable provider via factory |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4, React Three Fiber |
| Observability | OpenTelemetry (OTLP), CloudWatch metrics (`services/metrics.py`), Sentry |
| Testing | pytest-asyncio (500+ tests), Playwright E2E (9 specs) |
| CI/CD | GitHub Actions (lint, test, docker), deploy gated on tests |
| Privacy/Compliance | GDPR Art. 6/7 + CCPA: separate AI consent, audit log, agent-level guards, data export, cascade deletion, Fernet field encryption for IDX keys |

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
    tenant.py                Tenant (name, plan, billing_model, stripe_customer_id, stripe_subscription_id, webhook_url, per_listing_credit_cost)
    user.py                  User (email, password_hash, name, role, consent_at/version, ai_consent_at/version)
    listing.py               Listing (address, metadata_, state: ListingState, lock_owner_id, credit_cost, mls_bundle_path, marketing_bundle_path, is_demo, demo_expires_at)
    asset.py                 Asset (listing_id, file_path, proxy_path, file_hash, state, required_for_mls)
    credit_account.py        CreditAccount (tenant_id, balance, granted_balance, purchased_balance, rollover_cap) — sole source of truth
    credit_transaction.py    CreditTransaction (tenant_id, amount, transaction_type, reference_type, reference_id, description)
    addon_purchase.py        AddonPurchase (listing_id, addon_slug, price_credits, status)
    social_content.py        SocialContent (listing_id, platform, caption, hashtags, cta)
    vision_result.py         VisionResult (asset_id, tier, room_label, quality_score, commercial_score, hero_candidate)
    package_selection.py     PackageSelection (listing_id, asset_id, channel, position, composite_score)
    scoring_event.py         ScoringEvent (listing_id, asset_id, features JSONB, composite_score, position, outcome)
    performance_event.py     PerformanceEvent (listing_id, metric_name, value) — learning-loop training signal
    learning_weight.py       LearningWeight (tenant_id, room_label, weight, labeled_listing_count)
    event.py                 Event (event_type, payload, tenant_id, listing_id)
    outbox.py                Outbox (event_id, delivered_at) — webhook delivery with idempotency key
    audit_log.py             AuditLog (user_id, tenant_id, action, resource_type, resource_id, details JSONB)
    brand_kit.py             BrandKit (logo_url, primary_color, secondary_color, font, raw_config JSONB)
    compliance_event.py      ComplianceEvent (asset_id, issue_type, severity)
    label_mapping.py         LabelMapping (raw_label, canonical_label)
    prompt_version.py        PromptVersion (agent_name, version, prompt_text)
    dollhouse_scene.py       DollhouseScene (listing_id, scene_json, floorplan_asset_id)
    video_asset.py           VideoAsset (listing_id, video_url, duration_seconds, chapter_markers)
    api_key.py               ApiKey (tenant_id, key_hash, name, last_used_at)
    listing_permission.py    ListingPermission (grantor_tenant_id, grantee_tenant_id, listing_id nullable for blanket grant)
    listing_microsite.py     ListingMicrosite (listing_id, subdomain, theme, published)
    listing_health_score.py  ListingHealthScore (listing_id, score, breakdown)
    health_score_history.py  HealthScoreHistory (tenant_id, calculated_at, score)
    cma_report.py            CMAReport (listing_id, report_html, comparable_properties)
    property_data.py         PropertyData (listing_id, beds, baths, sqft from ATTOM/MLS)
    notification.py          Notification + NotificationPreference
    import_job.py            ImportJob (listing_id, source, status)

  agents/
    base.py                  BaseAgent ABC: agent_name, requires_ai_consent flag, execute(), instrumented_execute() [OTel + StepTimer + consent re-check]
    ingestion.py             IngestionAgent: dedup by file_hash, S3 upload + 1024px proxy generation via PIL
    vision.py                VisionAgent: tier-1 Google Vision, tier-2 Qwen/GPT-4V (proxy-first, 30s timeout)  [AI]
    coverage.py              CoverageAgent: check REQUIRED_SHOTS coverage
    packaging.py             PackagingAgent: composite score, per-tenant weight blending, → AWAITING_REVIEW
    photo_compliance.py      PhotoComplianceAgent: detect people/signs/branding in photos  [AI]
    content.py               ContentAgent: dual-tone descriptions (mls_safe + marketing), FHA filter  [AI]
    brand.py                 BrandAgent: template render → S3 flyer
    learning.py              LearningAgent: read override events, update per-tenant weights, 90-day decay
    performance_intelligence.py  PerformanceIntelligenceAgent: photo→outcome correlations (Phase 5)
    distribution.py          DistributionAgent: → DELIVERED, emit pipeline.completed
    social_content.py        SocialContentAgent: IG + FB captions, FHA filtered (gated)  [AI]
    mls_export.py            MLSExportAgent: dual ZIP bundles (MLS + marketing)
    floorplan.py             FloorplanAgent: Qwen/GPT-4V → dollhouse JSON (proxy-first)  [AI]
    video.py                 VideoAgent: Kling clips → FFmpeg-stitched H.264 video  [AI]
    video_template.py        STANDARD_60S + other video templates (room prompts, durations)
    chapter.py               ChapterAgent: vision keyframes → chapter markers  [AI]
    social_cuts.py           SocialCutAgent: platform-specific video clips (IG/TT/FB/YT)
    virtual_staging.py       VirtualStagingAgent: empty-room → staged (addon, opt-in)  [AI]
    cma_report.py            CMAReportAgent: comparable market analysis HTML report  [AI]
    watermark.py             WatermarkAgent: brand watermark on photos
    health_score.py          HealthScoreAgent: listing quality score with custom weights
    microsite_generator.py   MicrositeGeneratorAgent: per-listing microsite
    property_verification.py PropertyVerificationAgent: ATTOM API cross-reference

  [AI] = sets requires_ai_consent = True; instrumented_execute halts if tenant consent is revoked mid-pipeline

  activities/
    pipeline.py              13 @activity.defn wrappers, all call agent.instrumented_execute()

  workflows/
    listing_pipeline.py      ListingPipeline: Phase 1 (→ AWAITING_REVIEW) → wait signal → Phase 2 (→ DELIVERED)
    worker.py                Temporal worker, init_tracing(), TracingInterceptor wiring

  services/
    auth.py                  hash_password, verify_password_constant_time, create_access_token, create_refresh_token, decode_token, set/clear_auth_cookies
    ai_consent.py            tenant_has_ai_consent, require_tenant_ai_consent — defense-in-depth for agent guards
    credits.py               CreditService: ensure_account, add_credits, deduct_credits (FIFO granted→purchased), refund, has_sufficient_credits
    billing.py               BillingService: Stripe customer, checkout, portal, webhook, resolve_plan, addon fulfillment
    account_lifecycle.py     delete_tenant_data (GDPR cascade), export_tenant_data (data portability)
    audit.py                 audit_log() — append-only AuditLog row writer
    events.py                emit_event() writes Event + Outbox in caller's transaction
    data_retention.py        cleanup_delivered_outbox (30d), cleanup_expired_exports (90d), cleanup_old_health_history (90d)
    demo_cleanup.py          cleanup_expired_demos (proxy + full-res S3)
    fha_filter.py            fha_check(): 8 FHA regex patterns
    weight_manager.py        WeightManager: blend, score, apply_update, apply_decay (90-day regression to 1.0)
    plan_limits.py           PLAN_LIMITS dict, check_listing_quota, check_asset_quota
    storage.py               StorageService: S3 upload/download/presigned URL/delete
    rate_limiter.py          Redis token bucket rate limiter (middleware)
    endpoint_rate_limit.py   rate_limit() dependency for per-endpoint limits
    outbox_poller.py         OutboxPoller: polls outbox, delivers to webhook URLs, X-ListingJet-Idempotency-Key
    drip_scheduler.py        Welcome drip email scheduler (1→5 over 10 days)
    notifications.py         notify_pipeline_complete, notify_pipeline_failed, notify_low_balance
    email.py                 Dual-backend email (SMTP + SES), factory + retries
    email_templates.py       Named template registry (welcome_drip_*, reset, pipeline notifications)
    field_encryption.py      Fernet encryption for IDX API keys (FIELD_ENCRYPTION_KEY)
    market_tracker.py        ATTOM API market data poller (automatic per-tenant)
    metrics.py               StepTimer, record_provider_call, record_cost, record_review_turnaround, PROVIDER_COSTS

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
    auth.py                  /auth/register, /login, /logout, /refresh, /me, /ai-consent, /forgot-password, /reset-password (audit-logged)
    listings_core.py         POST/GET /listings, GET/PATCH/DELETE /listings/{id} (S3 cleanup incl. proxies on delete)
    listings_draft.py        POST /listings/{id}/start-pipeline (AI consent guard + credit deduction)
    listings_media.py        Asset upload URLs, thumbnails (proxy-first), package reorder
    listings_video.py        Video upload register, video asset endpoints
    listings_import.py       Dropbox / Show & Tour / MLS link import
    listings_review.py       /review, /approve, /reject, /retry, /cancel (idempotent)
    listings_workflow.py     /start-pipeline retry semantics, pipeline-status endpoint
    listings_permissions.py  Cross-tenant grants (Phase B blanket, Phase C per-listing)
    assets.py                GET /assets
    analytics.py             GET /analytics/overview, /timeline, /usage, /credits (paginated)
    credits.py               GET /credits/balance, /transactions (paginated), /pricing, /service-costs; POST /credits/purchase
    addons.py                Addon catalog, purchase, fulfillment
    demo.py                  POST /demo/upload, GET /demo/{id}, POST /demo/{id}/claim
    billing.py               Checkout, status, portal, webhook
    admin.py                 Tenant CRUD, user management, platform stats, credit management, revenue analytics
    microsite.py             Microsite CRUD + public subdomain resolver
    team.py                  Team member invitation + role management
    health.py                /health, /ready, /metrics
    webhooks.py              Stripe webhook entry, credit.bundle_fulfilled, billing.payment_failed
    deps.py                  get_current_user, require_admin, get_db, get_db_admin
    deps_permissions.py      Cross-tenant permission resolution (blanket + per-listing grants)
    schemas/
      auth.py                RegisterRequest (consent + ai_consent), LoginRequest, TokenResponse, UserResponse (exposes ai_consent_at/version)
      listings.py            CreateListingRequest, ListingResponse, PaginatedResponse
      assets.py              AssetInput, UploadUrlsRequest, CreateAssetsRequest, AssetResponse
      billing.py             CheckoutRequest, BillingStatusResponse
      admin.py               TenantResponse, CreditTransactionResponse, AdjustCreditsRequest, RevenueBreakdownResponse
      demo.py                DemoUploadRequest/Response, DemoViewResponse

  middleware/
    tenant.py                TenantMiddleware: JWT decode → request.state.tenant_id; _PUBLIC_PATHS skip list

alembic/versions/
  Chain runs 001 → 049 linearly (no merges, no gaps).
  Highlights:
  001 Initial schema + RLS policies on all tenant-scoped tables
  010 credit_transactions table
  011-013 Brand kit + voice samples
  018 import_jobs table
  020 Query indexes (tenant_id, listing_id, state)
  023 property_data table (ATTOM/MLS cross-reference)
  024 ListingState.CANCELLED enum value
  027 Additional performance indexes
  028 User GDPR consent fields
  034 addon_catalog seed data
  040 Social features (listing_events, social_accounts, notifications)
  041 listing_health_scores, health_score_history, idx_feed_configs
  042 listing_outcomes, performance_insights (Phase 5)
  043 White-label columns on brand_kits
  044 FORCE ROW LEVEL SECURITY on all tenant-isolated tables
  046 Drop Tenant.credit_balance — CreditAccount is sole source of truth
  047 tenant_health_weights table
  048 User AI consent fields (ai_consent_at, ai_consent_version)
  049 Team invite tokens; password_hash nullable for pending invites

tests/
  conftest.py                test_engine (NullPool, port 5433), db_session, async_client, JWT helpers, promote_to_superadmin
  test_agents/               agent unit tests + E2E pipeline smoke (23 agents)
  test_api/                  auth, billing, listings, assets, admin, plan_limits, admin_credits, addons, credits, dollhouse, demo, etc.
  test_integration/          test_credit_lifecycle.py — full register→credits→listing→webhook→admin flows + AI consent coverage
                             test_s11_15_workflows.py — /credits/service-costs, /admin/audit-log (filters+pagination), billing page init flow, admin dashboard workflow, credit purchase + webhook fulfillment
  test_middleware/           tenant middleware, security headers
  test_providers/            mock, factory, storage, rate_limiter, vision, canva, kling, claude providers
  test_services/             events, outbox, fha_filter, weight_manager, credits, ai_consent, audit, account_lifecycle, data_retention, notifications, email_templates, endcard, drip_scheduler, link_import, outcome_tracker, help_agent
  test_workflows/            listing_pipeline, activities, worker
  test_monitoring/           telemetry, pipeline_metrics, instrumented_execute, security_headers

frontend/tests/              Playwright E2E specs (9 files) — mocks APIs at the route level
  auth/register.spec.ts      Registration form validation, plan selection
  auth/login.spec.ts         Login form
  app/create-listing.spec.ts Listing creation dialog
  app/billing.spec.ts        Balance display, bundle selection
  app/checkout-to-workflow.spec.ts  Full happy path (billing → pipeline start)
  app/listings.spec.ts       Listings list
  app/settings.spec.ts       Settings page
  public/demo.spec.ts, pricing.spec.ts

frontend/src/
  app/
    page.tsx                 Landing page (3D FloatingHouse)
    login/page.tsx           Login
    register/page.tsx        Register with separate ToS + AI consent checkboxes
    forgot-password/page.tsx Password reset request (stateless JWT, 15-min expiry)
    reset-password/page.tsx  Password reset completion
    onboarding/page.tsx      Post-register welcome + plan setup
    listings/page.tsx        Listings dashboard
    listings/[id]/page.tsx   Listing detail (PhotoOrbit, pipeline state, review actions)
    listings/[id]/export/page.tsx  MLS/Marketing ZIP download
    demo/page.tsx            Demo dropzone (no auth)
    demo/[id]/page.tsx       Demo result viewer + claim CTA
    pricing/page.tsx         Plan comparison + Stripe checkout
    billing/page.tsx         Credit balance, transaction history, bundle purchase
    admin/page.tsx           Admin: Overview, Tenants, Listings, Credits, Audit Log tabs
    settings/page.tsx        Brand kit + AI consent toggle + Canva integration
    settings/_components/    brokerage-info, brand-colors, typography, brand-voice, logos, canva-integration, connected-accounts, ai-consent-section, hud-preview
    settings/team/page.tsx   Team member management
  components/
    layout/nav.tsx           Responsive nav
    layout/protected-route.tsx  Auth guard
    ui/glass-card.tsx, button.tsx, plan-badge.tsx, toast.tsx
    listings/listing-card.tsx, social-preview.tsx, video-player.tsx, video-upload.tsx
    3d/floating-house.tsx, photo-orbit.tsx, pipeline-visualizer.tsx
  contexts/
    auth-context.tsx         AuthProvider + useAuth() (register takes consent + aiConsent)
    plan-context.tsx         PlanProvider + usePlan() + isFeatureGated()
  lib/
    api-client.ts            All API calls; updateAiConsent(), register(email,...,consent,aiConsent)
    types.ts                 UserResponse (id, email, role, tenant_id, ai_consent_at, ai_consent_version), ListingResponse, etc.
    generated/api.d.ts       Canonical types generated from FastAPI OpenAPI spec (npm run generate-api)
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
- `CreditAccount` is the **sole source of truth** for balances (`granted_balance` + `purchased_balance`); `Tenant.credit_balance` was dropped in migration 046
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

## Plan Tiers (v3)

Credit-based billing is the default. Tier defaults live in `config/tiers.py`:

| Tier | Monthly price | Founding | Included credits | Rollover cap |
|------|---------------|----------|------------------|--------------|
| free | $0 (PAYG @ $0.50/credit) | — | 0 | 0 |
| lite | $19 | $13 | 25 (~2 listings) | 50 |
| active_agent | $49 | $34 | 75 (~6 listings) | 150 |
| team | $99 | $69 | 250 (~20 listings) | 500 |

- `Tenant.billing_model` is `"credit"` for all new registrations (legacy `"subscription"` rows still supported via resolve_plan).
- Credit bundles purchasable as addons through Stripe checkout; webhook grants via `CreditService.add_credits` using idempotent `X-ListingJet-Idempotency-Key`.
- `CreditAccount.granted_balance` is deducted first (FIFO); `purchased_balance` consumed after.
- Per-listing cost is `Tenant.per_listing_credit_cost` (default 1) + addon cost from selected addons.

---

## Privacy & AI Consent (GDPR Art. 6/7, CCPA)

Third-party AI processing (Google Vision, Qwen, Claude, Kling, virtual staging) requires explicit, revocable consent — enforced at three layers:

1. **Data model**: `User.ai_consent_at` (timestamp) + `ai_consent_version` (string). Missing `ai_consent_at` means no consent. Tracked separately from `consent_at` (ToS). Migration 048.
2. **API entry point**: `POST /listings/{id}/start-pipeline` returns 403 if caller has no consent. `POST /auth/ai-consent` grants/revokes and writes an `AuditLog` row (`user.ai_consent.granted` / `user.ai_consent.revoked`) with `previous`/`current`/`version` details.
3. **Agent-level guards** (defense-in-depth — catches mid-pipeline revocation): `BaseAgent.requires_ai_consent: bool` class flag. `instrumented_execute()` calls `services/ai_consent.require_tenant_ai_consent()` before `execute()` if the flag is True. Halts the workflow (raises `ConsentRevokedError`) before any PII leaves the system. Opted-in agents: vision, floorplan, virtual_staging, photo_compliance, social_content, chapter, cma_report, content, video.

**Frontend**: `frontend/src/app/register/page.tsx` has a separate AI-consent checkbox (ToS is the required one). `frontend/src/app/settings/_components/ai-consent-section.tsx` renders a live toggle with current state, grant timestamp, and policy version.

**Compliance-supporting services**: `account_lifecycle.delete_tenant_data` (GDPR right-to-erasure, cascade), `account_lifecycle.export_tenant_data` (data portability), `audit_log` (append-only trail), `data_retention` (outbox 30d, exports 90d, health history 90d), `field_encryption` (Fernet for IDX API keys).

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
| GET | /admin/audit-log | Paginated audit log (filter: action, resource_type, tenant_id) |
| GET | /admin/events/recent | Recent system events feed |

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
| Deploy | `.github/workflows/deploy.yml` | push to main / workflow_dispatch — runs tests, then ECS run-task `migrate` (aborts on failure), then force-new-deployment |

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
