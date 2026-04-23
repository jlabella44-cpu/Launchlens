# CDK RDS Encryption Reconciliation — Execution Plan

**Status:** planned, not started
**Owner:** next-session
**Estimated time:** 2–3 focused hours (includes retry cycles on `cdk import`)
**Blast radius:** production RDS — getting wedged mid-sequence is possible and recoverable but costly.

---

## Context

The 2026-04-16/17 session migrated prod RDS from an unencrypted instance to `listingjet-postgres-encrypted` via raw `aws rds` CLI (not CDK). CloudFormation still tracks the old (now deleted) instance under the logical ID `Postgres` in the `ListingJetDatabase` stack. Until this drift is reconciled:

- **DO NOT** run `cdk deploy ListingJetDatabase` — a normal deploy would either fail or recreate a brand-new empty Postgres on top of live data.
- **Side effect visible today (2026-04-21):** the prod Temporal task def still holds a hardcoded old RDS endpoint (`…kjyxgeldpfef…`) in its `POSTGRES_SEEDS` env var, because the CDK reference `db_instance.db_instance_endpoint_address` resolves to CFN's stale stored value. This keeps the prod Temporal server in a crashloop ("GetNamespace operation failed. Error no usable database connection found") and stalls the pipeline.

The handoff at `docs/archive/HANDOFF-SESSION-APRIL-2*.md` described a 4-step plan (RETAIN → remove → re-add → `cdk import`). Review on 2026-04-21 found that plan has real gaps. This document is the revised plan.

---

## Live RDS properties (captured 2026-04-21)

These must match exactly when re-adding the construct, or `cdk import` will reject:

| Property | Value |
|---|---|
| DB identifier | `listingjet-postgres-encrypted` |
| Engine | `postgres` |
| Engine version | `16.10` (NOT floating `16.x`) |
| Instance class | `db.t4g.micro` |
| Allocated storage | 20 GB |
| Storage type | `gp2` |
| Storage encrypted | `true` |
| KMS key | `arn:aws:kms:us-east-1:265911026550:key/1482e415-1d7e-4269-b887-1a25d453cf6b` (alias `alias/aws/rds`) |
| Master username | `listingjet` |
| Port | 5432 |
| Multi-AZ | `false` |
| Publicly accessible | `false` |
| Backup retention | 1 day |
| Deletion protection | `true` |
| Subnet group | `listingjetdatabase-postgressubnetgroup9f8a4d6e-ixyvwsoprif1` (reuse existing — still in CFN) |
| Parameter group | `listingjet-pg16` (**custom** — CDK currently defaults to `default.postgres16`) |
| Security group | `sg-03d031a7d7993954a` |
| CA cert | `rds-ca-rsa2048-g1` |
| Performance Insights | disabled |

---

## Complications identified 2026-04-21 (why the handoff's 4-step plan needs revision)

### 1. Downstream consumers of `db_instance`

`DatabaseStack.db_instance` is passed into two other stacks and used in 5 places:

- `infra/app.py:31,41` — wires into `ServicesStack` + `MonitoringStack`
- `infra/stacks/services.py:90` — `db_secret = db_instance.secret`
- `infra/stacks/services.py:364` — `"POSTGRES_SEEDS": db_instance.db_instance_endpoint_address` (Temporal task def)
- `infra/stacks/monitoring.py:122,133,227,228` — CloudWatch alarms on DB metrics

The handoff's step 2 says "remove `Postgres` resource from the template." Doing that makes `database.db_instance` undefined → synth fails for Services + Monitoring stacks.

**Mitigation:** Temporarily replace `db_instance`-typed refs with hardcoded values during the transition window:
- `db_instance_endpoint_address` → string literal `"listingjet-postgres-encrypted.c8xiacyu8dyh.us-east-1.rds.amazonaws.com"`
- `db_instance.secret` → `secretsmanager.Secret.from_secret_name_v2(self, "DbSecretRef", "<actual-secret-name>")` (see "Open questions" — the original CDK-generated secret may have been orphaned when the instance was deleted; verify before Phase 3)
- CloudWatch alarms in `monitoring.py` — either remove alarm block temporarily, or switch to `cloudwatch.Metric(namespace="AWS/RDS", dimensions_map={"DBInstanceIdentifier": "listingjet-postgres-encrypted"}, metric_name=…)` constructed manually

### 2. Current `removal_policy=SNAPSHOT` will fail at remove time

`database.py:99` sets `removal_policy=RemovalPolicy.SNAPSHOT`. When CFN tries to remove the resource in step 2, it would call `DeleteDBInstance` with `FinalDBSnapshotIdentifier` — which fails because the physical instance is already gone ("DB instance … not found"). The handoff assumed this would no-op; it won't.

