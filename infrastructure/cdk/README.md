# DeepWiki-OMR AWS CDK インフラストラクチャ

## 概要

このディレクトリには、DeepWiki-Open-MultiRepo（DeepWiki-OMR）のAWSインフラストラクチャをAWS CDKで定義したコードが含まれています。

## アーキテクチャ

### スタック構成

1. **NetworkStack**: VPC、サブネット、セキュリティグループ
2. **SecurityStack**: IAMロール、Secrets Manager
3. **DataStack**: DynamoDB、OpenSearch、S3、SQS
4. **ComputeStack**: ECS、ALB、API Gateway
5. **MonitoringStack**: CloudWatch、アラーム、ダッシュボード

### リソース構成

#### ネットワーク
- VPC (10.0.0.0/16)
- パブリックサブネット x2 (ALB用)
- プライベートサブネット x2 (アプリケーション用)
- 分離サブネット x2 (データベース用)
- NATゲートウェイ x1
- VPCエンドポイント (S3, DynamoDB, SQS, Secrets Manager等)

#### データストレージ
- **DynamoDB テーブル**:
  - `repos`: リポジトリ情報
  - `pages`: ページメタデータ
  - `jobs`: ジョブ管理
- **S3 バケット**: Wikiコンテンツ保存
- **OpenSearch Serverless**: 検索インデックス
- **SQS キュー**: 非同期ジョブ処理

#### コンピュート
- **ECS Fargate**: API サーバーとワーカー
- **Application Load Balancer**: トラフィック分散
- **API Gateway**: Webhook エンドポイント
- **ECR**: コンテナイメージ保存

#### セキュリティ
- **IAM ロール**: 最小権限の原則
- **Secrets Manager**: 認証情報管理
- **KMS**: データ暗号化

#### 監視
- **CloudWatch**: メトリクス、ログ、アラーム
- **SNS**: アラート通知
- **ダッシュボード**: 可視化

## セットアップ

### 前提条件

1. AWS CLI の設定
2. Python 3.8+ のインストール
3. Node.js 18+ のインストール
4. AWS CDK CLI のインストール

```bash
npm install -g aws-cdk
```

### 環境構築

1. 仮想環境の作成と有効化:
```bash
cd infrastructure/cdk
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# または
.venv\Scripts\activate.bat  # Windows
```

2. 依存関係のインストール:
```bash
pip install -r requirements.txt
```

3. CDK の初期化（初回のみ）:
```bash
cdk bootstrap
```

### デプロイ

#### 開発環境

```bash
# 全スタックのデプロイ
cdk deploy --all -c environment=dev

# 特定のスタックのみデプロイ
cdk deploy deepwiki-omr-dev-network -c environment=dev
```

#### ステージング環境

```bash
cdk deploy --all -c environment=staging
```

#### 本番環境

```bash
cdk deploy --all -c environment=prod
```

### 設定パラメータ

環境別の設定は `cdk.json` の `context` セクションで管理します：

```json
{
  "context": {
    "environment": "dev",
    "account": "123456789012",
    "region": "ap-northeast-1"
  }
}
```

## 運用

### 監視

- CloudWatch ダッシュボード: デプロイ後に出力されるURLでアクセス
- アラート: SNS トピックにメール通知を設定

### ログ

- ECS タスクログ: CloudWatch Logs
- ALB アクセスログ: S3 バケット（オプション）

### スケーリング

- ECS サービス: CPU使用率ベースの自動スケーリング
- ワーカー: SQSキュー深度ベースのスケーリング

### セキュリティ

- 認証情報: Secrets Manager で管理
- 暗号化: KMS キーによる暗号化
- ネットワーク: VPC内での通信制御

## トラブルシューティング

### よくある問題

1. **デプロイエラー**:
   - IAM権限の確認
   - リソース制限の確認
   - 既存リソースとの競合確認

2. **接続エラー**:
   - セキュリティグループの設定確認
   - VPCエンドポイントの設定確認

3. **パフォーマンス問題**:
   - CloudWatch メトリクスの確認
   - リソース使用率の確認

### ログの確認

```bash
# ECS タスクログ
aws logs describe-log-groups --log-group-name-prefix "/aws/ecs/deepwiki-omr"

# CloudFormation イベント
aws cloudformation describe-stack-events --stack-name deepwiki-omr-dev-network
```

## クリーンアップ

```bash
# 全スタックの削除
cdk destroy --all -c environment=dev

# 特定のスタックの削除
cdk destroy deepwiki-omr-dev-monitoring -c environment=dev
```

**注意**: 本番環境のリソースは `RemovalPolicy.RETAIN` が設定されているため、手動での削除が必要な場合があります。

## 参考資料

- [AWS CDK Developer Guide](https://docs.aws.amazon.com/cdk/)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [DeepWiki-OMR 設計書](../../docs/design.md)