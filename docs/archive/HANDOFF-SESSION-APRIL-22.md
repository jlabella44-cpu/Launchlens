# Session Handoff — 2026-04-22

Context: continuation of the pre-launch readiness push. Focus was shipping
Phase 1 of the CDK RDS encryption reconciliation, deploying the Resend
SMTP wiring from PR #261, and verifying end-to-end production health.

---

## State at session end

### Shipped + on main

- **PR #265** — `chore/rds-reconciliation-phase1` — Phase 1 prep: broke the
  `db_instance` dependency chain in `services.py` + `monitoring.py` + `app.py`.
  Hardcoded the encrypted endpoint + live secret ARN behind clearly-marked
  `⚠️ TEMPORARY` module constants. Resolved all 4 open questions from the
  plan doc via AWS CLI probes.
- **PR #266** — `docs/strike-stale-v1-prefix-claims` — CLAUDE.md + smoke
  script cleanup. CLAUDE.md previously claimed a `/v1` route prefix that
  never actually existed in the running app. Also fixed the smoke script:
  dropped the `/ready` check (endpoint doesn't exist), fixed demo-upload
  path/payload, broadened 429 as acceptable on rate-limited demo.
- **Prod deploy** — `cdk deploy ListingJetServices --exclusively` rolled
  task def rev `:16` onto all three services (api, worker, temporal) in
  244s. Dependency deadlock on first attempt (CDK tried to deploy
  Database first; CFN rejected the Outputs removal because Services
  still imported them) — `--exclusively` breaks the chain.

### Verified on live prod

| Check | Result |
|---|---|
| `/health` | 200, `{api:ok, database:ok}` |
| `/health/deep` | 200, `{database:ok, redis:ok, temporal:ok}` — **Temporal crashloop fixed** |
| New API container (rev `:16`) | Connected to `listingjet-postgres-encrypted`, ran Alembic migrations cleanly at startup |
| Temporal task def `POSTGRES_SEEDS` | `listingjet-postgres-encrypted.c8xiacyu8dyh…` literal string (no stale `Fn::GetAtt`) |
| API + Worker task defs | `EMAIL_ENABLED=true`, `SMTP_HOST=smtp.resend.com`, `SMTP_PORT=587`, `SMTP_USER=resend`, `RESEND_API_KEY` env from `listingjet/app` secret |
| Resend email delivery | End-to-end confirmed: `jlabella44@gmail.com` received a forgot-password email from Resend |
| `scripts/prod_smoke.sh` | PASS 3/3 |

### Non-obvious discoveries worth remembering

1. **There is no `/v1` prefix in the running API.** Routes are mounted at
   their bare router prefixes (`/auth/...`, `/listings/...`, `/demo/...`).
   CLAUDE.md previously asserted a `/v1` prefix; that was aspirational
   and never shipped. Corrected in PR #266.
2. **No `/ready` endpoint exists.** `listingjet/api/health.py` defines
   only `/health` and `/health/deep`.
3. **Tenant middleware returns 401 "Missing token" for unknown paths**
   (e.g. `/v1/*`). It's not 404 — the middleware rejects any path not
   in its public-path allowlist before FastAPI can say "route not found."
   If you see 401 on a path you expect to be public, check
   `_PUBLIC_PATHS` in `src/listingjet/middleware/tenant.py`.
4. **The API log group does not record access logs** — only structured
   application events. "No recent log activity" is NOT evidence that
   the API isn't serving requests.
5. **The users table is not the same as 12+ days ago.** The author's
   own account was missing; had to `/auth/register` again. Reason is
   unclear — could be a DB reset between the 2026-04-10 era and now,
   or the encryption-migration snapshot was older than expected. Live
   data loss risk on RDS reconciliation is low (all phases are
   non-destructive to the instance), but this is worth noting.
6. **ECS exec, production secret reads, `cdk deploy --require-approval never`,
   and remote-branch deletes are all sandbox-denied by default.** The
   Claude harness on this machine is correctly blocking these; work
   around them with user-driven commands in PowerShell, not by
   searching for bypasses.
7. **CDK deploy dependency graph still thinks Services depends on
   Database** because `app.py` passes `redis_cluster=database.redis_cluster`.
   That's intentional (Redis still belongs in `DatabaseStack`), but it
   means `cdk deploy ListingJetServices` without `--exclusively` will
   try to deploy Database first and deadlock on the stale Outputs.
   **Always use `--exclusively` until RDS reconciliation completes.**

---

## Next session: execute RDS reconciliation Phases 2–6

Plan: `docs/plans/2026-04-21-cdk-rds-encryption-reconciliation.md` (already
updated with resolved open-question values).

**Time budget**: 2 focused hours, AWS creds ready, live prod awareness.

**Absolute rule**: never `cdk deploy ListingJetDatabase` until Phase 5
`cdk import` has fully adopted the encrypted instance under logical id
`Postgres`. A bare deploy would try to create a new empty Postgres on top
of live data.

### Pre-flight

- On `main`, branch off `chore/rds-reconciliation-phase2`.
- Confirm nothing else is in flight: `gh pr list --state open` should
  show 0 (as of session end) or whatever else you're aware of.
- Have this shell handy with AWS creds exported.

### Phase 2 — Flip `removal_policy` to RETAIN (small deploy, low risk)

1. Edit `infra/stacks/database.py:99`:
   ```python
   removal_policy=RemovalPolicy.RETAIN,  # was: SNAPSHOT
   ```
2. `cd infra && cdk diff ListingJetDatabase` — expect DeletionPolicy
   change only, no resource replacement.
3. `cdk deploy ListingJetDatabase` — CFN updates stored DeletionPolicy
   metadata. No AWS API call fires (resource already gone).
4. Verify:
   ```bash
   aws cloudformation describe-stack-resource \
     --stack-name ListingJetDatabase --logical-resource-id Postgres \
     --query "StackResourceDetail.Metadata"
   ```
   Resource detail should confirm `Retain` deletion policy.

**If CFN complains about the deleted physical resource**: fall back to
`aws cloudformation continue-update-rollback`. If still stuck, halt and
reassess — do not attempt Phases 3+.

### Phase 3 — Remove `Postgres` from the template

1. Delete the entire `self.db_instance = rds.DatabaseInstance(...)` block
   from `database.py` (lines ~69–100).
2. `cdk diff ListingJetDatabase` — expect `Postgres` resource removal
   and the 3 orphaned `ExportsOutput*` outputs finally being removed.
3. `cdk deploy ListingJetDatabase` — CFN drops tracking without calling
   `DeleteDBInstance` (thanks to Phase 2 RETAIN).
4. Verify:
   ```bash
   aws cloudformation describe-stack-resources \
     --stack-name ListingJetDatabase \
     --query "StackResources[?ResourceType=='AWS::RDS::DBInstance']"
   ```
   Should return `[]`.
5. Live sanity check (belt-and-suspenders):
   ```bash
   aws rds describe-db-instances \
     --db-instance-identifier listingjet-postgres-encrypted \
     --query "DBInstances[0].DBInstanceStatus"
   ```
   Should return `"available"`.

### Phase 4 — Re-add `Postgres` with exact-match properties

Verified values (2026-04-22):

```python
# Secret (still alive, not pending deletion):
#   arn:aws:secretsmanager:us-east-1:265911026550:secret:\
#     ListingJetDatabasePostgresS-2g2B0n8yjwAF-DRYvqm
# KMS:
#   arn:aws:kms:us-east-1:265911026550:key/1482e415-1d7e-4269-b887-1a25d453cf6b
# Subnet group: CFN-tracked under logical id PostgresSubnetGroup9F8A4D6E
#   (physical: listingjetdatabase-postgressubnetgroup9f8a4d6e-ixyvwsoprif1)
# Parameter group: listingjet-pg16 (custom — NOT default.postgres16)
# Engine version: 16.10 exactly (not floating 16.x)
```

Construct template to re-add:

```python
from aws_cdk import aws_kms as kms
from aws_cdk import aws_secretsmanager as sm

_DB_SECRET_ARN = (
    "arn:aws:secretsmanager:us-east-1:265911026550:secret:"
    "ListingJetDatabasePostgresS-2g2B0n8yjwAF-DRYvqm"
)
_DB_KMS_ARN = (
    "arn:aws:kms:us-east-1:265911026550:key/"
    "1482e415-1d7e-4269-b887-1a25d453cf6b"
)

self.db_instance = rds.DatabaseInstance(
    self, "Postgres",
    engine=rds.DatabaseInstanceEngine.postgres(
        version=rds.PostgresEngineVersion.VER_16_10,  # see note below
    ),
    instance_type=ec2.InstanceType.of(
        ec2.InstanceClass.BURSTABLE4_GRAVITON,
        ec2.InstanceSize.MICRO,
    ),
    vpc=vpc,
    vpc_subnets=ec2.SubnetSelection(
        subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
    ),
    security_groups=[self.db_sg],
    database_name="listingjet",
    credentials=rds.Credentials.from_secret(
        sm.Secret.from_secret_complete_arn(self, "DbSecret", _DB_SECRET_ARN),
    ),
    allocated_storage=20,
    max_allocated_storage=50,
    storage_type=rds.StorageType.GP2,
    storage_encrypted=True,
    storage_encryption_key=kms.Key.from_key_arn(
        self, "DbKmsKey", _DB_KMS_ARN,
    ),
    parameter_group=rds.ParameterGroup.from_parameter_group_name(
        self, "DbParamGroup", "listingjet-pg16",
    ),
    multi_az=False,
    backup_retention=Duration.days(1),
    deletion_protection=True,
    removal_policy=RemovalPolicy.RETAIN,
)
```

**Engine version gotcha**: if `rds.PostgresEngineVersion.VER_16_10` is not
in the CDK version in use, drop to `rds.CfnDBInstance` (L1 construct)
and pin `engine_version="16.10"` exactly. `VER_16` will NOT work — Phase 5
`cdk import` fails because live instance reports `16.10` exactly.

Steps:

1. Re-add the block with every property above.
2. `cdk synth ListingJetDatabase` — **do not deploy yet**. Inspect the
   synthesized `AWS::RDS::DBInstance` resource YAML and compare every
   property against the live describe output. Any float (`VER_16` vs
   `VER_16_10`, default param group vs custom, missing `storage_encrypted`,
   etc.) will cause Phase 5 to fail.

### Phase 5 — `cdk import` to adopt the encrypted instance

1. `cdk import ListingJetDatabase`
2. When prompted for the physical identifier of `Postgres`, answer:
   `listingjet-postgres-encrypted`
3. When prompted for KMS key id, answer:
   `arn:aws:kms:us-east-1:265911026550:key/1482e415-1d7e-4269-b887-1a25d453cf6b`
4. **Expect failures here.** Each property mismatch fails the import with
   a clear "property X expected Y got Z" message. For each: edit the
   construct to match, `cdk synth`, re-run `cdk import`. Typical 2–3
   iterations.
5. On success: CFN now tracks the encrypted instance under logical id
   `Postgres`. `db_instance.db_instance_endpoint_address` resolves to
   the encrypted endpoint.

### Phase 6 — Undo Phase 1 temporary hardcodes

1. Revert the three `_DB_ENDPOINT` / `_DB_SECRET_ARN` / `_rds_metric()`
   blocks in `services.py` + `monitoring.py` + `app.py` from PR #265.
   Easiest way: `git revert <PR#265 merge sha>` on a new branch, then
   fix any conflicts against the current state.
2. `cdk diff ListingJetServices` — expect env vars + secret refs to
   change back to `Fn::GetAtt` / `Fn::ImportValue` against the newly-
   imported `Postgres` resource. The resolved values should be identical
   to the current hardcodes.
3. `cdk deploy ListingJetServices` — rolls a new task def rev onto all
   three services. (No `--exclusively` this time — the dependency chain
   is now coherent.)
4. `cdk deploy ListingJetMonitoring` — restores native `db_instance.metric_*`
   alarms and the dashboard RDS widget.
5. Verify:
   ```bash
   TD=$(aws ecs list-task-definitions --family-prefix ListingJetServicesTemporalTaskE084D0B5 --sort DESC --region us-east-1 --query 'taskDefinitionArns[0]' --output text)
   aws ecs describe-task-definition --task-definition "$TD" --region us-east-1 \
     --query "taskDefinition.containerDefinitions[0].environment[?Name=='POSTGRES_SEEDS']"
   ```
   Value should be the encrypted endpoint again — but via CDK ref this
   time, not a literal string.
6. Run `scripts/prod_smoke.sh` — expect PASS 3/3.

### After Phase 6 — pick up remaining pre-launch work

Once reconciliation is done, the deferred pre-launch work becomes easy
to tackle on a stable baseline:

- `docs/PRE_LAUNCH_INFRA_CHECKLIST.md` §A is complete (encryption done).
- Items 1–7 (t4g.micro → t4g.small, backup retention 1d → 7d, Redis
  single-node → 2-node failover, ECS task sizing) — straightforward
  `cdk deploy ListingJetDatabase` + `ListingJetServices` after editing
  the construct. No drift to worry about anymore.
- Cost data collection (MASTER_TODO.md "Cost Optimization") — wait for
  7–14 days of real traffic.

---

## Known inert drift / housekeeping

- **Legacy branches (11)** still on remote after auto-delete-on-merge
  was enabled mid-stream. Sandbox blocks remote delete; easiest cleanup
  is via GitHub UI → branches page → delete merged. List in session
  chat transcript under "branch hygiene" if needed.
- **jlabella44@gmail.com account** was re-registered during email
  smoke testing with password `SomethingRealThisTime1!`. Use the
  forgot-password email that arrived to reset it.
- **Ambiguous branches** not linked to any recent PR — review before
  deleting:
  - `claude/phase4-social-publish`
  - `claude/reso-web-api-certification-OYzxG`
  - `infra/cdk-cleanup` (known to conflict with main per earlier session)

---

## Commands reference (tested this session)

```bash
# Get latest task def revision (drop --max-items, it adds a pagination token)
aws ecs list-task-definitions --family-prefix <family> --sort DESC \
  --region us-east-1 --query 'taskDefinitionArns[0]' --output text

# Tail log group on Windows git-bash (need MSYS_NO_PATHCONV or path rewrite eats the leading slash)
MSYS_NO_PATHCONV=1 aws logs tail "/listingjet/api" --since 10m --region us-east-1

# Prod API probe from git-bash (UA matters — default Python urllib UA gets 403 from WAF)
python -c "
import urllib.request, json
headers = {'User-Agent': 'Mozilla/5.0 (compatible; Smoke/1.0)'}
req = urllib.request.Request('https://api.listingjet.ai/health', headers=headers)
with urllib.request.urlopen(req, timeout=15) as r:
    print(r.status, r.read().decode()[:200])
"

# cdk deploy Services only (break Database dependency)
cd infra && cdk deploy ListingJetServices --exclusively
```
