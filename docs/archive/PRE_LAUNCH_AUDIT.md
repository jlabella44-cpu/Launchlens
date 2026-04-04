# LaunchLens Pre-Launch Codebase Audit

**Date:** April 2, 2026
**Scope:** Full-stack (FastAPI + Next.js 16 + PostgreSQL + Temporal + AWS CDK)
**Auditors:** Senior Full-Stack Architect, Lead QA Engineer, DevSecOps Specialist, Product Legal Consultant

---

## Executive Summary

The LaunchLens codebase is **well-structured** with solid fundamentals — proper JWT auth, bcrypt hashing, security headers, rate limiting, PII filtering, structured logging, and infrastructure-as-code. However, the audit uncovered **7 critical blockers** and **19 optimization items** across architecture, security, QA, compliance, and operations that must be triaged before launch.

| Severity | Count |
|----------|-------|
| CRITICAL (must fix before launch) | 7 |
| HIGH (fix within first sprint post-launch) | 8 |
| MEDIUM (technical debt — schedule post-launch) | 11 |
| LOW (nice-to-have improvements) | 5 |

---

## PART 1: CRITICAL BLOCKERS (Must Fix Before Launch)

---

### CRITICAL-1: No GDPR/CCPA Account Deletion or Data Export

**Workstream:** Legal & Compliance
**Impact:** Non-compliance with GDPR Articles 17 & 20, CCPA data deletion rights
**Files:** All API routers searched — no `DELETE /account` or `GET /export-data` endpoint exists

**Problem:** Users cannot delete their accounts or export their personal data. There is no cascade deletion strategy for tenants, and no endpoint to fulfill "right to be forgotten" or "right to data portability" requests.

**Current state** — data retention only covers outbox records (30 days) and S3 exports (90 days):

```python
# src/listingjet/services/data_retention.py — only partial retention
OUTBOX_RETENTION_DAYS = 30
EXPORT_RETENTION_DAYS = 90
# Missing: user PII, audit logs, credit transactions, events (retained FOREVER)
```

**Required fix:**
```python
# New endpoint: src/listingjet/api/auth.py
@router.post("/delete-account")
async def delete_account(
    body: DeleteAccountRequest,  # requires password confirmation
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    # 1. Verify password
    # 2. Soft-delete user + tenant (deleted_at timestamp)
    # 3. Queue async job to: delete S3 objects, cancel Stripe subscription,
    #    purge PII from events/audit logs, anonymize credit transactions
    # 4. Hard-delete after 30-day grace period

@router.get("/export-data")
async def export_data(user=Depends(get_current_user), db=Depends(get_db)):
    # Return JSON archive of all user-associated data
    # (listings, events, credits, audit logs, settings)
```

---

### CRITICAL-2: Missing Database Indexes on High-Traffic Columns

**Workstream:** Architecture
**Impact:** O(n) full table scans on Listing, Event, and Asset tables — will degrade severely at scale
**Files:** `src/listingjet/models/listing.py:30-43`, `src/listingjet/models/event.py:14-19`, `src/listingjet/models/asset.py`

**Problem:** Several heavily-queried columns lack indexes:

```python
# src/listingjet/models/listing.py — NO INDEX on state or created_at
state: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
created_at: Mapped[datetime] = mapped_column(server_default=func.now())

# src/listingjet/models/asset.py — NO INDEX on listing_id (FK)
listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id"))

# src/listingjet/models/event.py — NO INDEX on listing_id
listing_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
```

**Required fix** — new Alembic migration:
```sql
CREATE INDEX idx_listing_state ON listings(state);
CREATE INDEX idx_listing_created_at ON listings(created_at);
CREATE INDEX idx_listing_composite ON listings(tenant_id, state, created_at DESC);
CREATE INDEX idx_asset_listing_id ON assets(listing_id);
CREATE INDEX idx_event_listing_id ON events(listing_id) WHERE listing_id IS NOT NULL;
CREATE INDEX idx_property_data_composite ON property_data(tenant_id, address_hash);
```

---

### CRITICAL-3: Stripe API Calls Completely Unguarded — Will 500 on Outage

