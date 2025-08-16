#!/bin/bash

# DeepWiki-OMR 開発環境セットアップスクリプト

set -e

# 色付きログ出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 前提条件のチェック
check_prerequisites() {
    log_info "前提条件をチェックしています..."

    # Docker のチェック
    if ! command -v docker &> /dev/null; then
        log_error "Docker がインストールされていません"
        log_info "インストール方法: https://docs.docker.com/get-docker/"
        exit 1
    fi

    # Docker Compose のチェック
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose がインストールされていません"
        log_info "インストール方法: https://docs.docker.com/compose/install/"
        exit 1
    fi

    # Node.js のチェック
    if ! command -v node &> /dev/null; then
        log_error "Node.js がインストールされていません"
        log_info "インストール方法: https://nodejs.org/"
        exit 1
    fi

    # Python のチェック
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 がインストールされていません"
        log_info "インストール方法: https://www.python.org/downloads/"
        exit 1
    fi

    log_success "前提条件のチェックが完了しました"
}

# 環境ファイルの作成
create_env_files() {
    log_info "環境ファイルを作成しています..."

    # .env.development ファイルの作成
    if [ ! -f ".env.development" ]; then
        cat > .env.development << EOF
# 開発環境設定
ENVIRONMENT=development
NODE_ENV=development

# API設定
API_PORT=8001
NEXT_PUBLIC_API_URL=http://localhost:8001

# AWS設定（ローカル開発用）
AWS_DEFAULT_REGION=ap-northeast-1
AWS_ACCESS_KEY_ID=dummy
AWS_SECRET_ACCESS_KEY=dummy

# DynamoDB Local
DYNAMODB_ENDPOINT=http://localhost:8000
DYNAMODB_REPOS_TABLE=deepwiki-omr-dev-repos
DYNAMODB_PAGES_TABLE=deepwiki-omr-dev-pages
DYNAMODB_JOBS_TABLE=deepwiki-omr-dev-jobs

# OpenSearch
OPENSEARCH_ENDPOINT=http://localhost:9200

# S3 (MinIO)
S3_ENDPOINT=http://localhost:9000
S3_CONTENT_BUCKET=deepwiki-omr-dev-content

# Redis (SQS代替)
REDIS_URL=redis://localhost:6379

# MinIO設定
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123

# デバッグ設定
DEBUG=true
LOG_LEVEL=DEBUG
EOF
        log_success ".env.development ファイルを作成しました"
    else
        log_info ".env.development ファイルは既に存在します"
    fi
}

# Python仮想環境のセットアップ
setup_python_env() {
    log_info "Python仮想環境をセットアップしています..."

    cd api

    # 仮想環境の作成
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
        log_success "Python仮想環境を作成しました"
    else
        log_info "Python仮想環境は既に存在します"
    fi

    # 仮想環境の有効化
    source .venv/bin/activate

    # 依存関係のインストール
    log_info "Python依存関係をインストールしています..."
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install pytest pytest-cov pytest-asyncio pytest-mock

    cd ..
    log_success "Python環境のセットアップが完了しました"
}

# Node.js依存関係のインストール
setup_node_env() {
    log_info "Node.js依存関係をインストールしています..."

    npm install

    log_success "Node.js環境のセットアップが完了しました"
}

# Dockerイメージのビルド
build_docker_images() {
    log_info "Dockerイメージをビルドしています..."

    docker-compose -f docker-compose.dev.yml build

    log_success "Dockerイメージのビルドが完了しました"
}

# 開発環境の起動
start_dev_environment() {
    log_info "開発環境を起動しています..."

    # バックグラウンドでサービスを起動
    docker-compose -f docker-compose.dev.yml up -d

    log_info "サービスの起動を待機しています..."
    sleep 10

    # サービスの状態確認
    log_info "サービスの状態を確認しています..."
    docker-compose -f docker-compose.dev.yml ps

    # ヘルスチェック
    log_info "ヘルスチェックを実行しています..."
    
    # DynamoDB Local
    if curl -f http://localhost:8000/shell &> /dev/null; then
        log_success "DynamoDB Local が起動しています"
    else
        log_warning "DynamoDB Local の起動に時間がかかっています"
    fi

    # OpenSearch
    if curl -f http://localhost:9200/_cluster/health &> /dev/null; then
        log_success "OpenSearch が起動しています"
    else
        log_warning "OpenSearch の起動に時間がかかっています"
    fi

    # MinIO
    if curl -f http://localhost:9000/minio/health/live &> /dev/null; then
        log_success "MinIO が起動しています"
    else
        log_warning "MinIO の起動に時間がかかっています"
    fi

    # Redis
    if redis-cli -h localhost -p 6379 ping &> /dev/null; then
        log_success "Redis が起動しています"
    else
        log_warning "Redis の起動に時間がかかっています"
    fi

    log_success "開発環境が起動しました"
}

# DynamoDBテーブルの作成
create_dynamodb_tables() {
    log_info "DynamoDBテーブルを作成しています..."

    # テーブル作成スクリプトの実行
    cd api
    source .venv/bin/activate
    python -c "
import boto3
from api.config import create_dev_tables

# DynamoDB Localに接続
dynamodb = boto3.resource('dynamodb', 
                          endpoint_url='http://localhost:8000',
                          region_name='ap-northeast-1',
                          aws_access_key_id='dummy',
                          aws_secret_access_key='dummy')

# 開発用テーブルを作成
create_dev_tables(dynamodb)
print('Development tables created successfully')
"
    cd ..

    log_success "DynamoDBテーブルの作成が完了しました"
}

# 開発環境の情報表示
show_dev_info() {
    log_info "開発環境の情報:"
    echo ""
    echo "🌐 フロントエンド:     http://localhost:3000"
    echo "🔧 API サーバー:       http://localhost:8001"
    echo "📊 DynamoDB Admin:     http://localhost:8001"
    echo "🔍 OpenSearch:         http://localhost:9200"
    echo "📈 OpenSearch Dashboard: http://localhost:5601"
    echo "💾 MinIO Console:      http://localhost:9001 (minioadmin/minioadmin123)"
    echo "🔴 Redis:              localhost:6379"
    echo ""
    echo "📝 ログの確認:"
    echo "   docker-compose -f docker-compose.dev.yml logs -f [service_name]"
    echo ""
    echo "🛑 環境の停止:"
    echo "   docker-compose -f docker-compose.dev.yml down"
    echo ""
}

# メイン処理
main() {
    log_info "DeepWiki-OMR 開発環境セットアップを開始します"

    # 前提条件のチェック
    check_prerequisites

    # 環境ファイルの作成
    create_env_files

    # Python環境のセットアップ
    setup_python_env

    # Node.js環境のセットアップ
    setup_node_env

    # Dockerイメージのビルド
    build_docker_images

    # 開発環境の起動
    start_dev_environment

    # DynamoDBテーブルの作成
    sleep 5  # DynamoDB Localの完全起動を待機
    create_dynamodb_tables

    # 開発環境の情報表示
    show_dev_info

    log_success "開発環境のセットアップが完了しました！"
}

# スクリプトの実行
main "$@"