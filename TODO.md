# ListingJet — Deferred Items

Items needing design decisions or pending verification.

> **Note:** Code-quality audit items (#8, #11, #12, #13, #16, #17, #18, #19, #20, #22) that previously lived under "Needs Larger Refactor" and "Low Priority Cleanup" have all been resolved. See the `[x]` entries under MASTER_TODO P3 ("Code Cleanup (from TODO.md)") for the receipts.

## Needs Design Decision

- **Nav grouping (UX W001):** Authenticated nav has 8+ top-level links with no hierarchy. Group into primary (Dashboard, Listings) and secondary/utility (Analytics, Billing, Settings, Support, Changelog) with a separator, or move Help items into a dropdown. Need design call on which items are primary.

- **Settings sub-nav (UX W007):** `/settings` and `/settings/team` are separate top-level routes with no sidebar between them. A persistent settings sidebar in `settings/layout.tsx` (Brand Kit, Team, Connected Accounts, Language) would unify navigation. Needs layout + route decisions.

- **Billing vs pricing route duplication (UX S003):** Both `/billing` and `/pricing` exist. Need product decision on whether `/pricing` is still needed post-auth, or should be removed/redirected for logged-in users.

- **Review page access gating (UX S004):** `/review` exists but intended audience is unclear. If internal/staff-only, gate behind a role check at the route level rather than relying on API 403s.

- **Social post hub entry point (UX S006):** Social workflow is accessible from the listing detail page AND via a separate route. Labeling and primary entry point need a decision.

## Low Priority Cleanup

- **CMA / microsite silent `.catch` on listing detail (UX W004):** `listings/[id]/page.tsx:64-65` swallows errors on initial prefetch via `.catch(() => {})`. Low priority because the fallback "Generate" button resurfaces the same error on retry, but could be made explicit if a user-visible failure indicator is desired.

## Pending Verification

- **Dollhouse render on real listings (PR #201 merged):** The `DollhouseRenderAgent` was shipped but hasn't been run against a real floorplan + room photos yet. When a listing with a real floorplan is available, run the pipeline and inspect the generated PNG at `listings/{id}/dollhouse.png`. The gpt-image-1.5 prompt in `src/listingjet/providers/openai_dollhouse.py:26` is a first cut and will likely want tuning after the first real output is reviewed.

- **Virtual staging + object removal real output (PR #202):** Switched from DALL-E 3 text-only to gpt-image-1.5 with real image input. Before merging, eye a sample of both `stage_image()` and `remove_object()` output on real photos — the model will behave differently than the current broken hallucination.

- **Team invite email template (PR #205):** The `team_member_invite` HTML template in `services/email_templates.py` is a first cut. Send yourself a real invite on prod after #205 merges (plus the Resend SMTP wiring from #261) to verify it renders correctly in a real inbox and the accept link round-trips through #206's frontend.

## Housekeeping

- **Untracked session handoff docs:** `docs/SESSION-HANDOFF-2026-04-07-deploy.md`, `docs/SESSION-HANDOFF-2026-04-07.md`, `docs/SESSION-HANDOFF-VIDEO-QUALITY.md` — historical records of already-shipped PRs. Either commit to `docs/archive/` or delete.

- **Untracked operational docs:** `frontend/UX_AUDIT.md` should either be committed as document-of-record or deleted since most items are now resolved. (`docs/runbooks/secret-rotation.md` and `scripts/smoke_resend.py` were committed via PR #260 on 2026-04-22.)
