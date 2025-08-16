"""
ネットワークスタック - VPC、サブネット、セキュリティグループの定義
"""

import aws_cdk as cdk
from aws_cdk import (
    aws_ec2 as ec2,
    Stack
)
from constructs import Construct
from typing import Dict, Any


class NetworkStack(Stack):
    """ネットワークリソースを管理するスタック"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        project_name: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.environment = environment
        self.project_name = project_name

        # VPCの作成
        self._create_vpc()

        # VPCエンドポイントの作成
        self._create_vpc_endpoints()

        # 出力の設定
        self._create_outputs()

    def _create_vpc(self) -> None:
        """VPCとサブネットの作成"""
        
        # VPC作成
        self.vpc = ec2.Vpc(
            self, "VPC",
            vpc_name=f"{self.project_name}-{self.environment}-vpc",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=2,  # 2つのAZを使用
            subnet_configuration=[
                # パブリックサブネット（ALB用）
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                # プライベートサブネット（アプリケーション用）
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                ),
                # 分離サブネット（データベース用）
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24
                )
            ],
            # NATゲートウェイの設定
            nat_gateways=1,  # コスト最適化のため1つのNATゲートウェイを使用
            enable_dns_hostnames=True,
            enable_dns_support=True
        )

        # VPCにタグを追加
        cdk.Tags.of(self.vpc).add("Name", f"{self.project_name}-{self.environment}-vpc")

    def _create_vpc_endpoints(self) -> None:
        """VPCエンドポイントの作成（AWS サービスへのプライベート接続）"""
        
        # S3用VPCエンドポイント（Gateway型）
        self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
            subnets=[
                ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED)
            ]
        )

        # DynamoDB用VPCエンドポイント（Gateway型）
        self.vpc.add_gateway_endpoint(
            "DynamoDBEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
            subnets=[
                ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED)
            ]
        )

        # セキュリティグループ（VPCエンドポイント用）
        vpc_endpoint_sg = ec2.SecurityGroup(
            self, "VPCEndpointSecurityGroup",
            vpc=self.vpc,
            description="Security group for VPC endpoints",
            security_group_name=f"{self.project_name}-{self.environment}-vpc-endpoint-sg"
        )

        # HTTPS通信を許可
        vpc_endpoint_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS from VPC"
        )

        # Interface型VPCエンドポイント用の共通設定
        interface_endpoint_config = {
            "vpc": self.vpc,
            "security_groups": [vpc_endpoint_sg],
            "subnets": ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            "private_dns_enabled": True
        }

        # SQS用VPCエンドポイント
        self.vpc.add_interface_endpoint(
            "SQSEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SQS,
            **interface_endpoint_config
        )

        # Secrets Manager用VPCエンドポイント
        self.vpc.add_interface_endpoint(
            "SecretsManagerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            **interface_endpoint_config
        )

        # CloudWatch Logs用VPCエンドポイント
        self.vpc.add_interface_endpoint(
            "CloudWatchLogsEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
            **interface_endpoint_config
        )

        # ECR用VPCエンドポイント
        self.vpc.add_interface_endpoint(
            "ECREndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.ECR,
            **interface_endpoint_config
        )

        # ECR Docker用VPCエンドポイント
        self.vpc.add_interface_endpoint(
            "ECRDockerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
            **interface_endpoint_config
        )

    def _create_outputs(self) -> None:
        """スタック出力の作成"""
        
        # VPC ID
        cdk.CfnOutput(
            self, "VpcId",
            value=self.vpc.vpc_id,
            description="VPC ID",
            export_name=f"{self.project_name}-{self.environment}-vpc-id"
        )

        # パブリックサブネットID
        for i, subnet in enumerate(self.vpc.public_subnets):
            cdk.CfnOutput(
                self, f"PublicSubnet{i+1}Id",
                value=subnet.subnet_id,
                description=f"Public Subnet {i+1} ID",
                export_name=f"{self.project_name}-{self.environment}-public-subnet-{i+1}-id"
            )

        # プライベートサブネットID
        for i, subnet in enumerate(self.vpc.private_subnets):
            cdk.CfnOutput(
                self, f"PrivateSubnet{i+1}Id",
                value=subnet.subnet_id,
                description=f"Private Subnet {i+1} ID",
                export_name=f"{self.project_name}-{self.environment}-private-subnet-{i+1}-id"
            )

        # 分離サブネットID
        for i, subnet in enumerate(self.vpc.isolated_subnets):
            cdk.CfnOutput(
                self, f"IsolatedSubnet{i+1}Id",
                value=subnet.subnet_id,
                description=f"Isolated Subnet {i+1} ID",
                export_name=f"{self.project_name}-{self.environment}-isolated-subnet-{i+1}-id"
            )