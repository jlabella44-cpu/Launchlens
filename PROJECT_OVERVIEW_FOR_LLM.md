# LaunchLens — Project Overview

> AI-powered real estate media automation. Upload listing photos, get marketing-ready assets in minutes.

## What It Does

Real estate agents upload property photos. LaunchLens runs them through a 14-agent AI pipeline to produce: property descriptions, AI-generated tour videos, 3D floorplans, social media content, branded flyers, MLS-compliant export bundles, and watermarked marketing packages — all with human review before delivery.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI (Python 3.12, fully async) |
| **Database** | PostgreSQL 16 + SQLAlchemy 2.0 + Alembic (10 migrations) |
| **Workflow** | Temporal (durable orchestration with human-in-the-loop) |
| **Cache** | Redis 7 |
| **Storage** | AWS S3 (presigned upload + download URLs) |
| **Auth** | JWT + bcrypt, role-based (ADMIN/OPERATOR/AGENT/VIEWER) |
| **Payments** | Stripe (checkout, subscriptions, webhooks, customer portal) |
| **AI — Vision** | Google Vision API, OpenAI GPT-4V (fallback chain) |
| **AI — LLM** | Anthropic Claude |
| **AI — Video** | Kling AI |
| **AI — Templates** | Canva Connect API (with Claude for design JSON) |
| **Monitoring** | Sentry, OpenTelemetry (Jaeger), structured logging, request metrics |
| **Virus Scanning** | ClamAV |
| **Frontend** | Next.js 16 + React 19 + TypeScript |
| **3D** | Three.js, React Three Fiber |
| **Animation** | Framer Motion |
| **Styling** | Tailwind CSS 4 |
| **Testing** | pytest (async), Vitest, Locust (load), chaos tests |
| **IaC** | AWS CDK (network, database, services, monitoring, CI stacks) |

---

## Pipeline Architecture

The core is `ListingPipeline`, a Temporal workflow orchestrating 14 agents across 3 phases:

```
Phase 1: Analysis (sequential)
  1. Ingestion      — Virus scan (ClamAV), dedup (SHA-256 + perceptual hash), normalize
  2. Vision Tier 1  — Room classification, quality scoring (Google Vision → OpenAI fallback)
  3. Vision Tier 2  — Deep analysis on hero candidates (GPT-4V)
  4. Coverage       — Completeness check (exterior, kitchen, bedroom, etc.)
  5. Floorplan      — 3D floorplan generation from photo analysis
  6. Packaging      — AI photo curation with Thompson Sampling weights
  7. Compliance     — GPT-4V scan for people, signage, branding, text overlay

  [Video generation starts in parallel — 30min timeout, non-blocking]

  >>> HUMAN REVIEW GATE (workflow pauses, waits for approval signal) <<<

Phase 2: Content (after approval)
  8. Content        — Dual-tone descriptions via Claude (MLS-safe + marketing)
  9. Brand          — Branded flyer PDF (Canva API + Claude design JSON)
  10. Social Content — Platform-specific captions (Instagram, Facebook) — Pro/Enterprise only
  11. Chapters      — Video chapter markers
  12. Social Cuts   — Platform-optimized video clips
  13. MLS Export    — ZIP bundles (MLS + marketing) with resized photos, metadata CSV
  14. Distribution  — Mark DELIVERED, trigger notifications
```

Every activity uses `instrumented_execute()` — wraps `execute()` with OpenTelemetry spans and step-duration metrics automatically.

---

## Data Model (18 tables)

| Model | Purpose |
|-------|---------|
| **Tenant** | Brokerage account (plan, Stripe IDs, webhook URL) |
| **User** | Agent/admin (email, bcrypt password, role) |
| **Listing** | Property (address, metadata, 14-state machine) |
| **Asset** | Photo file (S3 key, SHA-256, perceptual hash, state) |
| **VisionResult** | AI analysis per photo (room label, quality/commercial scores, hero candidate) |
| **VideoAsset** | Generated video (chapters, social cuts, thumbnail, branded player config) |
| **PackageSelection** | Curated photo selection (channel, position, composite score, ai/human) |
| **DollhouseScene** | 3D floorplan (scene JSON, room count) |
| **SocialContent** | Platform-specific post (caption, hashtags, CTA) |
| **BrandKit** | Tenant branding (logo, colors, fonts, agent/brokerage names) |
| **Event** | Immutable audit trail (event type, payload, tenant, listing) |
| **Outbox** | Transactional outbox for reliable event delivery |
| **ComplianceEvent** | Photo compliance issue (resolvable) |
| **PromptVersion** | Versioned AI prompts per agent with eval scores |
| **LearningWeight** | Per-tenant photo scoring weights (Thompson Sampling: alpha/beta) |
| **GlobalBaselineWeight** | Global baseline weights |
| **PerformanceEvent** | Engagement/feedback signals for weight learning |
| **APIKey** | Tenant API keys |
| **NotificationPreference** | Per-user email notification toggles |