**Mitigation:** Phase A explicitly flips `SNAPSHOT` → `RETAIN` *before* the remove.

### 3. Property mismatches will block `cdk import`

The current construct omits or floats several properties that `cdk import` requires to match live exactly. Additions required before Phase 4:

- `storage_encrypted=True`
- `storage_encryption_key=kms.Key.from_key_arn(…, "arn:aws:kms:us-east-1:265911026550:key/1482e415-1d7e-4269-b887-1a25d453cf6b")`
- `engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_16_10)` (or equivalent — **not** `VER_16`)
- `parameter_group=rds.ParameterGroup.from_parameter_group_name(self, "ParamGroup", "listingjet-pg16")`
- `storage_type=rds.StorageType.GP2` explicit

---

## Revised execution plan

Each phase ends with a verification step. If any verification fails, halt and investigate; do not proceed.

### Phase 1 — Break the `db_instance` dependency chain (prep, no prod risk)

Goal: make Services + Monitoring stacks synth without a `DatabaseStack.db_instance` attribute.

1. Introduce temporary string constants at the top of `services.py` + `monitoring.py` for the encrypted endpoint + secret ARN.
2. Replace the 5 `db_instance.*` references with the constants.
3. Local synth check: `cd infra && cdk synth ListingJetServices ListingJetMonitoring` must succeed.
4. Commit on feature branch. **Do not deploy yet.**

### Phase 2 — Flip `RemovalPolicy` to `RETAIN` (small deploy, low risk)

1. `database.py:99` — `removal_policy=RemovalPolicy.SNAPSHOT` → `removal_policy=RemovalPolicy.RETAIN`.
2. `cdk diff ListingJetDatabase` — expect DeletionPolicy change only, no resource replacement.
3. `cdk deploy ListingJetDatabase` — CFN updates its stored DeletionPolicy metadata. No AWS API call fires because the resource is already gone.
4. Verify: `aws cloudformation describe-stack-resource --stack-name ListingJetDatabase --logical-resource-id Postgres` — `DeletionPolicy` should read `Retain`.

**If CFN complains about the deleted physical resource here:** fall back to `aws cloudformation set-stack-policy` / `continue-update-rollback` to force-update. If stuck, stop and escalate; do not attempt phases 3+.

### Phase 3 — Remove `Postgres` from template

1. Delete the entire `self.db_instance = rds.DatabaseInstance(...)` block from `database.py`.
2. Remove the `db_instance` attribute exports from `DatabaseStack.__init__` return surface.
3. `cdk diff ListingJetDatabase` — expect `Postgres` resource removal, no other changes.
4. `cdk deploy ListingJetDatabase` — CFN drops tracking without calling `DeleteDBInstance` (thanks to Phase 2).
5. Verify: `aws cloudformation describe-stack-resources --stack-name ListingJetDatabase` — no `Postgres` row.
6. Live sanity: `aws rds describe-db-instances --db-instance-identifier listingjet-postgres-encrypted` — still there.

### Phase 4 — Re-add `Postgres` with exact-match properties

1. Edit `database.py`: re-add the `rds.DatabaseInstance` block with every property from the "Live RDS properties" table above.
2. `cdk synth ListingJetDatabase` — inspect the synthesized `AWS::RDS::DBInstance` YAML; compare each property against the live RDS describe output. Any float (`VER_16` vs `VER_16_10`, default param group vs custom) will cause Phase 5 to fail.
3. **Do not `cdk deploy` yet.** The next step is `cdk import`, not `deploy`.

### Phase 5 — `cdk import` to adopt the encrypted instance

1. `cd infra && cdk import ListingJetDatabase`
2. CDK prompts for the physical identifier for `Postgres` — provide `listingjet-postgres-encrypted`.
3. CDK asks for the KMS key ID (for `StorageEncryptionKey`) — provide the ARN from the table above.
4. **Expect failures here.** Each property mismatch will fail the import with a clear message ("property X expected Y got Z"). For each failure: edit the construct, re-synth, re-run import. Typical 2–3 iterations.
5. On success: CFN now tracks `listingjet-postgres-encrypted` under logical ID `Postgres`. The `db_instance.db_instance_endpoint_address` CDK ref now resolves to the new endpoint.

### Phase 6 — Undo Phase 1 temporary hardcodes

1. Revert Phase 1 changes in `services.py` + `monitoring.py` — restore the `db_instance.*` references.
2. `cdk diff ListingJetServices` — expect task def env var `POSTGRES_SEEDS` changes from old endpoint to new endpoint on api + worker + Temporal.
3. `cdk deploy ListingJetServices` — rolls a new task def revision onto each service. Temporal crashloop resolves (it now reaches the live encrypted Postgres).
4. `cdk deploy ListingJetMonitoring` if alarms were touched.
5. Verify: `aws ecs describe-task-definition --task-definition ListingJetServicesTemporalTaskE084D0B5 --query 'taskDefinition.containerDefinitions[].environment'` — `POSTGRES_SEEDS` now points at `listingjet-postgres-encrypted…`.
6. Verify downstream: CloudWatch log group `/listingjet/worker` → no more "no usable database connection" warnings.

