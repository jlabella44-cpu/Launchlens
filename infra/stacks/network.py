"""VPC, subnets, NAT Gateway, and security groups."""

from aws_cdk import (
    Stack,
)
from aws_cdk import (
    aws_ec2 as ec2,
)
from constructs import Construct


class NetworkStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.vpc = ec2.Vpc(
            self, "Vpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
            ],
        )

        # S3 Gateway Endpoint (free, reduces NAT costs)
        self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )

        # Secrets Manager Interface Endpoint
        self.vpc.add_interface_endpoint(
            "SecretsManagerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
        )

        # Security group: ALB (public-facing)
        self.alb_sg = ec2.SecurityGroup(
            self, "AlbSg",
            vpc=self.vpc,
            description="ALB - accepts HTTPS from internet",
            allow_all_outbound=True,
        )
        self.alb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443), "HTTPS")
        self.alb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "HTTP redirect")

        # Security group: ECS services
        self.svc_sg = ec2.SecurityGroup(
            self, "SvcSg",
            vpc=self.vpc,
            description="ECS services - accepts traffic from ALB",
            allow_all_outbound=True,
        )
        self.svc_sg.add_ingress_rule(self.alb_sg, ec2.Port.tcp(8000), "ALB to API")

        # Security group: databases
        self.db_sg = ec2.SecurityGroup(
            self, "DbSg",
            vpc=self.vpc,
            description="Databases - accepts from ECS services",
            allow_all_outbound=False,
        )
        self.db_sg.add_ingress_rule(self.svc_sg, ec2.Port.tcp(5432), "ECS to PostgreSQL")
        self.db_sg.add_ingress_rule(self.svc_sg, ec2.Port.tcp(6379), "ECS to Redis")
        self.db_sg.add_ingress_rule(self.svc_sg, ec2.Port.tcp(7233), "ECS to Temporal")
