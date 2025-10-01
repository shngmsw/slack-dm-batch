# デプロイガイド - Google Cloud Run

## 📋 前提条件

1. Google Cloud アカウント
2. gcloud CLI のインストール
3. Docker のインストール（オプション）

## 🚀 クイックスタート

### 1. GCP プロジェクトの準備

```bash
# gcloud CLIのインストール（未インストールの場合）
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# 認証
gcloud auth login

# プロジェクトIDの設定
PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID
```

### 2. デプロイの実行

```bash
# デプロイスクリプトを使用
./deploy.sh $PROJECT_ID asia-northeast1 slack-dm-batch

# または手動でデプロイ
gcloud run deploy slack-dm-batch \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated
```

### 3. Slack Token の設定

```bash
# Secret Manager でトークンを保存
echo -n "xoxp-your-slack-token" | gcloud secrets create slack-token --data-file=-

# Cloud Run サービスにシークレットを設定
gcloud run services update slack-dm-batch \
  --region=asia-northeast1 \
  --update-secrets=SLACK_TOKEN=slack-token:latest
```

## 🔧 詳細設定

### 環境変数

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| DEBUG | デバッグモード | false |
| LOG_LEVEL | ログレベル | INFO |
| PORT | ポート番号 | 8080 |
| SLACK_TOKEN | Slack User Token | (Secret Manager) |

### リソース設定

```bash
# メモリとCPUの調整
gcloud run services update slack-dm-batch \
  --region=asia-northeast1 \
  --memory=1Gi \
  --cpu=2
```

### スケーリング設定

```bash
# インスタンス数の調整
gcloud run services update slack-dm-batch \
  --region=asia-northeast1 \
  --min-instances=1 \
  --max-instances=100
```

## 🔐 セキュリティ

### アクセス制御

```bash
# 認証を必須にする
gcloud run services remove-iam-policy-binding slack-dm-batch \
  --region=asia-northeast1 \
  --member=allUsers \
  --role=roles/run.invoker

# 特定のユーザーにアクセス権を付与
gcloud run services add-iam-policy-binding slack-dm-batch \
  --region=asia-northeast1 \
  --member=user:email@example.com \
  --role=roles/run.invoker
```

### カスタムドメイン

```bash
# ドメインマッピング
gcloud run domain-mappings create \
  --service=slack-dm-batch \
  --domain=your-domain.com \
  --region=asia-northeast1
```

## 📊 モニタリング

### ログの確認

```bash
# リアルタイムログ
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=slack-dm-batch"

# 過去のログ
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=slack-dm-batch" \
  --limit=50 \
  --format=json
```

### メトリクスの確認

Google Cloud Console > Cloud Run > slack-dm-batch > メトリクス

## 🔄 CI/CD (GitHub Actions)

### 1. サービスアカウントの作成

```bash
# サービスアカウント作成
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions"

# 必要な権限を付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

# キーの生成
gcloud iam service-accounts keys create key.json \
  --iam-account=github-actions@$PROJECT_ID.iam.gserviceaccount.com
```

### 2. GitHub Secrets の設定

1. GitHubリポジトリの Settings > Secrets and variables > Actions
2. 以下のシークレットを追加:
   - `GCP_PROJECT_ID`: プロジェクトID
   - `GCP_SA_KEY`: key.json の内容（base64エンコード）

```bash
# key.jsonをbase64エンコード
base64 key.json
```

### 3. 自動デプロイ

mainブランチにプッシュすると自動的にデプロイされます。

## 🔨 トラブルシューティング

### ビルドエラー

```bash
# ローカルでDockerイメージをテスト
docker build -t slack-dm-batch .
docker run -p 8080:8080 -e PORT=8080 slack-dm-batch
```

### メモリ不足

```bash
# メモリを増やす
gcloud run services update slack-dm-batch \
  --region=asia-northeast1 \
  --memory=2Gi
```

### コールドスタート対策

```bash
# 最小インスタンスを1に設定
gcloud run services update slack-dm-batch \
  --region=asia-northeast1 \
  --min-instances=1
```

## 📚 参考リンク

- [Cloud Run ドキュメント](https://cloud.google.com/run/docs)
- [gcloud コマンドリファレンス](https://cloud.google.com/sdk/gcloud/reference)
- [Cloud Run 料金](https://cloud.google.com/run/pricing)