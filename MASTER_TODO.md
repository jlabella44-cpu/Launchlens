# ListingJet — Master TODO

Rework tracker. Spec: `docs/superpowers/specs/2026-09-05-free-tier-rework-design.md`.

| Phase | Branch / PR | Status |
|---|---|---|
| 1 Security fixes | `fix/security-week1` / #306 | done, awaiting merge |
| 2 Job queue replaces Temporal | `feat/job-queue` / #307 | done, awaiting merge |
| 3 Delete and flag | `chore/delete-and-flag` / #308 | done, awaiting merge |
| 4 Claude providers + photo analysis | `feat/claude-providers` / #309 | done, awaiting merge |
| 5 Content + social | `feat/content-social` / #310 | done, awaiting merge |
| 6 Video two-tier (ffmpeg + Runway) | `feat/video-two-tier` / #311 | done, awaiting merge |
| 7 Frontend, CI, hosting config | `feat/frontend-ci-hosting` / #312 | done, awaiting merge |
| 8 Docs rewrite | `docs/rewrite-claude-md` / #313 | done, awaiting merge |

Merge order: #306 → #307 → #308 → #309 → #310 → #311 → #312 → #313

## Carried items
- Real-provider runs are pending keys: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `RUNWAY_API_KEY`.
- Ops: create the Supabase/Upstash/R2/Render/Vercel/Runway accounts — see [free-tier-setup.md](docs/runbooks/free-tier-setup.md).
- Ops: move `GOOGLE_VISION_API_KEY` value to `GOOGLE_API_KEY` in Render env (alias keeps the old name working, but Render's env list now shows both — copy the value and delete the old key).
- Runway API has no Kling — routing is `gen4_turbo`/`veo3.1_fast` via settings; revisit if Runway adds it.
- Frontend lint: `no-explicit-any`, `no-img-element`, `set-state-in-effect` downgraded to warnings — 79 warnings to burn down.
- Frontend: SSE hook reconnect has no backoff.
- `services/pii_filter.sanitize_for_prompt` does not recurse into lists.
- SSE auth passes the access JWT in the `?token=` query string (`api/deps.get_current_user_or_query_token`); it should use a short-lived, single-purpose ticket instead so the long-lived JWT never lands in server/proxy access logs.
- Watchdog nuance: `pipeline/runner.reclaim_stale` treats only `RUNNING` as active — a job left `QUEUED`/`WAITING` (deferred) past what would be its cut-off is not covered by this path and would be failed rather than reclaimed if that changes without adjusting the query.
- No `LICENSE` file, though the README used to claim MIT — owner decision needed.
