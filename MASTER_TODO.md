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
- [x] **Run `cdk deploy`** — deployed 2026-04-16 from main. Only `ListingJetServices` drifted; applied task-def rollover + `/launchlens/*` → `/listingjet/*` log groups + S3 bucket cutover. All ECS services healthy on new task defs (api:15, worker:14, temporal:7).
- [x] **Apply `property_data` table migration** (blocker — obs #1028) — fixed entrypoint.sh stamp bug that was skipping 023+024; explicit ECS migrate task added to deploy.yml
- [x] **Run missing migrations on prod DB** — `alembic upgrade head` via deploy.yml `Run database migrations` step (ECS run-task); manual runbook at `scripts/run_prod_migrations.sh`
- [x] **Separate dev/prod S3 buckets** — cutover deployed 2026-04-16. Live bucket is `listingjet-media-265911026550-us-east-1`; old `listingjet-dev` (913 objects / ~3 GB of pre-launch test data) and empty `listingjet-prod` were deleted post-deploy. Stale default `s3_bucket_name = "listingjet-dev"` remains in `src/listingjet/config/__init__.py:81` — harmless in prod (env var overrides), but a local-dev fallback landmine; fix in a follow-up.
- [x] **Rename CloudWatch log groups** from `/launchlens/*` to `/listingjet/*` — deployed 2026-04-16. Old `/launchlens/*` log groups were replaced on deploy; historical logs under the old names are gone (retention was 30 days so no meaningful loss).
- [ ] **Pre-launch infra revert** — apply `docs/PRE_LAUNCH_INFRA_CHECKLIST.md` (RDS/Redis/ECS upsizing, Multi-AZ, Container Insights, budget ceiling)
- [ ] **🚨 RDS encrypted-storage migration** — live DB `kjyxgeldpfef` is unencrypted; must migrate to encrypted instance before real user data lands. One-shot ~30-60 min downtime window. Full cutover plan in `docs/PRE_LAUNCH_INFRA_CHECKLIST.md` (section A).
- [ ] **🚨 Confirm email provider — SMTP path appears abandoned in favor of Resend.** Verified live state on 2026-04-16: `listingjet/app` has `RESEND_API_KEY` set to a real `re_...` value (36 chars), `EMAIL_ENABLED=true`, and `SMTP_PASSWORD` is **empty string** (not the old `PLACEHOLDER_SMTP_PASSWORD`). Action: audit `src/listingjet/notifications/` for any remaining SMTP callers (if none, drop `SMTP_PASSWORD` from the secret + `.env.example`); otherwise pick one provider and delete the other path. SES production access is still pending (sandbox: 1/sec, 200/day cap).

### Post-Apr-14 Infra Followups (from the drift-fix + #226 deploy session)
- (RDS encryption migration — see the P0 entry above; same item, single source of truth.)
- (SMTP password — superseded. Verified live on 2026-04-16: `SMTP_PASSWORD` in `listingjet/app` is an empty string, not a placeholder. Resend is the active provider via `RESEND_API_KEY`. The remaining decision is the email-provider audit/cleanup tracked in the P0 entry above.)
- (~~Delete orphan S3 bucket `listingjet-media-265911026550-us-east-1`~~ — **DO NOT DELETE.** This is the **live CDK-managed MediaBucket** as of the 2026-04-16 cutover. The actually-orphaned buckets (`listingjet-dev`, `listingjet-prod`) were already deleted on 2026-04-16.)
- [ ] **Rotate the `handoff-safety-20260414-0830` snapshot** out of retention once the DB has been migrated to encrypted storage (it's a pre-migration safety net; keep at least until the new encrypted instance is verified).
- [ ] **Verify `deletion_protection` stays True** on the real Postgres — today's rollbacks toggled it off once. Good safety net, add CloudWatch alarm if CDK lets it drift again.

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
- [x] Create `README.md` — 244 lines with architecture diagram, quick start, tech stack, CI badges
- [x] Update `.env.example` — added JWT refresh, v3 Stripe tiers, LLM provider, Canva OAuth, SES, property data keys
- [x] Create `CHANGELOG.md` — 226 lines documenting features by milestone
- [ ] Update `PROJECT_OVERVIEW_FOR_LLM.md`
- [x] Add CI badge to README — test + lint badges present

### Learning Loop (Session 22)
- [x] Wire `LearningAgent` into pipeline — already in Step 6 of `listing_pipeline.py` after distribution
- [x] Photo reorder endpoint — `POST /{listing_id}/package/reorder` already in `listings_media.py`
- [x] Performance event ingestion — already writes to `PerformanceEvent` on delivery (`distribution.py`) and export (`listings_media.py`)
- [x] Weight decay — `apply_decay` method already exists in `weight_manager.py` (90-day decay toward 1.0)
- [ ] XGBoost model upgrade (Phase 2 of weight manager)

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
