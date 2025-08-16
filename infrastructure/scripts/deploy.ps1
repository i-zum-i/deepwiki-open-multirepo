# DeepWiki-OMR インフラストラクチャデプロイスクリプト (PowerShell版)

param(
    [Parameter(Position=0)]
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment,
    
    [string]$Stack,
    [switch]$Diff,
    [switch]$Approve,
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
    Write-Host "使用方法: .\deploy.ps1 [環境] [オプション]"
    Write-Host ""
    Write-Host "環境:"
    Write-Host "  dev       開発環境"
    Write-Host "  staging   ステージング環境"
    Write-Host "  prod      本番環境"
    Write-Host ""
    Write-Host "オプション:"
    Write-Host "  -Stack STACK_NAME  特定のスタックのみデプロイ"
    Write-Host "  -Diff              変更内容の確認のみ"
    Write-Host "  -Approve           確認なしでデプロイ"
    Write-Host "  -Help              このヘルプを表示"
    Write-Host ""
    Write-Host "例:"
    Write-Host "  .\deploy.ps1 dev                    # 開発環境の全スタックをデプロイ"
    Write-Host "  .\deploy.ps1 prod -Diff             # 本番環境の変更内容を確認"
    Write-Host "  .\deploy.ps1 staging -Stack data    # ステージング環境のデータスタックのみデプロイ"
}

# 前提条件のチェック
function Test-Prerequisites {
    Write-InfoLog "前提条件をチェックしています..."

    # AWS CLI のチェック
    try {
        aws --version | Out-Null
    }
    catch {
        Write-ErrorLog "AWS CLI がインストールされていません"
        exit 1
    }

    # CDK CLI のチェック
    try {
        cdk --version | Out-Null
    }
    catch {
        Write-ErrorLog "AWS CDK CLI がインストールされていません"
        Write-InfoLog "インストール方法: npm install -g aws-cdk"
        exit 1
    }

    # Python のチェック
    try {
        python --version | Out-Null
    }
    catch {
        Write-ErrorLog "Python がインストールされていません"
        exit 1
    }

    # AWS 認証情報のチェック
    try {
        aws sts get-caller-identity | Out-Null
    }
    catch {
        Write-ErrorLog "AWS 認証情報が設定されていません"
        Write-InfoLog "設定方法: aws configure"
        exit 1
    }

    Write-SuccessLog "前提条件のチェックが完了しました"
}

# CDK 環境のセットアップ
function Initialize-CdkEnvironment {
    Write-InfoLog "CDK 環境をセットアップしています..."

    # CDK ディレクトリに移動
    $cdkPath = Join-Path (Split-Path $PSScriptRoot -Parent) "cdk"
    Set-Location $cdkPath

    # 仮想環境の作成（存在しない場合）
    if (-not (Test-Path ".venv")) {
        Write-InfoLog "Python 仮想環境を作成しています..."
        python -m venv .venv
    }

    # 仮想環境の有効化
    & ".venv\Scripts\Activate.ps1"

    # 依存関係のインストール
    Write-InfoLog "依存関係をインストールしています..."
    pip install -r requirements.txt | Out-Null

    Write-SuccessLog "CDK 環境のセットアップが完了しました"
}

# CDK Bootstrap のチェック
function Test-CdkBootstrap {
    param([string]$Environment)
    
    Write-InfoLog "CDK Bootstrap の状態をチェックしています..."

    # Bootstrap の確認（簡易チェック）
    try {
        cdk bootstrap --show-template | Out-Null
        Write-SuccessLog "CDK Bootstrap は既に実行済みです"
    }
    catch {
        Write-WarningLog "CDK Bootstrap が必要です"
        $response = Read-Host "CDK Bootstrap を実行しますか？ (y/N)"
        if ($response -eq "y" -or $response -eq "Y") {
            Write-InfoLog "CDK Bootstrap を実行しています..."
            cdk bootstrap -c environment=$Environment
            Write-SuccessLog "CDK Bootstrap が完了しました"
        }
        else {
            Write-ErrorLog "CDK Bootstrap が必要です。手動で実行してください: cdk bootstrap"
            exit 1
        }
    }
}

