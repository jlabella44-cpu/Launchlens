# LaunchLens Session Handoff

## What Is LaunchLens

LaunchLens is a real estate listing media processing SaaS. Photographers/agents upload raw listing photos, and an AI pipeline curates, scores, packages, and delivers launch-ready marketing materials. The tagline: "From raw listing media to launch-ready marketing in minutes."

**Strategic pivot in progress:** Repositioning from "AI photo curation tool" to "Listing Media OS" — a full workflow automation platform covering photo curation, AI listing descriptions, branded content, MLS export, and social media generation.

---

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, PostgreSQL 16
- **Orchestration:** Temporal (workflow + activities)
- **Cache/Queue:** Redis 7
- **Storage:** S3 (via boto3)
- **Auth:** JWT (PyJWT), bcrypt password hashing
- **Payments:** Stripe (checkout, portal, webhooks)
- **Testing:** pytest-asyncio, 193 tests all passing
- **CI/CD:** GitHub Actions (lint, test, docker build)
- **Dev Environment:** Docker Compose (Postgres, Postgres-test, Redis, Temporal, Temporal UI, API, Worker)
- **Frontend (planned, not built):** Next.js 15, React 19, TypeScript, Tailwind CSS 4, React Three Fiber, Framer Motion

---

## Project Structure

