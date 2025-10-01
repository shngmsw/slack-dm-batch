import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class MessageProcessor:
    def __init__(self):
        # 変数パターン: {variable_name} 形式
        self.variable_pattern = re.compile(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}')
    
    def extract_variables(self, template: str) -> List[str]:
        """テンプレートから変数を抽出"""
        if not template:
            return []
        
        matches = self.variable_pattern.findall(template)
        # 重複を除去して順序を保持
        variables = []
        seen = set()
        for var in matches:
            if var not in seen:
                variables.append(var)
                seen.add(var)
        
        return variables
    
    def validate_template(self, template: str) -> List[str]:
        """テンプレートを検証し、エラーメッセージのリストを返す"""
        errors = []
        
        if not template or not template.strip():
            errors.append("Template cannot be empty")
            return errors
        
        # 不正な変数形式をチェック
        # 例: {123}, {var-name}, {var name} など
        invalid_pattern = re.compile(r'\{([^}]*)\}')
        all_matches = invalid_pattern.findall(template)
        valid_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
        
        for match in all_matches:
            if not valid_pattern.match(match):
                errors.append(f"Invalid variable name: '{match}'. Variables must start with a letter or underscore, followed by letters, numbers, or underscores.")
        
        # 閉じられていない括弧をチェック
        open_count = template.count('{')
        close_count = template.count('}')
        if open_count != close_count:
            errors.append(f"Mismatched braces: {open_count} opening, {close_count} closing")
        
        return errors
    
    def render_template(self, template: str, variables: Dict[str, Any]) -> str:
        """テンプレートに変数を埋め込んでレンダリング"""
        if not template:
            return ""
        
        try:
            # Pythonの文字列フォーマットを使用
            return template.format(**variables)
        except KeyError as e:
            missing_var = str(e).strip("'")
            logger.warning(f"Missing variable in template: {missing_var}")
            # 欠けている変数は元の形式で残す
            return template
        except Exception as e:
            logger.error(f"Error rendering template: {str(e)}")
            return template
    
    def render_template_safe(self, template: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """安全なテンプレートレンダリング（エラー情報付き）"""
        result = {
            "rendered_message": template,
            "success": True,
            "missing_variables": [],
            "error": None
        }

        if not template:
            result["success"] = False
            result["error"] = "Template is empty"
            return result

        # 必要な変数を取得
        required_variables = self.extract_variables(template)

        # 変数が1つもない場合はそのまま返す（全員に同じメッセージを送る場合）
        if not required_variables:
            result["rendered_message"] = template
            return result

        missing_variables = [var for var in required_variables if var not in variables]

        if missing_variables:
            result["missing_variables"] = missing_variables
            # 部分的にレンダリング（利用可能な変数のみ）
            available_variables = {k: v for k, v in variables.items() if k in required_variables}
            try:
                # 欠けている変数は元の形式で保持
                partial_template = template
                for var, value in available_variables.items():
                    partial_template = partial_template.replace(f"{{{var}}}", str(value))
                result["rendered_message"] = partial_template
            except Exception as e:
                result["error"] = f"Partial rendering failed: {str(e)}"
        else:
            try:
                result["rendered_message"] = self.render_template(template, variables)
            except Exception as e:
                result["success"] = False
                result["error"] = f"Rendering failed: {str(e)}"

        return result
    
    def render_for_users(self, template: str, user_data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """複数ユーザー用のテンプレートレンダリング"""
        results = {}
        
        for user_id, variables in user_data.items():
            results[user_id] = self.render_template_safe(template, variables)
        
        return results
    
    def get_template_info(self, template: str) -> Dict[str, Any]:
        """テンプレートの情報を取得"""
        return {
            "variables": self.extract_variables(template),
            "validation_errors": self.validate_template(template),
            "is_valid": len(self.validate_template(template)) == 0,
            "character_count": len(template),
            "line_count": template.count('\n') + 1 if template else 0
        }