# デプロイの実行
function Invoke-StackDeploy {
    param(
        [string]$Environment,
        [string]$StackName,
        [bool]$DiffOnly,
        [bool]$AutoApprove
    )

    Write-InfoLog "デプロイを開始します..."
    Write-InfoLog "環境: $Environment"

    # デプロイ対象の決定
    $deployTarget = "--all"
    if ($StackName) {
        $deployTarget = "deepwiki-omr-$Environment-$StackName"
        Write-InfoLog "対象スタック: $StackName"
    }
    else {
        Write-InfoLog "対象: 全スタック"
    }

    # 変更内容の確認
    if ($DiffOnly) {
        Write-InfoLog "変更内容を確認しています..."
        cdk diff $deployTarget -c environment=$Environment
        return
    }

    # 変更内容の表示（diff_only でない場合）
    Write-InfoLog "変更内容を表示しています..."
    try {
        cdk diff $deployTarget -c environment=$Environment
    }
    catch {
        # diff でエラーが出ても続行
    }

    # 確認プロンプト
    if (-not $AutoApprove) {
        Write-Host ""
        $response = Read-Host "デプロイを続行しますか？ (y/N)"
        if ($response -ne "y" -and $response -ne "Y") {
            Write-InfoLog "デプロイをキャンセルしました"
            exit 0
        }
    }

    # デプロイの実行
    Write-InfoLog "デプロイを実行しています..."
    
    $deployCmd = "cdk deploy $deployTarget -c environment=$Environment"
    
    if ($AutoApprove) {
        $deployCmd += " --require-approval never"
    }

    Invoke-Expression $deployCmd

    Write-SuccessLog "デプロイが完了しました"
}

# 本番環境デプロイの追加確認
function Confirm-ProductionDeploy {
    param([string]$Environment)
    
    if ($Environment -eq "prod") {
        Write-WarningLog "本番環境へのデプロイを実行しようとしています"
        Write-Host ""
        Write-Host "本番環境への影響を十分に理解していることを確認してください："
        Write-Host "- データの損失や破損の可能性"
        Write-Host "- サービスの一時的な停止"
        Write-Host "- 予期しない費用の発生"
        Write-Host ""
        
        $response = Read-Host "本当に本番環境にデプロイしますか？ (yes/no)"
        if ($response -ne "yes") {
            Write-InfoLog "本番環境へのデプロイをキャンセルしました"
            exit 0
        }
        
        Write-WarningLog "最終確認: 本番環境にデプロイします"
        $finalResponse = Read-Host "続行するには 'DEPLOY' と入力してください"
        if ($finalResponse -ne "DEPLOY") {
            Write-InfoLog "本番環境へのデプロイをキャンセルしました"
            exit 0
        }
    }
}

# メイン処理
function Main {
    # ヘルプの表示
    if ($Help -or -not $Environment) {
        Show-Usage
        if (-not $Environment) {
            Write-ErrorLog "環境を指定してください"
            exit 1
        }
        exit 0
    }

    Write-InfoLog "DeepWiki-OMR インフラストラクチャデプロイを開始します"
    Write-InfoLog "環境: $Environment"

    # 前提条件のチェック
    Test-Prerequisites

    # CDK 環境のセットアップ
    Initialize-CdkEnvironment

    # CDK Bootstrap のチェック
    Test-CdkBootstrap $Environment

    # 本番環境の追加確認
    Confirm-ProductionDeploy $Environment

    # デプロイの実行
    Invoke-StackDeploy $Environment $Stack $Diff $Approve

    Write-SuccessLog "すべての処理が完了しました"
}

# スクリプトの実行
Main