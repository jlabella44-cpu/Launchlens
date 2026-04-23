# Session Handoff — 2026-04-23

Context: picked up the RDS encryption reconciliation that the
2026-04-22 handoff teed up for Phase 2–6. The handoff's runbook was
wrong about CFN resource-provider semantics, so Phase 2 failed twice.
Pivoted to a zombie-parallel `cdk import` path, shipped it, ran the
Phase 6 dehardcoding, and merged. RDS encryption drift is closed.

---

## State at session end

### Shipped + on main

- **PR #267** (`docs/session-handoff-2026-04-22`) — merged at session
  start. The April-22 handoff doc is now at
  `docs/archive/HANDOFF-SESSION-APRIL-22.md` as a historical record of
  what was *planned*, not what happened. Leave it unchanged; it's
  referenced by the current session's learnings.
- **PR #268** (`chore/rds-reconciliation-phase2`) — zombie-path RDS
  encryption reconciliation. Live `listingjet-postgres-encrypted` is
  now tracked in `ListingJetDatabase` under logical id
  `PostgresEncrypted9317B6C2`. Phase 1's hardcodes in `services.py` +
  `monitoring.py` + `app.py` are gone; those stacks now use native
  CDK cross-stack refs (`db_instance.db_instance_endpoint_address`,
  `db_instance.metric_cpu_utilization()`,
  `db_instance.metric_free_storage_space()`).
