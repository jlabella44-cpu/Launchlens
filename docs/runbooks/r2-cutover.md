# Cloudflare R2 Cutover Runbook

ListingJet's media storage is migrating from **AWS S3** to **Cloudflare R2** as part of [Phase 1 of the Render+Supabase migration](../../.. /.claude/plans/breezy-foraging-karp.md). Code is already cutover-ready (PR #285): `StorageService` uses any S3-compatible endpoint when `S3_ENDPOINT_URL` is set. This runbook is the operational side — provisioning R2, syncing data, flipping env vars, smoke testing, rollback.

**Estimated downtime**: 0. The cutover is read-flip-then-rewrite — old S3 reads stay live until the env var changes, R2 starts serving the moment env var is set on the next deploy.

**Estimated effort**: ~30–45 minutes once you have a Cloudflare account.

---

## Prerequisites

- Cloudflare account (free tier is fine — R2 has 10 GB free + $0 egress)
- Local AWS CLI logged in to the ListingJet account
- `rclone` installed (`brew install rclone` / `choco install rclone`) OR willingness to use `aws s3 sync` to a temp local dir + upload script
- PR #285 merged and deployed (so the code can read `S3_ENDPOINT_URL`)

---

## Steps

### 1. Provision R2 in Cloudflare

In the Cloudflare dashboard:

1. **R2 → Create bucket** — name: `listingjet-media`. Location hint: leave default (auto). Click Create.
2. **R2 → Manage R2 API Tokens → Create API token**:
   - Name: `listingjet-prod`
   - Permissions: **Object Read & Write**
   - Bucket: `listingjet-media` (scope it down)
   - TTL: forever (or set a rotation reminder)
   - Click Create. **Copy the Access Key ID, Secret Access Key, and the S3 endpoint URL.** They're shown once.

The endpoint URL looks like `https://<32-char-hex-account-id>.r2.cloudflarestorage.com`.

### 2. Sync existing S3 contents to R2

Source bucket: `listingjet-media-265911026550-us-east-1` (per `infra/stacks/services.py`). Confirm the exact name:

```bash
aws s3api list-buckets --query "Buckets[?starts_with(Name, 'listingjet-media')].Name" --output text
```

Configure rclone with both remotes (one-time):

```bash
rclone config create aws-s3 s3 provider AWS region us-east-1 access_key_id <AWS_KEY> secret_access_key <AWS_SECRET>
rclone config create r2 s3 provider Cloudflare region auto endpoint <R2_ENDPOINT_URL> access_key_id <R2_KEY> secret_access_key <R2_SECRET>
```

Dry-run the sync first to see what'll move and how big it is:

```bash
rclone sync aws-s3:listingjet-media-265911026550-us-east-1 r2:listingjet-media --dry-run --progress
```

If the size and file count look right, do it for real:

```bash
rclone sync aws-s3:listingjet-media-265911026550-us-east-1 r2:listingjet-media --progress
```

For larger payloads, add `--transfers 16 --checkers 32` to parallelize. R2 has $0 ingress, so no cost worry.

Verify counts match:

```bash
aws s3 ls s3://listingjet-media-265911026550-us-east-1 --recursive --summarize | tail -3
rclone size r2:listingjet-media
```

Total size and object count should be identical (or off by a few from in-flight uploads).

### 3. Flip env vars on the running deploy

Today the app runs on AWS ECS with secrets in Secrets Manager. Add three new keys to the `listingjet/app` secret:

```bash
aws secretsmanager get-secret-value --secret-id listingjet/app --query SecretString --output text > /tmp/app.json
# edit /tmp/app.json — add:
#   "S3_ENDPOINT_URL": "https://<account>.r2.cloudflarestorage.com",
#   "S3_ACCESS_KEY_ID": "<R2_KEY>",
#   "S3_SECRET_ACCESS_KEY": "<R2_SECRET>"
aws secretsmanager put-secret-value --secret-id listingjet/app --secret-string "$(cat /tmp/app.json)"
rm /tmp/app.json
```

Force ECS to pick up the new values (running tasks keep the old env until restart):

```bash
aws ecs update-service --cluster listingjet --service listingjet-api --force-new-deployment
aws ecs update-service --cluster listingjet --service listingjet-worker --force-new-deployment
```

Wait for both to roll:

```bash
aws ecs describe-services --cluster listingjet --services listingjet-api listingjet-worker \
  --query "services[*].[serviceName,deployments[0].rolloutState]" --output text
```

Both should report `COMPLETED` (typically 2–3 minutes).

### 4. Smoke test

Through the running app, exercise each of the four `StorageService` operations:

| Operation | How to trigger |
|---|---|
| **upload** | Upload a photo via the listing creation wizard (frontend) — completes if the worker can write to R2 |
| **presigned_url** | Open a listing detail page that displays photos — the gallery loads from presigned R2 URLs |
| **download** | Trigger any pipeline activity that downloads originals (e.g. retry a workflow) |
| **delete** | Delete an asset from a listing |

Backend check — tail worker logs for any `StorageError`:

```bash
MSYS_NO_PATHCONV=1 aws logs filter-log-events --log-group-name '/listingjet/worker' \
  --start-time $(($(date +%s%3N) - 600000)) --filter-pattern "StorageError" --max-items 10
```

If empty for 10 minutes after a real listing flow, cutover is healthy.

### 5. Decommission AWS S3 (optional, do later)

**Don't rush this.** Keep the AWS bucket for a week or two as a rollback safety net. Once you're confident R2 is healthy:

```bash
aws s3 rb s3://listingjet-media-265911026550-us-east-1 --force
```

When the CDK stack is torn down in Phase 3, the bucket goes with it.

---

## Rollback

The whole cutover is a 3-env-var flip. To revert:

1. Edit `listingjet/app` secret — remove `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` (or set them empty).
2. `aws ecs update-service ... --force-new-deployment` for both api and worker.
3. App falls back to default boto3 credential chain → AWS S3 with IAM role.

R2 keeps the data; nothing is destroyed by the rollback. New writes during the R2 window stay in R2 and are not present in S3 (this is a real, but small, consequence — usually <1 hour of writes if rolling back fast).

---

## Common gotchas

- **`region: auto` vs `region: us-east-1`** — R2 wants `auto`. The app reads `aws_region` from `AWS_REGION`. Either set `AWS_REGION=auto` for the R2-using services, OR leave it as `us-east-1` (boto3 sigv4 still works because the signature is computed against the endpoint URL, not the region — but `auto` is the supported config).
- **Presigned PUT URLs** — used by the photo upload wizard via `generate_presigned_post`. R2 supports this since it's standard S3 sigv4. Test specifically by uploading a photo through the wizard — that's the only call site that uses POST presigning.
- **CORS on R2 bucket** — if the frontend uploads directly to R2 via presigned URLs (it does), the R2 bucket needs a CORS policy allowing the Vercel origin. In the Cloudflare dashboard: R2 → bucket → Settings → CORS Policy → add an entry allowing `https://listingjet.ai` and the Vercel preview URL pattern with `PUT`, `POST`, `GET` methods.
- **Public asset URLs** — if any code constructs raw S3 URLs (`https://bucket.s3.region.amazonaws.com/key`), they won't work on R2. Audit before flipping. As of PR #285 all asset URLs go through `presigned_url`, which uses the configured client — safe.
