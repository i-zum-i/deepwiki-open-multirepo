"""
監視スタック - CloudWatch、アラーム、ダッシュボードの定義
"""

import aws_cdk as cdk
from aws_cdk import (
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
    aws_logs as logs,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_dynamodb as dynamodb,
    aws_sqs as sqs,
    aws_opensearchserverless as opensearch,
    Stack,
    Duration
)
from constructs import Construct
from typing import Dict, Any, List


class MonitoringStack(Stack):
    """監視・アラートリソースを管理するスタック"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        project_name: str,
        ecs_cluster: ecs.Cluster,
        ecs_service: ecs.FargateService,
        alb: elbv2.ApplicationLoadBalancer,
        dynamodb_tables: Dict[str, dynamodb.Table],
        opensearch_domain: opensearch.CfnCollection,
        sqs_queues: Dict[str, sqs.Queue],
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.environment = environment
        self.project_name = project_name
        self.ecs_cluster = ecs_cluster
        self.ecs_service = ecs_service
        self.alb = alb
        self.dynamodb_tables = dynamodb_tables
        self.opensearch_domain = opensearch_domain
        self.sqs_queues = sqs_queues

        # SNS トピックの作成
        self._create_sns_topics()

        # CloudWatch アラームの作成
        self._create_cloudwatch_alarms()

        # CloudWatch ダッシュボードの作成
        self._create_cloudwatch_dashboard()

        # 出力の設定
        self._create_outputs()

    def _create_sns_topics(self) -> None:
        """SNS トピックの作成"""
        
        # 緊急アラート用トピック
        self.critical_alerts_topic = sns.Topic(
            self, "CriticalAlertsTopic",
            topic_name=f"{self.project_name}-{self.environment}-critical-alerts",
            display_name=f"{self.project_name.title()} {self.environment.title()} Critical Alerts"
        )

        # 警告アラート用トピック
        self.warning_alerts_topic = sns.Topic(
            self, "WarningAlertsTopic",
            topic_name=f"{self.project_name}-{self.environment}-warning-alerts",
            display_name=f"{self.project_name.title()} {self.environment.title()} Warning Alerts"
        )

        # 本番環境では実際のメールアドレスを設定
        if self.environment == "prod":
            # 注意: 実際のメールアドレスに置き換えてください
            # self.critical_alerts_topic.add_subscription(
            #     sns_subscriptions.EmailSubscription("admin@example.com")
            # )
            pass

    def _create_cloudwatch_alarms(self) -> None:
        """CloudWatch アラームの作成"""
        
        self.alarms = {}

        # ALB関連のアラーム
        self._create_alb_alarms()

        # ECS関連のアラーム
        self._create_ecs_alarms()

        # DynamoDB関連のアラーム
        self._create_dynamodb_alarms()

        # SQS関連のアラーム
        self._create_sqs_alarms()

    def _create_alb_alarms(self) -> None:
        """ALB関連のアラーム"""
        
        # ALB 5xxエラー率
        self.alarms["alb_5xx_errors"] = cloudwatch.Alarm(
            self, "ALB5xxErrorsAlarm",
            alarm_name=f"{self.project_name}-{self.environment}-alb-5xx-errors",
            alarm_description="ALB 5xx error rate is high",
            metric=cloudwatch.Metric(
                namespace="AWS/ApplicationELB",
                metric_name="HTTPCode_ELB_5XX_Count",
                dimensions_map={
                    "LoadBalancer": self.alb.load_balancer_full_name
                },
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=10,
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )

        self.alarms["alb_5xx_errors"].add_alarm_action(
            cw_actions.SnsAction(self.critical_alerts_topic)
        )

        # ALB レスポンス時間
        self.alarms["alb_response_time"] = cloudwatch.Alarm(
            self, "ALBResponseTimeAlarm",
            alarm_name=f"{self.project_name}-{self.environment}-alb-response-time",
            alarm_description="ALB response time is high",
            metric=cloudwatch.Metric(
                namespace="AWS/ApplicationELB",
                metric_name="TargetResponseTime",
                dimensions_map={
                    "LoadBalancer": self.alb.load_balancer_full_name
                },
                statistic="Average",
                period=Duration.minutes(5)
            ),
            threshold=5.0,  # 5秒
            evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )

        self.alarms["alb_response_time"].add_alarm_action(
            cw_actions.SnsAction(self.warning_alerts_topic)
        )

    def _create_ecs_alarms(self) -> None:
        """ECS関連のアラーム"""
        
        # ECS CPU使用率
        self.alarms["ecs_cpu_utilization"] = cloudwatch.Alarm(
            self, "ECSCPUUtilizationAlarm",
            alarm_name=f"{self.project_name}-{self.environment}-ecs-cpu-utilization",
            alarm_description="ECS CPU utilization is high",
            metric=cloudwatch.Metric(
                namespace="AWS/ECS",
                metric_name="CPUUtilization",
                dimensions_map={
                    "ServiceName": self.ecs_service.service_name,
                    "ClusterName": self.ecs_cluster.cluster_name
                },
                statistic="Average",
                period=Duration.minutes(5)
            ),
            threshold=80.0,
            evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )

        self.alarms["ecs_cpu_utilization"].add_alarm_action(
            cw_actions.SnsAction(self.warning_alerts_topic)
        )

        # ECS メモリ使用率
        self.alarms["ecs_memory_utilization"] = cloudwatch.Alarm(
            self, "ECSMemoryUtilizationAlarm",
            alarm_name=f"{self.project_name}-{self.environment}-ecs-memory-utilization",
            alarm_description="ECS memory utilization is high",
            metric=cloudwatch.Metric(
                namespace="AWS/ECS",
                metric_name="MemoryUtilization",
                dimensions_map={
                    "ServiceName": self.ecs_service.service_name,
                    "ClusterName": self.ecs_cluster.cluster_name
                },
                statistic="Average",
                period=Duration.minutes(5)
            ),
            threshold=85.0,
            evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )

        self.alarms["ecs_memory_utilization"].add_alarm_action(
            cw_actions.SnsAction(self.warning_alerts_topic)
        )

        # ECS タスク数
        self.alarms["ecs_running_tasks"] = cloudwatch.Alarm(
            self, "ECSRunningTasksAlarm",
            alarm_name=f"{self.project_name}-{self.environment}-ecs-running-tasks",
            alarm_description="ECS running tasks count is low",
            metric=cloudwatch.Metric(
                namespace="AWS/ECS",
                metric_name="RunningTaskCount",
                dimensions_map={
                    "ServiceName": self.ecs_service.service_name,
                    "ClusterName": self.ecs_cluster.cluster_name
                },
                statistic="Average",
                period=Duration.minutes(5)
            ),
            threshold=1,
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.BREACHING
        )

        self.alarms["ecs_running_tasks"].add_alarm_action(
            cw_actions.SnsAction(self.critical_alerts_topic)
        )

    def _create_dynamodb_alarms(self) -> None:
        """DynamoDB関連のアラーム"""
        
        for table_name, table in self.dynamodb_tables.items():
            # DynamoDB スロットリング
            self.alarms[f"dynamodb_{table_name}_throttles"] = cloudwatch.Alarm(
                self, f"DynamoDB{table_name.title()}ThrottlesAlarm",
                alarm_name=f"{self.project_name}-{self.environment}-dynamodb-{table_name}-throttles",
                alarm_description=f"DynamoDB {table_name} table is being throttled",
                metric=cloudwatch.Metric(
                    namespace="AWS/DynamoDB",
                    metric_name="ThrottledRequests",
                    dimensions_map={
                        "TableName": table.table_name
                    },
                    statistic="Sum",
                    period=Duration.minutes(5)
                ),
                threshold=0,
                evaluation_periods=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
            )

            self.alarms[f"dynamodb_{table_name}_throttles"].add_alarm_action(
                cw_actions.SnsAction(self.critical_alerts_topic)
            )

            # DynamoDB エラー率
            self.alarms[f"dynamodb_{table_name}_errors"] = cloudwatch.Alarm(
                self, f"DynamoDB{table_name.title()}ErrorsAlarm",
                alarm_name=f"{self.project_name}-{self.environment}-dynamodb-{table_name}-errors",
                alarm_description=f"DynamoDB {table_name} table error rate is high",
                metric=cloudwatch.Metric(
                    namespace="AWS/DynamoDB",
                    metric_name="SystemErrors",
                    dimensions_map={
                        "TableName": table.table_name
                    },
                    statistic="Sum",
                    period=Duration.minutes(5)
                ),
                threshold=5,
                evaluation_periods=2,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
            )

            self.alarms[f"dynamodb_{table_name}_errors"].add_alarm_action(
                cw_actions.SnsAction(self.warning_alerts_topic)
            )

    def _create_sqs_alarms(self) -> None:
        """SQS関連のアラーム"""
        
        for queue_name, queue in self.sqs_queues.items():
            # SQS DLQ メッセージ蓄積
            if "dlq" not in queue_name.lower():  # DLQでない場合のみ
                # 対応するDLQを探す
                dlq_name = f"{queue_name}_dlq"
                if dlq_name in [q for q in self.sqs_queues.keys()]:
                    dlq = self.sqs_queues[dlq_name]
                    
                    self.alarms[f"sqs_{queue_name}_dlq_messages"] = cloudwatch.Alarm(
                        self, f"SQS{queue_name.title().replace('_', '')}DLQMessagesAlarm",
                        alarm_name=f"{self.project_name}-{self.environment}-sqs-{queue_name}-dlq-messages",
                        alarm_description=f"SQS {queue_name} DLQ has messages",
                        metric=cloudwatch.Metric(
                            namespace="AWS/SQS",
                            metric_name="ApproximateNumberOfMessages",
                            dimensions_map={
                                "QueueName": dlq.queue_name
                            },
                            statistic="Maximum",
                            period=Duration.minutes(1)
                        ),
                        threshold=1,
                        evaluation_periods=1,
                        comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                        treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
                    )

                    self.alarms[f"sqs_{queue_name}_dlq_messages"].add_alarm_action(
                        cw_actions.SnsAction(self.critical_alerts_topic)
                    )

            # SQS キュー深度
            self.alarms[f"sqs_{queue_name}_depth"] = cloudwatch.Alarm(
                self, f"SQS{queue_name.title().replace('_', '')}DepthAlarm",
                alarm_name=f"{self.project_name}-{self.environment}-sqs-{queue_name}-depth",
                alarm_description=f"SQS {queue_name} queue depth is high",
                metric=cloudwatch.Metric(
                    namespace="AWS/SQS",
                    metric_name="ApproximateNumberOfMessages",
                    dimensions_map={
                        "QueueName": queue.queue_name
                    },
                    statistic="Maximum",
                    period=Duration.minutes(5)
                ),
                threshold=100,
                evaluation_periods=3,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
            )

            self.alarms[f"sqs_{queue_name}_depth"].add_alarm_action(
                cw_actions.SnsAction(self.warning_alerts_topic)
            )

    def _create_cloudwatch_dashboard(self) -> None:
        """CloudWatch ダッシュボードの作成"""
        
        self.dashboard = cloudwatch.Dashboard(
            self, "MonitoringDashboard",
            dashboard_name=f"{self.project_name}-{self.environment}-monitoring"
        )

        # ALB メトリクス
        alb_widgets = [
            cloudwatch.GraphWidget(
                title="ALB Request Count",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/ApplicationELB",
                        metric_name="RequestCount",
                        dimensions_map={
                            "LoadBalancer": self.alb.load_balancer_full_name
                        },
                        statistic="Sum",
                        period=Duration.minutes(5)
                    )
                ],
                width=12,
                height=6
            ),
            cloudwatch.GraphWidget(
                title="ALB Response Time",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/ApplicationELB",
                        metric_name="TargetResponseTime",
                        dimensions_map={
                            "LoadBalancer": self.alb.load_balancer_full_name
                        },
                        statistic="Average",
                        period=Duration.minutes(5)
                    )
                ],
                width=12,
                height=6
            )
        ]

        # ECS メトリクス
        ecs_widgets = [
            cloudwatch.GraphWidget(
                title="ECS CPU & Memory Utilization",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/ECS",
                        metric_name="CPUUtilization",
                        dimensions_map={
                            "ServiceName": self.ecs_service.service_name,
                            "ClusterName": self.ecs_cluster.cluster_name
                        },
                        statistic="Average",
                        period=Duration.minutes(5)
                    )
                ],
                right=[
                    cloudwatch.Metric(
                        namespace="AWS/ECS",
                        metric_name="MemoryUtilization",
                        dimensions_map={
                            "ServiceName": self.ecs_service.service_name,
                            "ClusterName": self.ecs_cluster.cluster_name
                        },
                        statistic="Average",
                        period=Duration.minutes(5)
                    )
                ],
                width=12,
                height=6
            ),
            cloudwatch.GraphWidget(
                title="ECS Running Tasks",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/ECS",
                        metric_name="RunningTaskCount",
                        dimensions_map={
                            "ServiceName": self.ecs_service.service_name,
                            "ClusterName": self.ecs_cluster.cluster_name
                        },
                        statistic="Average",
                        period=Duration.minutes(5)
                    )
                ],
                width=12,
                height=6
            )
        ]

        # DynamoDB メトリクス
        dynamodb_widgets = []
        for table_name, table in self.dynamodb_tables.items():
            dynamodb_widgets.append(
                cloudwatch.GraphWidget(
                    title=f"DynamoDB {table_name.title()} Operations",
                    left=[
                        cloudwatch.Metric(
                            namespace="AWS/DynamoDB",
                            metric_name="ConsumedReadCapacityUnits",
                            dimensions_map={
                                "TableName": table.table_name
                            },
                            statistic="Sum",
                            period=Duration.minutes(5)
                        )
                    ],
                    right=[
                        cloudwatch.Metric(
                            namespace="AWS/DynamoDB",
                            metric_name="ConsumedWriteCapacityUnits",
                            dimensions_map={
                                "TableName": table.table_name
                            },
                            statistic="Sum",
                            period=Duration.minutes(5)
                        )
                    ],
                    width=12,
                    height=6
                )
            )

        # SQS メトリクス
        sqs_widgets = []
        for queue_name, queue in self.sqs_queues.items():
            sqs_widgets.append(
                cloudwatch.GraphWidget(
                    title=f"SQS {queue_name.replace('_', ' ').title()} Messages",
                    left=[
                        cloudwatch.Metric(
                            namespace="AWS/SQS",
                            metric_name="ApproximateNumberOfMessages",
                            dimensions_map={
                                "QueueName": queue.queue_name
                            },
                            statistic="Maximum",
                            period=Duration.minutes(5)
                        )
                    ],
                    width=12,
                    height=6
                )
            )

        # ダッシュボードにウィジェットを追加
        for widget in alb_widgets + ecs_widgets + dynamodb_widgets + sqs_widgets:
            self.dashboard.add_widgets(widget)

    def _create_outputs(self) -> None:
        """スタック出力の作成"""
        
        # SNS トピック ARN
        cdk.CfnOutput(
            self, "CriticalAlertsTopicArn",
            value=self.critical_alerts_topic.topic_arn,
            description="Critical alerts SNS topic ARN",
            export_name=f"{self.project_name}-{self.environment}-critical-alerts-topic-arn"
        )

        cdk.CfnOutput(
            self, "WarningAlertsTopicArn",
            value=self.warning_alerts_topic.topic_arn,
            description="Warning alerts SNS topic ARN",
            export_name=f"{self.project_name}-{self.environment}-warning-alerts-topic-arn"
        )

        # ダッシュボード URL
        cdk.CfnOutput(
            self, "DashboardURL",
            value=f"https://{self.region}.console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name={self.dashboard.dashboard_name}",
            description="CloudWatch dashboard URL",
            export_name=f"{self.project_name}-{self.environment}-dashboard-url"
        )