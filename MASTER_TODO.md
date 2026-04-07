# LaunchLens / ListingJet — Master TODO List

Compiled from: `TODO.md`, `PRE_LAUNCH_AUDIT.md`, `ADMIN_DASHBOARD_PROGRESS.md`, all `HANDOFF-SESSION-*` files, plan docs, and inline code TODOs.

---

## P0 — Production Blockers

### Critical Bugs (from Session 17)
- [x] **Temporal Worker registers zero activities** — `ALL_ACTIVITIES` import already in place
- [x] **Alembic migration chain broken** — chain is linear and correct (001→041), no duplicate revisions
- [x] **No CORS middleware** — `CORSMiddleware` already configured in `main.py`

### Pre-Launch Audit — Critical
- [x] **CRITICAL-1: No GDPR/CCPA account deletion or data export** — cascade deletion via `account_lifecycle.py` + `GET /export-data`
- [x] **CRITICAL-2: Missing database indexes** — already added via migrations 020 and 027
- [x] **CRITICAL-3: Stripe API calls unguarded** — wrapped all calls in `try/except stripe.StripeError`
- [x] **CRITICAL-4: Global singleton race conditions** — added `threading.Lock` for `_demo_limiter`; `_low_credit_sent` uses atomic Redis `SET NX`
- [x] **CRITICAL-5: Debug tracebacks exposed to clients** — global exception handler returns generic message
- [x] **CRITICAL-6: WCAG 2.1 accessibility violations** — added `htmlFor` to Input/Select/ColorPicker, `role="alert"` to error messages, `aria-label`/`role="button"` to listing card
- [x] **CRITICAL-7: Worker health check misconfigured** — heartbeat file + `_heartbeat_loop` already configured