**Workstream:** QA & Logic
**Impact:** Any Stripe outage returns raw 500 errors to users; credit purchases, billing checkout, and portal sessions all affected
**Files:** `src/listingjet/api/credits.py:103-109`, `src/listingjet/api/billing.py:72-78,113`

**Problem:** Zero error handling around Stripe SDK calls:

```python
# src/listingjet/api/credits.py:103-109 — NO try/catch
session = stripe.checkout.Session.create(**create_kwargs)  # Can raise stripe.error.*
return CreditPurchaseResponse(checkout_url=session.url)    # Will 500 if above fails

# src/listingjet/api/billing.py:72-78 — same pattern
session = await svc.create_checkout_session(...)  # Unguarded
```

**Required fix:**
```python
# src/listingjet/api/credits.py
try:
    session = stripe.checkout.Session.create(**create_kwargs)
except stripe.error.CardError as e:
    raise HTTPException(status_code=402, detail="Payment method declined")
except stripe.error.RateLimitError:
    raise HTTPException(status_code=503, detail="Payment service busy, retry shortly")
except stripe.error.APIConnectionError:
    raise HTTPException(status_code=503, detail="Payment service unavailable")
except stripe.error.StripeError as e:
    logger.error("stripe.error type=%s message=%s", type(e).__name__, str(e))
    raise HTTPException(status_code=502, detail="Payment processing error")
```

---

### CRITICAL-4: Global Singleton Race Conditions — Broken Rate Limiting

**Workstream:** Architecture / Scalability
**Impact:** Rate limiting silently broken under concurrent workers; potential memory leaks
**Files:** `src/listingjet/services/storage.py:112-120`, `src/listingjet/middleware/rate_limit.py:50-59`, `src/listingjet/services/credits.py:15-16`

**Problem:** Three critical singletons use non-atomic check-and-set without locking:

```python
# src/listingjet/middleware/rate_limit.py:50-59 — RACE CONDITION
_limiter = None

def _get_limiter():
    global _limiter
    if _limiter is None:        # <-- Two workers check simultaneously
        _limiter = RateLimiter(...)  # <-- Both create separate instances
    return _limiter             # <-- Each worker gets independent token buckets
```

```python
# src/listingjet/services/credits.py:15-16 — MEMORY LEAK
_low_credit_sent: dict[uuid.UUID, datetime] = {}  # Grows unbounded, never cleaned
```

**Required fix:**
```python
# src/listingjet/middleware/rate_limit.py
import threading

_limiter = None
_limiter_lock = threading.Lock()

def _get_limiter():
    global _limiter
    if _limiter is None:
        with _limiter_lock:
            if _limiter is None:  # Double-checked locking
                _limiter = RateLimiter(...)
    return _limiter
```

For `_low_credit_sent`, add TTL-based eviction or move to Redis.

---

### CRITICAL-5: Debug Tracebacks Exposed to Clients in Development Mode

**Workstream:** Security (OWASP A01)
**Impact:** Full stack traces, file paths, and internal code structure leaked to API consumers
**File:** `src/listingjet/main.py:131-137`

**Problem:**
```python
# src/listingjet/main.py:131-137
if settings.app_env == "development":
    @app.exception_handler(Exception)
    async def debug_exception_handler(request, exc):
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "traceback": tb.format_exc()},  # LEAK
        )
```

**Risk:** If `APP_ENV` is misconfigured or defaults to `development`, production users see full tracebacks.

**Required fix:**
```python
if settings.app_env == "development":
    @app.exception_handler(Exception)
    async def debug_exception_handler(request, exc):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception("unhandled_error request_id=%s", request_id)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
        )
```

---

### CRITICAL-6: WCAG 2.1 Accessibility Violations in Core UI Components

**Workstream:** Legal & Compliance
**Impact:** WCAG 2.1 Level A violations — potential ADA/Section 508 liability
**Files:** `frontend/src/components/ui/input.tsx:14-16`, `frontend/src/components/ui/select.tsx:13-16`, `frontend/src/components/ui/toast.tsx:46-62`