```
C:\Users\Jeff\launchlens\
  src/launchlens/
    main.py                    — FastAPI app (create_app, lifespan, routers)
    config.py                  — Settings (pydantic-settings, .env)
    database.py                — SQLAlchemy engine, AsyncSessionLocal, get_db, Base
    temporal_client.py         — TemporalClient singleton (start_pipeline, signal_review)

    models/
      base.py                  — TenantScopedModel (id, tenant_id, created_at)
      tenant.py                — Tenant (name, plan, stripe_customer_id, stripe_subscription_id)
      user.py                  — User (email, password_hash, name, role: UserRole enum)
      listing.py               — Listing (address, metadata_, state: ListingState enum, lock_owner_id, lock_expires_at, mls_bundle_path, marketing_bundle_path, is_demo, demo_expires_at)
      asset.py                 — Asset (listing_id, file_path, file_hash, state, required_for_mls)
      social_content.py        — SocialContent (listing_id, platform, caption, hashtags, cta)
      vision_result.py         — VisionResult (asset_id, tier, room_label, quality_score, commercial_score, hero_candidate)
      package_selection.py     — PackageSelection (listing_id, asset_id, channel, position, composite_score, selected_by)
      event.py                 — Event (event_type, payload, tenant_id, listing_id)
      outbox.py                — Outbox (event_id, delivered_at)
      learning_weight.py       — LearningWeight (tenant_id, room_label, weight)
      global_baseline_weight.py
      brand_kit.py
      compliance_event.py
      label_mapping.py
      performance_event.py
      prompt_version.py

    agents/
      base.py                  — BaseAgent (ABC), AgentContext (listing_id, tenant_id)
      ingestion.py             — IngestionAgent: dedup by file_hash, state → ANALYZING
      vision.py                — VisionAgent: run_tier1 (Google Vision bulk), run_tier2 (GPT-4V top 20)
      coverage.py              — CoverageAgent: checks REQUIRED_SHOTS coverage
      packaging.py             — PackagingAgent: scores + selects top 25, state → AWAITING_REVIEW
      content.py               — ContentAgent: dual-tone (mls_safe + marketing) via Claude, FHA compliant
      brand.py                 — BrandAgent: template render → S3 flyer upload
      learning.py              — LearningAgent: reads override events, updates weights
      distribution.py          — DistributionAgent: state → DELIVERED, emits pipeline.completed
      social_content.py        — SocialContentAgent: Instagram + Facebook captions via Claude, FHA filtered
      mls_export.py            — MLSExportAgent: dual ZIP bundles (MLS unbranded + marketing branded)

    activities/
      pipeline.py              — 10 @activity.defn wrappers + ALL_ACTIVITIES list

    workflows/
      listing_pipeline.py      — ListingPipeline: Phase 1 (ingestion→packaging) → wait signal → Phase 2 (content→[brand+social parallel]→mls_export→distribution)
      worker.py                — Temporal worker (create_worker, main)

    services/
      auth.py                  — hash_password, verify_password, create_access_token, decode_token
      billing.py               — BillingService (Stripe customer, checkout, portal, webhook, resolve_plan)
      events.py                — emit_event (writes Event + Outbox in caller's transaction)
      fha_filter.py            — fha_check: 8 hardcoded FHA regex patterns
      weight_manager.py        — WeightManager: blend, score, apply_update
      plan_limits.py           — PLAN_LIMITS dict, check_listing_quota, check_asset_quota
      storage.py               — StorageService (S3 upload/download)
      rate_limiter.py          — Redis token bucket rate limiter
      outbox_poller.py         — OutboxPoller (polls outbox, delivers events)

    providers/
      base.py                  — VisionProvider, LLMProvider, TemplateProvider ABCs + VisionLabel dataclass
      factory.py               — get_vision_provider, get_llm_provider, get_template_provider
      mock.py                  — MockVisionProvider, MockLLMProvider, MockTemplateProvider
      google_vision.py         — GoogleVisionProvider
      openai_vision.py         — OpenAIVisionProvider (GPT-4V)
      claude.py                — ClaudeProvider (Anthropic)

    api/
      auth.py                  — POST /auth/register, POST /auth/login, GET /auth/me
      listings.py              — POST/GET /listings, GET/PATCH /listings/{id}, POST/GET assets, GET package, POST review/approve
      assets.py                — GET /assets (stub for standalone Phase 2 API)
      demo.py                  — POST /demo/upload (no auth), GET /demo/{id}, POST /demo/{id}/claim
      billing.py               — POST /billing/checkout, GET /billing/status, POST /billing/portal, POST /billing/webhook
      admin.py                 — GET/PATCH /admin/tenants, GET/POST users, PATCH role, GET /admin/stats
      deps.py                  — get_current_user, require_admin, get_current_tenant, get_tenant, get_db_admin
      schemas/
        auth.py                — RegisterRequest, LoginRequest, TokenResponse, UserResponse
        listings.py            — CreateListingRequest, UpdateListingRequest, ListingResponse
        assets.py              — AssetInput, CreateAssetsRequest, CreateAssetsResponse, AssetResponse
        billing.py             — CheckoutRequest/Response, PortalRequest/Response, BillingStatusResponse
        admin.py               — TenantResponse, TenantDetailResponse, UserResponse, InviteUserRequest, PlatformStatsResponse
        demo.py                — DemoUploadRequest/Response, DemoViewResponse

    middleware/
      tenant.py                — TenantMiddleware: JWT decode, sets request.state.tenant_id, _PUBLIC_PATHS skip list

  alembic/versions/
    001_initial_schema.py      — tables + RLS policies + tenant_isolation policies
    002_outbox_add_tenant_listing_delivered.py
    003_users_add_password_hash.py
    004_tenant_stripe_fields.py
    005_social_content_export_demo.py

  tests/
    conftest.py                — test_engine (NullPool, port 5433), db_session, async_client (overrides get_db + get_db_admin)
    test_agents/               — 8 agent test files + conftest (make_session_factory, listing/assets fixtures) + test_pipeline (E2E smoke)
    test_api/                  — test_auth, test_billing, test_listings, test_assets, test_admin, test_plan_limits
    test_middleware/            — test_tenant (real user registration)
    test_providers/            — test_mock, test_factory, test_storage, test_rate_limiter, test_google_vision, test_openai_vision, test_claude, test_factory_real
    test_services/             — test_events, test_outbox_poller, test_fha_filter, test_weight_manager
    test_workflows/            — test_listing_pipeline, test_activities, test_worker

  .github/workflows/
    lint.yml                   — ruff on push/PR
    test.yml                   — pytest with 2 Postgres service containers
    docker.yml                 — Docker build validation on main

  docker-compose.yml           — postgres, postgres-test, redis, temporal, temporal-ui, api, worker
  Dockerfile                   — Python 3.12-slim, installs deps, entrypoint.sh
  docker/
    init-db.sh                 — creates launchlens_test database
    entrypoint.sh              — waits for postgres, runs alembic, dispatches api/worker/test
```

---

## Version History

