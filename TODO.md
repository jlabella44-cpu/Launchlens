# ListingJet — Deferred Items

Items from the code quality audit and UX audit that need design decisions, larger refactors, or are low priority.

## Needs Design Decision

- **Dual credit systems (Audit #8):** `CreditAccount` table vs `Tenant.credit_balance` — two sources of truth for credit balance. Need product decision on which is canonical. `CreditService` uses `CreditAccount`; admin API uses `Tenant.credit_balance`. Risk: balances diverge.

- **Nav grouping (UX W001):** Authenticated nav has 8+ top-level links with no hierarchy. Group into primary (Dashboard, Listings) and secondary/utility (Analytics, Billing, Settings, Support, Changelog) with a separator, or move Help items into a dropdown. Need design call on which items are primary.

- **Settings sub-nav (UX W007):** `/settings` and `/settings/team` are separate top-level routes with no sidebar between them. A persistent settings sidebar in `settings/layout.tsx` (Brand Kit, Team, Connected Accounts, Language) would unify navigation. Needs layout + route decisions.

- **Billing vs pricing route duplication (UX S003):** Both `/billing` and `/pricing` exist. Need product decision on whether `/pricing` is still needed post-auth, or should be removed/redirected for logged-in users.

- **Review page access gating (UX S004):** `/review` exists but intended audience is unclear. If internal/staff-only, gate behind a role check at the route level rather than relying on API 403s.

- **Social post hub entry point (UX S006):** Social workflow is accessible from the listing detail page AND via a separate route. Labeling and primary entry point need a decision.

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

- **CMA / microsite silent `.catch` on listing detail (UX W004):** `listings/[id]/page.tsx:64-65` swallows errors on initial prefetch via `.catch(() => {})`. Low priority because the fallback \"Generate\" button resurfaces the same error on retry, but could be made explicit if a user-visible failure indicator is desired.

- **Error boundary dashboard link (UX C004):** Mostly shipped in PR #207, but the audit's concern about \"no recovery path\" was inaccurate — the Try Again button already existed. The dashboard link was a 3-line addition. No further action needed unless specific pages want their own fallback.

## Pending Verification

- **Dollhouse render on real listings (PR #201 merged):** The `DollhouseRenderAgent` was shipped but hasn't been run against a real floorplan + room photos yet. When a listing with a real floorplan is available, run the pipeline and inspect the generated PNG at `listings/{id}/dollhouse.png`. The gpt-image-1.5 prompt in `src/listingjet/providers/openai_dollhouse.py:26` is a first cut and will likely want tuning after the first real output is reviewed.

- **Virtual staging + object removal real output (PR #202):** Switched from DALL-E 3 text-only to gpt-image-1.5 with real image input. Before merging, eye a sample of both `stage_image()` and `remove_object()` output on real photos — the model will behave differently than the current broken hallucination.

- **Team invite email template (PR #205):** The `team_member_invite` HTML template in `services/email_templates.py` is a first cut. Send yourself a real invite on staging after #205 merges to verify it renders correctly in a real inbox and the accept link round-trips through #206's frontend.

## Housekeeping

- **Untracked session handoff docs:** `docs/SESSION-HANDOFF-2026-04-07-deploy.md`, `docs/SESSION-HANDOFF-2026-04-07.md`, `docs/SESSION-HANDOFF-VIDEO-QUALITY.md` — historical records of already-shipped PRs. Either commit to `docs/archive/` or delete.

- **Untracked operational docs:** `docs/runbooks/secret-rotation.md` (valuable active runbook) and `scripts/smoke_resend.py` (useful email smoke test) should be committed. `frontend/UX_AUDIT.md` should either be committed as document-of-record or deleted since most items are now resolved.
