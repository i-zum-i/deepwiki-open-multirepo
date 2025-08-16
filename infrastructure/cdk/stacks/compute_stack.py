"""
コンピュートスタック - ECS、ALB、API Gatewayの定義
"""

import aws_cdk as cdk
from aws_cdk import (
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_apigateway as apigateway,
    aws_logs as logs,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_sqs as sqs,
    aws_opensearchserverless as opensearch,
    Stack,
    Duration,
    RemovalPolicy
)
from constructs import Construct
from typing import Dict, Any


class ComputeStack(Stack):
    """コンピュートリソースを管理するスタック"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        project_name: str,
        vpc: ec2.Vpc,
        security_groups: Dict[str, ec2.SecurityGroup],
        dynamodb_tables: Dict[str, dynamodb.Table],
        s3_bucket: s3.Bucket,
        opensearch_domain: opensearch.CfnCollection,
        sqs_queues: Dict[str, sqs.Queue],
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.environment = environment
        self.project_name = project_name
        self.vpc = vpc
        self.security_groups = security_groups
        self.dynamodb_tables = dynamodb_tables
        self.s3_bucket = s3_bucket
        self.opensearch_domain = opensearch_domain
        self.sqs_queues = sqs_queues

        # ECR リポジトリの作成
        self._create_ecr_repositories()

        # ECS クラスターの作成
        self._create_ecs_cluster()

        # Application Load Balancer の作成
        self._create_alb()

        # ECS サービスの作成
        self._create_ecs_services()

        # API Gateway の作成
        self._create_api_gateway()

        # 出力の設定
        self._create_outputs()

    def _create_ecr_repositories(self) -> None:
        """ECR リポジトリの作成"""
        
        self.ecr_repositories = {}

        # API サーバー用リポジトリ
        self.ecr_repositories["api"] = ecr.Repository(
            self, "APIRepository",
            repository_name=f"{self.project_name}-{self.environment}-api",
            image_scan_on_push=True,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Keep last 10 images",
                    max_image_count=10
                )
            ],
            removal_policy=RemovalPolicy.DESTROY if self.environment != "prod" else RemovalPolicy.RETAIN
        )

        # ワーカー用リポジトリ
        self.ecr_repositories["worker"] = ecr.Repository(
            self, "WorkerRepository",
            repository_name=f"{self.project_name}-{self.environment}-worker",
            image_scan_on_push=True,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Keep last 10 images",
                    max_image_count=10
                )
            ],
            removal_policy=RemovalPolicy.DESTROY if self.environment != "prod" else RemovalPolicy.RETAIN
        )

    def _create_ecs_cluster(self) -> None:
        """ECS クラスターの作成"""
        
        self.ecs_cluster = ecs.Cluster(
            self, "ECSCluster",
            cluster_name=f"{self.project_name}-{self.environment}-cluster",
            vpc=self.vpc,
            container_insights=True
        )

    def _create_alb(self) -> None:
        """Application Load Balancer の作成"""
        
        self.alb = elbv2.ApplicationLoadBalancer(
            self, "ALB",
            load_balancer_name=f"{self.project_name}-{self.environment}-alb",
            vpc=self.vpc,
            internet_facing=True,
            security_group=self.security_groups["alb"]
        )

        # ターゲットグループ（API用）
        self.api_target_group = elbv2.ApplicationTargetGroup(
            self, "APITargetGroup",
            target_group_name=f"{self.project_name}-{self.environment}-api-tg",
            port=8000,
            protocol=elbv2.ApplicationProtocol.HTTP,
            vpc=self.vpc,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                enabled=True,
                healthy_http_codes="200",
                path="/health",
                protocol=elbv2.Protocol.HTTP,
                timeout=Duration.seconds(5),
                interval=Duration.seconds(30),
                healthy_threshold_count=2,
                unhealthy_threshold_count=3
            )
        )

        # リスナー（HTTP）
        self.alb.add_listener(
            "HTTPListener",
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            default_target_groups=[self.api_target_group]
        )

        # 本番環境ではHTTPS リスナーも追加（証明書は手動で設定）
        if self.environment == "prod":
            # 注意: 実際の証明書ARNを設定する必要があります
            pass

    def _create_ecs_services(self) -> None:
        """ECS サービスの作成"""
        
        # CloudWatch ロググループ
        api_log_group = logs.LogGroup(
            self, "APILogGroup",
            log_group_name=f"/aws/ecs/{self.project_name}-{self.environment}-api",
            retention=logs.RetentionDays.ONE_WEEK if self.environment != "prod" else logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY if self.environment != "prod" else RemovalPolicy.RETAIN
        )

        worker_log_group = logs.LogGroup(
            self, "WorkerLogGroup",
            log_group_name=f"/aws/ecs/{self.project_name}-{self.environment}-worker",
            retention=logs.RetentionDays.ONE_WEEK if self.environment != "prod" else logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY if self.environment != "prod" else RemovalPolicy.RETAIN
        )

        # タスク定義（API）
        api_task_definition = ecs.FargateTaskDefinition(
            self, "APITaskDefinition",
            family=f"{self.project_name}-{self.environment}-api",
            cpu=512,  # 0.5 vCPU
            memory_limit_mib=1024,  # 1 GB
            execution_role=iam.Role.from_role_arn(
                self, "ImportedECSExecutionRole",
                role_arn=f"arn:aws:iam::{self.account}:role/{self.project_name}-{self.environment}-ecs-execution-role"
            ),
            task_role=iam.Role.from_role_arn(
                self, "ImportedECSTaskRole",
                role_arn=f"arn:aws:iam::{self.account}:role/{self.project_name}-{self.environment}-ecs-task-role"
            )
        )

        # API コンテナ
        api_container = api_task_definition.add_container(
            "APIContainer",
            container_name="api",
            image=ecs.ContainerImage.from_ecr_repository(
                repository=self.ecr_repositories["api"],
                tag="latest"
            ),
            port_mappings=[
                ecs.PortMapping(
                    container_port=8000,
                    protocol=ecs.Protocol.TCP
                )
            ],
            environment={
                "ENVIRONMENT": self.environment,
                "AWS_DEFAULT_REGION": self.region,
                "DYNAMODB_REPOS_TABLE": self.dynamodb_tables["repos"].table_name,
                "DYNAMODB_PAGES_TABLE": self.dynamodb_tables["pages"].table_name,
                "DYNAMODB_JOBS_TABLE": self.dynamodb_tables["jobs"].table_name,
                "S3_CONTENT_BUCKET": self.s3_bucket.bucket_name,
                "SQS_PARSE_JOBS_QUEUE": self.sqs_queues["parse_jobs"].queue_url,
                "SQS_WEBHOOK_EVENTS_QUEUE": self.sqs_queues["webhook_events"].queue_url,
                "OPENSEARCH_ENDPOINT": self.opensearch_domain.attr_collection_endpoint
            },
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="api",
                log_group=api_log_group
            ),
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
                start_period=Duration.seconds(60)
            )
        )

        # API ECS サービス
        self.ecs_service = ecs.FargateService(
            self, "APIService",
            service_name=f"{self.project_name}-{self.environment}-api",
            cluster=self.ecs_cluster,
            task_definition=api_task_definition,
            desired_count=1 if self.environment != "prod" else 2,
            security_groups=[self.security_groups["ecs"]],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            enable_logging=True,
            # ヘルスチェック設定
            health_check_grace_period=Duration.seconds(60)
        )

        # ALB ターゲットグループにサービスを登録
        self.ecs_service.attach_to_application_target_group(self.api_target_group)

        # オートスケーリング設定
        scaling = self.ecs_service.auto_scale_task_count(
            min_capacity=1,
            max_capacity=10 if self.environment == "prod" else 3
        )

        # CPU使用率ベースのスケーリング
        scaling.scale_on_cpu_utilization(
            "CPUScaling",
            target_utilization_percent=70,
            scale_in_cooldown=Duration.minutes(5),
            scale_out_cooldown=Duration.minutes(2)
        )

        # ワーカータスク定義
        worker_task_definition = ecs.FargateTaskDefinition(
            self, "WorkerTaskDefinition",
            family=f"{self.project_name}-{self.environment}-worker",
            cpu=1024,  # 1 vCPU
            memory_limit_mib=2048,  # 2 GB
            execution_role=iam.Role.from_role_arn(
                self, "ImportedWorkerECSExecutionRole",
                role_arn=f"arn:aws:iam::{self.account}:role/{self.project_name}-{self.environment}-ecs-execution-role"
            ),
            task_role=iam.Role.from_role_arn(
                self, "ImportedWorkerECSTaskRole",
                role_arn=f"arn:aws:iam::{self.account}:role/{self.project_name}-{self.environment}-ecs-task-role"
            )
        )

        # ワーカーコンテナ
        worker_container = worker_task_definition.add_container(
            "WorkerContainer",
            container_name="worker",
            image=ecs.ContainerImage.from_ecr_repository(
                repository=self.ecr_repositories["worker"],
                tag="latest"
            ),
            environment={
                "ENVIRONMENT": self.environment,
                "AWS_DEFAULT_REGION": self.region,
                "DYNAMODB_REPOS_TABLE": self.dynamodb_tables["repos"].table_name,
                "DYNAMODB_PAGES_TABLE": self.dynamodb_tables["pages"].table_name,
                "DYNAMODB_JOBS_TABLE": self.dynamodb_tables["jobs"].table_name,
                "S3_CONTENT_BUCKET": self.s3_bucket.bucket_name,
                "SQS_PARSE_JOBS_QUEUE": self.sqs_queues["parse_jobs"].queue_url,
                "SQS_WEBHOOK_EVENTS_QUEUE": self.sqs_queues["webhook_events"].queue_url,
                "OPENSEARCH_ENDPOINT": self.opensearch_domain.attr_collection_endpoint
            },
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="worker",
                log_group=worker_log_group
            )
        )

        # ワーカー ECS サービス
        self.worker_service = ecs.FargateService(
            self, "WorkerService",
            service_name=f"{self.project_name}-{self.environment}-worker",
            cluster=self.ecs_cluster,
            task_definition=worker_task_definition,
            desired_count=1,
            security_groups=[self.security_groups["ecs"]],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            enable_logging=True
        )

        # ワーカーのオートスケーリング（SQSキューの深さベース）
        worker_scaling = self.worker_service.auto_scale_task_count(
            min_capacity=1,
            max_capacity=5 if self.environment == "prod" else 2
        )

    def _create_api_gateway(self) -> None:
        """API Gateway の作成（Webhook用）"""
        
        # REST API
        self.api_gateway = apigateway.RestApi(
            self, "WebhookAPI",
            rest_api_name=f"{self.project_name}-{self.environment}-webhook-api",
            description=f"Webhook API for {self.project_name} {self.environment}",
            endpoint_configuration=apigateway.EndpointConfiguration(
                types=[apigateway.EndpointType.REGIONAL]
            ),
            # CORS設定
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key", "X-Amz-Security-Token"]
            )
        )

        # Webhook リソース
        webhook_resource = self.api_gateway.root.add_resource("webhook")
        
        # GitHub Webhook
        github_resource = webhook_resource.add_resource("github")
        
        # CodeCommit Webhook
        codecommit_resource = webhook_resource.add_resource("codecommit")

        # 実際のLambda統合は後のフェーズで実装
        # 現在はモックレスポンスを設定
        github_resource.add_method(
            "POST",
            apigateway.MockIntegration(
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code="200",
                        response_templates={
                            "application/json": '{"message": "GitHub webhook received"}'
                        }
                    )
                ],
                request_templates={
                    "application/json": '{"statusCode": 200}'
                }
            ),
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_models={
                        "application/json": apigateway.Model.EMPTY_MODEL
                    }
                )
            ]
        )

        codecommit_resource.add_method(
            "POST",
            apigateway.MockIntegration(
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code="200",
                        response_templates={
                            "application/json": '{"message": "CodeCommit webhook received"}'
                        }
                    )
                ],
                request_templates={
                    "application/json": '{"statusCode": 200}'
                }
            ),
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_models={
                        "application/json": apigateway.Model.EMPTY_MODEL
                    }
                )
            ]
        )

    def _create_outputs(self) -> None:
        """スタック出力の作成"""
        
        # ALB DNS名
        cdk.CfnOutput(
            self, "ALBDNSName",
            value=self.alb.load_balancer_dns_name,
            description="Application Load Balancer DNS name",
            export_name=f"{self.project_name}-{self.environment}-alb-dns-name"
        )

        # ECS クラスター名
        cdk.CfnOutput(
            self, "ECSClusterName",
            value=self.ecs_cluster.cluster_name,
            description="ECS cluster name",
            export_name=f"{self.project_name}-{self.environment}-ecs-cluster-name"
        )

        # ECR リポジトリURI
        for repo_name, repo in self.ecr_repositories.items():
            cdk.CfnOutput(
                self, f"{repo_name.title()}ECRRepositoryURI",
                value=repo.repository_uri,
                description=f"{repo_name.title()} ECR repository URI",
                export_name=f"{self.project_name}-{self.environment}-{repo_name}-ecr-uri"
            )

        # API Gateway URL
        cdk.CfnOutput(
            self, "WebhookAPIURL",
            value=self.api_gateway.url,
            description="Webhook API Gateway URL",
            export_name=f"{self.project_name}-{self.environment}-webhook-api-url"
        )