| Version | Feature | Tests Added |
|---------|---------|-------------|
| v0.1.0 | Scaffold (models, config, DB, middleware) | ~20 |
| v0.2.0 | Core Services (providers, storage, rate limiter, events, outbox) | ~40 |
| v0.3.0 | Agent Pipeline (8 agents, full state machine, E2E smoke test) | ~50 |
| v0.4.0 | Auth (register, login, JWT, get_current_user, require_admin) | ~16 |
| v0.5.0 | Payments (Stripe checkout, portal, webhooks) | ~10 |
| v0.6.0 | API Endpoints (9 REST endpoints, CRUD + review flow) | ~20 |
| v0.7.0 | Temporal Wiring (activities, workflow, worker, API trigger) | ~10 |
| v0.8.0 | Plan Enforcement (tier-based listing + asset limits) | ~12 |
| v0.8.1 | Docker Compose (full dev environment) | — |
| v0.8.2 | Admin Dashboard (tenant/user CRUD, platform stats) | ~12 |
| v0.8.3 | CI/CD (lint, test, docker build workflows) | — |
| v0.9.0 | Listing Media OS (SocialContentAgent, MLSExportAgent, dual-tone ContentAgent, export endpoint, demo pipeline, Temporal parallel Phase 2, PRD v3) | ~21 |

**Total: 214 tests, all passing.**

---

## Key Patterns

### Session Injection (Agents)
Agents take `session_factory=None`, defaulting to `AsyncSessionLocal`. Tests use `make_session_factory(db_session)` which wraps the test session in an async context manager. Agents use `begin_nested()` when already in a transaction (test SAVEPOINTs).

### Transaction Pattern
```python
async with (session.begin() if not session.in_transaction() else session.begin_nested()):
```

### Test DB Override
`conftest.py` overrides `get_db` and `get_db_admin` in the `async_client` fixture to use `test_engine` (NullPool, port 5433). This avoids asyncpg connection-sharing bugs and ensures all tests hit the test DB.

### RLS
RLS is enabled on all tenant-scoped tables (migration 001). `get_db` sets `SET LOCAL app.current_tenant`. `get_db_admin` skips this for cross-tenant admin queries.

### Listing State Machine
```
NEW → UPLOADING → ANALYZING → AWAITING_REVIEW → IN_REVIEW → APPROVED → EXPORTING → DELIVERED
DEMO → (claimed) → UPLOADING → ... (normal flow)
DEMO → (expired) → deleted by cleanup
```
- `POST /listings/{id}/assets` → UPLOADING (triggers Temporal pipeline)
- Pipeline Phase 1 runs → AWAITING_REVIEW
- `POST /listings/{id}/review` → IN_REVIEW
- `POST /listings/{id}/approve` → APPROVED (signals Temporal to continue)
- Phase 2: Content → [Brand + Social parallel] → MLSExport (EXPORTING) → Distribution (DELIVERED)
- `GET /listings/{id}/export?mode=mls|marketing` → presigned S3 URL for ZIP bundle
- `POST /demo/upload` → DEMO (no auth, 24h TTL, Phase 1 only)
- `POST /demo/{id}/claim` → converts to real listing, triggers Phase 2

### Plan Limits
```python
PLAN_LIMITS = {
    "starter":    {"max_listings_per_month": 5,   "max_assets_per_listing": 25,  "tier2_vision": False, "social_content": False},
    "pro":        {"max_listings_per_month": 50,  "max_assets_per_listing": 50,  "tier2_vision": True,  "social_content": True},
    "enterprise": {"max_listings_per_month": 500, "max_assets_per_listing": 100, "tier2_vision": True,  "social_content": True},
}
```
- SocialContentAgent is skipped for Starter tier (plan-gated in Temporal workflow)
- MLS Export runs for all tiers; Marketing bundle includes social posts only for Pro+

### Design System (for frontend)
Generated by UI/UX Pro Max, persisted at `design-system/launchlens/MASTER.md`:
- Colors: Primary `#2563EB`, CTA `#F97316`, Background `#F8FAFC`, Text `#1E293B`
- Typography: Cinzel (headings), Josefin Sans (body)
- Style: Immersive interactive, glassmorphism, real-time monitoring
- 3D: React Three Fiber (FloatingHouse, PhotoOrbit, PipelineVisualizer)

---

## Plans Written But Not Yet Executed

### v1.0.0 — Frontend (3D Interactive)
**File:** `docs/plans/2026-03-27-frontend.md`
**5 tasks:**
1. Scaffold (Next.js + Three.js + Framer Motion + design system)
2. API client + UI primitives (GlassCard with 3D tilt, animated Badge, spring Button, SceneWrapper)
3. 3D auth pages (FloatingHouse, split-screen login/register with particles)
4. Listings dashboard (3D tilt cards, stagger animation, spring-animated create dialog)
5. Listing detail (PhotoOrbit 3D carousel, PipelineVisualizer 3D, package viewer, review/approve)

