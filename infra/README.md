# infra/ — AWS CDK (DECOMMISSION-ONLY)

> **ListingJet has migrated off AWS** to Render + Supabase + Upstash +
> Cloudflare R2 + Temporal Cloud. These CDK stacks are **no longer the deploy
> target.** They are kept here for one reason only: so the still-live AWS
> resources can be torn down cleanly with `cdk destroy`.

**Do not** add features, deploy, or `cdk deploy` these stacks. New
infrastructure lives in [`render.yaml`](../render.yaml) and the managed-service
dashboards.

## What this still does
- `cdk destroy` the remaining AWS resources during decommission (Phase 3 of the
  migration). See [`docs/runbooks/render-supabase-cutover.md`](../docs/runbooks/render-supabase-cutover.md#5-decommission-aws-phase-3--do-after-a-confidence-window).
- The `ListingJetDatabase` stack adopts the live encrypted RDS via the
  zombie-import path — read the header docstring in `stacks/database.py` before
  touching anything (the don't-mutate-the-zombies rule still applies until destroy).

Once AWS is fully decommissioned and a confidence window has passed, delete this
directory and `cdk.json` in a follow-up PR.
