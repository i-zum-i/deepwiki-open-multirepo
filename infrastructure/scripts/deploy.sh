#!/bin/bash

# DeepWiki-OMR インフラストラクチャデプロイスクリプト

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

# 使用方法の表示
show_usage() {
    echo "使用方法: $0 [環境] [オプション]"
    echo ""
    echo "環境:"
    echo "  dev       開発環境"
    echo "  staging   ステージング環境"
    echo "  prod      本番環境"
    echo ""
    echo "オプション:"
    echo "  --stack STACK_NAME  特定のスタックのみデプロイ"
    echo "  --diff              変更内容の確認のみ"
    echo "  --approve           確認なしでデプロイ"
    echo "  --help              このヘルプを表示"
    echo ""
    echo "例:"
    echo "  $0 dev                    # 開発環境の全スタックをデプロイ"
    echo "  $0 prod --diff            # 本番環境の変更内容を確認"
    echo "  $0 staging --stack data   # ステージング環境のデータスタックのみデプロイ"
}

# 前提条件のチェック
check_prerequisites() {
    log_info "前提条件をチェックしています..."

    # AWS CLI のチェック
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI がインストールされていません"
        exit 1
    fi

    # CDK CLI のチェック
    if ! command -v cdk &> /dev/null; then
        log_error "AWS CDK CLI がインストールされていません"
        log_info "インストール方法: npm install -g aws-cdk"
        exit 1
    fi

    # Python のチェック
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 がインストールされていません"
        exit 1
    fi

    # AWS 認証情報のチェック
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS 認証情報が設定されていません"
        log_info "設定方法: aws configure"
        exit 1
    fi

    log_success "前提条件のチェックが完了しました"
}

# CDK 環境のセットアップ
setup_cdk_environment() {
    log_info "CDK 環境をセットアップしています..."

    # CDK ディレクトリに移動
    cd "$(dirname "$0")/../cdk"

    # 仮想環境の作成（存在しない場合）
    if [ ! -d ".venv" ]; then
        log_info "Python 仮想環境を作成しています..."
        python3 -m venv .venv
    fi

    # 仮想環境の有効化
    source .venv/bin/activate

    # 依存関係のインストール
    log_info "依存関係をインストールしています..."
    pip install -r requirements.txt > /dev/null

    log_success "CDK 環境のセットアップが完了しました"
}

# CDK Bootstrap のチェック
check_cdk_bootstrap() {
    local environment=$1
    log_info "CDK Bootstrap の状態をチェックしています..."

    # Bootstrap の確認
    if ! cdk bootstrap --show-template &> /dev/null; then
        log_warning "CDK Bootstrap が必要です"
        read -p "CDK Bootstrap を実行しますか？ (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "CDK Bootstrap を実行しています..."
            cdk bootstrap -c environment="$environment"
            log_success "CDK Bootstrap が完了しました"
        else
            log_error "CDK Bootstrap が必要です。手動で実行してください: cdk bootstrap"
            exit 1
        fi
    else
        log_success "CDK Bootstrap は既に実行済みです"
    fi
}

# デプロイの実行
deploy_stacks() {
    local environment=$1
    local stack_name=$2
    local diff_only=$3
    local auto_approve=$4

    log_info "デプロイを開始します..."
    log_info "環境: $environment"

    # デプロイ対象の決定
    local deploy_target="--all"
    if [ -n "$stack_name" ]; then
        deploy_target="deepwiki-omr-$environment-$stack_name"
        log_info "対象スタック: $stack_name"
    else
        log_info "対象: 全スタック"
    fi

    # 変更内容の確認
    if [ "$diff_only" = "true" ]; then
        log_info "変更内容を確認しています..."
        cdk diff $deploy_target -c environment="$environment"
        return 0
    fi

    # 変更内容の表示（diff_only でない場合）
    log_info "変更内容を表示しています..."
    cdk diff $deploy_target -c environment="$environment" || true

    # 確認プロンプト
    if [ "$auto_approve" != "true" ]; then
        echo
        read -p "デプロイを続行しますか？ (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "デプロイをキャンセルしました"
            exit 0
        fi
    fi

    # デプロイの実行
    log_info "デプロイを実行しています..."
    
    local deploy_cmd="cdk deploy $deploy_target -c environment=$environment"
    
    if [ "$auto_approve" = "true" ]; then
        deploy_cmd="$deploy_cmd --require-approval never"
    fi

    eval $deploy_cmd

    log_success "デプロイが完了しました"
}

# 本番環境デプロイの追加確認
confirm_production_deploy() {
    local environment=$1
    
    if [ "$environment" = "prod" ]; then
        log_warning "本番環境へのデプロイを実行しようとしています"
        echo
        echo "本番環境への影響を十分に理解していることを確認してください："
        echo "- データの損失や破損の可能性"
        echo "- サービスの一時的な停止"
        echo "- 予期しない費用の発生"
        echo
        read -p "本当に本番環境にデプロイしますか？ (yes/no): " -r
        if [ "$REPLY" != "yes" ]; then
            log_info "本番環境へのデプロイをキャンセルしました"
            exit 0
        fi
        
        log_warning "最終確認: 本番環境にデプロイします"
        read -p "続行するには 'DEPLOY' と入力してください: " -r
        if [ "$REPLY" != "DEPLOY" ]; then
            log_info "本番環境へのデプロイをキャンセルしました"
            exit 0
        fi
    fi
}

# メイン処理
main() {
    local environment=""
    local stack_name=""
    local diff_only=false
    local auto_approve=false

    # 引数の解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            dev|staging|prod)
                environment="$1"
                shift
                ;;
            --stack)
                stack_name="$2"
                shift 2
                ;;
            --diff)
                diff_only=true
                shift
                ;;
            --approve)
                auto_approve=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log_error "不明なオプション: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # 環境の指定チェック
    if [ -z "$environment" ]; then
        log_error "環境を指定してください"
        show_usage
        exit 1
    fi

    # 有効な環境かチェック
    if [[ ! "$environment" =~ ^(dev|staging|prod)$ ]]; then
        log_error "無効な環境: $environment"
        show_usage
        exit 1
    fi

    log_info "DeepWiki-OMR インフラストラクチャデプロイを開始します"
    log_info "環境: $environment"

    # 前提条件のチェック
    check_prerequisites

    # CDK 環境のセットアップ
    setup_cdk_environment

    # CDK Bootstrap のチェック
    check_cdk_bootstrap "$environment"

    # 本番環境の追加確認
    confirm_production_deploy "$environment"

    # デプロイの実行
    deploy_stacks "$environment" "$stack_name" "$diff_only" "$auto_approve"

    log_success "すべての処理が完了しました"
}

# スクリプトの実行
main "$@"