# ListingJet — Master TODO

Rework tracker. Spec: `docs/superpowers/specs/2026-09-05-free-tier-rework-design.md`.

| Phase | Branch / PR | Status |
|---|---|---|
| 1 Security fixes | `fix/security-week1` / #306 | done, awaiting merge |
| 2 Job queue replaces Temporal | `feat/job-queue` / #307 | done, awaiting merge |
| 3 Delete and flag | `chore/delete-and-flag` | done, awaiting merge |
| 4 Claude providers + photo analysis | — | next |
| 5 Content + social | — | |
| 6 Video two-tier (ffmpeg + Runway) | — | |
| 7 Frontend, CI, hosting config | — | |
| 8 Docs rewrite | — | |

## Carried items
- Phase 4: Claude provider passes `temperature` (rejected by current SDK); vision tier 1 swallows provider errors; record real token usage.
- Phase 6: `VideoAsset.chapters` derived from the clip manifest (chapter agent removed in Phase 3).
- Phase 7: frontend build gate in CI (cannot build on the dev machine); wire `pipeline-progress.tsx` to SSE; single `vercel.json` in `frontend/`.
- Pipeline watchdog to replace Temporal's execution timeout (`PIPELINE_TIMEOUT` state is unused).
- Operational: create Supabase/Upstash/R2/Render/Vercel/Runway accounts (spec "Operational steps").
