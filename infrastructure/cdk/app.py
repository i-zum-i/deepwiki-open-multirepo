#!/usr/bin/env python3
"""
DeepWiki-OMR AWS CDK アプリケーション
"""

import aws_cdk as cdk
from constructs import Construct

from stacks.network_stack import NetworkStack
from stacks.data_stack import DataStack
from stacks.compute_stack import ComputeStack
from stacks.security_stack import SecurityStack
from stacks.monitoring_stack import MonitoringStack


class DeepWikiOMRApp(cdk.App):
    """DeepWiki-OMR CDK アプリケーション"""

    def __init__(self):
        super().__init__()

        # 環境設定
        env = cdk.Environment(
            account=self.node.try_get_context("account"),
            region=self.node.try_get_context("region") or "ap-northeast-1"
        )

        # 環境名の取得（dev, staging, prod）
        environment = self.node.try_get_context("environment") or "dev"
        
        # プロジェクト設定
        project_name = "deepwiki-omr"
        
        # 共通タグ
        common_tags = {
            "Project": project_name,
            "Environment": environment,
            "ManagedBy": "CDK"
        }

        # ネットワークスタック
        network_stack = NetworkStack(
            self, f"{project_name}-{environment}-network",
            env=env,
            environment=environment,
            project_name=project_name,
            tags=common_tags
        )

        # セキュリティスタック
        security_stack = SecurityStack(
            self, f"{project_name}-{environment}-security",
            env=env,
            environment=environment,
            project_name=project_name,
            vpc=network_stack.vpc,
            tags=common_tags
        )

        # データスタック
        data_stack = DataStack(
            self, f"{project_name}-{environment}-data",
            env=env,
            environment=environment,
            project_name=project_name,
            vpc=network_stack.vpc,
            security_groups=security_stack.security_groups,
            tags=common_tags
        )

        # コンピュートスタック
        compute_stack = ComputeStack(
            self, f"{project_name}-{environment}-compute",
            env=env,
            environment=environment,
            project_name=project_name,
            vpc=network_stack.vpc,
            security_groups=security_stack.security_groups,
            dynamodb_tables=data_stack.dynamodb_tables,
            s3_bucket=data_stack.s3_bucket,
            opensearch_domain=data_stack.opensearch_domain,
            sqs_queues=data_stack.sqs_queues,
            tags=common_tags
        )

        # 監視スタック
        monitoring_stack = MonitoringStack(
            self, f"{project_name}-{environment}-monitoring",
            env=env,
            environment=environment,
            project_name=project_name,
            ecs_cluster=compute_stack.ecs_cluster,
            ecs_service=compute_stack.ecs_service,
            alb=compute_stack.alb,
            dynamodb_tables=data_stack.dynamodb_tables,
            opensearch_domain=data_stack.opensearch_domain,
            sqs_queues=data_stack.sqs_queues,
            tags=common_tags
        )

        # スタック間の依存関係を明示的に設定
        security_stack.add_dependency(network_stack)
        data_stack.add_dependency(security_stack)
        compute_stack.add_dependency(data_stack)
        monitoring_stack.add_dependency(compute_stack)


if __name__ == "__main__":
    app = DeepWikiOMRApp()
    app.synth()