import asyncio
import logging
from typing import Optional, Dict, Any, List
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
import time
from .config import settings

logger = logging.getLogger(__name__)

class SlackClient:
    def __init__(self, token: str):
        self.token = token
        self.client = AsyncWebClient(token=token)
        self.last_request_time = 0
        self._users_cache = None
        self._cache_timestamp = 0
        self._cache_duration = 300  # 5分でキャッシュを無効化
        
    async def validate_token(self) -> bool:
        """トークンの有効性を検証"""
        try:
            response = await self.client.auth_test()
            return response["ok"]
        except SlackApiError as e:
            logger.error(f"Token validation failed: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return False
    
    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """ユーザーIDからユーザー情報を取得"""
        try:
            await self._rate_limit()
            response = await self.client.users_info(user=user_id)
            if response["ok"]:
                user = response["user"]
                return {
                    "id": user["id"],
                    "name": user["name"],
                    "display_name": user.get("profile", {}).get("display_name") or user["real_name"] or user["name"],
                    "real_name": user.get("real_name"),
                    "email": user.get("profile", {}).get("email")
                }
            return None
        except SlackApiError as e:
            logger.error(f"Failed to get user info for {user_id}: {e.response['error']}")
            return None
        except Exception as e:
            logger.error(f"Error getting user info for {user_id}: {str(e)}")
            return None
    
    async def _get_users_list(self) -> List[Dict[str, Any]]:
        """ユーザーリストを取得（キャッシュ付き）"""
        current_time = time.time()
        
        # キャッシュが有効な場合はそれを返す
        if (self._users_cache is not None and 
            current_time - self._cache_timestamp < self._cache_duration):
            return self._users_cache
        
        try:
            await self._rate_limit()
            response = await self.client.users_list()
            if response["ok"]:
                self._users_cache = response["members"]
                self._cache_timestamp = current_time
                logger.info(f"Updated users cache with {len(self._users_cache)} users")
                return self._users_cache
            return []
        except SlackApiError as e:
            logger.error(f"Failed to get users list: {e.response['error']}")
            return []
        except Exception as e:
            logger.error(f"Error getting users list: {str(e)}")
            return []

    async def get_user_by_name(self, display_name: str) -> Optional[Dict[str, Any]]:
        """表示名からユーザー情報を取得（キャッシュされたユーザーリストから検索）"""
        users = await self._get_users_list()
        
        for user in users:
            if user.get("deleted"):
                continue
            
            # 複数の名前パターンをチェック
            names_to_check = [
                user["name"],
                user.get("real_name", ""),
                user.get("profile", {}).get("display_name", ""),
                user.get("profile", {}).get("real_name", "")
            ]
            
            # @を除去した表示名でも比較
            clean_display_name = display_name.lstrip("@")
            
            for name in names_to_check:
                if name and (name == display_name or name == clean_display_name):
                    return {
                        "id": user["id"],
                        "name": user["name"],
                        "display_name": user.get("profile", {}).get("display_name") or user.get("real_name") or user["name"],
                        "real_name": user.get("real_name"),
                        "email": user.get("profile", {}).get("email")
                    }
        return None
    
    async def send_dm(self, user_id: str, message: str) -> Dict[str, Any]:
        """ユーザーにDMを送信"""
        try:
            await self._rate_limit()
            
            # DMチャンネルを開く
            channel_response = await self.client.conversations_open(users=[user_id])
            if not channel_response["ok"]:
                error_code = channel_response.get('error', 'unknown')
                return {
                    "success": False,
                    "error": f"Failed to open DM channel: {error_code}",
                    "error_code": error_code,
                    "detailed_error": self._get_detailed_error_message(error_code)
                }
            
            channel_id = channel_response["channel"]["id"]
            
            # メッセージを送信
            message_response = await self.client.chat_postMessage(
                channel=channel_id,
                text=message
            )
            
            if message_response["ok"]:
                return {
                    "success": True,
                    "message_ts": message_response["ts"],
                    "channel": channel_id
                }
            else:
                error_code = message_response.get('error', 'unknown')
                return {
                    "success": False,
                    "error": f"Failed to send message: {error_code}",
                    "error_code": error_code,
                    "detailed_error": self._get_detailed_error_message(error_code)
                }
                
        except SlackApiError as e:
            error_code = e.response.get('error', 'unknown')
            error_msg = f"Slack API error: {error_code}"
            logger.error(f"Failed to send DM to {user_id}: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "error_code": error_code,
                "detailed_error": self._get_detailed_error_message(error_code)
            }
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Failed to send DM to {user_id}: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "error_code": "system_error",
                "detailed_error": "予期しないエラーが発生しました。ログを確認してください。"
            }
    
    def _get_detailed_error_message(self, error_code: str) -> str:
        """エラーコードから詳細なエラーメッセージを生成"""
        error_messages = {
            "missing_scope": "権限不足: Slackアプリに以下の権限が必要です:\n• chat:write (メッセージ送信)\n• users:read (ユーザー情報取得)\n• im:write (DM送信)\n\n解決方法:\n1. https://api.slack.com/apps であなたのSlackアプリを開く\n2. 「OAuth & Permissions」ページで上記のスコープを追加\n3. ワークスペースに再インストール\n4. 新しいUser OAuth Tokenを取得",
            
            "not_authed": "認証エラー: トークンが無効または期限切れです。\n• 正しいUser OAuth Token (xoxp-) を使用していることを確認\n• トークンが期限切れでないか確認",
            
            "token_revoked": "トークンが無効化されました。\n• 新しいトークンを取得して再設定してください",
            
            "account_inactive": "アカウントが無効です。\n• Slackワークスペースでアカウントが有効か確認してください",
            
            "channel_not_found": "DMチャンネルが作成できませんでした。\n• 対象ユーザーが存在するか確認\n• 対象ユーザーがワークスペースのメンバーか確認",
            
            "user_not_found": "ユーザーが見つかりません。\n• ユーザー名またはユーザーIDが正しいか確認\n• ユーザーがワークスペースのメンバーか確認",
            
            "cant_dm_bot": "ボットにはDMを送信できません。",
            
            "user_disabled": "無効化されたユーザーです。",
            
            "rate_limited": "API呼び出し制限に達しました。しばらく待ってから再試行してください。",
            
            "team_access_not_granted": "このワークスペースへのアクセス権限がありません。"
        }
        
        return error_messages.get(error_code, f"不明なエラー: {error_code}\n詳細はSlack APIドキュメントを確認してください。")
    
    async def send_dm_with_retry(self, user_id: str, message: str, max_retries: int = None) -> Dict[str, Any]:
        """リトライ機能付きのDM送信"""
        if max_retries is None:
            max_retries = settings.SLACK_MAX_RETRIES
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            result = await self.send_dm(user_id, message)
            
            if result["success"]:
                if attempt > 0:
                    logger.info(f"Successfully sent DM to {user_id} after {attempt} retries")
                return result
            
            last_error = result["error"]
            
            # 最終試行でなければ待機
            if attempt < max_retries:
                wait_time = (2 ** attempt) * settings.SLACK_RATE_LIMIT_DELAY
                logger.warning(f"Attempt {attempt + 1} failed for {user_id}: {last_error}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
        
        logger.error(f"All {max_retries + 1} attempts failed for {user_id}: {last_error}")
        return {
            "success": False,
            "error": f"Failed after {max_retries + 1} attempts: {last_error}"
        }
    
    async def _rate_limit(self):
        """レート制限を遵守するための待機"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < settings.SLACK_RATE_LIMIT_DELAY:
            wait_time = settings.SLACK_RATE_LIMIT_DELAY - time_since_last
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    async def resolve_users_from_mentions(self, mentions: List[str]) -> tuple[List[Dict[str, Any]], List[str]]:
        """メンションリストからユーザー情報を解決（効率化版）"""
        users = []
        errors = []
        
        # 一度だけユーザーリストを取得
        all_users = await self._get_users_list()
        
        for mention in mentions:
            clean_mention = mention.strip().lstrip("@")
            if not clean_mention:
                continue
            
            # キャッシュされたリストから検索（API呼び出し不要）
            user_info = self._find_user_in_list(all_users, clean_mention)
            if user_info:
                users.append(user_info)
            else:
                errors.append(f"User not found: {mention}")
        
        return users, errors
    
    def _find_user_in_list(self, users: List[Dict[str, Any]], display_name: str) -> Optional[Dict[str, Any]]:
        """ユーザーリストから指定した名前のユーザーを検索"""
        for user in users:
            if user.get("deleted"):
                continue
            
            # 複数の名前パターンをチェック
            names_to_check = [
                user["name"],
                user.get("real_name", ""),
                user.get("profile", {}).get("display_name", ""),
                user.get("profile", {}).get("real_name", "")
            ]
            
            for name in names_to_check:
                if name and name == display_name:
                    return {
                        "id": user["id"],
                        "name": user["name"],
                        "display_name": user.get("profile", {}).get("display_name") or user.get("real_name") or user["name"],
                        "real_name": user.get("real_name"),
                        "email": user.get("profile", {}).get("email")
                    }
        return None