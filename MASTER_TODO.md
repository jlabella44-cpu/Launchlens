# ListingJet — Master TODO

Rework tracker. Spec: `docs/superpowers/specs/2026-09-05-free-tier-rework-design.md`.

| Phase | Branch / PR | Status |
|---|---|---|
| 1 Security fixes | `fix/security-week1` / #306 | done, awaiting merge |
| 2 Job queue replaces Temporal | `feat/job-queue` / #307 | done, awaiting merge |
| 3 Delete and flag | `chore/delete-and-flag` / #308 | done, awaiting merge |
| 4 Claude providers + photo analysis | `feat/claude-providers` / #309 | done, awaiting merge |
| 5 Content + social | `feat/content-social` / #310 | done, awaiting merge |
| 6 Video two-tier (ffmpeg + Runway) | — | |
| 7 Frontend, CI, hosting config | — | |
| 8 Docs rewrite | — | |

## Carried items
- Phase 6: `VideoAsset.chapters` derived from the clip manifest (chapter agent removed in Phase 3).
- Phase 7: frontend build gate in CI (cannot build on the dev machine); wire `pipeline-progress.tsx` to SSE; single `vercel.json` in `frontend/`.
- Phase 7: `pipeline-status.tsx` lists stale state names (content, brand_social, chapters, compliance).
- `services/pii_filter.sanitize_for_prompt` does not recurse into lists.
- Pipeline watchdog to replace Temporal's execution timeout (`PIPELINE_TIMEOUT` state is unused).
- Operational: create Supabase/Upstash/R2/Render/Vercel/Runway accounts (spec "Operational steps").
- Ops: move `GOOGLE_VISION_API_KEY` value to `GOOGLE_API_KEY` in Render env (alias keeps the old name working, but Render's env list now shows both — copy the value and delete the old key).
