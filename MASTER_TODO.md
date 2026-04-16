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
- [x] **Apply `property_data` table migration** (blocker — obs #1028) — fixed entrypoint.sh stamp bug that was skipping 023+024; explicit ECS migrate task added to deploy.yml
- [x] **Run missing migrations on prod DB** — `alembic upgrade head` via deploy.yml `Run database migrations` step (ECS run-task); manual runbook at `scripts/run_prod_migrations.sh`
- [x] **Separate dev/prod S3 buckets** — `S3_BUCKET_NAME` env var and IAM now wired to CDK-managed `listingjet-media-{account}-{region}` bucket via `grant_read_write()`; deploy will provision the prod bucket
- [x] **Rename CloudWatch log groups** from `/launchlens/*` to `/listingjet/*` — updated in `infra/stacks/services.py`
- [ ] **Pre-launch infra revert** — apply `docs/PRE_LAUNCH_INFRA_CHECKLIST.md` (RDS/Redis/ECS upsizing, Multi-AZ, Container Insights, budget ceiling)
- [ ] **🚨 RDS encrypted-storage migration** — live DB `kjyxgeldpfef` is unencrypted; must migrate to encrypted instance before real user data lands. One-shot ~30-60 min downtime window. Full cutover plan in `docs/PRE_LAUNCH_INFRA_CHECKLIST.md` (section A).
- [ ] **🚨 Replace `SMTP_PASSWORD` placeholder with real credentials** — `listingjet/app` secret has `PLACEHOLDER_SMTP_PASSWORD`. Pick SES or Resend, generate real SMTP password, update secret, force ECS redeployment. See `docs/PRE_LAUNCH_INFRA_CHECKLIST.md` (section B).

### Cost Optimization — Data to Collect from AWS
After the cost-optimization branch is deployed and has run for **at least 7 days** (ideally 14), gather the following and bring it back to the next session for further right-sizing decisions. Commands documented in `docs/PRE_LAUNCH_INFRA_CHECKLIST.md`.

- [ ] **AWS Cost Explorer** — last 30 days, group by Service. Identifies the actual top spenders (NAT data transfer, Fargate, RDS, etc.).
- [ ] **AWS Compute Optimizer — ECS** — recommendations for `listingjet-api`, `listingjet-worker`, `listingjet-temporal`. Confirms or refines the manual right-sizing.
- [ ] **AWS Compute Optimizer — RDS** — recommendation for the `Postgres` instance.
- [ ] **CloudWatch — NAT Gateway `BytesOutToDestination`** — last 7 days. Decides whether ECR/CloudWatch Logs interface endpoints (~$14/mo each) are worth adding.
- [ ] **CloudWatch — ECS service CPU/Memory utilization** — `Average` and `Maximum` for the API and Worker over 7 days.
- [ ] **S3 Storage Lens / bucket metrics** — current size + version count on `listingjet-media-*` bucket. Validates the lifecycle policy is doing its job.
- [ ] **CloudWatch Logs storage** — total `IncomingBytes` per log group over 7 days. Catches noisy log producers.
- [ ] **Trusted Advisor cost checks** (if Business/Enterprise support) — automated recommendations.
- [ ] **AWS Cost Optimization Hub** — turn it on; it surfaces Savings Plans, Reserved Instance, and rightsizing opportunities for free.

---

## P1 — High Priority (First Sprint Post-Launch)

### Security (from Pre-Launch Audit)
- [x] **HIGH-1: JWT tokens stored in localStorage** — already using httpOnly cookies via `set_auth_cookies()`
- [x] **HIGH-2: PII (email addresses) logged in plaintext** — masked as `u***@e***.com` in all log output
- [x] **HIGH-3: No token revocation** — Redis-backed blocklist on logout; TTL matches token lifetime
- [x] **HIGH-4: No account lockout after failed login attempts** — Redis-based lockout (5 attempts / 15min)
- [x] **HIGH-7: No consent management for third-party AI processing** — register page + settings toggle + agent-level guards via `requires_ai_consent` flag + audit log on grant/revoke
- [x] **Rate limiting on auth endpoints** — Redis rate limiter already applied via `rate_limit()` dependency

### Data Integrity
- [x] **HIGH-5: Outbox poller can duplicate webhook deliveries** — `X-ListingJet-Idempotency-Key` header added
- [x] **HIGH-6: Unbounded analytics queries** — pagination with offset/limit on `/analytics/credits`
- [x] **Dual credit systems (Audit #8)** — Dropped `Tenant.credit_balance`; `CreditAccount` is sole source of truth (migration 046)

### Deployment
- [ ] **Deploy backend with new analytics endpoints** (ECR push + ECS redeploy)
- [ ] **Test analytics page on production**
- [ ] **Merge PR #109** once CI passes
- [x] **4 unpushed commits on local master** — already pushed; local main == origin/main

### Vision Pipeline
- [x] **Add per-image logging** — already logging before/after each T1 and T2 analysis with asset ID and proxy status
- [x] **Add timeouts** — 30s `asyncio.wait_for` per image on both T1 and T2; individual failures logged and skipped
- [x] **Build proxy image pipeline** — 1024px proxies generated during ingestion, vision T1/T2 + floorplan use proxy-first resolution, S3 cleanup on listing delete and demo expiry (full-res + proxy)

---

## P2 — Feature Work (Sessions 11–22)

### Credit System Frontend (Session 11)
- [x] Credit system frontend integration — billing page, dashboard balance, plan context, purchase flow all exist; added insufficient-credit warning to listing creation wizard

### Credit System Tests (Session 12)
- [x] Credit service test coverage — 27 tests covering deduction, FIFO, dual-pool, rollover, idempotency, concurrency, has_sufficient_credits, count_transactions

### Registration (Session 13)
- [x] Complete registration flow — backend registration, plan tier selection, credit account creation, welcome email, frontend register + onboarding pages all implemented

### Webhooks (Session 14)
- [x] Webhook expansion — emit `credit.bundle_fulfilled`, `billing.payment_failed`, `credit.low_balance` events via outbox

### Admin Dashboard (Session 15 + Progress Doc)
- [x] **Overview tab** — stats, attention alert, revenue summary, recent events feed
- [x] **Tenants tab** — search, sort, detail panel with edit form, webhook test, user management, credit adjustment
- [x] **Listings tab** — state filter, address search, pagination, retry/edit actions
- [x] **Credits tab** — global credit summary, tenant credit table with adjustment
- [x] **Audit Log tab** — action/resource filters, expandable JSON details
- [x] Lint & verify (ruff + TypeScript checks) — both pass clean

### E2E Tests (Session 16)
- [x] Integration test cases — 16 tests in `test_s11_15_workflows.py` covering all session 11-15 feature gaps

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
- [x] API versioning — `/api/v1/` prefix — all feature routes under `/v1`, health unversioned; conftest transport wrapper rewrites test paths

### Documentation (Session 21)
- [x] Create `README.md` — 244 lines with architecture diagram, quick start, tech stack, CI badges
- [x] Update `.env.example` — added JWT refresh, v3 Stripe tiers, LLM provider, Canva OAuth, SES, property data keys
- [x] Create `CHANGELOG.md` — 226 lines documenting features by milestone
- [x] Update `PROJECT_OVERVIEW_FOR_LLM.md`
- [x] Add CI badge to README — test + lint badges present

### Learning Loop (Session 22)
- [x] Wire `LearningAgent` into pipeline — already in Step 6 of `listing_pipeline.py` after distribution
- [x] Photo reorder endpoint — `POST /{listing_id}/package/reorder` already in `listings_media.py`
- [x] Performance event ingestion — already writes to `PerformanceEvent` on delivery (`distribution.py`) and export (`listings_media.py`)
- [x] Weight decay — `apply_decay` method already exists in `weight_manager.py` (90-day decay toward 1.0)
- [x] XGBoost model upgrade (Phase 2 of weight manager) — `train_model()` in WeightManager, triggered from LearningAgent after weight updates; falls back to rule-based when < 50 samples

### Listing Permissions — Remaining Phases
- [ ] Phase C: Cross-tenant email invitations (needs SES production access)
- [ ] Phase E: Email notifications (share/revoke/edit digest — templates built, needs SES)
- [x] Blanket per-agent grant (Phase B) — already implemented in `deps_permissions.py` (listing_id NULL + grantor_tenant_id)

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
- [x] **Pipeline status endpoint expensive** — engagement score cached in-process after first computation per listing
- [x] Dead comment in listings.py (Audit #18) — no longer present
- [x] Unused listing states: `SHADOW_REVIEW`, `GENERATING`, `DELIVERING`, `TRACKING` (Audit #19) — never existed in enum
- [x] Test JWT fixture doesn't create User rows (Audit #20) — `make_jwt` updated with proper UUID sub, role, and type fields
- [x] `upload-urls` endpoint uses `body: dict` (Audit #12) — now uses `UploadUrlsRequest` Pydantic schema
- [x] Cancel listing reuses `FAILED` state (Audit #16) — `CANCELLED` enum added in migration 024
- [x] Brand Kit migration gap (Audit #22) — chain is correct (011→013), gap is harmless
- [x] **10 service modules have zero test coverage** (HIGH-8) — added tests for account_lifecycle, audit, notifications, email_templates, link_import, endcard, drip_scheduler (3 remaining: canva_tokens, idx_feed_poller — require external mocks)

### Session Apr 9, 2026 — Resolved
- [x] **Dependabot cryptography CVE-2026-39892** — merged #195, bumped to 46.0.7
- [x] **Dual credit systems** — dropped `Tenant.credit_balance`, migration 046
- [x] **CI workflows reference `master`** — removed dead branch from lint/docker/test workflows
- [x] **Deploy not gated on tests** — added `needs: test` to deploy job
- [x] **IDX API keys stored plaintext** — added Fernet encryption via `FIELD_ENCRYPTION_KEY` env var
- [x] **Health score history no cleanup** — added 90-day cleanup to `data_retention.py`
- [x] **Video prompts generic** — expanded to 31 room types, spatial walkthrough ordering
- [x] **No automatic market tracking** — added `MarketTracker` using ATTOM API (zero agent setup)

### Deferred to Post-Launch
- [x] Password reset flow — `/auth/forgot-password` + `/auth/reset-password` implemented with 15-min JWT tokens, rate limited, frontend pages wired (blocked only on SES prod access for email delivery)
- [ ] OAuth / SSO (enterprise tier)
- [x] User invitation flow (invite to existing tenant) — `POST/DELETE /team/invite`, `POST /team/invite/{token}/accept` in `team.py`
- [x] Dark mode (Phase 2) — `ThemeToggle` component + comprehensive `.dark` CSS variables in `globals.css`
- [ ] Stripe Connect (marketplace payouts)
- [ ] Usage-based billing / metering
- [x] Tenant deletion / deactivation — migration 050 adds `deactivated_at`; `DELETE /admin/tenants/{id}` soft-deletes, `POST /reactivate` restores; 403 guard in start_pipeline
- [x] Workflow cancellation / compensation — `cancel_workflow()` on TemporalClient; `cancel_listing` now sends Temporal cancellation signal after DB state update
- [x] Shadow review signal flow — `POST /admin/listings/{id}/shadow-approve` sends Temporal signal; `signal_shadow_review_approved` added to TemporalClient
- [x] LearningAgent as separate Temporal workflow — `LearningWorkflow` in `workflows/learning_workflow.py`; pipeline Step 6 now fires child workflow with `ABANDON` policy (non-blocking, registered in worker)
- [ ] Workflow versioning / migration strategy
- [x] Security scanning — Trivy CRITICAL scan in deploy.yml (blocks deploy on unfixed CVEs)
- [x] Coverage reporting — pytest-cov + Codecov upload in test.yml
- [x] Release automation (semantic-release) — `.releaserc.json` + `.github/workflows/release.yml`
- [x] Frontend CI — `frontend` job in test.yml: npm ci, lint, vitest run, next build
- [x] Docker image push to registry (ECR/GHCR) — worker image tagged and pushed in `deploy.yml`
- [ ] Deployment workflows (staging, production)
- [x] 3D dollhouse viewer component — `DollhouseViewer` Canvas-based floorplan renderer; wired into `DollhouseCard`
- [x] Email blast generation — `POST /listings/{id}/email-blast` LLM-generated HTML+text email
- [x] Property website generation — `POST /listings/{id}/microsite` in `microsite.py`; `ListingMicrosite` model
- [x] Image resizing for MLS specs — `MLS_PROFILES` dict in `mls_export.py`; `MLSExportAgent` accepts `mls_profile` param
- [x] Per-user limits — `max_listings_per_day_per_user` in PLAN_LIMITS (free=3, lite=10, active_agent=25, team=∞); checked in start_pipeline behind `bypass_limits` flag
- [x] Real-time usage dashboard — `GET /admin/usage-stream` SSE + `UsageDashboard` React component
- [x] Configurable limits via admin API — `GET/PATCH /admin/tenants/{id}/limits`; `plan_overrides` JSONB merged on top of plan defaults
- [x] Admin override to bypass limits — `bypass_limits` boolean on Tenant (migration 050); skips credit deduction + daily quota in start_pipeline
- [x] S3 local mock (LocalStack) — `localstack` service in `docker-compose.yml`; init script creates `listingjet-media-local` bucket
