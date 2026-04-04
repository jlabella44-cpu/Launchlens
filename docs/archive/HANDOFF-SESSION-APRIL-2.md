# Session Handoff — April 1-2, 2026

## What Was Accomplished

### Frontend Assets (Merged)
- Pulled 9 images from Stitch project, replaced all gradient placeholders
- Homepage hero, register bg, login villa, feature sections, listing property photos
- PRs #94, #99 merged

### Brand Kit Expansion (Merged — PR #95)
- Phase 1: Headshot upload, dual logos (brokerage + team), 5 sub-components, polished UI
- Phase 2: Accent/background colors, brand voice/tone, secondary font with preview
- Phase 3: Team API (5 endpoints), settings tabs, team management page
- All new fields in `raw_config` JSONB — zero DB migrations for brand kit

### Listing Permissions (Merged — PR #95)
- Phase A: `listing_permissions` + `listing_audit_log` tables (migration 025)
- Permission levels: read/write/publish/billing
- Share panel drawer on listing detail page
- Phase B: Blanket grants, shared-with-me dashboard tab
- Phase D: Audit log viewer (activity timeline)
- Phase F: Plan gating (pro same-tenant, enterprise cross-tenant)

### AWS SES Email (Merged — PR #95)
- SES backend alongside existing SMTP
- 4 email templates: listing_shared, listing_unshared, permission_expiring, edit_digest
- Domain `listingjet.ai` verified in SES (DKIM SUCCESS)

### Domain Setup
- `listingjet.ai` + `www.listingjet.ai` connected to Vercel
- DNS records in Cloudflare (A + CNAME for Vercel, 3 DKIM CNAMEs for SES)
- CORS updated for new domain
- SES still in sandbox mode — need to request production access

### Bug Fixes (Merged)
- PR #99: Removed unused R3F imports causing THREE namespace errors
- PR #100: Drag-drop zone extended over previews + audit-log 404 silenced
- PR #101: Asset grid thumbnails now use actual presigned S3 URLs
- PR #103: Backend allows retry for stuck uploading/analyzing listings
- PR #104: Frontend shows "Processing Stalled" retry button for stuck listings

### Infrastructure Fixes
- Worker `TEMPORAL_HOST` fixed: `temporal:7233` → `temporal.listingjet.local:7233` (task def rev 4)
- API `TEMPORAL_HOST` also fixed (task def rev 4)
- Security group rules added: worker SG → Temporal:7233, API SG → Temporal:7233
- Entrypoint.sh: Alembic stamp-before-migrate to handle DB-ahead-of-tracking issue

---

## Open PR
- **PR #106** — `chore/session-cleanup`: Entrypoint migration fix + proxy pipeline plan doc. Waiting for CI.

---

## Current State of Pipeline

### What Works
- Worker connects to Temporal ✅
- API can trigger pipeline via Temporal ✅
- Retry from stuck states works (backend + frontend) ✅
- Ingestion agent runs ✅
- Photos are in S3 (`listingjet-dev` bucket, 18 photos) ✅

### What's Stuck
- **Vision T1 is hanging** on listing `19724c40-28d0-46fb-b11b-97f5f9b6fb5e`
- Worker produces NO logs at all during Vision T1 (completely silent, multiple retries)
- Confirmed: worker connects to Temporal, picks up workflow, starts Vision T1, then goes silent
- Confirmed: 18 photos in S3, all API keys set, S3 bucket correct, NAT gateway exists
- The property_data table doesn't exist in prod (property verification agent fails, but non-blocking)
- **Root cause: Almost certainly the vision agent downloading full-res photos without any timeout/logging. 18 × 3-8MB = ~90MB download + Google Vision API calls with no per-image logging.**

### FIRST THING TOMORROW — Fix Vision T1
1. **Add per-image logging** to vision agent: log before/after each S3 download and each Google Vision API call
2. **Add timeouts**: per-image download timeout (30s) and per-API-call timeout (30s)  
3. **Build proxy image pipeline** — plan is at `docs/PROXY-IMAGE-PIPELINE.md` (4x speedup, 90MB → 3MB)
4. Deploy updated vision agent, retry the listing
5. **Run missing migrations** on prod DB — `property_data` table needs to be created
6. **Request SES production access** in AWS Console for unrestricted email sending

---

## Production Environment Reference

| Service | Task Definition | Key Config |
|---------|----------------|------------|
| API | `ListingJetServicesApiTaskCC6F2D94:4` | `TEMPORAL_HOST=temporal.listingjet.local:7233` |
| Worker | `ListingJetServicesWorkerTask8FB3F42B:4` | `TEMPORAL_HOST=temporal.listingjet.local:7233` |
| Temporal | `ListingJetServicesTemporalTaskE084D0B5:4` | Service discovery: `temporal.listingjet.local` |

| Resource | Value |
|----------|-------|
| ECS Cluster | `listingjet` |
| S3 Bucket | `listingjet-dev` (both dev and prod use this currently) |
| RDS | `listingjetdatabase-postgres9dc8bb04-kjyxgeldpfef.c8xiacyu8dyh.us-east-1.rds.amazonaws.com` |
| Redis | `lis-re-10delv4c2sqbw.fjbwkc.0001.use1.cache.amazonaws.com:6379` |
| Domain | `listingjet.ai` (Cloudflare DNS → Vercel) |
| SES | `listingjet.ai` verified, sandbox mode |
| Cloud Map | `listingjet.local` (private DNS namespace) |

| Log Group | Service |
|-----------|---------|
| `/launchlens/api` | API container |
| `/launchlens/worker` | Worker container |
| `/launchlens/temporal` | Temporal server |

| Security Group | Service | Ingress |
|---------------|---------|---------|
| `sg-078a532f32b045d2f` | API | ALB traffic |
| `sg-02fc8c8c34238e447` | Worker | None (outbound only) |
| `sg-02e94c6dfdf76e1c5` | Temporal | Worker:7233, API:7233 |

---

## Planned Feature Work

### Proxy Image Pipeline (Ready to Build)
- Plan: `docs/PROXY-IMAGE-PIPELINE.md`
- Generate 1024px proxies during ingestion
- Vision T1/T2/Floorplan use proxies, everything else uses full-res
- Estimated 4x speedup on Vision T1

### Listing Permissions — Remaining Phases
- Plan: `docs/LISTING-PERMISSIONS-PLAN.md`
- Phase C: Cross-tenant email invitations (needs SES production access)
- Phase E: Email notifications (share/revoke/edit digest — templates built, just needs SES)

### Pipeline Testing
- Workflow orchestration tests (critical gap — zero tests for Temporal workflows)
- Expand chaos tests from 3 to 20 agents
- End-to-end integration test