---

## Rollback plan

- **Phases 1, 4, 6:** purely code changes, uncommitted or on branch — revert via git.
- **Phase 2:** if DeletionPolicy flip itself fails, abandon; no state change.
- **Phase 3 fails partway:** `aws cloudformation cancel-update-stack` / `continue-update-rollback`. The live RDS is unaffected.
- **Phase 5 refuses to converge:** revert Phases 3+4 code, re-add a manually-tracked resource with `CfnInclude` as an escape hatch. Worst case: accept permanent drift, switch all consumers to hardcoded references, and drop the `DatabaseStack.db_instance` abstraction.

Live RDS `listingjet-postgres-encrypted` is protected by `DeletionProtection=True` throughout. No phase of this plan calls `DeleteDBInstance` against it.

---

## Open questions — RESOLVED 2026-04-22

All four questions verified via AWS CLI against the live account before Phase 1 code was drafted.

1. **CDK-generated secret is still alive.**
   - `aws secretsmanager describe-secret --secret-id arn:aws:secretsmanager:us-east-1:265911026550:secret:ListingJetDatabasePostgresS-2g2B0n8yjwAF-DRYvqm` → Name `ListingJetDatabasePostgresS-2g2B0n8yjwAF`, `DeletedDate=None`, last changed 2026-04-14 (i.e., after the encryption migration).
   - Phase 4 should wire `credentials=rds.Credentials.from_secret(sm.Secret.from_secret_complete_arn(self, "DbSecret", _DB_SECRET_ARN))`.
   - Phase 1 already references this ARN directly (see `services.py` module-level constant).

2. **Engine version is exactly `16.10`** (`aws rds describe-db-instances …`).
   - Use `rds.PostgresEngineVersion.VER_16_10` if available. If the CDK version in use only exposes `VER_16`, drop to `CfnDBInstance` L1 to pin `EngineVersion: "16.10"` exactly — Phase 5 `cdk import` will fail otherwise.

3. **Subnet group is still CFN-tracked** (logical id `PostgresSubnetGroup9F8A4D6E`, physical id `listingjetdatabase-postgressubnetgroup9f8a4d6e-ixyvwsoprif1`, status `CREATE_COMPLETE`).
   - Phase 4 can reference it via the existing construct. No `from_subnet_group_name` lookup needed.

4. **KMS key is the full ARN** `arn:aws:kms:us-east-1:265911026550:key/1482e415-1d7e-4269-b887-1a25d453cf6b` (confirmed by `DBInstance.KmsKeyId`).
   - Phase 4 uses `kms.Key.from_key_arn(self, "DbKmsKey", <arn>)` — no lookup fallback needed.

### Additional facts confirmed 2026-04-22

- Stale CFN entry still present: `Postgres9DC8BB04` physical id `listingjetdatabase-postgres9dc8bb04-kjyxgeldpfef` status `UPDATE_COMPLETE`. Drift is exactly as described in the Context section.
- Live instance: status `available`, master username `listingjet`, port `5432`, `StorageEncrypted=true`.

---

## Not covered by this plan (intentional)

- **Pre-launch infra revert** (t4g.micro → t4g.small, backup 1d → 7d, Redis HA, ECS task sizing). See `docs/PRE_LAUNCH_INFRA_CHECKLIST.md` items 1–7. Easier to tackle *after* this reconciliation lands, on a stable baseline.
- **Email provider wiring** (`EMAIL_ENABLED=true`, Resend SMTP relay). Separate PR. See `CLAUDE.md` "Remaining P0 items" §1.

---

## References

- `docs/PRE_LAUNCH_INFRA_CHECKLIST.md` §A — original encryption migration runbook (completed 2026-04-17)
- `docs/archive/HANDOFF-SESSION-APRIL-2*.md` — prior-session handoff with the original 4-step plan
- `infra/stacks/database.py` — module-level ⚠️ warning with superseded plan
- `infra/stacks/services.py` — `db_instance` consumers (now hardcoded via `_DB_ENDPOINT` / `_DB_SECRET_ARN` module constants after Phase 1)
- `infra/stacks/monitoring.py` — `db_instance` consumers (now via `_rds_metric()` helper after Phase 1)
- `infra/app.py` — stack-to-stack wiring (`db_instance=` kwargs dropped from Services + Monitoring after Phase 1)
