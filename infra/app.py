#!/usr/bin/env python3
"""LaunchLens CDK application — instantiates all infrastructure stacks."""

import aws_cdk as cdk

from stacks.network import NetworkStack
from stacks.database import DatabaseStack
from stacks.services import ServicesStack
from stacks.monitoring import MonitoringStack
from stacks.ci import CIStack

app = cdk.App()

env = cdk.Environment(
    account=app.node.try_get_context("account") or cdk.Aws.ACCOUNT_ID,
    region=app.node.try_get_context("region") or "us-east-1",
)

alert_email = app.node.try_get_context("alert_email") or "ops@launchlens.com"

network = NetworkStack(app, "LaunchLensNetwork", env=env)

database = DatabaseStack(
    app, "LaunchLensDatabase",
    vpc=network.vpc,
    env=env,
)

services = ServicesStack(
    app, "LaunchLensServices",
    vpc=network.vpc,
    db_instance=database.db_instance,
    redis_cluster=database.redis_cluster,
    env=env,
)

monitoring = MonitoringStack(
    app, "LaunchLensMonitoring",
    cluster=services.cluster,
    api_service=services.api_service,
    alb=services.alb,
    db_instance=database.db_instance,
    alert_email=alert_email,
    env=env,
)

ci = CIStack(
    app, "LaunchLensCI",
    api_repo=services.api_repo,
    cluster=services.cluster,
    env=env,
)

app.synth()
