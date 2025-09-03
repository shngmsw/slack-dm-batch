FROM python:3.9-slim

WORKDIR /app

# 依存関係をコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY app/ ./app/
COPY static/ ./static/
COPY templates/ ./templates/
COPY logs/ ./logs/

# ポートを公開
EXPOSE 8000

# アプリケーションを起動
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]