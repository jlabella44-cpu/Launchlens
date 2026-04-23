#!/usr/bin/env python3
"""ListingJet CDK application — instantiates all infrastructure stacks."""

import aws_cdk as cdk
from stacks.ci import CIStack
from stacks.database import DatabaseStack
from stacks.monitoring import MonitoringStack
from stacks.network import NetworkStack
from stacks.services import ServicesStack

app = cdk.App()

env = cdk.Environment(
    account=app.node.try_get_context("account") or cdk.Aws.ACCOUNT_ID,
    region=app.node.try_get_context("region") or "us-east-1",
)

alert_email = app.node.try_get_context("alert_email") or "ops@listingjet.com"

network = NetworkStack(app, "ListingJetNetwork", env=env)

database = DatabaseStack(
    app, "ListingJetDatabase",
    vpc=network.vpc,
    env=env,
)

services = ServicesStack(
    app, "ListingJetServices",
    vpc=network.vpc,
    redis_cluster=database.redis_cluster,
    env=env,
)

monitoring = MonitoringStack(
    app, "ListingJetMonitoring",
    cluster=services.cluster,
    api_service=services.api_service,
    alb=services.alb,
    alert_email=alert_email,
    env=env,
)

ci = CIStack(
    app, "ListingJetCI",
    api_repo=services.api_repo,
    worker_repo=services.worker_repo,
    cluster=services.cluster,
    env=env,
)

app.synth()