### Infrastructure
- [ ] **SES production access** — wait for AWS approval, then verify
- [ ] **Run `cdk deploy`** to apply IAM changes permanently (currently inline policies)
- [ ] **Apply `property_data` table migration** (blocker — obs #1028)
- [ ] **Run missing migrations on prod DB**
- [ ] **Separate dev/prod S3 buckets** — both currently use `listingjet-dev`
- [ ] **Rename CloudWatch log groups** from `/launchlens/*` to `/listingjet/*`

---

## P1 — High Priority (First Sprint Post-Launch)

### Security (from Pre-Launch Audit)
- [x] **HIGH-1: JWT tokens stored in localStorage** — already using httpOnly cookies via `set_auth_cookies()`
- [x] **HIGH-2: PII (email addresses) logged in plaintext** — masked as `u***@e***.com` in all log output
- [x] **HIGH-3: No token revocation** — Redis-backed blocklist on logout; TTL matches token lifetime
- [x] **HIGH-4: No account lockout after failed login attempts** — Redis-based lockout (5 attempts / 15min)
- [ ] **HIGH-7: No consent management for third-party AI processing**
- [x] **Rate limiting on auth endpoints** — Redis rate limiter already applied via `rate_limit()` dependency

### Data Integrity
- [x] **HIGH-5: Outbox poller can duplicate webhook deliveries** — `X-ListingJet-Idempotency-Key` header added
- [x] **HIGH-6: Unbounded analytics queries** — pagination with offset/limit on `/analytics/credits`
- [ ] **Dual credit systems (Audit #8)** — `CreditAccount` table vs `Tenant.credit_balance` are two sources of truth; needs product decision

### Deployment
- [ ] **Deploy backend with new analytics endpoints** (ECR push + ECS redeploy)
- [ ] **Test analytics page on production**
- [ ] **Investigate stuck Lenexa listing** (`uploading` since Apr 1)
- [ ] **Review and approve Parkville listing** through review queue
- [ ] **Merge PR #109** once CI passes
- [ ] **4 unpushed commits on local master** — decide: PR these or reset to origin

### Vision Pipeline
- [ ] **Add per-image logging** to vision agent (log before/after S3 download and Google Vision API call)
- [ ] **Add timeouts** — per-image download (30s) and per-API-call (30s)
- [ ] **Build proxy image pipeline** — generate 1024px proxies during ingestion (4x speedup, 90MB → 3MB); plan at `docs/PROXY-IMAGE-PIPELINE.md`

---

## P2 — Feature Work (Sessions 11–22)

### Credit System Frontend (Session 11)
- [ ] Credit system frontend integration

### Credit System Tests (Session 12)
- [ ] Credit service test coverage gaps

### Registration (Session 13)
- [ ] Complete registration flow tasks

### Webhooks (Session 14)
- [ ] Webhook expansion for credit bundle fulfillment

### Admin Dashboard (Session 15 + Progress Doc)
- [ ] **Overview tab** — listings by state table, "Attention Required" alert, revenue summary, recent events feed
- [ ] **Tenants tab** — click tenant → detail panel with edit form, webhook test, user management
- [ ] **Listings tab** — filters (state, tenant, address search), actions (retry, edit)
- [ ] **Credits tab** — global credit ledger, tenant credit table
- [ ] **Audit Log tab** — filters and expandable JSON details
- [ ] Lint & verify (ruff + TypeScript checks)

### E2E Tests (Session 16)
- [ ] Integration test cases (run after sessions 11–15 are merged)

### Stub Fixes (Session 18)
- [ ] **Implement real video cutting** — replace stub in `VideoCutter.create_cut()` with FFmpeg
- [x] **Wire Canva provider into factory** — factory already selects `CanvaTemplateProvider` when `canva_api_key` is set
- [x] **Improve mock vision provider** — returns deterministic varied data based on image URL hash

### Test Coverage (Session 19)
- [x] ChapterAgent tests — already exist in `tests/test_agents/test_chapter.py`
- [x] LearningAgent tests — already exist in `tests/test_agents/test_learning.py`
- [x] WatermarkAgent tests — already exist in `tests/test_agents/test_watermark.py`
- [x] Fix PackagingAgent weight loading — replaced magic `1.0` with `DEFAULT_ROOM_WEIGHT` constant; LearningWeight query already wired
- [ ] SSE endpoint tests (`/listings/{id}/events` returns `text/event-stream`)
- [ ] Middleware tests (security headers)
- [ ] Provider tests (canva.py, kling.py, claude.py)

### API Polish (Session 20)
- [x] OpenAPI documentation / FastAPI metadata — already configured (title, version, description, 14 tag groups)
- [ ] Response models for all endpoints (ActionResponse, CancelResponse, PipelineStatusResponse)
- [ ] Standardize pagination — `PaginatedResponse` generic for `/listings`, `/credits/transactions`, `/admin/tenants`
- [x] Rate limit headers (`X-RateLimit-*`) — `X-RateLimit-Limit` and `X-RateLimit-Remaining` on all responses
- [ ] API versioning — `/api/v1/` prefix (optional)

### Documentation (Session 21)
- [ ] Create `README.md`
- [ ] Update `.env.example` with all config settings
- [ ] Create `CHANGELOG.md`
- [ ] Update `PROJECT_OVERVIEW_FOR_LLM.md`
- [ ] Add CI badge to README

### Learning Loop (Session 22)
- [x] Wire `LearningAgent` into pipeline — already in Step 6 of `listing_pipeline.py` after distribution
- [x] Photo reorder endpoint — `POST /{listing_id}/package/reorder` already in `listings_media.py`
- [ ] Performance event ingestion — write to `PerformanceEvent` table on listing delivery and export download
- [x] Weight decay — `apply_decay` method already exists in `weight_manager.py` (90-day decay toward 1.0)
- [ ] XGBoost model upgrade (Phase 2 of weight manager)

### Listing Permissions — Remaining Phases
- [ ] Phase C: Cross-tenant email invitations (needs SES production access)
- [ ] Phase E: Email notifications (share/revoke/edit digest — templates built, needs SES)
- [ ] Blanket per-agent grant (Phase B) — `deps_permissions.py:50`

### Frontend Remaining Pages
- [ ] Demo dropzone page
- [ ] Pricing page
- [ ] Export download page
- [ ] Video player
- [ ] Video upload
- [ ] Social preview cards

---

## P3 — Low Priority / Deferred

### Code Cleanup (from TODO.md)
- [ ] **Listings.py monolith** — split 800+ line file into sub-routers (CRUD, review, export, video, package)
- [ ] **CSP blocks frontend** — `SecurityHeadersMiddleware` sets overly restrictive CSP; needs frontend audit
- [ ] **Pipeline status endpoint expensive** — `get_pipeline_status` recomputes on every request; needs caching
- [ ] Dead comment in listings.py (Audit #18)
- [ ] Unused listing states: `SHADOW_REVIEW`, `GENERATING`, `DELIVERING`, `TRACKING` (Audit #19)
- [ ] Test JWT fixture doesn't create User rows (Audit #20)
- [ ] `upload-urls` endpoint uses `body: dict` — no Pydantic schema (Audit #12)
- [ ] Cancel listing reuses `FAILED` state — add `CANCELLED` enum value (Audit #16)
- [ ] Brand Kit migration gap — verify migration numbering/chain (Audit #22)
- [ ] **10 service modules have zero test coverage** (HIGH-8)

### Deferred to Post-Launch
- [ ] Password reset flow
- [ ] OAuth / SSO (enterprise tier)
- [ ] User invitation flow (invite to existing tenant)
- [ ] Dark mode (Phase 2)
- [ ] Stripe Connect (marketplace payouts)
- [ ] Usage-based billing / metering
- [ ] Tenant deletion / deactivation (soft-delete pattern)
- [ ] Workflow cancellation / compensation
- [ ] Shadow review signal flow (implemented but not triggered by API)
- [ ] LearningAgent as separate Temporal workflow
- [ ] Workflow versioning / migration strategy
- [ ] Security scanning (Trivy, Snyk)
- [ ] Coverage reporting (codecov)
- [ ] Release automation (semantic-release)
- [ ] Frontend CI (npm test, next build)
- [ ] Docker image push to registry (ECR/GHCR)
- [ ] Deployment workflows (staging, production)
- [ ] 3D dollhouse viewer component
- [ ] Email blast generation
- [ ] Property website generation
- [ ] Image resizing for MLS specs
- [ ] Per-user limits (only per-tenant for now)
- [ ] Real-time usage dashboard
- [ ] Configurable limits via admin API
- [ ] Admin override to bypass limits
- [ ] S3 local mock (LocalStack)
