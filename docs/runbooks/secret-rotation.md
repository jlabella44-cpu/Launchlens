# Secret Rotation Runbook

All application secrets for ListingJet live in **AWS Secrets Manager** under the secret id `listingjet/app` (region `us-east-1`). ECS task definitions read from this secret via the CDK `services.py` stack. Local development uses `.env`.

This runbook covers every key in `listingjet/app`: when to rotate, how to rotate, downtime risk, and the exact cutover procedure.

---

## Rotation cadence at a glance

| Key | Cadence | Downtime risk | Notes |
|---|---|---|---|
| `RESEND_API_KEY` | 90 days or on compromise | None | Regenerate + paste |
| `OPENAI_API_KEY` | 90 days | None | Regenerate + paste |
| `ANTHROPIC_API_KEY` | 90 days | None | Regenerate + paste |
| `GOOGLE_VISION_API_KEY` | 180 days | None | Regenerate + paste |
| `KLING_ACCESS_KEY` / `KLING_SECRET_KEY` | 180 days | None | Rotate together |
| `SENTRY_DSN` | Never (unless compromised) | None | DSNs are not sensitive auth tokens |
| `STRIPE_SECRET_KEY` | Only on compromise | **Medium** — requires coordinated cutover | |
| `STRIPE_WEBHOOK_SECRET` | Only on compromise or endpoint change | **Medium** — webhooks fail during swap | |
| `JWT_SECRET` | Only on compromise | **High** — logs out all users | |
| `DATABASE_URL` (password) | Yearly or on compromise | **High** — coordinated RDS + secret + task redeploy | |
| `FIELD_ENCRYPTION_KEY` (Fernet, for IDX) | Never rotate without migration | **Critical** — breaks IDX feeds | Requires re-encrypting all rows |

Golden rule: **don't rotate for the sake of rotating.** Every rotation is a cutover. Only do it on schedule or on known compromise.

---

## Universal cutover procedure

Most rotations follow this pattern. Steps vary only in how you generate the new key (step 1).

**Preflight**
```powershell
aws secretsmanager get-secret-value --secret-id listingjet/app --query SecretString --output text > $env:TEMP\app.json
notepad $env:TEMP\app.json
```
Add or replace the key/value pair. Save, close.

**Push**
```powershell
aws secretsmanager put-secret-value --secret-id listingjet/app --secret-string (Get-Content $env:TEMP\app.json -Raw)
Remove-Item $env:TEMP\app.json
```

**Force ECS to pick up the new value** — ECS only re-reads secrets on task start, so running tasks still hold the old key until they're replaced:
```powershell
aws ecs update-service --cluster listingjet --service listingjet-api --force-new-deployment
aws ecs update-service --cluster listingjet --service listingjet-worker --force-new-deployment
```

**Verify**
```powershell
aws ecs describe-services --cluster listingjet --services listingjet-api listingjet-worker --query "services[*].[serviceName,runningCount,desiredCount,deployments[0].rolloutState]"
```
Wait until `rolloutState` is `COMPLETED` on both.

Then smoke test whatever the key authenticates against (send an email, hit a Stripe test endpoint, run a vision call).

**Revoke the old key** at the provider dashboard **only after** verification. If you revoke first and the deploy fails, you have downtime.

---

## Per-key rotation notes

### RESEND_API_KEY

**Generate:** https://resend.com/api-keys → Create API key → scope: "Sending access" only → copy.
**Verify after deploy:** Trigger a pipeline complete email on a test listing, or run the smoke test script at `scripts/smoke_resend.py` (if present).
**Downtime risk:** None. Old key still works until revoked.

### OPENAI_API_KEY / ANTHROPIC_API_KEY / GOOGLE_VISION_API_KEY

**Generate:**
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/settings/keys
- Google Vision: https://console.cloud.google.com/apis/credentials (restrict to Vision API)

**Verify:** Retry a listing through the pipeline — it will hit T1 (vision) and description generation (LLM) on restart.
**Downtime risk:** None. Old key works until revoked.
**Cost note:** Rotation has no billing impact; usage stays under the same org/project.

### KLING_ACCESS_KEY / KLING_SECRET_KEY

**Generate:** https://klingai.com dashboard → API → regenerate access + secret pair.
**Must rotate as a pair.** Kling signs requests with both; partial rotation fails.
**Verify:** Submit a test video clip via the smoke script or retry a listing that needs video.
**Downtime risk:** None if done together.

### SENTRY_DSN

A Sentry DSN is technically a project identifier, not an auth secret. It authorizes event submission only, not read access. **Do not rotate casually.** Rotate only if you're moving projects or have confirmed abuse (spam events on your project quota).

### STRIPE_SECRET_KEY

**Medium risk — read the whole section before starting.**

**Generate:** https://dashboard.stripe.com/apikeys → "Create restricted key" (never use an unrestricted live key in prod).
**Required scopes for ListingJet:**
- Customers: read/write
- Subscriptions: read/write
- Checkout Sessions: read/write
- Payment Intents: read
- Prices: read
- Products: read
- Webhooks: read
- Invoices: read

