import re
import csv
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from io import StringIO
from .slack_client import SlackClient

logger = logging.getLogger(__name__)

class UserParser:
    def __init__(self):
        # メンションパターン: @ユーザー名 (日本語文字も含む)
        self.mention_pattern = re.compile(r'@([a-zA-Z0-9._\-\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\u3400-\u4DBF\uFF00-\uFFEF]+)')
    
    def parse_mentions(self, text: str) -> List[str]:
        """テキストからメンションを抽出"""
        if not text:
            return []
        
        # @マークを含むユーザー名を抽出
        mentions = self.mention_pattern.findall(text)
        
        # 重複を除去して順序を保持
        unique_mentions = []
        seen = set()
        for mention in mentions:
            if mention not in seen:
                unique_mentions.append(mention)
                seen.add(mention)
        
        return unique_mentions
    
    def parse_csv(self, file_content: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """CSVファイルの内容を解析"""
        users_data = []
        errors = []
        
        try:
            # CSVを解析
            reader = csv.DictReader(StringIO(file_content))
            
            # ヘッダーの確認
            if not reader.fieldnames:
                errors.append("CSV file is empty or has no headers")
                return users_data, errors
            
            # 必須フィールドの確認
            required_fields = ['user_id']  # 最低限user_idが必要
            alternative_fields = ['username', 'display_name', 'name']  # user_idの代替
            
            has_user_identifier = any(field in reader.fieldnames for field in required_fields + alternative_fields)
            if not has_user_identifier:
                errors.append(f"CSV must contain at least one of: {required_fields + alternative_fields}")
                return users_data, errors
            
            # 各行を処理
            for row_num, row in enumerate(reader, start=2):  # ヘッダーを考慮して2から開始
                if not any(row.values()):  # 空行をスキップ
                    continue
                
                # ユーザー識別子を取得
                user_identifier = None
                identifier_type = None
                
                for field in required_fields + alternative_fields:
                    if field in row and row[field] and row[field].strip():
                        user_identifier = row[field].strip()
                        identifier_type = field
                        break
                
                if not user_identifier:
                    errors.append(f"Row {row_num}: No valid user identifier found")
                    continue
                
                # ユーザーデータを構築
                user_data = {
                    "identifier": user_identifier,
                    "identifier_type": identifier_type,
                    "variables": {}
                }
                
                # 変数データを抽出（user_id以外のフィールド）
                for field, value in row.items():
                    if field not in required_fields + alternative_fields and value is not None:
                        user_data["variables"][field] = value.strip() if isinstance(value, str) else value
                
                users_data.append(user_data)
        
        except csv.Error as e:
            errors.append(f"CSV parsing error: {str(e)}")
        except Exception as e:
            errors.append(f"Unexpected error parsing CSV: {str(e)}")
        
        return users_data, errors
    
    def parse_json(self, file_content: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """JSONファイルの内容を解析"""
        users_data = []
        errors = []
        
        try:
            data = json.loads(file_content)
            
            if not isinstance(data, list):
                errors.append("JSON must be an array of user objects")
                return users_data, errors
            
            for index, item in enumerate(data):
                if not isinstance(item, dict):
                    errors.append(f"Item {index}: Must be an object")
                    continue
                
                # ユーザー識別子を取得
                user_identifier = None
                identifier_type = None
                
                for field in ['user_id', 'username', 'display_name', 'name']:
                    if field in item and item[field]:
                        user_identifier = str(item[field]).strip()
                        identifier_type = field
                        break
                
                if not user_identifier:
                    errors.append(f"Item {index}: No valid user identifier found")
                    continue
                
                # ユーザーデータを構築
                user_data = {
                    "identifier": user_identifier,
                    "identifier_type": identifier_type,
                    "variables": {}
                }
                
                # 変数データを抽出
                for field, value in item.items():
                    if field not in ['user_id', 'username', 'display_name', 'name'] and value is not None:
                        user_data["variables"][field] = str(value) if not isinstance(value, (dict, list)) else value
                
                users_data.append(user_data)
        
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            errors.append(f"Unexpected error parsing JSON: {str(e)}")
        
        return users_data, errors
    
    async def resolve_users(self, slack_client: SlackClient, user_identifiers: List[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """ユーザー識別子のリストからSlackユーザー情報を解決"""
        resolved_users = []
        errors = []
        
        for identifier in user_identifiers:
            try:
                clean_identifier = identifier.strip().lstrip('@')
                if not clean_identifier:
                    continue
                
                # ユーザーIDの形式かチェック（Uで始まる）
                if clean_identifier.startswith('U') and len(clean_identifier) == 11:
                    # ユーザーIDとして扱う
                    user_info = await slack_client.get_user_info(clean_identifier)
                else:
                    # 表示名として扱う
                    user_info = await slack_client.get_user_by_name(clean_identifier)
                
                if user_info:
                    resolved_users.append(user_info)
                else:
                    errors.append(f"User not found: {identifier}")
            
            except Exception as e:
                logger.error(f"Error resolving user {identifier}: {str(e)}")
                errors.append(f"Error resolving user {identifier}: {str(e)}")
        
        return resolved_users, errors
    
    async def resolve_users_with_variables(self, slack_client: SlackClient, users_data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]], List[str]]:
        """変数付きのユーザーデータからSlackユーザー情報と変数データを解決"""
        resolved_users = []
        user_variables = {}
        errors = []
        
        for user_data in users_data:
            try:
                identifier = user_data["identifier"]
                identifier_type = user_data["identifier_type"]
                variables = user_data["variables"]
                
                # Slackユーザー情報を取得
                if identifier_type == 'user_id' or (identifier.startswith('U') and len(identifier) == 11):
                    user_info = await slack_client.get_user_info(identifier)
                else:
                    user_info = await slack_client.get_user_by_name(identifier)
                
                if user_info:
                    resolved_users.append(user_info)
                    # 変数データを保存
                    if variables:
                        user_variables[user_info["id"]] = variables
                else:
                    errors.append(f"User not found: {identifier}")
            
            except Exception as e:
                logger.error(f"Error resolving user with variables {user_data}: {str(e)}")
                errors.append(f"Error resolving user {identifier}: {str(e)}")
        
        return resolved_users, user_variables, errors
    
    def validate_file_format(self, file_content: str, filename: str) -> Tuple[bool, str]:
        """ファイル形式を検証"""
        if not file_content or not file_content.strip():
            return False, "File is empty"
        
        file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
        
        if file_ext == 'csv':
            try:
                reader = csv.reader(StringIO(file_content))
                next(reader)  # ヘッダー行を読む
                return True, "CSV format detected"
            except:
                return False, "Invalid CSV format"
        
        elif file_ext == 'json':
            try:
                json.loads(file_content)
                return True, "JSON format detected"
            except:
                return False, "Invalid JSON format"
        
        else:
            # 内容から推測
            try:
                json.loads(file_content)
                return True, "JSON format detected (by content)"
            except:
                try:
                    reader = csv.reader(StringIO(file_content))
                    next(reader)
                    return True, "CSV format detected (by content)"
                except:
                    return False, "Unknown file format"