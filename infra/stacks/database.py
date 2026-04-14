"""RDS PostgreSQL and ElastiCache Redis."""

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
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.SMALL,
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[self.db_sg],
            database_name="listingjet",
            credentials=rds.Credentials.from_generated_secret("listingjet"),
            allocated_storage=20,
            max_allocated_storage=50,
            storage_encrypted=True,
            multi_az=True,
            backup_retention=Duration.days(7),
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

        self.redis_cluster = elasticache.CfnReplicationGroup(
            self, "RedisRg",
            replication_group_description="ListingJet Redis replication group",
            cache_node_type="cache.t4g.small",
            engine="redis",
            engine_version="7.1",
            num_cache_clusters=2,
            automatic_failover_enabled=True,
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