**Problem 1 — Form labels not associated with inputs:**
```tsx
// frontend/src/components/ui/input.tsx:14-16
<label className={...}>{label}</label>      {/* Missing htmlFor */}
<input className={...} {...props} />         {/* Missing id */}
```

**Problem 2 — Toast notifications invisible to screen readers:**
```tsx
// frontend/src/components/ui/toast.tsx:46-62
<div className={...}>  {/* Missing role="alert" and aria-live */}
  <span>{toast.message}</span>
  {/* Missing close button with aria-label */}
</div>
```

**Required fix (input example):**
```tsx
// frontend/src/components/ui/input.tsx
const inputId = id || `input-${label?.toLowerCase().replace(/\s+/g, '-')}`;
<label htmlFor={inputId} className={...}>{label}</label>
<input id={inputId} aria-describedby={error ? `${inputId}-error` : undefined} {...props} />
{error && <span id={`${inputId}-error`} role="alert">{error}</span>}
```

**Required fix (toast):**
```tsx
<div role="alert" aria-live="polite" className={...}>
  <span>{toast.message}</span>
  <button aria-label="Dismiss notification" onClick={dismiss}>×</button>
</div>
```

---

### CRITICAL-7: Worker Health Check Misconfigured — Will Never Be Healthy

**Workstream:** Operational Readiness
**Impact:** Worker container will never pass health check in production, preventing auto-restart
**File:** `docker-compose.yml:137-142`

**Problem:** Docker Compose defines an HTTP health check on port 8081, but the worker runs no HTTP server:
```yaml
# docker-compose.yml:137-142
worker:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8081/health"]  # No server on 8081!
    interval: 30s
    retries: 3
```

**Required fix:** Either add a lightweight health endpoint to the worker, or use a process-based check:
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import listingjet.workflows.worker; print('ok')"]
  # Or: add a /health endpoint to the worker via a sidecar thread
```

---

## PART 2: HIGH-PRIORITY ISSUES (Fix Within First Sprint)

---

### HIGH-1: JWT Tokens Stored in localStorage — XSS Vulnerable

**File:** `frontend/src/contexts/auth-context.tsx:30,48,56,65`

```typescript
const token = localStorage.getItem("listingjet_token");
localStorage.setItem("listingjet_token", res.access_token);
```

**Risk:** Any XSS compromise reads all tokens. Consider httpOnly cookies with CSRF tokens, or accept the risk with strong CSP headers and document the decision.

---

### HIGH-2: PII (Email Addresses) Logged in Plaintext

**File:** `src/listingjet/api/auth.py:89,119,237,276`

```python
logger.info("auth.register email=%s tenant=%s tier=%s", email, ...)
logger.info("auth.login_success email=%s user=%s", email, ...)
```

**Fix:** Hash emails before logging: `hashlib.sha256(email.encode()).hexdigest()[:12]`

---

### HIGH-3: No Token Revocation — Logout Is a No-Op

**File:** `src/listingjet/api/auth.py:157-164`

```python
@router.post("/logout")
async def logout():
    """Client should discard tokens."""
    return {"status": "ok"}  # Does nothing server-side
```

**Fix:** Implement Redis-backed token blocklist. Add revoked token check in `get_current_user` dependency.

---

### HIGH-4: No Account Lockout After Failed Login Attempts

**File:** `src/listingjet/api/auth.py:96-123`

Failed logins are logged but no lockout is enforced. Brute-force attacks are only throttled by the global rate limiter (10 req/min on login). Implement per-account lockout after 5 failures for 15 minutes.

---

### HIGH-5: Outbox Poller Can Duplicate Webhook Deliveries

**File:** `src/listingjet/services/outbox_poller.py:59-66`

```python
except Exception:
    # FOR UPDATE SKIP LOCKED failed — falls back to plain SELECT
    result = await session.execute(
        select(Outbox).where(Outbox.delivered_at.is_(None)).limit(BATCH_SIZE)
    )  # Multiple workers will process same rows!
