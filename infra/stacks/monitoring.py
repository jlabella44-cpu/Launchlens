"""CloudWatch dashboard, alarms, and SNS alerting."""

from aws_cdk import (
    Duration,
    Stack,
)
from aws_cdk import (
    aws_budgets as budgets,
)
from aws_cdk import (
    aws_cloudwatch as cw,
)
from aws_cdk import (
    aws_cloudwatch_actions as cw_actions,
)
from aws_cdk import (
    aws_ecs as ecs,
)
from aws_cdk import (
    aws_elasticloadbalancingv2 as elbv2,
)
from aws_cdk import (
    aws_sns as sns,
)
from aws_cdk import (
    aws_sns_subscriptions as subs,
)
from constructs import Construct

# ⚠️ TEMPORARY — removed in Phase 6 of RDS reconciliation.
# See docs/plans/2026-04-21-cdk-rds-encryption-reconciliation.md.
# While `DatabaseStack.db_instance` tracks a deleted physical resource,
# alarms and dashboards build CloudWatch metrics by DBInstanceIdentifier
# directly against the live encrypted instance.
_DB_INSTANCE_ID = "listingjet-postgres-encrypted"


def _rds_metric(metric_name: str) -> cw.Metric:
    """Build an AWS/RDS metric pinned to the live encrypted instance."""
    return cw.Metric(
        namespace="AWS/RDS",
        metric_name=metric_name,
        dimensions_map={"DBInstanceIdentifier": _DB_INSTANCE_ID},
        statistic="Average",
        period=Duration.minutes(5),
    )


class MonitoringStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        cluster: ecs.ICluster,
        api_service,
        alb: elbv2.IApplicationLoadBalancer,
        alert_email: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # SNS topic for all alerts
        self.alert_topic = sns.Topic(
            self, "AlertTopic",
            topic_name="listingjet-alerts",
        )
        self.alert_topic.add_subscription(subs.EmailSubscription(alert_email))
        alarm_action = cw_actions.SnsAction(self.alert_topic)

        # --- ALB Health -------------------------------------------------------
        unhealthy_alarm = cw.Alarm(
            self, "ApiUnhealthy",
            metric=cw.Metric(
                namespace="AWS/ApplicationELB",
                metric_name="UnHealthyHostCount",
                dimensions_map={
                    "LoadBalancer": alb.load_balancer_full_name,
                    "TargetGroup": api_service.target_group.target_group_full_name,
                },
                statistic="Maximum",
                period=Duration.minutes(1),
            ),
            threshold=1,
            evaluation_periods=2,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="API target group has unhealthy hosts",
        )
        unhealthy_alarm.add_alarm_action(alarm_action)

        # --- High Error Rate --------------------------------------------------
        error_rate_alarm = cw.Alarm(
            self, "HighErrorRate",
            metric=cw.MathExpression(
                expression="errors / requests * 100",
                using_metrics={
                    "errors": cw.Metric(
                        namespace="ListingJet",
                        metric_name="ErrorCount",
                        statistic="Sum",
                        period=Duration.minutes(5),
                    ),
                    "requests": cw.Metric(
                        namespace="ListingJet",
                        metric_name="RequestCount",
                        statistic="Sum",
                        period=Duration.minutes(5),
                    ),
                },
            ),
            threshold=5,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
            alarm_description="Error rate exceeds 5% over 5 minutes",
        )
        error_rate_alarm.add_alarm_action(alarm_action)

        # --- High Latency (p95) -----------------------------------------------
        latency_alarm = cw.Alarm(
            self, "HighLatency",
            metric=cw.Metric(
                namespace="ListingJet",
                metric_name="RequestLatency",
                statistic="p95",
                period=Duration.minutes(5),
            ),
            threshold=5000,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
            alarm_description="p95 request latency exceeds 5000ms",
        )
        latency_alarm.add_alarm_action(alarm_action)

        # --- RDS Storage Low --------------------------------------------------
        storage_alarm = cw.Alarm(
            self, "RdsStorageLow",
            metric=_rds_metric("FreeStorageSpace"),
            threshold=4 * 1024 * 1024 * 1024,  # 4 GB
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.LESS_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="RDS free storage below 4 GB",
        )
        storage_alarm.add_alarm_action(alarm_action)

        # --- RDS CPU High -----------------------------------------------------
        cpu_alarm = cw.Alarm(
            self, "RdsCpuHigh",
            metric=_rds_metric("CPUUtilization"),
            threshold=80,
            evaluation_periods=2,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
            alarm_description="RDS CPU utilization above 80% for 10 minutes",
        )
        cpu_alarm.add_alarm_action(alarm_action)

        # --- AWS Budget: monthly cost ceiling --------------------------------
        # Sends an email at 80% actual, 100% actual, and 100% forecasted.
        # Limit is intentionally conservative for the pre-launch footprint
        # (~$100/mo expected). Raise once real users start driving spend.
        budgets.CfnBudget(
            self, "MonthlyCostBudget",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_name="listingjet-monthly",
                budget_type="COST",
                time_unit="MONTHLY",
                budget_limit=budgets.CfnBudget.SpendProperty(
                    amount=150,
                    unit="USD",
                ),
            ),
            notifications_with_subscribers=[
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        notification_type="ACTUAL",
                        comparison_operator="GREATER_THAN",
                        threshold=80,
                        threshold_type="PERCENTAGE",
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type="EMAIL",
                            address=alert_email,
                        ),
                    ],
                ),
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        notification_type="ACTUAL",
                        comparison_operator="GREATER_THAN",
                        threshold=100,
                        threshold_type="PERCENTAGE",
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type="EMAIL",
                            address=alert_email,
                        ),
                    ],
                ),
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        notification_type="FORECASTED",
                        comparison_operator="GREATER_THAN",
                        threshold=100,
                        threshold_type="PERCENTAGE",
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type="EMAIL",
                            address=alert_email,
                        ),
                    ],
                ),
            ],
        )

        # --- CloudWatch Dashboard ---------------------------------------------
        self.dashboard = cw.Dashboard(
            self, "Dashboard",
            dashboard_name="ListingJet",
            widgets=[
                [
                    cw.GraphWidget(
                        title="Request Latency (p50 / p95 / p99)",
                        left=[
                            cw.Metric(namespace="ListingJet", metric_name="RequestLatency", statistic="p50"),
                            cw.Metric(namespace="ListingJet", metric_name="RequestLatency", statistic="p95"),
                            cw.Metric(namespace="ListingJet", metric_name="RequestLatency", statistic="p99"),
                        ],
                        width=12,
                    ),
                    cw.GraphWidget(
                        title="Requests & Errors",
                        left=[cw.Metric(namespace="ListingJet", metric_name="RequestCount", statistic="Sum")],
                        right=[cw.Metric(namespace="ListingJet", metric_name="ErrorCount", statistic="Sum")],
                        width=12,
                    ),
                ],
                [
                    cw.GraphWidget(
                        title="RDS CPU / Storage",
                        left=[_rds_metric("CPUUtilization")],
                        right=[_rds_metric("FreeStorageSpace")],
                        width=12,
                    ),
                    cw.GraphWidget(
                        title="Pipeline Stage Duration",
                        left=[
                            cw.Metric(
                                namespace="ListingJet",
                                metric_name="PipelineStageDuration",
                                dimensions_map={"stage": stage},
                                statistic="Average",
                            )
                            for stage in [
                                "ingestion", "vision", "coverage", "packaging",
                                "content", "brand", "social", "mls_export", "distribution",
                            ]
                        ],
                        width=12,
                    ),
                ],
            ],
        )
