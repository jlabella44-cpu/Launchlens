# ListingJet — Deferred Items

Items from the code quality audit that need design decisions, larger refactors, or are low priority.

## Needs Design Decision

- **Dual credit systems (Audit #8):** `CreditAccount` table vs `Tenant.credit_balance` — two sources of truth for credit balance. Need product decision on which is canonical. `CreditService` uses `CreditAccount`; admin API uses `Tenant.credit_balance`. Risk: balances diverge.

## Needs Larger Refactor

- **Listings.py monolith (Audit #11):** 800+ line single file with 19 endpoints and scattered inline imports. Should split into sub-routers (listings CRUD, review, export, video, package). Risky mid-session — needs careful route migration.

- **CSP blocks frontend (Audit #13):** `SecurityHeadersMiddleware` sets `Content-Security-Policy: default-src 'self'` which blocks inline styles, external fonts, CDN scripts, and Three.js WebGL. Needs frontend audit to determine correct CSP directives (at minimum `style-src 'unsafe-inline'`, likely `script-src` and `connect-src` adjustments for Three.js, API calls, and Stripe.js).

- **Pipeline status endpoint expensive (Audit #17):** `get_pipeline_status` runs `predict_engagement()` and `extract_features()` on every request, computing over all vision results. Needs caching strategy — either compute once during pipeline execution and store on the listing, or add Redis caching with TTL.

## Low Priority Cleanup

- **Dead comment in listings.py (Audit #18):** `# Duplicate retry endpoint removed — use the one at line ~616` at end of file.

- **Unused listing states (Audit #19):** `SHADOW_REVIEW`, `GENERATING`, `DELIVERING`, `TRACKING` don't appear in transition logic. Should audit and remove or document intended use.

- **Test JWT fixture doesn't create User rows (Audit #20):** `make_jwt` generates `"sub": f"user-{tenant_id}"` — not a real UUID, no corresponding User row. Tests that go through `get_current_user` would fail. Suggests some endpoints aren't tested through full auth stack.

- **upload-urls endpoint uses `body: dict` (Audit #12 partial):** No Pydantic schema, no OpenAPI docs for request body, no input validation beyond manual key access.

- **Cancel listing reuses FAILED state (Audit #16):** Response returns `"state": "cancelled"` but `ListingState` has no `CANCELLED` value. Should add `CANCELLED` enum value or honestly return `"failed"`.

- **Brand Kit migration gap (Audit #22):** `brand_kit.py` model referenced in migration 011 but migration numbering/chain should be verified.
