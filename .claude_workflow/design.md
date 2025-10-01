# Google Cloud Run デプロイ設計

## プラットフォーム: Google Cloud Run
選定理由:
- サーバーレスで自動スケーリング
- Dockerコンテナのネイティブサポート
- HTTPS自動設定
- 料金は使用分のみ（無料枠あり）

## アーキテクチャ設計

### 1. サービス構成
- **Cloud Run サービス**: メインアプリケーション
- **Secret Manager**: 環境変数の安全な管理
- **Cloud Logging**: ログの永続化と監視
- **Cloud Storage**: ファイルアップロードの永続化（必要に応じて）

### 2. Dockerfile の調整
現在のDockerfileの問題点と修正:
- ログディレクトリの作成が必要
- Cloud Run用のポート設定（$PORT環境変数）
- ヘルスチェックエンドポイントの考慮

### 3. 環境変数の管理
- **Secret Manager使用**:
  - SLACK_TOKEN（セキュアに管理）
- **環境変数として設定**:
  - DEBUG=false
  - LOG_LEVEL=INFO
  - PORT=8080（Cloud Runのデフォルト）

### 4. ネットワーキング
- Cloud Runの自動HTTPS設定を利用
- カスタムドメイン設定（オプション）
- リージョン選択: asia-northeast1（東京）推奨

### 5. CI/CDパイプライン
- GitHub ActionsまたはCloud Build
- 自動ビルドとデプロイ
- ブランチ別環境（dev/staging/prod）

## 必要な設定ファイル

### 1. .gcloudignore
デプロイ時に除外するファイル

### 2. cloudbuild.yaml
Cloud Buildの設定（オプション）

### 3. Dockerfile修正
Cloud Run対応版

### 4. app/main.py修正
ポート設定の動的化

## セキュリティ考慮事項
- IAM設定によるアクセス制御
- Secret Managerでの機密情報管理
- VPCコネクタ（必要に応じて）

## コスト最適化
- 最小インスタンス数: 0（コールドスタート許容）
- 最大インスタンス数: 10（初期設定）
- メモリ: 512MB（初期設定）
- CPU: 1（初期設定）

## デプロイ手順概要
1. GCPプロジェクトのセットアップ
2. 必要なAPIの有効化
3. Dockerfileと設定ファイルの修正
4. gcloudツールでのデプロイ
5. 環境変数とシークレットの設定
6. 動作確認とモニタリング設定
