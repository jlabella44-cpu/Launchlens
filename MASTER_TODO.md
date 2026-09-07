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
| 7 Frontend, CI, hosting config | `feat/frontend-ci-hosting` / #TBD | done, awaiting merge |
| 8 Docs rewrite | — | |

## Carried items
- `services/pii_filter.sanitize_for_prompt` does not recurse into lists.
- Operational: create Supabase/Upstash/R2/Render/Vercel/Runway accounts (spec "Operational steps").
- Ops: move `GOOGLE_VISION_API_KEY` value to `GOOGLE_API_KEY` in Render env (alias keeps the old name working, but Render's env list now shows both — copy the value and delete the old key).
- Ops: set `RUNWAY_API_KEY` in Render; `FFMPEG_BIN` defaults to `ffmpeg` (Docker image has it).
- Runway API has no Kling — routing is `gen4_turbo`/`veo3.1_fast`; revisit if Runway adds it.
- Frontend lint: `no-explicit-any`, `no-img-element`, `set-state-in-effect` downgraded to warnings — 79 warnings to burn down.
- Frontend: debounce `fetchData` on SSE bursts; hook reconnect has no backoff.
- SSE cursor bug (pre-existing, not Phase 7): `api/sse.py`'s `event_stream` tracks `last_seen_id` and filters `Event.id > last_seen_id`, but `Event.id` is a random UUID (`models/event.py`), not time-ordered — events created after the cursor advances can sort lexicographically "below" it and be silently dropped (or duplicated) for the life of one connection. Verified live: a long-lived curl session missed `content_social.completed`/`mls_export.completed`/`pipeline.completed` entirely; a fresh connection saw the full history. Fix: order/filter by `created_at` (with `id` as a tiebreaker), not by `id` alone.
- CORS bug (pre-existing, not Phase 7, introduced in `ceb2c09`): `frontend/src/lib/api-client.ts`'s `fetchClient` auth middleware (`setToken`) attaches a stray `ngrok-skip-browser-warning` header to every authenticated request, which is not in the backend's CORS `allow_headers` list — any cross-origin authenticated call (e.g. `/auth/me` right after login) fails CORS preflight in a real browser. Reproduced locally with `NEXT_PUBLIC_API_URL` pointing at a different origin/port than the frontend; worth checking whether production's frontend/API are same-origin (proxied) or this is already live there too.
