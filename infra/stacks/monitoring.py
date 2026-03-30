"""CloudWatch dashboard, alarms, and SNS alerting."""

from aws_cdk import (
    Duration,
    Stack,
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as cw_actions,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_rds as rds,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
)
from constructs import Construct


class MonitoringStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        cluster: ecs.ICluster,
        api_service,
        alb: elbv2.IApplicationLoadBalancer,
        db_instance: rds.DatabaseInstance,
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
            metric=db_instance.metric_free_storage_space(),
            threshold=4 * 1024 * 1024 * 1024,  # 4 GB
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.LESS_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="RDS free storage below 4 GB",
        )
        storage_alarm.add_alarm_action(alarm_action)

        # --- RDS CPU High -----------------------------------------------------
        cpu_alarm = cw.Alarm(
            self, "RdsCpuHigh",
            metric=db_instance.metric_cpu_utilization(),
            threshold=80,
            evaluation_periods=2,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
            alarm_description="RDS CPU utilization above 80% for 10 minutes",
        )
        cpu_alarm.add_alarm_action(alarm_action)

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
                        left=[db_instance.metric_cpu_utilization()],
                        right=[db_instance.metric_free_storage_space()],
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
