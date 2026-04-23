"""RDS PostgreSQL and ElastiCache Redis.

⚠️  CDK RECONCILIATION — encryption migration, zombie-resource path (2026-04-23) ⚠️

History: the live RDS instance for this stack is
`listingjet-postgres-encrypted` (StorageEncrypted=True, restored
2026-04-17 from an encrypted snapshot of the old
`listingjetdatabase-postgres9dc8bb04-kjyxgeldpfef` instance, which has
been deleted). That migration was done via `aws rds` CLI, NOT CDK, so
CloudFormation's `Postgres` logical id (Postgres9DC8BB04) points at a
physical resource that returns 404 on any describe.

Reconciliation attempted 2026-04-23 with the RETAIN-flip → remove →
re-add → import plan. RETAIN flip failed: CFN's v2 RDS resource
provider calls `describe-db-instances` on any logical-resource update
(including pure metadata changes like DeletionPolicy) and the 404 is
terminal. Remove-and-recreate would have the same failure mode during
the implicit DELETE.

Pivoted to the zombie-resource path:
- The original `Postgres` construct below is LEFT UNCHANGED. Its
  synthesized resources (Postgres9DC8BB04, the generated secret, the
  secret attachment) are CFN zombies — present in the template and in
  CFN state, but the underlying AWS resources are gone. Do NOT attempt
  any mutation on them; every mutation will fail.
- A parallel `PostgresEncrypted` construct below adopts the live
  encrypted instance via `cdk import`, reusing the existing (still-alive)
  subnet group + KMS key + secret. Downstream code (services.py,
  monitoring.py) wires off `self.db_instance_encrypted`.
- The subnet group `PostgresSubnetGroup9F8A4D6E` is NOT a zombie: its
  physical resource is alive and in use by the live encrypted
  instance. Leaving the old construct's auto-generated subnet group in
  place keeps the live instance's subnet group tracked correctly.

If you ever need to clean up the zombies: that requires delete-stack
--retain-resources rebuild work, not worth it unless we're consolidating
infra later.
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
    aws_kms as kms,
)
from aws_cdk import (
    aws_rds as rds,
)
from aws_cdk import (
    aws_secretsmanager as sm,
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

        # --- RDS PostgreSQL 16 (ENCRYPTED, zombie-path re-add) ---------------
        # The construct above is a zombie (see file header). The live
        # encrypted instance `listingjet-postgres-encrypted` is adopted
        # here via `cdk import` under a NEW logical id. Exact-match
        # properties against the live instance are required or import
        # fails; values below were verified 2026-04-23 against
        # `aws rds describe-db-instances --db-instance-identifier
        # listingjet-postgres-encrypted`.
        # NOTE: `rds.Credentials.from_secret()` would implicitly create
        # an AWS::SecretsManager::SecretTargetAttachment — a NEW resource
        # that `cdk import` cannot create alongside the adopted instance
        # (CFN import only adopts existing resources). Using
        # `from_password` with a dynamic secret reference avoids the
        # attachment entirely; the live secret already has the correct
        # host/port from the restore, so no attachment is needed.

        self.db_secret_encrypted = sm.Secret.from_secret_complete_arn(
            self,
            "EncryptedDbSecret",
            (
                "arn:aws:secretsmanager:us-east-1:265911026550:secret:"
                "ListingJetDatabasePostgresS-2g2B0n8yjwAF-DRYvqm"
            ),
        )
        encrypted_db_kms_key = kms.Key.from_key_arn(
            self,
            "EncryptedDbKmsKey",
            (
                "arn:aws:kms:us-east-1:265911026550:key/"
                "1482e415-1d7e-4269-b887-1a25d453cf6b"
            ),
        )
        encrypted_db_subnet_group = rds.SubnetGroup.from_subnet_group_name(
            self,
            "EncryptedDbSubnetGroup",
            "listingjetdatabase-postgressubnetgroup9f8a4d6e-ixyvwsoprif1",
        )
        self.db_instance_encrypted = rds.DatabaseInstance(
            self,
            "PostgresEncrypted",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16_10,
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON,
                ec2.InstanceSize.MICRO,
            ),
            vpc=vpc,
            subnet_group=encrypted_db_subnet_group,
            security_groups=[self.db_sg],
            database_name="listingjet",
            credentials=rds.Credentials.from_password(
                "listingjet",
                self.db_secret_encrypted.secret_value_from_json("password"),
            ),
            allocated_storage=20,
            storage_type=rds.StorageType.GP2,
            storage_encrypted=True,
            storage_encryption_key=encrypted_db_kms_key,
            parameter_group=rds.ParameterGroup.from_parameter_group_name(
                self,
                "EncryptedDbParamGroup",
                "listingjet-pg16",
            ),
            multi_az=False,
            backup_retention=Duration.days(1),
            deletion_protection=True,
            removal_policy=RemovalPolicy.RETAIN,
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
