FROM python:3.9-slim

WORKDIR /app

# 依存関係をコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY app/ ./app/
COPY static/ ./static/
COPY templates/ ./templates/

# ログディレクトリを作成（Cloud Run用）
RUN mkdir -p /app/logs && chmod 755 /app/logs

# Cloud Runはポートを環境変数で指定
EXPOSE 8080

# 非rootユーザーで実行（セキュリティベストプラクティス）
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

# アプリケーションを起動（PORT環境変数を使用）
CMD exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}