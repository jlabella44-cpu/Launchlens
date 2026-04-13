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
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # ECR repositories
        # Keep last 10 images — sufficient for rollbacks; reduces ECR storage cost.
        self.api_repo = ecr.Repository(
            self, "ApiRepo",
            repository_name="listingjet-api",
            lifecycle_rules=[ecr.LifecycleRule(max_image_count=10)],
        )
        self.worker_repo = ecr.Repository(
            self, "WorkerRepo",
            repository_name="listingjet-worker",
            lifecycle_rules=[ecr.LifecycleRule(max_image_count=10)],
        )

        # ECS cluster with CloudMap namespace for service discovery.
        # FARGATE and FARGATE_SPOT capacity providers are registered so that
        # individual services can opt into Spot pricing (~70% off) where the
        # workload tolerates 2-minute eviction notices. The API and Temporal
        # services keep the FARGATE default; only the Worker uses Spot.
        # Container Insights v2 disabled pre-launch to skip the per-task
        # observability cost. Re-enable before onboarding paying customers.
        self.cluster = ecs.Cluster(
            self, "Cluster",
            cluster_name="listingjet",
            vpc=vpc,
            container_insights_v2=ecs.ContainerInsights.DISABLED,
            default_cloud_map_namespace=ecs.CloudMapNamespaceOptions(
                name="listingjet.local",
            ),
            enable_fargate_capacity_providers=True,
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
            # TEMPORARY: hardcoded to the currently-deployed Redis CacheCluster
            # endpoint so Services stops importing the Redis export from
            # Database, allowing Database to rename Redis -> RedisRg without a
            # circular-export deadlock. A follow-up PR restores this to
            # `redis_cluster.attr_primary_end_point_address` once RedisRg
            # exists and is ready to be consumed.
            "REDIS_URL": "redis://lis-re-10delv4c2sqbw.fjbwkc.0001.use1.cache.amazonaws.com:6379/0",
            "CORS_ORIGINS": "http://localhost:3000,https://listingjet.ai,https://www.listingjet.ai",
            "TEMPORAL_HOST": "temporal.listingjet.local:7233",
            "S3_BUCKET_NAME": "listingjet-dev",
        }

        # --- API Service (Fargate + ALB) ------------------------------------
        # Pre-launch sizing: 0.5 vCPU / 1 GB. FastAPI + uvicorn idles below
        # 100 MB; this gives headroom for dev/QA traffic. Bump back to
        # 1 vCPU / 2 GB before opening to real users (auto-scaling already
        # caps at 4 tasks).
        api_task = ecs.FargateTaskDefinition(
            self, "ApiTask",
            cpu=512,
            memory_limit_mib=1024,
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
                "CANVA_CLIENT_ID": ecs.Secret.from_secrets_manager(app_secrets, "CANVA_CLIENT_ID"),
                "CANVA_CLIENT_SECRET": ecs.Secret.from_secrets_manager(app_secrets, "CANVA_CLIENT_SECRET"),
                "CANVA_DEFAULT_TEMPLATE_ID": ecs.Secret.from_secrets_manager(app_secrets, "CANVA_DEFAULT_TEMPLATE_ID"),
                "ATTOM_API_KEY": ecs.Secret.from_secrets_manager(app_secrets, "ATTOM_API_KEY"),
                "QWEN_API_KEY": ecs.Secret.from_secrets_manager(app_secrets, "QWEN_API_KEY"),
                "VISION_PROVIDER_TIER2": ecs.Secret.from_secrets_manager(app_secrets, "VISION_PROVIDER_TIER2"),
                "SMTP_PASSWORD": ecs.Secret.from_secrets_manager(app_secrets, "SMTP_PASSWORD"),
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
        # Lifecycle rules:
        #   * Abort incomplete multipart uploads after 7 days (uploads abandoned
        #     mid-flight otherwise accrue storage indefinitely).
        #   * Transition noncurrent versions to STANDARD_IA after 30 days, then
        #     expire them after 90 days. Current versions are never expired.
        self.media_bucket = s3.Bucket(
            self, "MediaBucket",
            bucket_name=f"listingjet-media-{Stack.of(self).account}-{Stack.of(self).region}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="AbortIncompleteMultipartUploads",
                    abort_incomplete_multipart_upload_after=Duration.days(7),
                ),
                s3.LifecycleRule(
                    id="ExpireNoncurrentVersions",
                    noncurrent_version_transitions=[
                        s3.NoncurrentVersionTransition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30),
                        ),
                    ],
                    noncurrent_version_expiration=Duration.days(90),
                ),
            ],
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
        # Pre-launch sizing: 1 vCPU / 2 GB. Sufficient for ad-hoc test
        # pipelines (vision, packaging, single-clip Kling renders). FFmpeg
        # video stitching for full virtual tours wants more — bump back to
        # 2 vCPU / 4 GB (or higher) before users start pushing real workloads,
        # and confirm with Compute Optimizer once we have a few weeks of data.
        worker_task = ecs.FargateTaskDefinition(
            self, "WorkerTask",
            cpu=1024,
            memory_limit_mib=2048,
        )

        worker_task.add_container(
            "worker",
            image=ecs.ContainerImage.from_ecr_repository(self.worker_repo, tag="latest"),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="worker",
                log_group=logs.LogGroup(
                    self, "WorkerLogs",
                    log_group_name="/launchlens/worker",
                    retention=logs.RetentionDays.TWO_WEEKS,
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
                "CANVA_CLIENT_ID": ecs.Secret.from_secrets_manager(app_secrets, "CANVA_CLIENT_ID"),
                "CANVA_CLIENT_SECRET": ecs.Secret.from_secrets_manager(app_secrets, "CANVA_CLIENT_SECRET"),
                "CANVA_DEFAULT_TEMPLATE_ID": ecs.Secret.from_secrets_manager(app_secrets, "CANVA_DEFAULT_TEMPLATE_ID"),
                "ATTOM_API_KEY": ecs.Secret.from_secrets_manager(app_secrets, "ATTOM_API_KEY"),
                "QWEN_API_KEY": ecs.Secret.from_secrets_manager(app_secrets, "QWEN_API_KEY"),
                "VISION_PROVIDER_TIER2": ecs.Secret.from_secrets_manager(app_secrets, "VISION_PROVIDER_TIER2"),
                "SMTP_PASSWORD": ecs.Secret.from_secrets_manager(app_secrets, "SMTP_PASSWORD"),
            },
            command=["worker"],
            # The worker doesn't serve HTTP — it touches /tmp/worker-heartbeat
            # every 15s (src/listingjet/workflows/worker.py). A hung worker
            # stops touching it; this check fails after ~2 min of no updates.
            health_check=ecs.HealthCheck(
                command=[
                    "CMD-SHELL",
                    "find /tmp/worker-heartbeat -mmin -2 | grep -q . || exit 1",
                ],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
                # Worker needs time to connect to Temporal + write first heartbeat.
                start_period=Duration.seconds(60),
            ),
        )

        worker_task.task_role.add_to_policy(s3_policy)
        worker_task.task_role.add_to_policy(s3_list_policy)
        worker_task.task_role.add_to_policy(cloudwatch_policy)

        # Worker runs Temporal activities, which are inherently retry-safe:
        # if a Spot reclamation interrupts an activity, Temporal reschedules it
        # on the next available worker (potentially redoing one external API
        # call). 100% Spot is acceptable here; switch to a mixed strategy
        # (e.g. weight=4 Spot + weight=1 on-demand) if Spot capacity in
        # us-east-1 ever becomes unreliable for our task size.
        self.worker_service = ecs.FargateService(
            self, "WorkerService",
            cluster=self.cluster,
            task_definition=worker_task,
            desired_count=1,
            service_name="listingjet-worker",
            assign_public_ip=False,
            capacity_provider_strategies=[
                ecs.CapacityProviderStrategy(
                    capacity_provider="FARGATE_SPOT",
                    weight=1,
                ),
            ],
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
                    retention=logs.RetentionDays.TWO_WEEKS,
                ),
            ),
            environment={
                "DB": "postgres12",
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
