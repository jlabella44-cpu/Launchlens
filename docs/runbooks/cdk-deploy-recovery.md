# CDK Deploy Recovery Runbook

The ListingJet CDK has accumulated drift from manual console edits and has a pre-existing cross-stack dependency cycle that prevents `cdk deploy`. This runbook captures the state as of 2026-04-10 and the steps needed to restore CDK as the source of truth.

---

## Current state (2026-04-10)

### What CDK thinks is true
- `infra/stacks/services.py` — defines ECS cluster, task defs, ALB, ECR repos, S3 media bucket
- `infra/stacks/cdn.py` — defines CloudFront distribution with OAI access to the media bucket
- `infra/app.py` — instantiates all stacks with `cdn.add_dependency(services)`

### What's actually running in AWS
- **ECS task defs are ahead of CDK** — manual revisions 9 exist for both API and worker that add SMTP + RESEND env vars and `SMTP_PASSWORD` secret. CDK's code would regenerate these and lose the SMTP additions.
- **Log groups are `/launchlens/*`** — predates the rebrand. CDK code now says `/listingjet/*` on `infra/cdk-cleanup` branch but can't deploy.
- **IAM policies** — "currently inline policies" per the MASTER_TODO. Someone patched roles in the console. Current state is unknown; `cdk diff` would show.
- **S3 bucket `listingjet-dev`** — the app's actual data bucket. CDK creates an unused `listingjet-media-<account>-<region>` bucket alongside it.
- **Secret `listingjet/app`** — has `RESEND_API_KEY`, `EMAIL_ENABLED`, `QWEN_API_KEY`, `VISION_PROVIDER_TIER2` that aren't in CDK's secrets block.

---

## The blocker: cross-stack cycle

```
ListingJetCDN → ListingJetServices   (explicit via cdn.add_dependency(services))
ListingJetServices → ListingJetCDN   (implicit via media_bucket.grant_read(cdn.oai))
```

The grant in `cdn.py:34` mutates the Services stack's bucket policy to reference the CDN stack's OAI. That creates a bidirectional dependency.

**cdk synth** reports:
```
DependencyCycle: 'ListingJetCDN' depends on 'ListingJetServices'.
Adding this dependency (ListingJetServices -> ListingJetCDN/MediaOAI/Resource.S3CanonicalUserId)
would create a cyclic reference.
```

### Fix options for the cycle

**Option A — Move the OAI to the Services stack (simplest, breaks existing deployed CloudFront)**
1. In `services.py`, create the OAI alongside the media bucket
2. Call `media_bucket.grant_read(self.oai)` in the Services stack
3. In `cdn.py`, receive the OAI as a constructor param (like media_bucket is today)
4. Remove the grant from CDN
5. `cdn.add_dependency(services)` still works
6. Deploy

Risk: CloudFormation will see the OAI moving stacks and replace it. CloudFront distribution will be updated to use the new OAI. Brief period where old/new OAIs both exist. Possible 1-2 min CDN cache churn.

**Option B — Migrate to Origin Access Control (OAC) [modern, cleaner]**
OAC is the AWS-recommended replacement for OAI. It uses the bucket policy instead of CanonicalUser grants, and CDK supports it via `cloudfront_origins.S3BucketOrigin.withOriginAccessControl(bucket)`.

1. In Services stack: create the media bucket with block-all public access (already does)
2. In CDN stack: use `cloudfront_origins.S3BucketOrigin.withOriginAccessControl(media_bucket)` instead of `S3Origin(media_bucket, origin_access_identity=oai)`
3. Delete the `media_bucket.grant_read(oai)` call — OAC handles the bucket policy automatically
4. Deploy

Risk: CloudFront will be updated to use OAC. Briefly, the distribution may reject requests that hit the OAI before the OAC takes over. Recommend running in a maintenance window.

**Recommended: Option B.** OAI is legacy, OAC is the future, and it eliminates the cycle without adding new constructor wiring.

---

## Deploy readiness checklist

Before running `cdk deploy`, verify each:

- [ ] **Cycle fixed** — `cdk synth ListingJetServices` succeeds without DependencyCycle error
- [ ] **Node version compatible** — use Node 22 LTS or earlier (Node 25 breaks jsii; install via `nvm install 22.22.2 64` with nvm-windows)
- [ ] **TMPDIR is not inside context-mode sandbox** — run from real PowerShell or set `TMP`/`TEMP` to `C:\Users\Jeff\AppData\Local\Temp`
- [ ] **CDK changes merged to `infra/cdk-cleanup` branch** — currently has log group rename + `RESEND_API_KEY` secret wiring
- [ ] **`cdk diff` reviewed** against live stacks — especially look for surprises in:
  - ECS task def changes (may try to remove the manual SMTP env vars we added in revision 9)
  - IAM policy changes (may try to remove inline policies that were added in console)
  - S3 bucket cleanup (`listingjet-media-*` removal)