**Listing state machine:**
```
NEW → UPLOADING → ANALYZING → SHADOW_REVIEW → AWAITING_REVIEW → IN_REVIEW → APPROVED → GENERATING → DELIVERING → DELIVERED
                                                                                                                    ↘ FAILED / PIPELINE_TIMEOUT (retryable)
```

**Multi-tenancy:** PostgreSQL `SET LOCAL app.current_tenant` for transaction-scoped row-level security.

---

## API Surface

### Auth (`/auth`)
- `POST /register` — create tenant + admin user, return JWT
- `POST /login` — email/password auth with timing-safe comparison
- `GET /me` — current user profile
- `GET/PATCH /me/notifications` — notification preferences

### Listings (`/listings`)
- `POST /` — create listing (enforces monthly quota)
- `GET /` — list for tenant (filterable by state)
- `GET /{id}` — detail
- `PATCH /{id}` — update
- `POST /{id}/upload-urls` — presigned S3 PUT URLs for browser-direct upload
- `POST /{id}/assets` — register uploaded assets (triggers pipeline)
- `GET /{id}/assets` — list assets
- `GET /{id}/package` — AI-curated photo selections
- `GET /{id}/dollhouse` — 3D floorplan
- `GET /{id}/pipeline-status` — per-step progress with completion times
- `POST /{id}/review` — start review
- `POST /{id}/approve` — approve (signals Temporal workflow)
- `POST /{id}/reject` — reject with reason code
- `POST /{id}/retry` — retry failed pipeline
- `GET /{id}/export?mode=mls|marketing` — presigned download URL (15-min TTL)
- `GET /{id}/video` — video asset details
- `GET /{id}/video/social-cuts` — social clips
- `POST /{id}/video/upload` — user-submitted video
- `POST /{id}/compliance` — on-demand compliance scan
- `GET /{id}/events` — SSE stream for real-time pipeline updates

### Billing (`/billing`)
- `POST /checkout` — Stripe checkout session
- `GET /status` — current plan + subscription info
- `POST /portal` — Stripe customer portal URL
- `GET /invoices` — invoice history
- `POST /webhook` — Stripe event handler (resolves plan from price_id)
- `PATCH /plan` — admin plan change

### Brand Kit (`/brand-kit`)
- `GET /` — get tenant brand kit
- `PUT /` — create/update (upsert)
- `POST /logo-upload-url` — presigned S3 URL for logo

### Admin (`/admin`)
- `GET /stats` — platform-wide statistics
- `GET /tenants`, `GET /tenants/{id}` — tenant management
- `PATCH /tenants/{id}` — update tenant
- `POST /tenants/{id}/users` — invite user
- `PATCH /users/{id}/role` — change role

### Analytics (`/analytics`)
- `GET /usage` — listing/asset counts for current tenant

### Demo (`/demo`)
- `POST /upload` — demo listing from S3 paths (rate-limited: 3/IP/day)

---

## Frontend (12 pages, 29 components)

### Pages
| Route | Purpose |
|-------|---------|
| `/login` | Split layout: 3D hero scene (desktop) + auth form |
| `/register` | Same layout, registration form |
| `/listings` | Dashboard grid with listing cards + create dialog + onboarding banner |
| `/listings/[id]` | Detail: drag-and-drop upload, pipeline progress, package viewer, 3D photo orbit, video, social preview, actions |
| `/listings/[id]/export` | Download MLS + marketing bundles |
| `/review` | Review queue: keyboard shortcuts (j/k/a/s), expandable photo grid, reject with reason codes, auto-refresh |
| `/billing` | Current plan, usage stats, upgrade/portal, invoice history |
| `/settings` | Brand kit setup: colors, logo upload, fonts, agent/brokerage name |
| `/pricing` | 3-tier comparison (Starter $29, Pro $99, Enterprise $299) |
| `/demo` | Public demo upload |
| `/demo/[id]` | Demo results |

### Key Components
- **ErrorBoundary** — catches render crashes with retry
- **OfflineBanner** — network connectivity indicator
- **Toast** — notification system (success/error/info)
- **PipelineProgress** — vertical step list with real-time status
- **PipelineVisualizer** — 3D pipeline visualization (16 steps)
- **PhotoOrbit** — 3D photo carousel (hidden on mobile)
- **AssetUploadForm** — drag-and-drop with presigned URLs, progress bars, client-side SHA-256
- **PackageViewer** — curated photo grid with scores
- **PlanBadge** — plan-gated feature indicators
- **ColorPicker** — hex color input for brand kit
- **SceneErrorBoundary** — graceful Three.js failure handling

