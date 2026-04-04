# ListingJet — Pre-Launch Checklist

## Critical Config (Must Do Before Launch)

- [ ] **Stripe keys** — Set `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` in production env
- [ ] **Stripe price IDs** — Populate all plan prices:
  - `STRIPE_PRICE_STARTER`, `STRIPE_PRICE_PRO`, `STRIPE_PRICE_ENTERPRISE`
  - `STRIPE_PRICE_LITE`, `STRIPE_PRICE_ACTIVE_AGENT`, `STRIPE_PRICE_TEAM`, `STRIPE_PRICE_ANNUAL`
  - Credit bundles: `STRIPE_PRICE_CREDIT_BUNDLE_5`, `_10`, `_25`, `_50`
- [ ] **Provider API keys** — Set `ANTHROPIC_API_KEY`, `GOOGLE_VISION_API_KEY` in production (or set `USE_MOCK_PROVIDERS=true` for soft launch)
- [ ] **AWS Secrets Manager** — Verify `DATABASE_URL`, `REDIS_URL`, `S3_BUCKET_NAME`, `TEMPORAL_HOST` are set

## Code Changes (Done)

- [x] **Startup validation** — App fails fast if `USE_MOCK_PROVIDERS=false` but provider keys are empty
- [x] **Credit balance consolidation** — All reads now use `CreditAccount.balance` (source of truth), not `Tenant.credit_balance`

## Manual QA (Must Do Before Launch)

- [ ] **Three.js CSP test** — Deploy to Vercel, open DevTools Console, navigate to 3D scenes, check for Content-Security-Policy errors
- [ ] **Stripe smoke test (test mode)**:
  - [ ] Checkout flow → use card `4242 4242 4242 4242`
  - [ ] Webhook fires → `checkout.session.completed` received
  - [ ] Plan updates in DB after checkout
  - [ ] Credit bundle purchase → `CreditAccount.balance` increases
  - [ ] Subscription renewal → `process_period_renewal` runs correctly

## Cloud Deploy (When Ready)

See `CLOUD_MIGRATION_GUIDE.md` (branch: `docs/cloud-migration-guide`) for full deploy sequence:
1. `cdk deploy ListingJetNetwork`
2. `cdk deploy ListingJetDatabase` → note RDS endpoint → populate Secrets Manager
3. `cdk deploy ListingJetServices`
4. `cdk deploy ListingJetCDN`
5. `cdk deploy ListingJetMonitoring`
6. `cdk deploy ListingJetCI`
7. Push Docker image / push to main (GitHub Actions handles it)
8. Run initial Alembic migration via ECS run-task
9. Set `API_ORIGIN` in Vercel env vars
