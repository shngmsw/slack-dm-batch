import logging
import logging.config
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .config import settings
from .models import (
    ParseMentionsRequest, ParseMentionsResponse,
    PreviewRequest, PreviewResponse,
    SendRequest, SendResult,
    ImportVariablesResponse,
    ErrorResponse, User
)
from .slack_client import SlackClient
from .message_processor import MessageProcessor
from .user_parser import UserParser

# ログ設定
logging.config.dictConfig(settings.get_log_config())
logger = logging.getLogger(__name__)
send_results_logger = logging.getLogger("send_results")

# アプリケーション初期化
app = FastAPI(
    title=settings.APP_NAME,
    description="Slack DM Batch Sender - Send personalized DMs to multiple users",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイル配信
app.mount("/static", StaticFiles(directory="static"), name="static")

# グローバル変数（本格的なアプリケーションではRedisなどを使用）
jobs: Dict[str, SendResult] = {}
message_processor = MessageProcessor()
user_parser = UserParser()

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント（Cloud Run用）"""
    return {"status": "healthy", "service": settings.APP_NAME, "version": "1.0.0"}

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Web UIを配信"""
    try:
        with open("templates/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><title>Slack DM Batch Sender</title></head>
        <body>
            <h1>Slack DM Batch Sender</h1>
            <p>Web UI is being prepared...</p>
        </body>
        </html>
        """)

@app.post("/api/parse-mentions", response_model=ParseMentionsResponse)
async def parse_mentions(request: ParseMentionsRequest):
    """メンション解析API"""
    try:
        # Slackクライアント初期化
        slack_client = SlackClient(request.token)
        
        # トークン検証
        if not await slack_client.validate_token():
            raise HTTPException(status_code=401, detail="Invalid Slack token")
        
        # メンション抽出
        mentions = user_parser.parse_mentions(request.text)
        logger.info(f"Extracted mentions: {mentions}")
        
        # ユーザー情報解決
        users, errors = await slack_client.resolve_users_from_mentions(mentions)
        
        return ParseMentionsResponse(
            users=[User(**user) for user in users],
            errors=errors
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing mentions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/preview", response_model=PreviewResponse)
async def preview_messages(request: PreviewRequest):
    """メッセージプレビューAPI"""
    try:
        # テンプレート検証
        validation_errors = message_processor.validate_template(request.template)
        if validation_errors:
            raise HTTPException(status_code=400, detail=f"Template validation failed: {', '.join(validation_errors)}")
        
        # 変数抽出
        available_variables = message_processor.extract_variables(request.template)
        
        # ユーザーごとにレンダリング
        rendered_messages = {}
        all_missing_variables = set()
        
        for user_id, variables in request.user_data.items():
            result = message_processor.render_template_safe(request.template, variables)
            rendered_messages[user_id] = result["rendered_message"]
            all_missing_variables.update(result.get("missing_variables", []))
        
        return PreviewResponse(
            rendered_messages=rendered_messages,
            missing_variables=list(all_missing_variables),
            available_variables=available_variables
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing messages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/import-variables", response_model=ImportVariablesResponse)
async def import_variables(file: UploadFile = File(...)):
    """変数データCSV/JSONインポートAPI"""
    try:
        # ファイルサイズチェック
        if file.size and file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File too large. Max size: {settings.MAX_FILE_SIZE} bytes")
        
        # ファイル内容読み取り
        content = await file.read()
        file_content = content.decode('utf-8')
        
        # ファイル形式検証
        is_valid, format_msg = user_parser.validate_file_format(file_content, file.filename or "")
        if not is_valid:
            raise HTTPException(status_code=400, detail=format_msg)
        
        # ファイル解析
        if file.filename and file.filename.lower().endswith('.json'):
            users_data, errors = user_parser.parse_json(file_content)
        else:
            users_data, errors = user_parser.parse_csv(file_content)
        
        if errors:
            logger.warning(f"Import errors: {errors}")
        
        # 変数データを構築
        user_variables = {}
        for user_data in users_data:
            # 識別子をキーとして使用（実際の使用時にはSlackユーザーIDに解決される）
            user_variables[user_data["identifier"]] = user_data["variables"]
        
        return ImportVariablesResponse(
            imported_count=len(users_data),
            user_data=user_variables,
            errors=errors
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing variables: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/send-messages", response_model=SendResult)
async def send_messages(request: SendRequest, background_tasks: BackgroundTasks):
    """メッセージ送信API"""
    try:
        # Slackクライアント初期化
        slack_client = SlackClient(request.token)
        
        # トークン検証
        if not await slack_client.validate_token():
            raise HTTPException(status_code=401, detail="Invalid Slack token")
        
        # テンプレート検証
        validation_errors = message_processor.validate_template(request.template)
        if validation_errors:
            raise HTTPException(status_code=400, detail=f"Template validation failed: {', '.join(validation_errors)}")
        
        # ジョブ作成
        job_id = str(uuid.uuid4())
        job = SendResult(
            job_id=job_id,
            total_users=len(request.users),
            status="pending",
            started_at=datetime.utcnow()
        )
        jobs[job_id] = job
        
        # バックグラウンドで送信処理を開始
        background_tasks.add_task(
            process_send_job,
            job_id,
            request.template,
            request.users,
            request.user_data,
            slack_client
        )
        
        logger.info(f"Started send job {job_id} for {len(request.users)} users")
        return job
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting send job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/status/{job_id}", response_model=SendResult)
async def get_job_status(job_id: str):
    """送信状況確認API"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]

async def process_send_job(
    job_id: str,
    template: str,
    users: List[User],
    user_data: Dict[str, Dict[str, Any]],
    slack_client: SlackClient
):
    """バックグラウンド送信処理"""
    job = jobs[job_id]
    job.status = "running"
    
    sent_count = 0
    failed_count = 0
    errors = []
    
    try:
        send_results_logger.info(f"Starting send job {job_id} for {len(users)} users")
        
        for user in users:
            try:
                # ユーザー固有の変数を取得
                variables = user_data.get(user.id, {})
                
                # メッセージをレンダリング
                result = message_processor.render_template_safe(template, variables)
                if not result["success"]:
                    error_msg = f"Template rendering failed: {result.get('error', 'Unknown error')}"
                    errors.append({"user_id": user.id, "user_name": user.display_name, "error": error_msg})
                    failed_count += 1
                    continue
                
                rendered_message = result["rendered_message"]
                
                # DMを送信
                send_result = await slack_client.send_dm_with_retry(user.id, rendered_message)
                
                if send_result["success"]:
                    sent_count += 1
                    send_results_logger.info(f"Successfully sent DM to {user.display_name} ({user.id})")
                else:
                    failed_count += 1
                    error_msg = send_result.get("error", "Unknown error")
                    error_code = send_result.get("error_code", "unknown")
                    detailed_error = send_result.get("detailed_error", "詳細なエラー情報がありません")
                    
                    error_info = {
                        "user_id": user.id, 
                        "user_name": user.display_name, 
                        "error": error_msg,
                        "error_code": error_code,
                        "detailed_error": detailed_error
                    }
                    errors.append(error_info)
                    send_results_logger.error(f"Failed to send DM to {user.display_name} ({user.id}): {error_msg} (Code: {error_code})")
                
                # 進捗更新
                job.sent_count = sent_count
                job.failed_count = failed_count
                job.errors = errors
                
            except Exception as e:
                failed_count += 1
                error_msg = f"Unexpected error: {str(e)}"
                errors.append({"user_id": user.id, "user_name": user.display_name, "error": error_msg})
                logger.error(f"Error sending to {user.display_name} ({user.id}): {error_msg}")
        
        # ジョブ完了
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        
        send_results_logger.info(f"Completed send job {job_id}: {sent_count} sent, {failed_count} failed")
        
    except Exception as e:
        job.status = "failed"
        job.completed_at = datetime.utcnow()
        error_msg = f"Job failed: {str(e)}"
        job.errors.append({"error": error_msg})
        logger.error(f"Send job {job_id} failed: {error_msg}")

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", settings.PORT))
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=port,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )