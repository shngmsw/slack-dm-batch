#!/bin/bash

# Google Cloud Run デプロイスクリプト
# 使用方法: ./deploy.sh [PROJECT_ID] [REGION] [SERVICE_NAME]

set -e

# デフォルト値
PROJECT_ID=${1:-"slack-dm-batch"}
REGION=${2:-"asia-northeast1"}
SERVICE_NAME=${3:-"slack-dm-batch"}

# 色付きログ出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 必要なパラメータのチェック
if [ "$PROJECT_ID" == "your-project-id" ]; then
    log_error "PROJECT_IDを指定してください"
    echo "使用方法: ./deploy.sh [PROJECT_ID] [REGION] [SERVICE_NAME]"
    echo "例: ./deploy.sh my-project asia-northeast1 slack-dm-batch"
    exit 1
fi

log_info "デプロイを開始します..."
log_info "Project: $PROJECT_ID"
log_info "Region: $REGION"
log_info "Service: $SERVICE_NAME"

# gcloud設定
log_info "GCP プロジェクトを設定中..."
gcloud config set project $PROJECT_ID

# 必要なAPIの有効化
log_info "必要なAPIを有効化中..."
gcloud services enable run.googleapis.com \
    containerregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com

# Dockerイメージのビルドとプッシュ
IMAGE_URL="gcr.io/$PROJECT_ID/$SERVICE_NAME"
log_info "Dockerイメージをビルド中: $IMAGE_URL"
gcloud builds submit --tag $IMAGE_URL .

# Cloud Runへのデプロイ
log_info "Cloud Runにデプロイ中..."
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_URL \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0 \
    --port 8080 \
    --set-env-vars "DEBUG=false,LOG_LEVEL=INFO"

# サービスURLの取得
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --format 'value(status.url)')

log_info "デプロイが完了しました！"
log_info "Service URL: $SERVICE_URL"

# ヘルスチェック
log_info "ヘルスチェックを実行中..."
if curl -s "$SERVICE_URL/health" | grep -q "healthy"; then
    log_info "ヘルスチェック成功！"
else
    log_warn "ヘルスチェックに失敗しました。手動で確認してください。"
fi

echo ""
log_info "次のステップ:"
echo "1. Secret Managerで SLACK_TOKEN を設定:"
echo "   gcloud secrets create slack-token --data-file=- # (トークンを入力してEnter, Ctrl+D)"
echo "   gcloud run services update $SERVICE_NAME \\"
echo "     --region=$REGION \\"
echo "     --update-secrets=SLACK_TOKEN=slack-token:latest"
echo ""
echo "2. カスタムドメインを設定する場合:"
echo "   gcloud run domain-mappings create --service=$SERVICE_NAME \\"
echo "     --domain=your-domain.com --region=$REGION"
echo ""
echo "3. アクセス制御を設定する場合:"
echo "   gcloud run services remove-iam-policy-binding $SERVICE_NAME \\"
echo "     --region=$REGION --member=allUsers --role=roles/run.invoker"