**Cutover:**
1. Create the new restricted key (do not revoke the old one yet)
2. Paste into Secrets Manager
3. Force-deploy ECS (procedure above)
4. In a separate terminal, watch logs: `aws logs tail /listingjet/api --follow --filter-pattern stripe`
5. Once you see successful Stripe calls with the new key (any checkout, plan fetch, or webhook), revoke the old key in Stripe dashboard

**If anything fails mid-cutover:** do **not** revoke the old key. Roll back the secret value to the old key, force-deploy again, triage.

**In-flight risk:** Customers mid-checkout during the swap may see one failed payment. Stripe retries. Schedule during low traffic (Tuesday 2-4am CT is typical).

### STRIPE_WEBHOOK_SECRET

Rotate **only** when you rotate the webhook endpoint itself in the Stripe dashboard. The secret is tied 1:1 to a specific webhook URL in Stripe.

**Cutover — this is a choreographed swap:**
1. In Stripe dashboard, go to Developers → Webhooks → your endpoint → "Roll secret"
2. Stripe gives you an expiration window (default 24h) where **both old and new secrets validate signatures**
3. During that window: paste new secret into Secrets Manager + force-deploy ECS
4. Verify webhooks are processing: check `/admin` audit log for recent `stripe.*` events
5. After verification, before the expiration window closes, confirm in Stripe that the old secret is invalidated

**If you miss the window:** Stripe webhooks will start returning 400 at your endpoint and Stripe will retry with exponential backoff, then give up. Customers will see delayed subscription state. You have ~24h of grace, don't waste it.

### JWT_SECRET

**High risk — only rotate on compromise.**

Rotating this invalidates:
- All existing JWT access tokens (users get 401 on next request)
- All existing refresh tokens (users get logged out, must re-authenticate)
- Any pending password reset / email verification tokens signed with the old secret

**Cutover:**
1. Announce planned downtime to users (even 60s of "please log in again" is user-visible)
2. Generate a new strong secret:
   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(64))"
   ```
3. Push to Secrets Manager + force-deploy
4. Every active user is logged out at next request
5. Clear the Redis JWT blocklist (old blocklist entries are for tokens signed with the old secret and are harmless but wasteful):
   ```
   redis-cli --scan --pattern "jwt:blocked:*" | xargs redis-cli del
   ```

**Never rotate as a "quarterly hygiene" task.** Only on confirmed leak.

### DATABASE_URL

**High risk — coordinated multi-system cutover.**

The DATABASE_URL in `listingjet/app` is a legacy override. The primary path is `db_secret = db_instance.secret` in the CDK, which points at the RDS-managed master secret (`ListingJetDatabase/Secret/...`).

**If rotating the RDS master password:**
1. Use AWS Secrets Manager rotation (automatic) — go to Secrets Manager → RDS secret → "Rotate" → "Immediately"
2. AWS Secrets Manager rotation lambda handles a dual-password window where both old and new are valid
3. Force-deploy ECS after the rotation completes
4. Verify connectivity: `curl https://api.listingjet.ai/health`

**If rotating a legacy DATABASE_URL override:**
1. The secret should probably be deleted entirely — prefer the RDS-managed path
2. File a ticket to remove the override; don't maintain a legacy rotation procedure

**Do not** manually `ALTER USER ... WITH PASSWORD` on RDS without using the rotation lambda — the window between DB password change and secret update is instant downtime.

### FIELD_ENCRYPTION_KEY (Fernet)

**Do not rotate without a migration script.**

This Fernet key encrypts `idx_feed_config.api_key_encrypted` at rest. Rotating without re-encrypting existing rows means every IDX feed breaks instantly — the old ciphertext can't be decrypted with the new key.

**Correct rotation procedure (if ever needed):**
1. Add `FIELD_ENCRYPTION_KEY_OLD` as a second secret
2. Deploy code that supports *read from either key, write with new key*
3. Write a migration: decrypt every row with old key, re-encrypt with new key
4. Run migration in production
5. Deploy code that removes the old-key read path
6. Delete `FIELD_ENCRYPTION_KEY_OLD` from Secrets Manager

This is a full code-change cycle, not a secret swap. Plan at least a week.

---

## Emergency rotation (known compromise)

If a key is *actively* compromised (appeared in a public repo, screenshot, Slack channel, etc.):

1. **Revoke first, ask questions later** — for zero-downtime keys (Resend, OpenAI, Anthropic, Vision, Kling, Sentry): revoke immediately at the provider, then rotate. A brief error spike is better than ongoing abuse.
2. **For high-risk keys** (Stripe, JWT, DB): open an incident channel before touching anything. The rotation is worse than the compromise unless you're certain active abuse is happening.
3. After rotation, audit usage logs on the provider side for abuse fingerprints (unexpected regions, unexpected models, spending anomalies).

---

## Automating: future work

- [ ] Enable AWS Secrets Manager automatic rotation for the RDS master secret (built-in lambda)
- [ ] Add a CloudWatch alarm on `listingjet/app` secret age — warn at 90 days per key
- [ ] Add a pre-deploy smoke test script per provider under `scripts/smoke_<provider>.py` that validates each rotated key end-to-end before `force-new-deployment`

---

**Last reviewed:** 2026-04-10
**Owner:** Jeff
