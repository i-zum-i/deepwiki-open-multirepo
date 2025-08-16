# DeepWiki-OMR 開発環境セットアップスクリプト (PowerShell版)

param(
    [switch]$Help
)

# 色付きログ出力
function Write-InfoLog {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-SuccessLog {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-WarningLog {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-ErrorLog {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# 使用方法の表示
function Show-Usage {
    Write-Host "DeepWiki-OMR 開発環境セットアップスクリプト"
    Write-Host ""
    Write-Host "使用方法: .\dev-setup.ps1 [オプション]"
    Write-Host ""
    Write-Host "オプション:"
    Write-Host "  -Help    このヘルプを表示"
    Write-Host ""
    Write-Host "このスクリプトは以下を実行します:"
    Write-Host "  1. 前提条件のチェック"
    Write-Host "  2. 環境ファイルの作成"
    Write-Host "  3. Python仮想環境のセットアップ"
    Write-Host "  4. Node.js依存関係のインストール"
    Write-Host "  5. Dockerイメージのビルド"
    Write-Host "  6. 開発環境の起動"
    Write-Host "  7. DynamoDBテーブルの作成"
}

# 前提条件のチェック
function Test-Prerequisites {
    Write-InfoLog "前提条件をチェックしています..."

    # Docker のチェック
    try {
        docker --version | Out-Null
    }
    catch {
        Write-ErrorLog "Docker がインストールされていません"
        Write-InfoLog "インストール方法: https://docs.docker.com/get-docker/"
        exit 1
    }

    # Docker Compose のチェック
    try {
        docker-compose --version | Out-Null
    }
    catch {
        Write-ErrorLog "Docker Compose がインストールされていません"
        Write-InfoLog "インストール方法: https://docs.docker.com/compose/install/"
        exit 1
    }

    # Node.js のチェック
    try {
        node --version | Out-Null
    }
    catch {
        Write-ErrorLog "Node.js がインストールされていません"
        Write-InfoLog "インストール方法: https://nodejs.org/"
        exit 1
    }

    # Python のチェック
    try {
        python --version | Out-Null
    }
    catch {
        Write-ErrorLog "Python がインストールされていません"
        Write-InfoLog "インストール方法: https://www.python.org/downloads/"
        exit 1
    }

    Write-SuccessLog "前提条件のチェックが完了しました"
}

# 環境ファイルの作成
function New-EnvironmentFiles {
    Write-InfoLog "環境ファイルを作成しています..."

    # .env.development ファイルの作成
    if (-not (Test-Path ".env.development")) {
        $envContent = @"
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
"@
        $envContent | Out-File -FilePath ".env.development" -Encoding UTF8
        Write-SuccessLog ".env.development ファイルを作成しました"
    }
    else {
        Write-InfoLog ".env.development ファイルは既に存在します"
    }
}

# Python仮想環境のセットアップ
function Initialize-PythonEnvironment {
    Write-InfoLog "Python仮想環境をセットアップしています..."

    Set-Location api

    # 仮想環境の作成
    if (-not (Test-Path ".venv")) {
        python -m venv .venv
        Write-SuccessLog "Python仮想環境を作成しました"
    }
    else {
        Write-InfoLog "Python仮想環境は既に存在します"
    }

    # 仮想環境の有効化
    & ".venv\Scripts\Activate.ps1"

    # 依存関係のインストール
    Write-InfoLog "Python依存関係をインストールしています..."
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    pip install pytest pytest-cov pytest-asyncio pytest-mock

    Set-Location ..
    Write-SuccessLog "Python環境のセットアップが完了しました"
}

# Node.js依存関係のインストール
function Initialize-NodeEnvironment {
    Write-InfoLog "Node.js依存関係をインストールしています..."

    npm install

    Write-SuccessLog "Node.js環境のセットアップが完了しました"
}

# Dockerイメージのビルド
function Build-DockerImages {
    Write-InfoLog "Dockerイメージをビルドしています..."

    docker-compose -f docker-compose.dev.yml build

    Write-SuccessLog "Dockerイメージのビルドが完了しました"
}

# 開発環境の起動
function Start-DevelopmentEnvironment {
    Write-InfoLog "開発環境を起動しています..."

    # バックグラウンドでサービスを起動
    docker-compose -f docker-compose.dev.yml up -d

    Write-InfoLog "サービスの起動を待機しています..."
    Start-Sleep -Seconds 10

    # サービスの状態確認
    Write-InfoLog "サービスの状態を確認しています..."
    docker-compose -f docker-compose.dev.yml ps

    # ヘルスチェック
    Write-InfoLog "ヘルスチェックを実行しています..."
    
    # DynamoDB Local
    try {
        Invoke-WebRequest -Uri "http://localhost:8000/shell" -Method GET -TimeoutSec 5 | Out-Null
        Write-SuccessLog "DynamoDB Local が起動しています"
    }
    catch {
        Write-WarningLog "DynamoDB Local の起動に時間がかかっています"
    }

    # OpenSearch
    try {
        Invoke-WebRequest -Uri "http://localhost:9200/_cluster/health" -Method GET -TimeoutSec 5 | Out-Null
        Write-SuccessLog "OpenSearch が起動しています"
    }
    catch {
        Write-WarningLog "OpenSearch の起動に時間がかかっています"
    }

    # MinIO
    try {
        Invoke-WebRequest -Uri "http://localhost:9000/minio/health/live" -Method GET -TimeoutSec 5 | Out-Null
        Write-SuccessLog "MinIO が起動しています"
    }
    catch {
        Write-WarningLog "MinIO の起動に時間がかかっています"
    }

    Write-SuccessLog "開発環境が起動しました"
}

# DynamoDBテーブルの作成
function New-DynamoDBTables {
    Write-InfoLog "DynamoDBテーブルを作成しています..."

    # テーブル作成スクリプトの実行
    Set-Location api
    & ".venv\Scripts\Activate.ps1"
    
    $pythonScript = @"
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
"@

    $pythonScript | python

    Set-Location ..

    Write-SuccessLog "DynamoDBテーブルの作成が完了しました"
}

# 開発環境の情報表示
function Show-DevelopmentInfo {
    Write-InfoLog "開発環境の情報:"
    Write-Host ""
    Write-Host "🌐 フロントエンド:     http://localhost:3000" -ForegroundColor Cyan
    Write-Host "🔧 API サーバー:       http://localhost:8001" -ForegroundColor Cyan
    Write-Host "📊 DynamoDB Admin:     http://localhost:8001" -ForegroundColor Cyan
    Write-Host "🔍 OpenSearch:         http://localhost:9200" -ForegroundColor Cyan
    Write-Host "📈 OpenSearch Dashboard: http://localhost:5601" -ForegroundColor Cyan
    Write-Host "💾 MinIO Console:      http://localhost:9001 (minioadmin/minioadmin123)" -ForegroundColor Cyan
    Write-Host "🔴 Redis:              localhost:6379" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📝 ログの確認:" -ForegroundColor Yellow
    Write-Host "   docker-compose -f docker-compose.dev.yml logs -f [service_name]"
    Write-Host ""
    Write-Host "🛑 環境の停止:" -ForegroundColor Yellow
    Write-Host "   docker-compose -f docker-compose.dev.yml down"
    Write-Host ""
}

# メイン処理
function Main {
    if ($Help) {
        Show-Usage
        exit 0
    }

    Write-InfoLog "DeepWiki-OMR 開発環境セットアップを開始します"

    # 前提条件のチェック
    Test-Prerequisites

    # 環境ファイルの作成
    New-EnvironmentFiles

    # Python環境のセットアップ
    Initialize-PythonEnvironment

    # Node.js環境のセットアップ
    Initialize-NodeEnvironment

    # Dockerイメージのビルド
    Build-DockerImages

    # 開発環境の起動
    Start-DevelopmentEnvironment

    # DynamoDBテーブルの作成
    Start-Sleep -Seconds 5  # DynamoDB Localの完全起動を待機
    New-DynamoDBTables

    # 開発環境の情報表示
    Show-DevelopmentInfo

    Write-SuccessLog "開発環境のセットアップが完了しました！"
}

# スクリプトの実行
Main