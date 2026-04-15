# Pre-Launch Infrastructure Checklist

Before onboarding the first paying users, **revert the cost-cutting
right-sizing** applied on branch `claude/aws-cost-optimization-6ygJY`. The
infra is intentionally undersized for a no-users state. Each item below
includes the file, the change, and the reasoning.

---

## Critical — must revert before launch

These changes meaningfully degrade the user experience or data safety
once real traffic arrives.

### 1. Restore RDS instance size

**File:** `infra/stacks/database.py`

```diff
- ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.MICRO,
+ ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.SMALL,
```

`t4g.micro` has 1 GB RAM. Postgres 16 + Temporal's history store + the
SQLAlchemy connection pool will throw it under the bus at the first
real workload. `t4g.small` is the minimum sane production size; consider
`t4g.medium` if traffic warrants.

### 2. Restore RDS backup retention

**File:** `infra/stacks/database.py`

```diff
- backup_retention=Duration.days(1),
+ backup_retention=Duration.days(7),
```

1-day PITR is fine when there is no production data to lose. Customers
expect at least a week of recovery window.

### 3. Re-enable RDS Multi-AZ (if SLA demands it)

**File:** `infra/stacks/database.py`

```diff
- multi_az=False,
+ multi_az=True,
```

Adds ~50% to the RDS bill but takes expected downtime from ~3.5 hr/yr
to ~4 min/yr. **Required** for any contractual uptime guarantee. Skip
only if you are explicitly comfortable with single-AZ for paying
customers.

### 4. Restore Redis size + HA

**File:** `infra/stacks/database.py`

```diff
- cache_node_type="cache.t4g.micro",
+ cache_node_type="cache.t4g.small",
...
- num_cache_clusters=1,
- automatic_failover_enabled=False,
+ num_cache_clusters=2,
+ automatic_failover_enabled=True,
```

Single-node Redis means a 5-15 min outage when AWS replaces a failed
node — and during that window, rate limiting, SSE pub/sub, and auth
lockout all degrade. With real users, the second node + automatic
failover is worth it.

### 5. Restore API task size

**File:** `infra/stacks/services.py`

```diff
- cpu=512,
- memory_limit_mib=1024,
+ cpu=1024,
+ memory_limit_mib=2048,
```

0.5 vCPU / 1 GB is fine for an idle service but will choke under
concurrent uploads + websocket fanout from real photographers/agents.
Auto-scaling already caps at 4 tasks, so this is the per-task floor.

### 6. Restore Worker task size

**File:** `infra/stacks/services.py`

```diff
- cpu=1024,
- memory_limit_mib=2048,
+ cpu=2048,
+ memory_limit_mib=4096,
```

The Worker runs the AI pipeline: Vision tier-1/tier-2, packaging,
FFmpeg video stitching, Kling clip generation, virtual staging.
FFmpeg in particular wants both cores. **Confirm with AWS Compute
Optimizer after 14 days of real traffic** — it may recommend going
larger still.

### 7. Re-enable Container Insights

**File:** `infra/stacks/services.py`

```diff
- container_insights_v2=ecs.ContainerInsights.DISABLED,
+ container_insights_v2=ecs.ContainerInsights.ENABLED,
```

Per-task metrics (CPU, memory, network, disk). Without these, you
cannot diagnose performance regressions or feed Compute Optimizer.
Cheap relative to revenue.

---

## Recommended — should revert before launch

### 8. Worker capacity provider — consider mixed strategy

**File:** `infra/stacks/services.py`

The Worker is currently 100% on `FARGATE_SPOT`. Temporal activities
are retry-safe so this is functionally fine — but a Spot reclamation
adds a 2-minute eviction window plus replacement-task startup time.
For latency-sensitive workloads (photographer waiting on a render):

```diff
  capacity_provider_strategies=[
      ecs.CapacityProviderStrategy(
          capacity_provider="FARGATE_SPOT",
-         weight=1,
+         weight=4,
+     ),
+     ecs.CapacityProviderStrategy(
+         capacity_provider="FARGATE",
+         weight=1,
+         base=1,  # always keep at least one on-demand task
      ),
  ],
```

This guarantees one always-on on-demand task while still capturing
~55% of the Spot discount on incremental capacity.

### 9. Restore Secrets Manager interface endpoint (only if needed)

**File:** `infra/stacks/network.py`

Currently removed. Only re-add if Secrets Manager API call volume
becomes high enough to justify the ~$14/mo two-AZ endpoint cost.
Unlikely with the current architecture (secrets read once at task
startup).

### 10. Raise the AWS Budget ceiling

**File:** `infra/stacks/monitoring.py`

Budget is set to **$150/mo** which assumes the pre-launch footprint.
After scaling up RDS, Redis, and ECS tasks, expect the floor to land
closer to **$300-450/mo**. Update:

```diff
- amount=150,
+ amount=500,  # or whatever production baseline lands at
```

---

## Safety net (already in place — do NOT remove)

These are protective and already configured correctly:

- `deletion_protection=True` on RDS
- `removal_policy=SNAPSHOT` on RDS
- `versioned=True` on the S3 media bucket (with lifecycle policy
  bounding noncurrent-version cost)
- `block_public_access=BlockPublicAccess.BLOCK_ALL` on the media bucket
- S3 lifecycle: abort incomplete multipart uploads after 7 days
- All log groups have retention configured (no unbounded log storage)

---

## Pre-launch deploy checklist

1. **Take a manual RDS snapshot** before any database stack change:
   ```
   aws rds create-db-snapshot \
     --db-instance-identifier <id> \
     --db-snapshot-identifier pre-launch-resize-$(date +%Y%m%d)
   ```
2. Apply items 1-7 above in a single `cdk diff` / `cdk deploy` window
   during low traffic.
3. Confirm Container Insights begins reporting in CloudWatch.
4. Wait 7-14 days, then check **AWS Compute Optimizer** for the
   `listingjet-worker` and `listingjet-api` ECS services. Apply any
   recommended sizing.
5. Update item 10 (budget ceiling) to match the new baseline.

---

## Reference — current pre-launch monthly cost

Approximate `us-east-1` spend with the current configuration:

| Component | ~Monthly |
|---|---|
| NAT Gateway (1) | $32 |
| Application Load Balancer | $16 |
| RDS t4g.micro single-AZ + 20 GB gp3 | $13 |
| Redis cache.t4g.micro | $11 |
| ECS Fargate API (0.5 / 1, 24×7) | $8 |
| ECS Fargate Temporal (0.5 / 1, 24×7) | $8 |
| ECS Fargate Spot Worker (1 / 2, 24×7) | $5 |
| CloudFront / S3 / CloudWatch / ECR | $5-10 |
| **Total** | **~$98-103** |

Post-launch with items 1-7 reverted (Multi-AZ on, larger tasks,
2-node Redis): expect **~$300-450/mo** as the floor before traffic
costs.

---

## Appendix — Data to collect from AWS before the next optimization pass

Wait at least **7 days** (ideally 14) after deploying the
cost-optimization branch so CloudWatch and Compute Optimizer have
real data. Then run / capture the following and hand it back for the
next round of decisions.

### 1. Cost Explorer breakdown (run in the AWS console)

```
AWS Console → Billing → Cost Explorer
  - Time range: Last 30 days
  - Granularity: Daily
  - Group by: Service
  - Save the resulting table or screenshot
```

Then a second view filtered to the top service (likely EC2-Other,
which is where NAT data transfer hides):

```
  - Filter: Service = "EC2 - Other"
  - Group by: Usage type
```

### 2. Compute Optimizer recommendations (console)

```
AWS Console → Compute Optimizer
  - ECS services tab → grab recommendations for
      listingjet-api, listingjet-worker, listingjet-temporal
  - RDS tab        → grab the Postgres recommendation
```

(Compute Optimizer is free; it auto-enables once Container Insights
is on, but you can also opt in manually.)

### 3. ECS utilization (CLI)

```sh
# Worker — last 7 days, hourly samples
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=listingjet-worker \
               Name=ClusterName,Value=listingjet \
  --start-time $(date -u -d '7 days ago' +%FT%T) \
  --end-time   $(date -u +%FT%T) \
  --period 3600 \
  --statistics Average Maximum

# Repeat with --metric-name MemoryUtilization
# Repeat with ServiceName=listingjet-api
# Repeat with ServiceName=listingjet-temporal
```

### 4. NAT Gateway data volume (CLI)

```sh
aws cloudwatch get-metric-statistics \
  --namespace AWS/NATGateway \
  --metric-name BytesOutToDestination \
  --start-time $(date -u -d '7 days ago' +%FT%T) \
  --end-time   $(date -u +%FT%T) \
  --period 86400 \
  --statistics Sum
```

If average daily egress > **5 GB**, ECR + CloudWatch Logs interface
endpoints (~$14/mo each across 2 AZs) likely pay for themselves.

### 5. S3 bucket size + version count (CLI)

```sh
# Current + noncurrent storage for the media bucket
aws s3api list-objects-v2 \
  --bucket listingjet-media-<account>-<region> \
  --query '[sum(Contents[].Size), length(Contents)]'

aws s3api list-object-versions \
  --bucket listingjet-media-<account>-<region> \
  --query '[sum(Versions[?IsLatest==`false`].Size), length(Versions[?IsLatest==`false`])]'
```

If noncurrent versions are still growing fast, tighten the lifecycle
expiration window.

### 6. CloudWatch Logs ingest by group (CLI)

```sh
aws logs describe-log-groups --query 'logGroups[].[logGroupName, storedBytes]' --output table
```

The biggest entries are the ones to either (a) lower retention
further or (b) reduce log verbosity in the application.

### 7. Enable Cost Optimization Hub (one-time, console)

```
AWS Console → Billing → Cost Optimization Hub → Get started
```

Free; surfaces consolidated Savings Plans, Reserved Instance, and
rightsizing recommendations across the account.

---

Bring the output of items 1-6 (and any Compute Optimizer screenshots)
to the next session and we can apply a second, data-driven
optimization pass.