- [ ] **Backfill manual drift into CDK** — add any inline IAM policies and SMTP env vars into `services.py` so `cdk deploy` doesn't remove them
- [ ] **Maintenance window scheduled** — log group rename will briefly interrupt log streaming; CDN OAC migration has CDN-cache impact

---

## Pre-deploy backfill — what CDK needs to know

Before the next `cdk deploy` attempt, update `services.py` to match what's in production:

### 1. Add SMTP env vars + secret to both API and worker

```python
# In base_env (or separate env block)
"SMTP_HOST": "smtp.resend.com",
"SMTP_PORT": "587",
"SMTP_USER": "resend",
"EMAIL_ENABLED": "true",
"EMAIL_FROM": "noreply@listingjet.ai",
```

```python
# In the secrets block of BOTH api_container and worker_container
"SMTP_PASSWORD": ecs.Secret.from_secrets_manager(app_secrets, "RESEND_API_KEY"),
```

Both API and worker task defs have these manually applied in revision 9 already.

### 2. Add the missing secret references CDK doesn't know about

Current `listingjet/app` has these that CDK doesn't reference:
- `RESEND_API_KEY` (aliased to `SMTP_PASSWORD` as above — or add it directly if moving to code-level Resend later)
- `EMAIL_ENABLED` (could be plain env var instead)
- `QWEN_API_KEY`
- `VISION_PROVIDER_TIER2`

### 3. Log group rename

Change `/launchlens/api`, `/launchlens/worker`, `/launchlens/temporal` → `/listingjet/*` in `services.py`. This is already done on `infra/cdk-cleanup`. **Note:** CDK will delete the old log groups on deploy. Old logs go with them unless exported first.

### 4. S3 bucket cleanup (separate effort)

The `s3.Bucket(...)` block at line ~198 creates `listingjet-media-<account>-<region>` which is unused. App writes to `listingjet-dev` (created outside CDK). Options:

**Option 1 — Adopt `listingjet-dev`:** Use `s3.Bucket.from_bucket_name(self, "MediaBucket", "listingjet-dev")` to reference it without CDK managing it. Remove the dead `s3.Bucket(...)` call. On deploy, CDK will try to delete `listingjet-media-*` — fine if empty.

**Option 2 — Migrate to new bucket:** Keep the CDK-created bucket, do `aws s3 sync s3://listingjet-dev s3://listingjet-media-<account>-us-east-1`, switch the app's `S3_BUCKET_NAME` env var. Requires data migration downtime and cutover coordination.

Recommended: Option 1 for lowest risk.

---

## The actual deploy sequence (when ready)

```powershell
# 1. Switch to Node 22
nvm use 22.22.2

# 2. Navigate to infra dir
cd C:\Users\Jeff\launchlens\infra

# 3. Bootstrap if first-time (skip if already bootstrapped)
cdk bootstrap

# 4. Review the diff — READ EVERY LINE
cdk diff ListingJetServices
cdk diff ListingJetCDN

# 5. If diff looks safe, deploy Services first (CDN depends on it)
cdk deploy ListingJetServices

# 6. Verify ECS is healthy after Services deploy
aws ecs describe-services --cluster listingjet --services listingjet-api listingjet-worker --query "services[*].{name:serviceName,state:deployments[0].rolloutState}" --output table

# 7. Deploy CDN
cdk deploy ListingJetCDN

# 8. Verify CloudFront distribution is still serving
curl -I https://<cloudfront-domain>
```

---

## Rollback plan

If `cdk deploy` breaks something:

1. **ECS services**: force previous task def revision
   ```powershell
   aws ecs update-service --cluster listingjet --service listingjet-api --task-definition ListingJetServicesApiTaskCC6F2D94:8
   aws ecs update-service --cluster listingjet --service listingjet-worker --task-definition ListingJetServicesWorkerTask8FB3F42B:8
   ```

2. **CloudFormation stack**: use the CloudFormation console to "Continue rollback" if the stack enters `UPDATE_ROLLBACK_FAILED`

3. **If all else fails**: comment out the breaking change in `services.py`, run `cdk deploy` again to restore working state

---

## Open items

- [ ] Fix cross-stack cycle (Option B: migrate to OAC)
- [ ] Backfill SMTP/email config into CDK
- [ ] Backfill Qwen/VisionProviderTier2 secret references into CDK
- [ ] Log group rename (code ready on `infra/cdk-cleanup`)
- [ ] Reconcile inline IAM policies (requires `cdk diff` inspection first)
- [ ] S3 bucket adoption (`listingjet-dev` → CDK-managed via `from_bucket_name`)
- [ ] Delete debug artifact `scripts/fix_secret.ps1`
- [ ] Add real `SENTRY_DSN` back (currently empty string to skip init)
- [ ] Update `MASTER_TODO.md` to mark migration items as done

---

**Last updated:** 2026-04-10
**Owner:** Jeff
**Estimated effort for full CDK reconciliation:** 4-6 hours of focused work