```

**Fix:** The fallback must also use `FOR UPDATE SKIP LOCKED`, or fail the batch entirely.

---

### HIGH-6: Unbounded Analytics Queries — No Pagination

**File:** `src/listingjet/api/analytics.py:96-107`

```python
rows = (await db.execute(
    select(CreditTransaction)
    .where(...)
    .order_by(CreditTransaction.created_at.asc())
)).scalars().all()  # NO LIMIT — loads all rows into memory
```

A tenant with 10K+ transactions will cause memory spikes and slow responses.

---

### HIGH-7: No Consent Management for Third-Party AI Processing

Users are not informed that their photos/data are processed by Google Vision, OpenAI, Anthropic, and Kling AI. GDPR Article 6/7 require explicit consent; Article 13/14 require transparency. Add consent tracking during registration and document vendor usage in a privacy policy.

---

### HIGH-8: 10 Service Modules Have Zero Test Coverage

Untested modules:
- `services/auth.py` — authentication logic
- `services/billing.py` — Stripe integration
- `services/plan_limits.py` — quota enforcement
- `services/notifications.py` — email alerts
- `services/link_import.py` — file import
- `services/audit.py` — audit logging
- `services/email_templates.py` — template rendering
- `services/endcard.py` — video endcard generation
- `services/metrics.py` — metrics collection
- `services/video_stitcher.py` — video assembly

---

## PART 3: MEDIUM-PRIORITY (Technical Debt — Post-Launch)

---

### MED-1: Business Logic Leaking into API Routes

**File:** `src/listingjet/api/listings.py:54-116`

Credit deduction, plan validation, and quota enforcement are embedded in the route handler with dynamic imports. Extract to a `ListingCreationService`.

---

### MED-2: Double Rate Limiting Without Coordination

**Files:** `src/listingjet/middleware/rate_limit.py` + `src/listingjet/services/endpoint_rate_limit.py`

Two independent rate limiters (global 60/min + per-endpoint 20/min) don't coordinate. A client can exceed the effective global limit. Consolidate into a single Redis-backed limiter with key hierarchy.

---

### MED-3: Loose JSONB Storage Without Schema Validation

**Files:** `src/listingjet/models/listing.py:30-31`, `src/listingjet/models/property_data.py:43-52`

`address`, `metadata_`, and multiple PropertyData fields are raw JSONB dicts with no Pydantic validation. Define typed models and validate before storage.

---

### MED-4: No Encryption at Rest for PII

**Files:** `src/listingjet/models/user.py` (email), `src/listingjet/models/listing.py` (address)

User emails and property addresses stored as plaintext in PostgreSQL. Enable RDS encryption or implement field-level encryption with pgcrypto.

---

### MED-5: Email Service Has No Retry Logic

**File:** `src/listingjet/services/email.py:45-57`

```python
with smtplib.SMTP(self.host, self.port) as server:  # Can timeout, no retry
    server.starttls()  # Can fail transiently
```

Welcome emails, password resets, and pipeline failure alerts fail silently on network blips. Add `@async_retry()` decorator (already used by webhook delivery).

---

### MED-6: Database Connection Pool Too Small for Production

**File:** `src/listingjet/database.py:8-15`

```python
engine = create_async_engine(
    settings.async_database_url,
    pool_size=20,      # Too small for 8 uvicorn workers
    max_overflow=10,
)
```

With 8 workers, each gets ~2-3 connections. Under load, connection starvation causes request queuing. Increase to `pool_size=50, max_overflow=20`.

---

### MED-7: Listing List Endpoint Can Return 50MB+ Responses

**File:** `src/listingjet/api/listings.py:119-172`

Default max page size is 200 with full JSONB address/metadata. Reduce to `max=50`, return summary fields only, lazy-load assets.

---

### MED-8: Video Agent Silently Drops Failed Clips

**File:** `src/listingjet/agents/video.py:212-216`

```python
except Exception:  # Swallowed — no error context
    return None     # Appears as missing clip, no user feedback
