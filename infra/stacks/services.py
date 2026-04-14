"""ECS Fargate cluster, task definitions, ALB, ECR repositories, and S3 media bucket."""

from aws_cdk import (
    Duration,
    Stack,
)
from aws_cdk import (
    aws_certificatemanager as acm,
)
from aws_cdk import (
    aws_ec2 as ec2,
)
from aws_cdk import (
    aws_ecr as ecr,
)
from aws_cdk import (
    aws_ecs as ecs,
)
from aws_cdk import (
    aws_ecs_patterns as ecs_patterns,
)
from aws_cdk import (
    aws_elasticache as elasticache,
)
from aws_cdk import (
    aws_elasticloadbalancingv2 as elbv2,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_logs as logs,
)
from aws_cdk import (
    aws_rds as rds,
)
from aws_cdk import (
    aws_s3 as s3,
)
from aws_cdk import (
    aws_secretsmanager as sm,
)
from constructs import Construct


class ServicesStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc: ec2.IVpc,
        db_instance: rds.DatabaseInstance,
        redis_cluster: elasticache.CfnReplicationGroup,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # ECR repositories
        self.api_repo = ecr.Repository(
            self, "ApiRepo",
            repository_name="listingjet-api",
            lifecycle_rules=[ecr.LifecycleRule(max_image_count=20)],
        )
        self.worker_repo = ecr.Repository(
            self, "WorkerRepo",
            repository_name="listingjet-worker",
            lifecycle_rules=[ecr.LifecycleRule(max_image_count=20)],
        )

        # ECS cluster with CloudMap namespace for service discovery
        self.cluster = ecs.Cluster(
            self, "Cluster",
            cluster_name="listingjet",
            vpc=vpc,
            container_insights_v2=ecs.ContainerInsights.ENABLED,
            default_cloud_map_namespace=ecs.CloudMapNamespaceOptions(
                name="listingjet.local",
            ),
        )

        # Shared secrets
        db_secret = db_instance.secret
        app_secrets = sm.Secret.from_secret_name_v2(
            self, "AppSecrets", "listingjet/app",
        )

        # Common environment variables
        base_env = {
            "APP_ENV": "production",
            "ENVIRONMENT": "production",
            "AWS_REGION": Stack.of(self).region,
            "REDIS_URL": f"redis://{redis_cluster.attr_primary_end_point_address}:{redis_cluster.attr_primary_end_point_port}/0",
            "CORS_ORIGINS": "http://localhost:3000,https://listingjet.ai,https://www.listingjet.ai",
            "TEMPORAL_HOST": "temporal.listingjet.local:7233",
            "S3_BUCKET_NAME": "listingjet-dev",
        }

        # --- API Service (Fargate + ALB) ------------------------------------
        api_task = ecs.FargateTaskDefinition(
            self, "ApiTask",
            cpu=1024,
            memory_limit_mib=2048,
        )

        api_container = api_task.add_container(
            "api",
            image=ecs.ContainerImage.from_ecr_repository(self.api_repo, tag="latest"),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="api",
                log_group=logs.LogGroup(
                    self, "ApiLogs",
                    log_group_name="/launchlens/api",
                    retention=logs.RetentionDays.ONE_MONTH,
                ),
            ),
            environment=base_env,
            secrets={
                "DATABASE_URL": ecs.Secret.from_secrets_manager(app_secrets, "DATABASE_URL"),
                "JWT_SECRET": ecs.Secret.from_secrets_manager(app_secrets, "JWT_SECRET"),
                "STRIPE_SECRET_KEY": ecs.Secret.from_secrets_manager(app_secrets, "STRIPE_SECRET_KEY"),
                "STRIPE_WEBHOOK_SECRET": ecs.Secret.from_secrets_manager(app_secrets, "STRIPE_WEBHOOK_SECRET"),
                "STRIPE_PRICE_LITE": ecs.Secret.from_secrets_manager(app_secrets, "STRIPE_PRICE_LITE"),
                "STRIPE_PRICE_ACTIVE_AGENT": ecs.Secret.from_secrets_manager(app_secrets, "STRIPE_PRICE_ACTIVE_AGENT"),
                "STRIPE_PRICE_TEAM": ecs.Secret.from_secrets_manager(app_secrets, "STRIPE_PRICE_TEAM"),
                "SENTRY_DSN": ecs.Secret.from_secrets_manager(app_secrets, "SENTRY_DSN"),
                "OPENAI_API_KEY": ecs.Secret.from_secrets_manager(app_secrets, "OPENAI_API_KEY"),
                "ANTHROPIC_API_KEY": ecs.Secret.from_secrets_manager(app_secrets, "ANTHROPIC_API_KEY"),
                "GOOGLE_VISION_API_KEY": ecs.Secret.from_secrets_manager(app_secrets, "GOOGLE_VISION_API_KEY"),
            },
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
            ),
            command=["api"],
        )
        api_container.add_port_mappings(ecs.PortMapping(container_port=8000))

        self.api_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "ApiService",
            cluster=self.cluster,
            task_definition=api_task,
            desired_count=1,
            listener_port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            assign_public_ip=False,
            service_name="listingjet-api",
        )

        self.api_service.target_group.configure_health_check(
            path="/health",
            healthy_http_codes="200",
            interval=Duration.seconds(30),
            timeout=Duration.seconds(5),
        )

        self.alb = self.api_service.load_balancer

        # --- HTTPS on ALB (optional, requires domain_name context) -----------
        domain_name = self.node.try_get_context("domain_name")
        if domain_name:
            certificate = acm.Certificate(
                self, "ApiCertificate",
                domain_name=domain_name,
                validation=acm.CertificateValidation.from_dns(),
            )

            # Add HTTPS listener forwarding to the existing target group
            self.alb.add_listener(
                "HttpsListener",
                port=443,
                protocol=elbv2.ApplicationProtocol.HTTPS,
                certificates=[certificate],
                default_target_groups=[self.api_service.target_group],
            )

            # Redirect HTTP → HTTPS on the existing port-80 listener
            self.api_service.listener.add_action(
                "HttpRedirect",
                action=elbv2.ListenerAction.redirect(
                    protocol="HTTPS",
                    port="443",
                    permanent=True,
                ),
            )

        # Auto-scaling for API service
        api_scaling = self.api_service.service.auto_scale_task_count(
            min_capacity=1,
            max_capacity=4,
        )
        api_scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=70,
            scale_in_cooldown=Duration.seconds(300),
            scale_out_cooldown=Duration.seconds(60),
        )

        # --- S3 media bucket -------------------------------------------------
        self.media_bucket = s3.Bucket(
            self, "MediaBucket",
            bucket_name=f"listingjet-media-{Stack.of(self).account}-{Stack.of(self).region}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
        )

        # --- IAM: Grant S3 + CloudWatch to API and Worker task roles ----------
        s3_bucket_arn = "arn:aws:s3:::listingjet-dev"
        s3_policy = iam.PolicyStatement(
            actions=["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
            resources=[f"{s3_bucket_arn}/*"],
        )
        s3_list_policy = iam.PolicyStatement(
            actions=["s3:ListBucket"],
            resources=[s3_bucket_arn],
        )
        cloudwatch_policy = iam.PolicyStatement(
            actions=["cloudwatch:PutMetricData"],
            resources=["*"],
        )

        api_task.task_role.add_to_policy(s3_policy)
        api_task.task_role.add_to_policy(s3_list_policy)
        api_task.task_role.add_to_policy(cloudwatch_policy)

        # --- Worker Service (Fargate, no ALB) --------------------------------
        worker_task = ecs.FargateTaskDefinition(
            self, "WorkerTask",
            cpu=2048,
            memory_limit_mib=4096,
        )

        worker_task.add_container(
            "worker",
            image=ecs.ContainerImage.from_ecr_repository(self.worker_repo, tag="latest"),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="worker",
                log_group=logs.LogGroup(
                    self, "WorkerLogs",
                    log_group_name="/launchlens/worker",
                    retention=logs.RetentionDays.ONE_MONTH,
                ),
            ),
            environment=base_env,
            secrets={
                "DATABASE_URL": ecs.Secret.from_secrets_manager(app_secrets, "DATABASE_URL"),
                "JWT_SECRET": ecs.Secret.from_secrets_manager(app_secrets, "JWT_SECRET"),
                "SENTRY_DSN": ecs.Secret.from_secrets_manager(app_secrets, "SENTRY_DSN"),
                "OPENAI_API_KEY": ecs.Secret.from_secrets_manager(app_secrets, "OPENAI_API_KEY"),
                "ANTHROPIC_API_KEY": ecs.Secret.from_secrets_manager(app_secrets, "ANTHROPIC_API_KEY"),
                "GOOGLE_VISION_API_KEY": ecs.Secret.from_secrets_manager(app_secrets, "GOOGLE_VISION_API_KEY"),
                "KLING_ACCESS_KEY": ecs.Secret.from_secrets_manager(app_secrets, "KLING_ACCESS_KEY"),
                "KLING_SECRET_KEY": ecs.Secret.from_secrets_manager(app_secrets, "KLING_SECRET_KEY"),
            },
            command=["worker"],
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8081/health')\" || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
                start_period=Duration.seconds(30),
            ),
        )

        worker_task.task_role.add_to_policy(s3_policy)
        worker_task.task_role.add_to_policy(s3_list_policy)
        worker_task.task_role.add_to_policy(cloudwatch_policy)

        self.worker_service = ecs.FargateService(
            self, "WorkerService",
            cluster=self.cluster,
            task_definition=worker_task,
            desired_count=1,
            service_name="listingjet-worker",
            assign_public_ip=False,
        )

        # --- Temporal Service (Fargate, internal only) -----------------------
        temporal_task = ecs.FargateTaskDefinition(
            self, "TemporalTask",
            cpu=512,
            memory_limit_mib=1024,
        )

        temporal_task.add_container(
            "temporal",
            image=ecs.ContainerImage.from_registry("temporalio/auto-setup:latest"),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="temporal",
                log_group=logs.LogGroup(
                    self, "TemporalLogs",
                    log_group_name="/launchlens/temporal",
                    retention=logs.RetentionDays.ONE_MONTH,
                ),
            ),
            environment={
                "DB": "postgresql",
                "DB_PORT": "5432",
                "POSTGRES_SEEDS": db_instance.db_instance_endpoint_address,
            },
            secrets={
                "POSTGRES_USER": ecs.Secret.from_secrets_manager(db_secret, "username"),
                "POSTGRES_PWD": ecs.Secret.from_secrets_manager(db_secret, "password"),
            },
        )
        temporal_task.default_container.add_port_mappings(
            ecs.PortMapping(container_port=7233),
        )

        self.temporal_service = ecs.FargateService(
            self, "TemporalService",
            cluster=self.cluster,
            task_definition=temporal_task,
            desired_count=1,
            service_name="listingjet-temporal",
            assign_public_ip=False,
            cloud_map_options=ecs.CloudMapOptions(name="temporal"),
        )
