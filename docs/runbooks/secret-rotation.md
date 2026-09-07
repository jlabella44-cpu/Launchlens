# Secret Rotation Runbook

All production secrets for ListingJet live in the Render environment group **`listingjet-shared`** (Render dashboard, Environment Groups). The `listingjet-api` service pulls the group in via `fromGroup` in [`render.yaml`](../../render.yaml); the pipeline worker runs inside that same service, so there is exactly one process to restart. Local development uses `.env`. Provisioning each of these from scratch is covered in [`free-tier-setup.md`](free-tier-setup.md).

This runbook covers every secret in the group: when to rotate, how to rotate, downtime risk, and the exact cutover procedure.

---

## Rotation cadence at a glance

| Key | Cadence | Downtime risk | Notes |
|---|---|---|---|
| `RESEND_API_KEY` | 90 days or on compromise | None | Regenerate and paste |
| `OPENAI_API_KEY` | 90 days | None | Regenerate and paste |
| `ANTHROPIC_API_KEY` | 90 days | None | Regenerate and paste |
| `RUNWAY_API_KEY` | 180 days | None | Regenerate and paste |
| `GOOGLE_API_KEY` | 180 days | None | Drive listing import only |
| `CANVA_API_KEY` / `CANVA_CLIENT_SECRET` | 180 days | None | Only the `brand` step, which is optional |
| `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` | Yearly or on compromise | **Medium** — all media reads and writes | Rotate as a pair |
| `SENTRY_DSN` | Never unless compromised | None | A DSN is not an auth token |
| `STRIPE_SECRET_KEY` | Only on compromise | **Medium** — needs a coordinated cutover | |
| `STRIPE_WEBHOOK_SECRET` | Only on compromise or endpoint change | **Medium** — webhooks fail during the swap | |
| `JWT_SECRET` | Only on compromise | **High** — logs out every user | |
| `DATABASE_URL` / `DATABASE_URL_SYNC` (password) | Yearly or on compromise | **High** — coordinated Supabase and Render change | |
| `FIELD_ENCRYPTION_KEY` (Fernet) | Never rotate without a migration | **Critical** — breaks encrypted tenant secrets | Requires re-encrypting every row |

Golden rule: **do not rotate for the sake of rotating.** Every rotation is a cutover. Do it on schedule or on known compromise, not on a whim.

---

## Universal cutover procedure

Most rotations follow this pattern. Only step 1, generating the new key, varies.

1. Generate the new key at the provider. **Do not revoke the old one yet.**
2. Render dashboard, Environment Groups, `listingjet-shared`, edit the key, Save.
3. Saving an env group triggers a redeploy of every service linked to it. If it does not, or you want to force it: `listingjet-api`, Manual Deploy, "Deploy latest commit". Render reads environment variables at process start, so a running instance keeps the old value until it is replaced.
4. Wait for the deploy to reach **live**, then verify:
   ```bash
   curl -fsS https://<service>.onrender.com/health/deep
   ```
   `/health/deep` covers Postgres, Redis, and the worker tick. Then smoke test whatever the rotated key actually authenticates against: send an email, run a listing through the pipeline, hit a Stripe test endpoint.
5. **Revoke the old key** at the provider only after verification. Revoking first turns a failed deploy into an outage.

Note that the free Render plan sleeps an idle service. If the service is asleep, the first request after a rotation both wakes it and picks up the new value; give it about 30 seconds before deciding something is broken.

---

## Per-key rotation notes

### RESEND_API_KEY

**Generate:** https://resend.com/api-keys, Create API key, scope "Sending access" only.
**Verify:** trigger a pipeline-complete email on a test listing, or run `scripts/smoke_resend.py`.
**Downtime risk:** none. The old key works until revoked.

### OPENAI_API_KEY / ANTHROPIC_API_KEY

**Generate:**
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/settings/keys

**Verify:** run one listing through the pipeline. `photo_analysis` and `content_social` hit Anthropic; `virtual_staging`, `image_edit`, and `dollhouse_render` hit OpenAI images.
**Downtime risk:** none. The old key works until revoked.
**Cost note:** rotation has no billing impact; usage stays in the same org or project.

