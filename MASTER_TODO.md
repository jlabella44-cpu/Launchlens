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
- [x] **Add per-image logging** — already logging before/after each T1 and T2 analysis with asset ID and proxy status
- [x] **Add timeouts** — 30s `asyncio.wait_for` per image on both T1 and T2; individual failures logged and skipped
- [ ] **Build proxy image pipeline** — generate 1024px proxies during ingestion (4x speedup, 90MB → 3MB); plan at `docs/PROXY-IMAGE-PIPELINE.md`

---

## P2 — Feature Work (Sessions 11–22)

### Credit System Frontend (Session 11)
- [x] Credit system frontend integration — billing page, dashboard balance, plan context, purchase flow all exist; added insufficient-credit warning to listing creation wizard

### Credit System Tests (Session 12)
- [x] Credit service test coverage — 27 tests covering deduction, FIFO, dual-pool, rollover, idempotency, concurrency, has_sufficient_credits, count_transactions

### Registration (Session 13)
- [ ] Complete registration flow tasks

### Webhooks (Session 14)
- [ ] Webhook expansion for credit bundle fulfillment

### Admin Dashboard (Session 15 + Progress Doc)
- [x] **Overview tab** — stats, attention alert, revenue summary, recent events feed
- [x] **Tenants tab** — search, sort, detail panel with edit form, webhook test, user management, credit adjustment
- [x] **Listings tab** — state filter, address search, pagination, retry/edit actions
- [x] **Credits tab** — global credit summary, tenant credit table with adjustment
- [x] **Audit Log tab** — action/resource filters, expandable JSON details
- [x] Lint & verify (ruff + TypeScript checks) — both pass clean

### E2E Tests (Session 16)
- [ ] Integration test cases (run after sessions 11–15 are merged)

### Stub Fixes (Session 18)
- [x] **Implement real video cutting** — already implemented with FFmpeg (H.264, aspect-ratio scaling, padding)
- [x] **Wire Canva provider into factory** — factory already selects `CanvaTemplateProvider` when `canva_api_key` is set
- [x] **Improve mock vision provider** — returns deterministic varied data based on image URL hash

### Test Coverage (Session 19)
- [x] ChapterAgent tests — already exist in `tests/test_agents/test_chapter.py`
- [x] LearningAgent tests — already exist in `tests/test_agents/test_learning.py`
- [x] WatermarkAgent tests — already exist in `tests/test_agents/test_watermark.py`
- [x] Fix PackagingAgent weight loading — replaced magic `1.0` with `DEFAULT_ROOM_WEIGHT` constant; LearningWeight query already wired
- [x] SSE endpoint tests — already exist in `tests/test_api/test_sse.py`
- [x] Middleware tests (security headers) — added `tests/test_monitoring/test_security_headers.py`
- [x] Provider tests — already exist for canva (12 tests), kling (6), claude (3), plus factory/fallback/routing

### API Polish (Session 20)
- [x] OpenAPI documentation / FastAPI metadata — already configured (title, version, description, 14 tag groups)
- [x] Response models — `ActionResponse` on approve/reject/retry, `CancelResponse` on cancel, `PipelineStatusResponse` on pipeline-status
- [x] Standardize pagination — `PaginatedResponse` generic added; paginated `/admin/tenants` and `/credits/transactions`
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
- [x] Performance event ingestion — already writes to `PerformanceEvent` on delivery (`distribution.py`) and export (`listings_media.py`)
- [x] Weight decay — `apply_decay` method already exists in `weight_manager.py` (90-day decay toward 1.0)
- [ ] XGBoost model upgrade (Phase 2 of weight manager)

### Listing Permissions — Remaining Phases
- [ ] Phase C: Cross-tenant email invitations (needs SES production access)
- [ ] Phase E: Email notifications (share/revoke/edit digest — templates built, needs SES)
- [ ] Blanket per-agent grant (Phase B) — `deps_permissions.py:50`

### Frontend Remaining Pages
- [x] Demo dropzone page — `src/app/demo/page.tsx` (drag-drop, file validation, upload progress)
- [x] Pricing page — `src/app/pricing/page.tsx` (4 tiers, credit calculator, Stripe checkout)
- [x] Export download page — `src/app/listings/[id]/export/page.tsx` (MLS/Marketing toggle, bundle download)
- [x] Video player — `src/components/listings/video-player.tsx` (HLS/MP4, chapter navigation)
- [x] Video upload — `src/components/listings/video-upload.tsx` (S3 key registration form)
- [x] Social preview cards — `src/components/listings/social-preview.tsx` (Instagram/TikTok/FB/YT cuts)

---

## P3 — Low Priority / Deferred

### Code Cleanup (from TODO.md)
- [x] **Listings.py monolith** — split 806-line `listings_media.py` into `listings_video.py` (115), `listings_import.py` (147), `listings_review.py` (130), keeping media at 440
- [x] **CSP blocks frontend** — already relaxed to `frame-ancestors 'none'` (API backend only)
- [ ] **Pipeline status endpoint expensive** — `get_pipeline_status` recomputes on every request; needs caching
- [x] Dead comment in listings.py (Audit #18) — no longer present
- [x] Unused listing states: `SHADOW_REVIEW`, `GENERATING`, `DELIVERING`, `TRACKING` (Audit #19) — never existed in enum
- [ ] Test JWT fixture doesn't create User rows (Audit #20)
- [x] `upload-urls` endpoint uses `body: dict` (Audit #12) — now uses `UploadUrlsRequest` Pydantic schema
- [x] Cancel listing reuses `FAILED` state (Audit #16) — `CANCELLED` enum added in migration 024
- [x] Brand Kit migration gap (Audit #22) — chain is correct (011→013), gap is harmless
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
