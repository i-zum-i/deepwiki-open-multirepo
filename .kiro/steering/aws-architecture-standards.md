# AWS アーキテクチャ標準

## 概要

DeepWiki-OMRプロジェクトにおけるAWSサービスの使用標準とベストプラクティスを定義します。

## 基本アーキテクチャ原則

### クラウドネイティブ設計
- **サーバーレス優先**: 可能な限りマネージドサービスを使用
- **水平スケーリング**: 負荷に応じた自動スケーリング
- **疎結合**: サービス間の依存関係を最小化
- **イベント駆動**: 非同期処理とイベントベースアーキテクチャ

### 可用性とレジリエンス
- **マルチAZ配置**: 単一障害点の排除
- **自動復旧**: 障害時の自動復旧メカニズム
- **サーキットブレーカー**: 障害の連鎖を防ぐ
- **グレースフルデグラデーション**: 部分的な機能停止時の対応

## 推奨AWSサービス構成

### コンピュート層
```yaml
プライマリ: ECS Fargate
  - API サーバー用
  - ワーカープロセス用
  - 自動スケーリング対応

代替案:
  - AWS Lambda (軽量処理用)
  - AWS App Runner (シンプルなAPI用)
```

### データ層
```yaml
メタデータ: Amazon DynamoDB
  - リポジトリ情報
  - ページメタデータ
  - ジョブ状態管理

検索エンジン: Amazon OpenSearch Serverless
  - 全文検索
  - ベクトル検索
  - 自動スケーリング

ファイルストレージ: Amazon S3
  - Wiki コンテンツ
  - 生成された図表
  - 一時ファイル
```

### AI/ML層
```yaml
LLM: Amazon Bedrock
  - Claude 3.5 Sonnet (文書生成)
  - Titan Embed v2 (ベクトル化)

設定:
  - 温度: 0.1 (一貫性重視)
  - 最大トークン: 4096
  - トップP: 0.9
```

### 統合・メッセージング層
```yaml
キューイング: Amazon SQS
  - 標準キュー (解析ジョブ)
  - FIFO キュー (順序保証が必要な処理)
  - デッドレターキュー (エラーハンドリング)

イベント: Amazon EventBridge
  - CodeCommit 連携
  - スケジュール実行
  - クロスサービス通信
```

### セキュリティ層
```yaml
認証情報: AWS Secrets Manager
  - GitHub PAT
  - Webhook 署名キー
  - データベース接続情報

暗号化: AWS KMS
  - 保存時暗号化
  - 転送時暗号化
  - キーローテーション

アクセス制御: AWS IAM
  - 最小権限の原則
  - ロールベースアクセス
  - リソースベースポリシー
```

## リソース命名規約

### 命名パターン
```
{プロジェクト名}-{環境}-{サービス名}-{リソース種別}

例:
- deepwiki-omr-prod-api-cluster
- deepwiki-omr-dev-search-domain
- deepwiki-omr-staging-wiki-bucket
```

### 環境識別子
- `prod`: 本番環境
- `staging`: ステージング環境
- `dev`: 開発環境
- `test`: テスト環境

## セキュリティ設定標準

### IAM ポリシー例
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:*:*:foundation-model/anthropic.claude-3-5-sonnet-*",
        "arn:aws:bedrock:*:*:foundation-model/amazon.titan-embed-text-v2:*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "opensearch:ESHttpPost",
        "opensearch:ESHttpPut",
        "opensearch:ESHttpGet"
      ],
      "Resource": "arn:aws:es:*:*:domain/deepwiki-omr-*/*"
    }
  ]
}
```

### VPC 設定
```yaml
VPC 構成:
  - プライベートサブネット: アプリケーション層
  - パブリックサブネット: ロードバランサー
  - NATゲートウェイ: アウトバウンド通信用

セキュリティグループ:
  - 最小限のポート開放
  - ソース IP の制限
  - アプリケーション層間の通信制御
```

## 監視・ログ設定

### CloudWatch 設定
```yaml
メトリクス:
  - API レスポンス時間
  - エラー率
  - リソース使用率
  - ジョブ処理時間

ログ:
  - アプリケーションログ
  - アクセスログ
  - エラーログ
  - 監査ログ

アラート:
  - エラー率 > 5%
  - レスポンス時間 > 5秒
  - DLQ メッセージ蓄積
  - リソース使用率 > 80%
```

### X-Ray トレーシング
```yaml
対象サービス:
  - API Gateway
  - Lambda 関数
  - ECS タスク
  - DynamoDB
  - OpenSearch

設定:
  - サンプリング率: 10%
  - 詳細トレース: エラー時
  - 保持期間: 30日
```

## コスト最適化

### リソース最適化
```yaml
ECS Fargate:
  - Spot インスタンス活用
  - 適切なタスクサイズ設定
  - 自動スケーリング設定

S3:
  - ライフサイクルポリシー
  - 適切なストレージクラス
  - 圧縮とデデュープ

DynamoDB:
  - オンデマンド vs プロビジョニング
  - TTL 設定
  - インデックス最適化
```

### 予算管理
```yaml
予算アラート:
  - 月次予算の80%到達時
  - 前月比150%増加時
  - サービス別コスト異常時

コスト配分タグ:
  - Environment: prod/staging/dev
  - Project: deepwiki-omr
  - Component: api/worker/search
  - Owner: チーム名
```

## デプロイメント戦略

### CI/CD パイプライン
```yaml
ソース: GitHub
ビルド: AWS CodeBuild
デプロイ: AWS CodeDeploy

ステージ:
  1. ソースコード取得
  2. 単体テスト実行
  3. セキュリティスキャン
  4. コンテナイメージビルド
  5. ステージング環境デプロイ
  6. 統合テスト実行
  7. 本番環境デプロイ (承認後)
```

### ブルーグリーンデプロイ
```yaml
対象サービス:
  - API サーバー
  - ワーカープロセス

切り替え戦略:
  - トラフィック段階的移行
  - ヘルスチェック確認
  - 自動ロールバック
```

## 災害復旧

### バックアップ戦略
```yaml
DynamoDB:
  - ポイントインタイムリカバリ有効
  - 日次バックアップ
  - クロスリージョンレプリケーション

S3:
  - バージョニング有効
  - クロスリージョンレプリケーション
  - MFA Delete 有効

OpenSearch:
  - 自動スナップショット
  - 手動スナップショット (重要な変更前)
```

### RTO/RPO 目標
```yaml
本番環境:
  - RTO: 4時間
  - RPO: 1時間

ステージング環境:
  - RTO: 24時間
  - RPO: 24時間
```

## コンプライアンス

### データ保護
```yaml
暗号化:
  - 保存時: AES-256
  - 転送時: TLS 1.2+
  - キー管理: AWS KMS

アクセス制御:
  - 多要素認証必須
  - 定期的なアクセス権見直し
  - 監査ログ保持
```

### 規制対応
```yaml
データ所在地:
  - 日本リージョン使用
  - データ越境制限

ログ保持:
  - アクセスログ: 1年
  - 監査ログ: 3年
  - エラーログ: 6ヶ月
```