# Session Handoff — April 2, 2026 (Afternoon)

## PRs Merged
- **#106** — Lint fix (unused CreditAccount import)
- **#107** — Proxy image pipeline (90MB → 3MB vision processing)
- **#110** — Removed React Three Fiber, replaced with CSS pipeline indicators
- **#111** — Infrastructure hardening (IAM, Temporal, CORS, SES)
- **#113** — Stable `api.listingjet.ai` for Vercel API rewrites

## Pipeline Fix — Complete
- **Root cause**: Vision T1 was passing raw S3 keys to Google Vision API (not presigned URLs)
- **Fix**: `_resolve_image_url()` generates presigned URLs from proxy or full-res S3 keys
- **Proxy pipeline**: Ingestion now generates 1024px JPEG proxies (~150KB vs 3-8MB)
- **Listing `19724c40...`**: Successfully processed to `awaiting_review` with 16/18 proxies

## Production Changes Applied
| Change | Method |
|--------|--------|
| Worker IAM: S3 read/write/delete on `listingjet-dev` | Inline policy |
| Worker IAM: CloudWatch PutMetricData | Inline policy |
| `property_data` table created | One-off ECS task |
| Alembic stamped to 026 | Entrypoint auto-stamp |
| SES suppression list (bounce + complaint) | CLI |
| SES config set `listingjet-default` | CLI |
| SES production access requested | CLI (pending ~24hrs) |

## Cloudflare Configuration
- SSL/TLS: **Full** (not Strict)
- HSTS: Enabled (max-age 63072000, include subdomains, no-sniff)
- Cache bypass rule: `*listingjet.ai/api/*` → Bypass
- DNS: `api.listingjet.ai` CNAME → ALB (DNS only)
- DNS: `listingjet.ai` A record → `216.198.79.1` (proxied)
- DNS: `www` CNAME → Vercel (proxied)

## 4 Unpushed Commits on Local Master
These are from a previous session and were never PR'd:
```
e01bd59 fix: add voiceover_enabled to BrandKitFormState interface
729e9ea feat: voiceover toggle — tenant default + per-listing override
816d65b feat: auto-process user-uploaded videos with endcard + social cuts
0c0e698 feat: add MockKlingProvider for testing video pipeline
```
Decision needed: PR these or reset local master to origin.

## Remaining Work
- [ ] SES production access — wait for AWS approval (~24hrs)
- [ ] Run `cdk deploy` to apply IAM changes permanently (currently inline policies)
- [ ] Install SSM Session Manager plugin locally for ECS exec debugging
- [ ] Separate dev/prod S3 buckets (both use `listingjet-dev` currently)
- [ ] Rename CloudWatch log groups from `/launchlens/*` to `/listingjet/*`
