"""
セキュリティスタック - IAMロール、セキュリティグループ、Secrets Managerの定義
"""

import aws_cdk as cdk
from aws_cdk import (
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_secretsmanager as secretsmanager,
    aws_kms as kms,
    Stack,
    RemovalPolicy
)
from constructs import Construct
from typing import Dict, Any, List


class SecurityStack(Stack):
    """セキュリティリソースを管理するスタック"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        project_name: str,
        vpc: ec2.Vpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.environment = environment
        self.project_name = project_name
        self.vpc = vpc

        # セキュリティグループの作成
        self._create_security_groups()

        # IAMロールの作成
        self._create_iam_roles()

        # Secrets Managerシークレットの作成
        self._create_secrets()

        # 出力の設定
        self._create_outputs()

    def _create_security_groups(self) -> None:
        """セキュリティグループの作成"""
        
        self.security_groups = {}

        # ALB用セキュリティグループ
        self.security_groups["alb"] = ec2.SecurityGroup(
            self, "ALBSecurityGroup",
            vpc=self.vpc,
            description="Security group for Application Load Balancer",
            security_group_name=f"{self.project_name}-{self.environment}-alb-sg"
        )

        # HTTP/HTTPS トラフィックを許可
        self.security_groups["alb"].add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP from anywhere"
        )
        self.security_groups["alb"].add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS from anywhere"
        )

        # ECS用セキュリティグループ
        self.security_groups["ecs"] = ec2.SecurityGroup(
            self, "ECSSecurityGroup",
            vpc=self.vpc,
            description="Security group for ECS tasks",
            security_group_name=f"{self.project_name}-{self.environment}-ecs-sg"
        )

        # ALBからのトラフィックを許可
        self.security_groups["ecs"].add_ingress_rule(
            peer=self.security_groups["alb"],
            connection=ec2.Port.tcp(8000),  # FastAPI デフォルトポート
            description="Allow traffic from ALB"
        )

        # ECS間通信を許可（マイクロサービス間通信用）
        self.security_groups["ecs"].add_ingress_rule(
            peer=self.security_groups["ecs"],
            connection=ec2.Port.all_traffic(),
            description="Allow inter-ECS communication"
        )

        # OpenSearch用セキュリティグループ
        self.security_groups["opensearch"] = ec2.SecurityGroup(
            self, "OpenSearchSecurityGroup",
            vpc=self.vpc,
            description="Security group for OpenSearch",
            security_group_name=f"{self.project_name}-{self.environment}-opensearch-sg"
        )

        # ECSからのHTTPS通信を許可
        self.security_groups["opensearch"].add_ingress_rule(
            peer=self.security_groups["ecs"],
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS from ECS"
        )

    def _create_iam_roles(self) -> None:
        """IAMロールの作成"""
        
        self.iam_roles = {}

        # ECS タスク実行ロール
        self.iam_roles["ecs_execution"] = iam.Role(
            self, "ECSExecutionRole",
            role_name=f"{self.project_name}-{self.environment}-ecs-execution-role",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ]
        )

        # Secrets Manager アクセス権限を追加
        self.iam_roles["ecs_execution"].add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret"
                ],
                resources=[f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:{self.project_name}-{self.environment}-*"]
            )
        )

        # CloudWatch Logs アクセス権限を追加
        self.iam_roles["ecs_execution"].add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                resources=[f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/ecs/{self.project_name}-{self.environment}*"]
            )
        )

        # ECS タスクロール
        self.iam_roles["ecs_task"] = iam.Role(
            self, "ECSTaskRole",
            role_name=f"{self.project_name}-{self.environment}-ecs-task-role",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com")
        )

        # DynamoDB アクセス権限
        self.iam_roles["ecs_task"].add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchGetItem",
                    "dynamodb:BatchWriteItem"
                ],
                resources=[
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/{self.project_name}-{self.environment}-*",
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/{self.project_name}-{self.environment}-*/index/*"
                ]
            )
        )

        # S3 アクセス権限
        self.iam_roles["ecs_task"].add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBucket"
                ],
                resources=[
                    f"arn:aws:s3:::{self.project_name}-{self.environment}-content",
                    f"arn:aws:s3:::{self.project_name}-{self.environment}-content/*"
                ]
            )
        )

        # SQS アクセス権限
        self.iam_roles["ecs_task"].add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sqs:SendMessage",
                    "sqs:ReceiveMessage",
                    "sqs:DeleteMessage",
                    "sqs:GetQueueAttributes",
                    "sqs:ChangeMessageVisibility"
                ],
                resources=[f"arn:aws:sqs:{self.region}:{self.account}:{self.project_name}-{self.environment}-*"]
            )
        )

        # OpenSearch アクセス権限
        self.iam_roles["ecs_task"].add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "aoss:APIAccessAll"
                ],
                resources=[f"arn:aws:aoss:{self.region}:{self.account}:collection/*"]
            )
        )

        # Bedrock アクセス権限
        self.iam_roles["ecs_task"].add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel"
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-5-sonnet-*",
                    f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v2:*"
                ]
            )
        )

        # Secrets Manager アクセス権限
        self.iam_roles["ecs_task"].add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret"
                ],
                resources=[f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:{self.project_name}-{self.environment}-*"]
            )
        )

        # KMS アクセス権限
        self.iam_roles["ecs_task"].add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "kms:Decrypt",
                    "kms:DescribeKey"
                ],
                resources=[f"arn:aws:kms:{self.region}:{self.account}:key/*"],
                conditions={
                    "StringEquals": {
                        "kms:ViaService": [
                            f"dynamodb.{self.region}.amazonaws.com",
                            f"s3.{self.region}.amazonaws.com",
                            f"sqs.{self.region}.amazonaws.com",
                            f"secretsmanager.{self.region}.amazonaws.com"
                        ]
                    }
                }
            )
        )

    def _create_secrets(self) -> None:
        """Secrets Manager シークレットの作成"""
        
        self.secrets = {}

        # GitHub Personal Access Token
        self.secrets["github_pat"] = secretsmanager.Secret(
            self, "GitHubPATSecret",
            secret_name=f"{self.project_name}-{self.environment}-github-pat",
            description="GitHub Personal Access Token for repository access",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "github"}',
                generate_string_key="token",
                exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/\"\\",
                password_length=40
            ),
            removal_policy=RemovalPolicy.DESTROY if self.environment != "prod" else RemovalPolicy.RETAIN
        )

        # Webhook署名キー
        self.secrets["webhook_secret"] = secretsmanager.Secret(
            self, "WebhookSecretKey",
            secret_name=f"{self.project_name}-{self.environment}-webhook-secret",
            description="Secret key for webhook signature verification",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/\"\\",
                password_length=32
            ),
            removal_policy=RemovalPolicy.DESTROY if self.environment != "prod" else RemovalPolicy.RETAIN
        )

        # JWT署名キー
        self.secrets["jwt_secret"] = secretsmanager.Secret(
            self, "JWTSecretKey",
            secret_name=f"{self.project_name}-{self.environment}-jwt-secret",
            description="Secret key for JWT token signing",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/\"\\",
                password_length=64
            ),
            removal_policy=RemovalPolicy.DESTROY if self.environment != "prod" else RemovalPolicy.RETAIN
        )

    def _create_outputs(self) -> None:
        """スタック出力の作成"""
        
        # セキュリティグループID
        for sg_name, sg in self.security_groups.items():
            cdk.CfnOutput(
                self, f"{sg_name.title()}SecurityGroupId",
                value=sg.security_group_id,
                description=f"{sg_name.title()} security group ID",
                export_name=f"{self.project_name}-{self.environment}-{sg_name}-sg-id"
            )

        # IAMロールARN
        for role_name, role in self.iam_roles.items():
            cdk.CfnOutput(
                self, f"{role_name.title().replace('_', '')}RoleArn",
                value=role.role_arn,
                description=f"{role_name.replace('_', ' ').title()} IAM role ARN",
                export_name=f"{self.project_name}-{self.environment}-{role_name.replace('_', '-')}-role-arn"
            )

        # Secrets Manager シークレットARN
        for secret_name, secret in self.secrets.items():
            cdk.CfnOutput(
                self, f"{secret_name.title().replace('_', '')}SecretArn",
                value=secret.secret_arn,
                description=f"{secret_name.replace('_', ' ').title()} secret ARN",
                export_name=f"{self.project_name}-{self.environment}-{secret_name.replace('_', '-')}-secret-arn"
            )