**Additional frontend work needed for v0.9.0 features:**
- Demo dropzone landing page (hits `POST /demo/upload`)
- Pipeline visualizer for demo flow
- Export download page with MLS vs Marketing toggle
- Social media preview cards
- Pricing page with updated "Media OS" copy

**Note:** Magic MCP (21st.dev) API key updated but needs Claude Code restart to activate. Stitch (Google) needs API enabled at console.

---

## Strategic Pivot: "Listing Media OS" (COMPLETED in v0.9.0)

Repositioned from "photo curation tool" to "Listing Media OS". Full PRD at `docs/LaunchLens-PRD-v3.md`.

### What was built in v0.9.0:
1. **SocialContentAgent** — Instagram + Facebook captions via Claude, FHA compliant, Pro+ only
2. **MLSExportAgent** — Dual ZIP bundles: MLS (unbranded, spec-compliant) + Marketing (branded, full content)
3. **ContentAgent dual-tone** — Single Claude call returns `mls_safe` + `marketing` descriptions
4. **Export endpoint** — `GET /listings/{id}/export?mode=mls|marketing` with presigned S3 URL
5. **Demo pipeline** — Results-first onboarding: upload without auth → see AI results → register → claim
6. **Temporal parallel Phase 2** — Content → [Brand + Social parallel] → MLS Export → Distribution
7. **PRD v3** — Updated positioning, pricing copy, MLS compliance strategy

### MLS Compliance Strategy:
- **Phase 1 (NOW):** Export unbranded MLS bundles, branded content separate, agent manually uploads. LaunchLens is a prep tool.
- **Phase 2:** Photo compliance scanner (detect branding/signs/people), two export modes already built
- **Phase 3:** RESO Web API vendor certification. **No browser automation — ever.**

### What's next:
- **Frontend** — Next.js 15 + React Three Fiber 3D interactive UI (plan at `docs/plans/2026-03-27-frontend.md`)
- Frontend needs to add: demo dropzone landing page, export download UI, social preview, MLS vs Marketing toggle

---

## Environment

- **Platform:** Windows 11 (bash via Git Bash)
- **Python:** `C:\Users\Jeff\AppData\Local\Programs\Python\Python312\python.exe`
- **Node:** v25.8.1, npm 11.11.0
- **Docker:** Docker Desktop (containers running: postgres:5432, postgres-test:5433)
- **Test DB:** `postgresql+asyncpg://launchlens:password@localhost:5433/launchlens_test`
- **Dev DB:** `postgresql+asyncpg://launchlens:password@localhost:5432/launchlens`

---

## Pending Decisions

1. ~~PRD rewrite~~ — **DONE** (v0.9.0, PRD v3)
2. ~~New agents~~ — **DONE** (SocialContentAgent, MLSExportAgent)
3. **Frontend execution** — Build with Magic MCP after restart, or proceed without?
4. **Production deployment** — Not yet planned (Kubernetes? ECS? Fly.io?)
5. **Monitoring** — Not yet planned (logging, metrics, alerting)
6. **Demo rate limiting** — Redis rate limiter wired but needs tuning (3/IP/day currently hardcoded)
7. **Demo cleanup job** — Temporal cron workflow to delete expired demo listings (designed but not yet built)

---

## How to Run

```bash
# Start infrastructure
docker compose up -d postgres postgres-test redis

# Run migrations
DATABASE_URL="postgresql+asyncpg://launchlens:password@localhost:5432/launchlens" \
DATABASE_URL_SYNC="postgresql://launchlens:password@localhost:5432/launchlens" \
JWT_SECRET="dev-secret" python -m alembic upgrade head

DATABASE_URL="postgresql+asyncpg://launchlens:password@localhost:5433/launchlens_test" \
DATABASE_URL_SYNC="postgresql://launchlens:password@localhost:5433/launchlens_test" \
JWT_SECRET="dev-secret" python -m alembic upgrade head

# Run tests (214 tests)
python -m pytest --tb=short -q

# Start full stack
docker compose up -d

# API: http://localhost:8000
# Temporal UI: http://localhost:8233
# Health: http://localhost:8000/health
```