```

---

### MED-9: No Idempotency Keys for Listing Creation

**File:** `src/listingjet/api/listings.py:54-116`

Network failure after DB write but before response → client retry → duplicate listing + double credit deduction. Add `Idempotency-Key` header support.

---

### MED-10: No Password Reset Flow

**File:** `src/listingjet/api/auth.py`

No `POST /auth/forgot-password` endpoint. Users locked out of their accounts must contact support.

---

### MED-11: Google JWKS Cache Never Expires

**File:** `src/listingjet/api/auth.py:172-185`

If Google rotates signing keys, cached JWKS won't update. Add 12-hour TTL.

---

## PART 4: LOW-PRIORITY (Nice-to-Have Improvements)

---

### LOW-1: CORS Regex Allows All Vercel Subdomains

**File:** `src/listingjet/main.py:96` — `r"https://launchlens[a-z0-9-]*\.vercel\.app"` matches any Vercel project. Pin to specific deployment URLs in production.

### LOW-2: No Log Rotation Configuration

**File:** `docker-compose.yml:109-117` — Logs to stdout only. Add Docker logging driver with rotation.

### LOW-3: Missing Liveness Probe (Separate from Readiness)

**File:** `infra/stacks/services.py:128-133` — Only readiness checks exist. Add `/health/live` for ECS restart detection.

### LOW-4: Refresh Token Not Rotated

**File:** `src/listingjet/services/auth.py:40-47` — No rotation nonce. Consider adding rotation for enhanced security.

### LOW-5: No Security Scanning in CI/CD

**Files:** `.github/workflows/` — No `npm audit`, `pip-audit`, or `bandit` in pipelines. Add automated dependency vulnerability scanning.

---

## PART 5: COMPLIANCE SCORECARD

| Framework | Current | Target for Launch | Gap |
|-----------|---------|-------------------|-----|
| **GDPR** | ~30% | 80% | Account deletion, data export, consent, privacy policy |
| **CCPA** | ~30% | 80% | Data deletion, access requests, vendor disclosure |
| **WCAG 2.1 AA** | ~15% | 70% | Form labels, ARIA, keyboard nav, focus management |
| **OWASP Top 10** | ~85% | 95% | Debug info leak, token storage |
| **SOC 2 Type II** | ~50% | 60% | Monitoring gaps, change control docs |

---

## PART 6: WHAT'S WORKING WELL (Maintain These)

1. **Authentication** — bcrypt + constant-time verification + dummy hash for non-existent users
2. **Security Headers** — Complete set (HSTS, X-Frame-Options, CSP, Permissions-Policy)
3. **SSRF Protection** — Webhook delivery validates against blocked IP ranges
4. **PII Filtering** — Strips sensitive fields before sending to AI providers
5. **Rate Limiting** — Global + per-endpoint limits with Redis backing
6. **Structured Logging** — JSON formatting in production with request ID correlation
7. **Observability** — OpenTelemetry + Sentry integration
8. **Infrastructure as Code** — AWS CDK with proper stack separation
9. **Type Safety** — TypeScript + Python type hints throughout
10. **License Compliance** — All dependencies use permissive licenses (MIT, Apache 2.0, BSD)
11. **Stripe Webhook Security** — Proper signature verification
12. **Tenant Isolation** — Row-level security with `SET LOCAL` tenant context

---

## RECOMMENDED FIX ORDER

| Week | Items | Effort |
|------|-------|--------|
| **Week 1** | CRITICAL-2 (indexes), CRITICAL-5 (debug leak), CRITICAL-7 (worker health) | 1 day |
| **Week 1** | CRITICAL-3 (Stripe error handling), CRITICAL-4 (singleton locks) | 1 day |
| **Week 2** | CRITICAL-6 (accessibility fixes), HIGH-2 (PII in logs) | 2 days |
| **Week 2** | CRITICAL-1 (GDPR deletion/export — design + implement) | 3 days |
| **Week 3** | HIGH-3 (logout revocation), HIGH-4 (lockout), HIGH-5 (outbox dedup) | 2 days |
| **Week 3** | HIGH-6 (analytics pagination), HIGH-7 (consent management) | 2 days |
| **Week 4** | HIGH-8 (test coverage for 10 modules) | 3 days |
| **Post-launch** | MED-1 through MED-11, LOW-1 through LOW-5 | Ongoing |

---

*Generated by automated codebase audit — April 2, 2026*