- **Mid-flight redeploy of `ListingJetMonitoring`** — discovered
  during the first failed Phase 2 attempt that PR #265 had patched
  `monitoring.py` but never actually deployed (only `ListingJetServices`
  was deployed at Phase 1's end). The deployed Monitoring stack still
  held `Fn::ImportValue` refs to the zombie exports, blocking
  Output cleanup. Redeployed once with the patched code — clean.

### Verified on live prod

| Check | Result |
|---|---|
| `/health` | 200 |
| `/health/deep` | 200, `{database:ok, redis:ok, temporal:ok}` |
| Temporal task def `ListingJetServicesTemporalTaskE084D0B5:8` | `POSTGRES_SEEDS = listingjet-postgres-encrypted.c8xiacyu8dyh.us-east-1.rds.amazonaws.com`, sourced via `Fn::ImportValue` (not literal) |
| `aws rds describe-db-instances --db-instance-identifier listingjet-postgres-encrypted` | `available`, `StorageEncrypted: True`, endpoint + SG + subnet group untouched |
| `aws cloudformation describe-stacks --stack-name ListingJetDatabase` | `UPDATE_COMPLETE` |
| New Database exports | `ExportsOutputFnGetAttPostgresEncrypted9317B6C2EndpointAddress1541A983` + `ExportsOutputRefPostgresEncrypted9317B6C27CA9E1C6`, both resolve correctly |

### Non-obvious discoveries worth remembering

1. **CFN's v2 RDS resource provider calls `describe-db-instances` on
   any logical-resource update — including pure metadata changes like
   DeletionPolicy.** The April-22 handoff's claim "Phase 2 deploy
   updates stored DeletionPolicy metadata. No AWS API call fires" was
   wrong. If the tracked physical resource is gone, any metadata
   update 404s. Reproduced twice.
2. **The live `listingjet-postgres-encrypted` reuses the stack's
   original subnet group** (`listingjetdatabase-postgressubnetgroup9f8a4d6e-ixyvwsoprif1`,
   CFN logical id `PostgresSubnetGroup9F8A4D6E`). The April-22
   handoff's Phase 3 ("remove the construct from the template") would
   have cascade-deleted a subnet group still in active use. Second
   blocker on top of the 404.
3. **`rds.Credentials.from_password()` avoids the implicit
   `SecretTargetAttachment` that `rds.Credentials.from_secret()`
   creates.** `cdk import` can only adopt existing resources, so any
   NEW resource in the template (like an auto-added attachment)
   causes the import to fail. Use `from_password` with
   `secret.secret_value_from_json("password")` when importing — the
   password still comes from Secrets Manager via a dynamic reference,
   but no attachment resource is synthesized.
4. **`cdk import --resource-mapping <file>` is non-interactive in
   CDK 2.1115.0.** File format:
   ```json
   { "LogicalId": { "PrimaryIdentifierKey": "physical-id" } }
   ```
   For `AWS::RDS::DBInstance`, the key is `DBInstanceIdentifier`. No
   stdin heredoc tricks needed.
5. **Removing an Output via `cdk deploy` works cleanly when it's the
   only change.** Combining it with `cdk import` in a single operation
   fails because post-import state transition re-resolves `Fn::GetAtt`
   on the very Output you're removing. If your stack has Outputs that
   reference a resource whose physical id is gone, deploy the Output
   removal *first*, then run `cdk import` separately.
6. **`aws cloudformation list-imports` returns a `ValidationError`
   with message `Export '...' is not imported by any stack` when
   nobody imports it.** Counter-intuitive — no JSON result means "no
   importers" and that's the *good* outcome. Check for this error
   string explicitly.
7. **`--resources-to-skip` during `continue-update-rollback` does
   NOT remove the resource from stack tracking.** It marks the
   resource as "rolled back successfully" in whatever pre-update
   state CFN had. We used this once to unstick a failed deploy; it
   doesn't help with the goal of forgetting a zombie.
8. **`scripts/prod_smoke.sh` step 3 is broken.** Sends 1 photo;
   `/demo/upload` now requires 5–50. Was PASS at Phase 1's end per
   the handoff; regressed between then and now. Not an infra issue.

---

## Known inert drift / housekeeping

### CFN zombies in `ListingJetDatabase`

Three tracked resources whose physical counterparts are gone. They
return 404 on any describe. Any `cdk deploy` change set that includes
them in its resource diff will fail.

- `Postgres9DC8BB04` (AWS::RDS::DBInstance)
- The CDK-generated master Secret synthesized by the old `Postgres`
  construct's `Credentials.from_generated_secret("listingjet")`
- `PostgresSecretAttachment75CD6F6F` (AWS::SecretsManager::SecretTargetAttachment)

**They are inert as long as nothing in the template references them.**
Current template doesn't — the old `Postgres` construct synthesizes
the resources but no `Fn::GetAtt`/`Ref` points at them. All live
usage flows through the new `PostgresEncrypted` construct.

**Don't try to clean them up in a routine session.** Full cleanup
requires a `delete-stack --retain-resources` rebuild, which is
riskier than the drift. The file header in `infra/stacks/database.py`
explains the state for future readers.

### Stale remote branches (not touched this session)

The April-22 handoff flagged 11 merged-but-undeleted branches. Sandbox
blocks remote delete; cleanup is via GitHub UI → branches → delete
merged. Plus 3 ambiguous ones worth reviewing before deletion:

- `claude/phase4-social-publish`
- `claude/reso-web-api-certification-OYzxG`
- `infra/cdk-cleanup` (known to conflict with main per earlier session)

### Smoke script regression

`scripts/prod_smoke.sh` step 3 fails with
`"Photo count must be between 5 and 50, got 1"`. Either bump the
payload to ≥5 photos or update the expected error band. Five-minute
fix.

---

## Next session priorities

### 1. Pre-launch infra right-sizing

`docs/PRE_LAUNCH_INFRA_CHECKLIST.md` lists the deliberate pre-launch
undersizing. Now that reconciliation is done, these are straight
CDK edits + `cdk deploy`:

- RDS: `t4g.micro` → `t4g.small`, `backup_retention=7`, consider Multi-AZ
- Redis: `cache.t4g.micro` → `cache.t4g.small`, single-node → 2-node failover
- ECS: bump CPU/memory on API + worker task defs

Apply in `infra/stacks/database.py` and `infra/stacks/services.py`.
All single-PR work. **Avoid touching the old `Postgres` zombie
construct's properties** — only edit `PostgresEncrypted`.

### 2. Fix the smoke script

Tiny. Skip or fix step 3.

### 3. Branch hygiene

GitHub UI sweep.

### 4. Wait on cost data

`MASTER_TODO.md` "Cost Optimization" section — needs 7–14 days of
traffic first, then right-size based on real numbers.

---

## Commands reference (tested this session)

```bash
# Non-interactive cdk import with resource mapping file
cat > resource-mapping.json <<'EOF'
{ "PostgresEncrypted9317B6C2": { "DBInstanceIdentifier": "listingjet-postgres-encrypted" } }
EOF
cdk import ListingJetDatabase --resource-mapping resource-mapping.json

# Unstick a stack in UPDATE_ROLLBACK_FAILED
aws cloudformation continue-update-rollback \
  --stack-name ListingJetDatabase \
  --resources-to-skip Postgres9DC8BB04 \
  --region us-east-1

# Verify an export has no importers
# (ValidationError "is not imported by any stack" = GOOD)
aws cloudformation list-imports \
  --export-name "ListingJetDatabase:ExportsOutputRefPostgres9DC8BB0479C34812" \
  --region us-east-1

# Deploy just Database without pulling in dependent stacks
cd infra && cdk deploy ListingJetDatabase --exclusively

# Dump all env vars on latest Temporal task def rev (case matters!)
TD=$(aws ecs list-task-definitions --family-prefix ListingJetServicesTemporalTaskE084D0B5 \
  --sort DESC --region us-east-1 --query 'taskDefinitionArns[0]' --output text)
aws ecs describe-task-definition --task-definition "$TD" --region us-east-1 \
  --query "taskDefinition.containerDefinitions[0].environment"
# JMESPath filter: use lowercase 'name' (not 'Name')

# Tail log group on Windows git-bash (leading slash eaten without this)
MSYS_NO_PATHCONV=1 aws logs tail "/listingjet/api" --since 10m --region us-east-1
```

---

## Budget postmortem

Session budget was 2h. Actual spend: ~2h10m. Breakdown:

- First 40 min: two failed Phase 2 attempts + recovery + Monitoring
  redeploy. Would have been avoided if the handoff had been right
  about CFN provider semantics.
- Next ~30 min: pivot design, parallel construct edit, first failed
  `cdk import` (zombie Outputs block), Outputs-only deploy, re-import.
- Final ~60 min: Phase 6 dehardcoding, three deploys (Database,
  Services, Monitoring), smoke, commit, PR, advisor review, merge.

The PR is cleanly scoped and honestly explains the pivot. Don't
revise the commit message to sound smoother — future sessions that
hit similar CFN resource-provider surprises will appreciate the
explicit counterexample.
