"""IAM role for GitHub Actions OIDC - allows CI/CD to push to ECR and deploy to ECS."""

from aws_cdk import (
    Stack,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_iam as iam,
)
from constructs import Construct


class CIStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        api_repo: ecr.IRepository,
        cluster: ecs.ICluster,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # GitHub OIDC provider (create once per account)
        gh_provider = iam.OpenIdConnectProvider(
            self, "GithubOidc",
            url="https://token.actions.githubusercontent.com",
            client_ids=["sts.amazonaws.com"],
        )

        # IAM role for GitHub Actions
        self.deploy_role = iam.Role(
            self, "DeployRole",
            role_name="listingjet-github-deploy",
            assumed_by=iam.WebIdentityPrincipal(
                gh_provider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                    },
                    "StringLike": {
                        "token.actions.githubusercontent.com:sub": "repo:jlabella44-cpu/Launchlens:*",
                    },
                },
            ),
        )

        # ECR push permissions
        api_repo.grant_pull_push(self.deploy_role)

        # ECS deploy permissions
        self.deploy_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ecs:UpdateService",
                    "ecs:DescribeServices",
                    "ecs:DescribeTaskDefinition",
                    "ecs:RegisterTaskDefinition",
                    "ecs:RunTask",
                    "ecs:DescribeTasks",
                    "ecs:ListTasks",
                ],
                resources=["*"],
                conditions={
                    "StringEquals": {
                        "ecs:cluster": cluster.cluster_arn,
                    },
                },
            )
        )

        # Pass role for task execution
        self.deploy_role.add_to_policy(
            iam.PolicyStatement(
                actions=["iam:PassRole"],
                resources=["*"],
                conditions={
                    "StringLike": {
                        "iam:PassedToService": "ecs-tasks.amazonaws.com",
                    },
                },
            )
        )