### RUNWAY_API_KEY

**Generate:** Runway developer portal, API keys, create a new key for the same organization so the prepaid credit balance carries over.
**Verify:** run a listing with the `ai_video_tour` add-on enabled and confirm `video_ai` completes. That step is optional, so a bad key shows up as a skipped video and a failed job row, not a failed listing — check `pipeline_jobs` rather than the listing state.
**Downtime risk:** none.
**Cost note:** generated clip URLs expire in 24 to 48 hours, but the agent downloads each clip immediately, so a rotation never invalidates already-delivered media.

### GOOGLE_API_KEY

Used only for the Google Drive listing-import path.

**Generate:** https://console.cloud.google.com/apis/credentials, restrict the key to the Drive API.
**Verify:** import a listing from a Drive folder link.
**Downtime risk:** none. Nothing in the pipeline depends on it.

### CANVA_API_KEY / CANVA_CLIENT_SECRET

`CANVA_API_KEY` is the platform key used for flyer rendering. `CANVA_CLIENT_SECRET` (with `CANVA_CLIENT_ID`) backs the per-tenant OAuth connection at `/auth/canva/callback`.

**Generate:** Canva developer portal, your integration, Keys.
**Rotating `CANVA_CLIENT_SECRET` invalidates existing tenant OAuth grants** — tenants have to reconnect Canva from Settings, Brand Kit. Announce it before rotating.
**Verify:** run a listing and confirm the `brand` step produces a flyer. `brand` is optional, so a broken key degrades to "no flyer" rather than a failed listing.
**Downtime risk:** none for `CANVA_API_KEY`; low but user-visible for `CANVA_CLIENT_SECRET`.

### S3_ACCESS_KEY_ID / S3_SECRET_ACCESS_KEY (Cloudflare R2)

**Medium risk — every upload, presigned URL, and download uses these.**

**Generate:** Cloudflare dashboard, R2, Manage R2 API Tokens, Create API token. Permissions "Object Read & Write", scoped to the `listingjet-media` bucket. Copy the Access Key ID and Secret; they are shown once. The endpoint URL does not change, so `S3_ENDPOINT_URL` stays as it is.
**Rotate as a pair.** Half a credential pair is a broken credential pair.
**Verify:** upload a photo through the creation wizard (presigned POST), open a listing gallery (presigned GET), and delete an asset. Tail the Render logs for `StorageError`.
**Downtime risk:** any in-flight presigned URL signed with the old key keeps working until it expires; new signing uses the new key immediately after the restart. Revoke the old token only after a clean upload and gallery load.

### SENTRY_DSN

A DSN is a project identifier that authorizes event submission, not read access. **Do not rotate casually.** Rotate only when moving projects or after confirmed abuse of your event quota.

### STRIPE_SECRET_KEY

**Medium risk — read the whole section before starting.**

**Generate:** https://dashboard.stripe.com/apikeys, "Create restricted key". Never put an unrestricted live key in production.
**Required scopes:** Customers read/write, Subscriptions read/write, Checkout Sessions read/write, Payment Intents read, Prices read, Products read, Webhooks read, Invoices read.

**Cutover:**
1. Create the new restricted key. Do not revoke the old one.
2. Paste it into `listingjet-shared` and let the redeploy run.
3. Watch the Render service logs for the first successful Stripe call: any checkout, plan fetch, or webhook.
4. Revoke the old key in the Stripe dashboard.

**If anything fails mid-cutover:** do not revoke the old key. Put the old value back, redeploy, and triage.
**In-flight risk:** a customer mid-checkout during the restart may see one failed payment. Stripe retries. Schedule for low traffic.

### STRIPE_WEBHOOK_SECRET

Rotate **only** when you rotate the webhook endpoint itself. The secret is tied one-to-one to a specific webhook URL in Stripe.