### Contexts
- **AuthContext** — JWT token, user info, login/logout
- **PlanContext** — current plan, limits, usage, upgrade prompts

---

## Infrastructure

### Docker Compose (9 services)
```
postgres       — PostgreSQL 16 (port 5432)
postgres-test  — Test database (port 5433)
redis          — Redis 7 (port 6379)
temporal       — Temporal Server (port 7233)
temporal-ui    — Workflow monitoring (port 8233)
clamav         — ClamAV virus scanner (port 3310)
jaeger         — OpenTelemetry traces (port 16686 UI, 4317 OTLP)
api            — FastAPI (port 8000, hot-reload)
worker         — Temporal activity executor
```

### AWS CDK Stacks (`infra/`)
- **NetworkStack** — VPC, subnets, security groups
- **DatabaseStack** — RDS PostgreSQL, ElastiCache Redis
- **ServicesStack** — ECS Fargate (API + Worker + Temporal)
- **MonitoringStack** — CloudWatch, alarms, dashboards
- **CIStack** — CodePipeline, CodeBuild

### Security Middleware
- **TenantMiddleware** — JWT → tenant isolation via PostgreSQL RLS
- **RateLimitMiddleware** — per-tenant/per-IP rate limiting (Redis-backed)
- **SecurityHeadersMiddleware** — HSTS, CSP, X-Frame-Options, etc.
- **RequestIdMiddleware** — correlation IDs for tracing
- **RequestMetricsMiddleware** — latency/count/error tracking per endpoint

### Observability
- **Sentry** — error tracking with release tagging
- **OpenTelemetry** — distributed tracing (FastAPI → Temporal → agents → providers)
- **Structured logging** — JSON in production, console in development
- **Pipeline metrics** — step duration histograms, failure counters, cost tracking, review turnaround

---

## Subscription Plans

| Feature | Starter ($29/mo) | Pro ($99/mo) | Enterprise ($299/mo) |
|---------|:-:|:-:|:-:|
| Listings/month | 5 | 50 | 500 |
| Assets/listing | 25 | 50 | 100 |
| Vision Tier 2 | No | Yes | Yes |
| Social Content | No | Yes | Yes |

---

## Testing (74 test files)

- **Unit/Integration** — pytest-asyncio, factory-boy, moto (S3), fakeredis
- **API tests** — async HTTP client against FastAPI test app
- **Agent tests** — each agent tested in isolation with mock providers
- **Workflow tests** — Temporal WorkflowEnvironment for deterministic testing
- **Chaos tests** — provider timeout fallback, low-confidence fallback, scanner failure, idempotent crash recovery
- **Load tests** — Locust targeting 100 concurrent listings
- **Frontend tests** — Vitest + React Testing Library

---

## Design System

- **Colors:** Primary #2563EB, CTA #F97316, Background #F8FAFC
- **Fonts:** Cinzel (headings), Josefin Sans (body)
- **Breakpoints:** 375px, 768px (md), 1024px (lg), 1440px (xl)
- **3D disabled on mobile** (< 768px) for performance
- **Touch targets:** 44x44px minimum, `touch-action: manipulation`
- **Glass-morphism** cards with tilt effect

---

## Key Architecture Decisions

1. **Temporal over Celery** — durable execution, human review gate, long-running video generation, built-in retry
2. **Multi-tenancy via RLS** — `SET LOCAL` for transaction-scoped isolation, safe for connection pooling
3. **Agent pattern** — each AI step is a self-contained `BaseAgent` with `execute()` + `instrumented_execute()`
4. **Provider fallback** — primary → secondary chain with confidence-based failover
5. **Thompson Sampling** — Beta distribution for photo scoring weights, learns from human overrides
6. **Outbox pattern** — events written atomically with state changes for reliable distributed delivery
7. **Presigned uploads** — browser uploads directly to S3, backend only registers metadata
8. **SSE for real-time** — Server-Sent Events for pipeline progress instead of polling
9. **PII filtering** — sanitize listing data before sending to external AI providers

---

## What's Working

Everything above is implemented and on master. The remaining open item is:

- **Issue #10** — Run the full test suite in Python 3.12, verify coverage > 60%, execute load tests, fix any failures from recent refactoring

---

## Questions for Discussion

1. How would you approach integration testing the full pipeline end-to-end with real provider APIs?
2. What's the best strategy for A/B testing AI prompts at scale using the existing PromptVersion infrastructure?
3. How should the learning feedback loop (PerformanceEvent → weight updates) be automated?
4. What's missing for SOC 2 compliance in a multi-tenant SaaS handling real estate data?
5. How would you optimize the video generation pipeline for cost efficiency at 1000+ listings/month?
6. What would a mobile-native experience look like for agents photographing properties in the field?
