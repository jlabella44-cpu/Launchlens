"""RDS PostgreSQL and ElastiCache Redis.

⚠️  CDK DRIFT WARNING — encryption migration 2026-04-17 ⚠️

The live RDS instance for this stack is now
`listingjet-postgres-encrypted` (StorageEncrypted=True, restored from an
encrypted snapshot of the old `listingjetdatabase-postgres9dc8bb04-kjyxgeldpfef`
instance, which has been deleted). That migration was done via `aws rds`
CLI, NOT through CDK, so CloudFormation still thinks this stack's `Postgres`
logical resource is the deleted physical instance.

DO NOT run `cdk deploy` on `ListingJetDatabase` until this drift is
reconciled. A normal deploy here would at best fail, at worst recreate a
brand-new empty Postgres on top of the real data.

Reconciliation plan (future session):
1. Rewrite this construct with `removal_policy=RemovalPolicy.RETAIN` and
   remove the `Postgres` resource from the template.
2. `cdk deploy` to release the (now missing) old resource from CFN
   tracking without deleting anything.
3. Re-add `Postgres` with `storage_encrypted=True` and all other
   properties matching the live new instance.
4. `cdk import` to adopt the live new instance under the same logical
   ID — CFN requires every property to match exactly, so expect a few
   retry cycles.

Until then: app runs fine (DATABASE_URL secret already points at the
new instance); Redis + SGs + subnet group in this stack are untouched
and safe to `cdk deploy` individually via `--exclusively` if needed.

See `docs/PRE_LAUNCH_INFRA_CHECKLIST.md` §A for the original runbook.
"""

from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_ec2 as ec2,
)
from aws_cdk import (
    aws_elasticache as elasticache,
)
from aws_cdk import (
    aws_rds as rds,
)
from constructs import Construct


class DatabaseStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc: ec2.IVpc,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Database security group
        self.db_sg = ec2.SecurityGroup(
            self, "DbSg",
            vpc=vpc,
            description="RDS + Redis - accepts from private subnets",
            allow_all_outbound=False,
        )

        # --- RDS PostgreSQL 16 -----------------------------------------------
        self.db_instance = rds.DatabaseInstance(
            self, "Postgres",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16,
            ),
            # Pre-launch sizing: t4g.micro (2 vCPU burstable, 1 GB RAM).
            # Comfortably handles app schema + Temporal state at zero load.
            # Upsize to t4g.small or t4g.medium before real traffic arrives.
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.MICRO,
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[self.db_sg],
            database_name="listingjet",
            credentials=rds.Credentials.from_generated_secret("listingjet"),
            allocated_storage=20,
            max_allocated_storage=50,
            # storage_encrypted: the LIVE instance is now encrypted (see file
            # header). This construct still omits the property because the
            # logical→physical mapping in CFN is stale — adding
            # storage_encrypted=True here without first reconciling state
            # would tell CFN to replace the resource, wiping live data.
            multi_az=False,
            # Pre-launch: 1-day backup retention. PITR window is short, but no
            # production data to protect yet. Restore retention to 7 days
            # before onboarding customers.
            backup_retention=Duration.days(1),
            deletion_protection=True,
            removal_policy=RemovalPolicy.SNAPSHOT,
        )

        # --- ElastiCache Redis 7 ---------------------------------------------
        redis_subnet_group = elasticache.CfnSubnetGroup(
            self, "RedisSubnets",
            description="Redis subnet group",
            subnet_ids=[s.subnet_id for s in vpc.private_subnets],
        )

        redis_sg = ec2.SecurityGroup(
            self, "RedisSg",
            vpc=vpc,
            description="Redis - accepts from private subnets",
            allow_all_outbound=False,
        )

        # Single-node Redis. Used for caching, rate limiting, SSE pub/sub, and
        # auth lockout — all features degrade gracefully on outage. A node
        # failure triggers an ElastiCache-managed replacement (~5-15 min) with
        # an empty cache; the API rewarms over the following minutes. Switch
        # back to a 2-node replication group with automatic_failover_enabled
        # if Redis becomes load-bearing for durable state.
        # Pre-launch sizing: cache.t4g.micro (2 vCPU burstable, ~0.5 GB RAM).
        # Plenty for cache + rate-limit counters + SSE pub/sub at zero load.
        # Upsize to cache.t4g.small (or larger) before real traffic.
        self.redis_cluster = elasticache.CfnReplicationGroup(
            self, "RedisRg",
            replication_group_description="ListingJet Redis (single node)",
            cache_node_type="cache.t4g.micro",
            engine="redis",
            engine_version="7.1",
            num_cache_clusters=1,
            automatic_failover_enabled=False,
            cache_subnet_group_name=redis_subnet_group.ref,
            security_group_ids=[redis_sg.security_group_id],
        )

        # Allow ECS services -> RDS and Redis
        for port, desc in [(5432, "PostgreSQL"), (6379, "Redis")]:
            self.db_sg.add_ingress_rule(
                ec2.Peer.ipv4(vpc.vpc_cidr_block),
                ec2.Port.tcp(port),
                f"Private subnets to {desc}",
            )
            redis_sg.add_ingress_rule(
                ec2.Peer.ipv4(vpc.vpc_cidr_block),
                ec2.Port.tcp(port),
                f"Private subnets to {desc}",
            )
