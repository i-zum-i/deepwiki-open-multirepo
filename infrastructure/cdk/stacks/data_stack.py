"""
データスタック - DynamoDB、OpenSearch、S3、SQSの定義
"""

import aws_cdk as cdk
from aws_cdk import (
    aws_dynamodb as dynamodb,
    aws_opensearchserverless as opensearch,
    aws_s3 as s3,
    aws_sqs as sqs,
    aws_kms as kms,
    aws_ec2 as ec2,
    Stack,
    RemovalPolicy,
    Duration
)
from constructs import Construct
from typing import Dict, Any, List


class DataStack(Stack):
    """データストレージリソースを管理するスタック"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        project_name: str,
        vpc: ec2.Vpc,
        security_groups: Dict[str, ec2.SecurityGroup],
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.environment = environment
        self.project_name = project_name
        self.vpc = vpc
        self.security_groups = security_groups

        # KMS キーの作成
        self._create_kms_keys()

        # DynamoDB テーブルの作成
        self._create_dynamodb_tables()

        # S3 バケットの作成
        self._create_s3_bucket()

        # SQS キューの作成
        self._create_sqs_queues()

        # OpenSearch Serverless コレクションの作成
        self._create_opensearch_collection()

        # 出力の設定
        self._create_outputs()

    def _create_kms_keys(self) -> None:
        """KMS キーの作成"""
        
        # データ暗号化用KMSキー
        self.data_kms_key = kms.Key(
            self, "DataKMSKey",
            description=f"KMS key for {self.project_name} {self.environment} data encryption",
            key_usage=kms.KeyUsage.ENCRYPT_DECRYPT,
            key_spec=kms.KeySpec.SYMMETRIC_DEFAULT,
            removal_policy=RemovalPolicy.DESTROY if self.environment != "prod" else RemovalPolicy.RETAIN
        )

        # KMSキーエイリアス
        kms.Alias(
            self, "DataKMSKeyAlias",
            alias_name=f"alias/{self.project_name}-{self.environment}-data",
            target_key=self.data_kms_key
        )

    def _create_dynamodb_tables(self) -> None:
        """DynamoDB テーブルの作成"""
        
        self.dynamodb_tables = {}

        # リポジトリテーブル
        self.dynamodb_tables["repos"] = dynamodb.Table(
            self, "ReposTable",
            table_name=f"{self.project_name}-{self.environment}-repos",
            partition_key=dynamodb.Attribute(
                name="repo_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.data_kms_key,
            removal_policy=RemovalPolicy.DESTROY if self.environment != "prod" else RemovalPolicy.RETAIN,
            point_in_time_recovery=True if self.environment == "prod" else False,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES
        )

        # ステータス別検索用GSI
        self.dynamodb_tables["repos"].add_global_secondary_index(
            index_name="status-index",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="updated_at",
                type=dynamodb.AttributeType.STRING
            )
        )

        # ページテーブル
        self.dynamodb_tables["pages"] = dynamodb.Table(
            self, "PagesTable",
            table_name=f"{self.project_name}-{self.environment}-pages",
            partition_key=dynamodb.Attribute(
                name="repo_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="page_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.data_kms_key,
            removal_policy=RemovalPolicy.DESTROY if self.environment != "prod" else RemovalPolicy.RETAIN,
            point_in_time_recovery=True if self.environment == "prod" else False
        )

        # ジョブテーブル
        self.dynamodb_tables["jobs"] = dynamodb.Table(
            self, "JobsTable",
            table_name=f"{self.project_name}-{self.environment}-jobs",
            partition_key=dynamodb.Attribute(
                name="job_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.data_kms_key,
            removal_policy=RemovalPolicy.DESTROY if self.environment != "prod" else RemovalPolicy.RETAIN,
            time_to_live_attribute="ttl"
        )

        # リポジトリ・ステータス別検索用GSI
        self.dynamodb_tables["jobs"].add_global_secondary_index(
            index_name="repo-status-index",
            partition_key=dynamodb.Attribute(
                name="repo_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING
            )
        )

    def _create_s3_bucket(self) -> None:
        """S3 バケットの作成"""
        
        self.s3_bucket = s3.Bucket(
            self, "ContentBucket",
            bucket_name=f"{self.project_name}-{self.environment}-content",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.data_kms_key,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY if self.environment != "prod" else RemovalPolicy.RETAIN,
            auto_delete_objects=True if self.environment != "prod" else False,
            # パブリックアクセスをブロック
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            # ライフサイクルルール
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteIncompleteMultipartUploads",
                    abort_incomplete_multipart_upload_after=Duration.days(1)
                ),
                s3.LifecycleRule(
                    id="TransitionToIA",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30)
                        )
                    ]
                )
            ]
        )

        # CORS設定
        self.s3_bucket.add_cors_rule(
            allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
            allowed_origins=["*"],  # 本番環境では適切なドメインに制限
            allowed_headers=["*"],
            max_age=3000
        )

    def _create_sqs_queues(self) -> None:
        """SQS キューの作成"""
        
        self.sqs_queues = {}

        # 解析ジョブキュー
        self.sqs_queues["parse_jobs"] = sqs.Queue(
            self, "ParseJobsQueue",
            queue_name=f"{self.project_name}-{self.environment}-parse-jobs",
            encryption=sqs.QueueEncryption.KMS,
            encryption_master_key=self.data_kms_key,
            visibility_timeout=Duration.minutes(15),  # ジョブ処理時間を考慮
            message_retention_period=Duration.days(14),
            receive_message_wait_time=Duration.seconds(20),  # Long polling
            # デッドレターキューの設定
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=sqs.Queue(
                    self, "ParseJobsDLQ",
                    queue_name=f"{self.project_name}-{self.environment}-parse-jobs-dlq",
                    encryption=sqs.QueueEncryption.KMS,
                    encryption_master_key=self.data_kms_key,
                    message_retention_period=Duration.days(14)
                )
            )
        )

        # Webhook処理キュー
        self.sqs_queues["webhook_events"] = sqs.Queue(
            self, "WebhookEventsQueue",
            queue_name=f"{self.project_name}-{self.environment}-webhook-events",
            encryption=sqs.QueueEncryption.KMS,
            encryption_master_key=self.data_kms_key,
            visibility_timeout=Duration.minutes(5),
            message_retention_period=Duration.days(7),
            receive_message_wait_time=Duration.seconds(20),
            # デッドレターキューの設定
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=sqs.Queue(
                    self, "WebhookEventsDLQ",
                    queue_name=f"{self.project_name}-{self.environment}-webhook-events-dlq",
                    encryption=sqs.QueueEncryption.KMS,
                    encryption_master_key=self.data_kms_key,
                    message_retention_period=Duration.days(7)
                )
            )
        )

    def _create_opensearch_collection(self) -> None:
        """OpenSearch Serverless コレクションの作成"""
        
        # OpenSearch Serverless コレクション
        self.opensearch_domain = opensearch.CfnCollection(
            self, "SearchCollection",
            name=f"{self.project_name}-{self.environment}-search",
            description=f"OpenSearch collection for {self.project_name} {self.environment}",
            type="SEARCH"
        )

        # セキュリティポリシー（暗号化）
        encryption_policy = opensearch.CfnSecurityPolicy(
            self, "SearchCollectionEncryptionPolicy",
            name=f"{self.project_name}-{self.environment}-search-encryption",
            type="encryption",
            policy=f"""{{
                "Rules": [
                    {{
                        "ResourceType": "collection",
                        "Resource": ["collection/{self.project_name}-{self.environment}-search"]
                    }}
                ],
                "AWSOwnedKey": true
            }}"""
        )

        # ネットワークポリシー
        network_policy = opensearch.CfnSecurityPolicy(
            self, "SearchCollectionNetworkPolicy",
            name=f"{self.project_name}-{self.environment}-search-network",
            type="network",
            policy=f"""[
                {{
                    "Rules": [
                        {{
                            "ResourceType": "collection",
                            "Resource": ["collection/{self.project_name}-{self.environment}-search"]
                        }},
                        {{
                            "ResourceType": "dashboard",
                            "Resource": ["collection/{self.project_name}-{self.environment}-search"]
                        }}
                    ],
                    "AllowFromPublic": true
                }}
            ]"""
        )

        # 依存関係の設定
        self.opensearch_domain.add_dependency(encryption_policy)
        self.opensearch_domain.add_dependency(network_policy)

    def _create_outputs(self) -> None:
        """スタック出力の作成"""
        
        # DynamoDB テーブル名
        for table_name, table in self.dynamodb_tables.items():
            cdk.CfnOutput(
                self, f"{table_name.title()}TableName",
                value=table.table_name,
                description=f"{table_name.title()} DynamoDB table name",
                export_name=f"{self.project_name}-{self.environment}-{table_name}-table-name"
            )

        # S3 バケット名
        cdk.CfnOutput(
            self, "ContentBucketName",
            value=self.s3_bucket.bucket_name,
            description="Content S3 bucket name",
            export_name=f"{self.project_name}-{self.environment}-content-bucket-name"
        )

        # SQS キューURL
        for queue_name, queue in self.sqs_queues.items():
            cdk.CfnOutput(
                self, f"{queue_name.title().replace('_', '')}QueueUrl",
                value=queue.queue_url,
                description=f"{queue_name.replace('_', ' ').title()} SQS queue URL",
                export_name=f"{self.project_name}-{self.environment}-{queue_name.replace('_', '-')}-queue-url"
            )

        # OpenSearch コレクションエンドポイント
        cdk.CfnOutput(
            self, "SearchCollectionEndpoint",
            value=self.opensearch_domain.attr_collection_endpoint,
            description="OpenSearch collection endpoint",
            export_name=f"{self.project_name}-{self.environment}-search-endpoint"
        )

        # KMS キー ID
        cdk.CfnOutput(
            self, "DataKMSKeyId",
            value=self.data_kms_key.key_id,
            description="Data encryption KMS key ID",
            export_name=f"{self.project_name}-{self.environment}-data-kms-key-id"
        )