**Cutover — a choreographed swap:**
1. Stripe dashboard, Developers, Webhooks, your endpoint, "Roll secret".
2. Stripe gives you an expiration window (default 24 hours) during which **both** secrets validate signatures.
3. Inside that window, paste the new secret into `listingjet-shared` and let the redeploy run.
4. Verify webhooks are processing: check the `/admin` audit log for recent `stripe.*` events.
5. Before the window closes, confirm in Stripe that the old secret is invalidated.

**If you miss the window:** the endpoint starts returning 400, Stripe retries with backoff and then gives up, and subscription state goes stale. You have about 24 hours of grace, do not waste it.

### JWT_SECRET

**High risk — rotate only on compromise.**

Rotating invalidates every access token (401 on the next request), every refresh token (everyone is logged out), and any pending password-reset or email-verification token signed with the old secret.

**Cutover:**
1. Announce the interruption. Even 60 seconds of "please log in again" is user-visible.
2. Generate a new secret:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(64))"
   ```
3. Paste into `listingjet-shared`, let the redeploy run.
4. Every active user is logged out at their next request.
5. Clear the Redis revocation entries. They refer to tokens signed with the old secret and are now dead weight:
   ```bash
   redis-cli --tls -u "$REDIS_URL" --scan --pattern "jwt:blocked:*" | xargs redis-cli --tls -u "$REDIS_URL" del
   ```
   Upstash counts every one of those commands against the free daily quota, so on a large keyspace let them expire on their own instead.

**Never rotate this as quarterly hygiene.** Only on a confirmed leak.

### DATABASE_URL / DATABASE_URL_SYNC

**High risk — coordinated Supabase and Render change.**

Both URLs carry the password for the `listingjet` role. `DATABASE_URL` is the transaction pooler on port 6543 (with `DB_USE_PGBOUNCER=true`); `DATABASE_URL_SYNC` is the direct connection on port 5432 that Alembic uses. They must be rotated together and must never point at the Supabase `postgres` superuser, which bypasses RLS and silently disables tenant isolation.

**Cutover:**
1. In the Supabase SQL editor: `ALTER ROLE listingjet WITH PASSWORD '<new password>';`
2. Immediately update **both** keys in `listingjet-shared` and save. The window between the `ALTER ROLE` and the redeploy finishing is real downtime, so do these back to back.
3. Verify: `curl -fsS https://<service>.onrender.com/health/deep`.
4. Update your own `.env` and any local tooling that used the old password.

**Do not** change the password and then walk away. There is no dual-password window on Supabase.

### FIELD_ENCRYPTION_KEY (Fernet)

**Do not rotate without a migration script.**

Anything encrypted with this key becomes unreadable if you swap it: old ciphertext cannot be decrypted with a new key.

**Correct procedure, if it is ever genuinely needed:**
1. Add `FIELD_ENCRYPTION_KEY_OLD` as a second value.
2. Deploy code that reads with either key and writes with the new one.
3. Write a migration that decrypts every affected row with the old key and re-encrypts with the new one.
4. Run it in production.
5. Deploy code that drops the old-key read path.
6. Delete `FIELD_ENCRYPTION_KEY_OLD` from the group.

This is a full code-change cycle, not a secret swap. Plan a week.

---

## Emergency rotation (known compromise)

If a key is *actively* compromised — pasted into a public repo, a screenshot, a Slack channel:

1. **Revoke first, ask questions later** for the zero-downtime keys: Resend, OpenAI, Anthropic, Runway, Google, Canva, Sentry. A brief error spike beats ongoing abuse.
2. **For the high-risk keys** — Stripe, JWT, database, R2 — open an incident channel before touching anything. An unplanned rotation is often worse than the compromise unless you are certain abuse is happening.
3. After rotating, audit the provider's usage logs for abuse fingerprints: unexpected regions, unexpected models, spending anomalies.

---

## Automating: future work

- [ ] Add a smoke script per provider under `scripts/smoke_<provider>.py` that validates a rotated key before the redeploy, alongside the existing `scripts/smoke_resend.py`.
- [ ] Track key age somewhere durable. Render environment groups have no age metadata, so today this is a calendar reminder.

---

**Last reviewed:** 2026-09-07
**Owner:** Jeff
