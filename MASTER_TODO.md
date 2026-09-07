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
| 7 Frontend, CI, hosting config | — | |
| 8 Docs rewrite | — | |

## Carried items
- Phase 7: frontend build gate in CI (cannot build on the dev machine); wire `pipeline-progress.tsx` to SSE; single `vercel.json` in `frontend/`.
- Phase 7: `pipeline-status.tsx` lists stale state names (content, brand_social, chapters, compliance).
- Phase 7: remove `video-upload.tsx` S3 key form if still present.
- `services/pii_filter.sanitize_for_prompt` does not recurse into lists.
- Pipeline watchdog to replace Temporal's execution timeout (`PIPELINE_TIMEOUT` state is unused).
- Operational: create Supabase/Upstash/R2/Render/Vercel/Runway accounts (spec "Operational steps").
- Ops: move `GOOGLE_VISION_API_KEY` value to `GOOGLE_API_KEY` in Render env (alias keeps the old name working, but Render's env list now shows both — copy the value and delete the old key).
- Ops: set `RUNWAY_API_KEY` in Render; `FFMPEG_BIN` defaults to `ffmpeg` (Docker image has it).
- Runway API has no Kling — routing is `gen4_turbo`/`veo3.1_fast`; revisit if Runway adds it.
