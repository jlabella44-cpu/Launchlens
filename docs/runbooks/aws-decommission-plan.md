# AWS Decommission Plan (run from a terminal with AWS creds)

**For:** the local Claude Code session that has AWS credentials.
**Goal:** delete the entire ListingJet AWS footprint and stop all charges.
**Context:** ListingJet has migrated off AWS (code-complete — Render + Supabase +
Upstash + Cloudflare R2 + Temporal Cloud). This is a **pre-launch** deployment with
**throwaway test data only**, confirmed by the owner. There is nothing to preserve
beyond an optional final snapshot. The app going offline is expected and fine.

> ⚠️ **Why not just `cdk destroy`?** The CDK config retains the stateful resources:
> RDS has `deletion_protection=True` + `removal_policy=RETAIN`, and the S3 bucket is
> RETAIN (`infra/stacks/database.py:180`). `cdk destroy` would **orphan the DB and
> bucket and keep billing.** Use the script below, which deletes them directly.

## Tooling
Everything is in **`scripts/aws_decommission.sh`** — dry-run by default, deletes in
cost-priority order (ECS → NAT → ALB → RDS → ElastiCache → CloudFront → S3/ECR/
Secrets/Logs), and ends with a scan for resources that silently keep billing.

## Steps for the agent

1. **Confirm identity & region.** Run `aws sts get-caller-identity` and verify it's the
   ListingJet account. Default region is `us-east-1` (pass `--region` if different).

2. **Dry run first — always.** Review the full list of what would be deleted:
   ```bash
   bash scripts/aws_decommission.sh
   ```
   Sanity-check the discovered resources (ECS services, the NAT gateway, the ALB, RDS
   `listingjet-postgres-encrypted`, the Redis group, CloudFront, the `listingjet-media*`
   bucket, ECR repos, secrets). If anything looks like it belongs to a *different*
   project, stop and ask the owner before proceeding.

3. **Decide on the final RDS snapshot.** Default keeps one (`listingjet-final-<date>`,
   ~pennies/mo) as a safety net. Since the data is throwaway, you may skip it with
   `--no-snapshot` if the owner prefers a truly clean teardown.

4. **Execute.** It will prompt for a typed `DELETE` confirmation:
   ```bash
   bash scripts/aws_decommission.sh --execute            # keeps a final RDS snapshot
   # or
   bash scripts/aws_decommission.sh --execute --no-snapshot
   ```

5. **CloudFront needs a second pass.** CloudFront can only be *disabled* synchronously;
   AWS takes ~10–15 min to deploy the disabled state before it can be deleted. The
   script prints the exact follow-up `delete-distribution` command per distribution —
   run it once each distribution shows `Deployed` + `Disabled`:
   ```bash
   aws cloudfront list-distributions --query "DistributionList.Items[?contains(Comment,'istingJet')].[Id,Status,Enabled]" --output table
   # then for each: get ETag, delete-distribution --if-match $ETAG
   ```

6. **Re-run the leftover scan** a few minutes later (NAT deletion is async, which frees
   the EIP). A second `--execute` pass is idempotent and will release the now-detached
   EIP and report anything still present:
   ```bash
   bash scripts/aws_decommission.sh --execute --yes
   ```

7. **Verify $0.** Next day, check **Billing → Cost Explorer** (group by Service). It
   should trend to ~$0. The free leftovers (VPC, subnets, IGW, empty security groups)
   are harmless; delete the `ListingJetNetwork` CFN stack last if you want a spotless
   account: `aws cloudformation delete-stack --stack-name ListingJetNetwork`.

8. **GitHub cleanup (optional).** Remove the now-unused repo secret `AWS_DEPLOY_ROLE_ARN`
   and the GitHub OIDC deploy role (`ListingJetCI` stack / IAM). The Render deploy uses
   `RENDER_DEPLOY_HOOK_*` instead.

9. **Repo cleanup (follow-up PR).** Once AWS is gone, delete the `infra/` directory and
   `cdk.json` — they exist only so this teardown could run. Open a small PR for that.

## Rollback
There is none after `--execute` beyond the optional final RDS snapshot. That's
acceptable here (pre-launch, throwaway data). If the owner ever changes their mind about
preserving data, take a `pg_dump` and `aws s3 sync` to local **before** step 4.

## Reference
- Migration cutover (for when you stand the app up on Render later):
  `docs/runbooks/render-supabase-cutover.md` and `docs/runbooks/r2-cutover.md`.
- The AWS resource definitions being torn down: `infra/` (decommission-only, see `infra/README.md`).
