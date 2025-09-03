# Slack一括DM送信システム 設計書

## 1. システム概要

### 1.1 アーキテクチャ
- **バックエンド**: FastAPI (高性能、型安全、自動文書生成)
- **フロントエンド**: HTML + CSS + JavaScript (軽量、依存関係最小)
- **データベース**: なし (セッション管理のみ、設定は環境変数/ファイル)
- **構成**: モノリス構成 (単一プロセスで完結)

### 1.2 ディレクトリ構造
```
slack-dm-batch/
├── app/
│   ├── main.py                 # FastAPIアプリケーション
│   ├── models.py               # データモデル定義
│   ├── slack_client.py         # Slack API クライアント
│   ├── message_processor.py    # メッセージ処理・テンプレート機能
│   ├── user_parser.py          # ユーザー情報パース機能
│   └── config.py               # 設定管理
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── app.js
│   └── uploads/                # ファイルアップロード一時保存
├── templates/
│   └── index.html              # Web UI
├── logs/
├── requirements.txt
└── README.md
```

## 2. 主要コンポーネント設計

### 2.1 FastAPI アプリケーション (main.py)
```python
# エンドポイント構成
POST /api/send-messages      # メッセージ送信
POST /api/parse-mentions     # メンション解析
POST /api/upload-file        # ファイルアップロード
GET  /api/preview           # メッセージプレビュー
GET  /api/status/{job_id}   # 送信状況確認
GET  /                      # Web UI
```

### 2.2 Slack クライアント (slack_client.py)
```python
class SlackClient:
    def __init__(self, token: str)
    def send_dm(self, user_id: str, message: str) -> dict
    def get_user_by_name(self, display_name: str) -> dict
    def get_user_info(self, user_id: str) -> dict
    def validate_token(self) -> bool
```

### 2.3 メッセージプロセッサー (message_processor.py)
```python
class MessageProcessor:
    def render_template(self, template: str, variables: dict) -> str
    def validate_template(self, template: str) -> list
    def extract_variables(self, template: str) -> list
```

### 2.4 ユーザーパーサー (user_parser.py)
```python
class UserParser:
    def parse_mentions(self, text: str) -> list[str]
    def parse_csv(self, file_content: str) -> list[dict]
    def parse_json(self, file_content: str) -> list[dict]
    def resolve_users(self, slack_client, user_names: list) -> list[dict]
```

## 3. データモデル設計

### 3.1 Pydantic モデル
```python
class User(BaseModel):
    id: str
    name: str
    display_name: str
    email: Optional[str]

class MessageTemplate(BaseModel):
    content: str
    variables: list[str]

class SendRequest(BaseModel):
    template: str
    users: list[User]
    user_data: dict[str, dict]  # user_id -> variables mapping

class SendResult(BaseModel):
    job_id: str
    total_users: int
    sent_count: int
    failed_count: int
    errors: list[dict]
    status: str  # 'running', 'completed', 'failed'
```

## 4. UI/UX設計

### 4.1 Web UI レイアウト
```
┌─────────────────────────────────────┐
│ Slack DM Batch Sender               │
├─────────────────────────────────────┤
│ 1. 認証設定                          │
│   [Slack Token] [______________]    │
├─────────────────────────────────────┤
│ 2. 送信対象設定                      │
│   ○ メンション貼り付け               │
│     [テキストエリア]                │
│   ○ ファイルアップロード             │
│     [ファイル選択] [ドラッグ&ドロップ]│
│   ○ 手動入力                       │
│     [ユーザー管理テーブル]           │
├─────────────────────────────────────┤
│ 3. メッセージ作成                    │
│   [メッセージテンプレート]           │
│   利用可能変数: {name}, {company}...│
│   [プレビューエリア]                │
├─────────────────────────────────────┤
│ 4. 変数設定 (テンプレートに変数がある場合)│
│   ┌─ユーザー別変数設定─────────────┐ │
│   │User: @Misawa.もせ            │ │
│   │name: [_______] company: [___]│ │
│   │User: @田中太郎               │ │  
│   │name: [_______] company: [___]│ │
│   │[CSVインポート] [一括設定]     │ │
│   └─────────────────────────────┘ │
├─────────────────────────────────────┤
│ 5. 送信実行                         │
│   [最終プレビュー] [送信開始]        │
│   [進捗バー]                       │
│   [結果一覧]                       │
└─────────────────────────────────────┘
```

### 4.2 ユーザーごと変数設定の操作フロー

#### 方法1: 手動入力
1. メッセージテンプレートに `{name}` `{company}` 等を記述
2. システムが自動で変数を検出
3. 送信対象ユーザーごとに変数入力フィールドが表示
4. 各ユーザーの変数を個別に入力

#### 方法2: CSVインポート
```csv
user_id,name,company
U123,もせさん,株式会社A
U456,田中さん,株式会社B
```
- user_id または display_name でユーザーを特定
- 変数列は自由に追加可能

#### 方法3: 一括設定
- 全ユーザーに同じ値を一括設定
- 後から個別編集も可能

### 4.3 JavaScript機能
- リアルタイムプレビュー（テンプレート変更時に即座に反映）
- ファイルドラッグ&ドロップ
- メンション自動解析
- 変数入力フィールドの動的生成
- 変数データの検証・エラー表示
- 送信進捗の WebSocket 更新
- エラー表示・ハンドリング

## 5. API設計

### 5.1 メンション解析API
```
POST /api/parse-mentions
Body: {
    "text": "@Misawa.もせ @田中太郎 @john.doe",
    "token": "xoxp-..."
}
Response: {
    "users": [
        {"id": "U123", "name": "Misawa.もせ", "display_name": "Misawa.もせ"},
        {"id": "U456", "name": "田中太郎", "display_name": "田中太郎"},
        {"id": "U789", "name": "john.doe", "display_name": "John Doe"}
    ],
    "errors": []
}
```

### 5.2 メッセージプレビューAPI
```
POST /api/preview
Body: {
    "template": "こんにちは {name} さん、{company} の件でご連絡です。",
    "user_data": {
        "U123": {"name": "もせさん", "company": "株式会社A"}
    }
}
Response: {
    "rendered_message": "こんにちは もせさん さん、株式会社A の件でご連絡です。",
    "missing_variables": [],
    "available_variables": ["name", "company"]
}
```

### 5.3 変数データCSVインポートAPI
```
POST /api/import-variables
Body: FormData with CSV file
CSV format:
user_id,name,company
U123,もせさん,株式会社A
U456,田中さん,株式会社B

Response: {
    "imported_count": 2,
    "user_data": {
        "U123": {"name": "もせさん", "company": "株式会社A"},
        "U456": {"name": "田中さん", "company": "株式会社B"}
    },
    "errors": []
}
```

### 5.4 メッセージ送信API
```
POST /api/send-messages
Body: {
    "template": "こんにちは {name} さん、{company} の件でご連絡です。",
    "users": [...],
    "user_data": {
        "U123": {"name": "もせさん", "company": "株式会社A"},
        "U456": {"name": "田中さん", "company": "株式会社B"}
    },
    "token": "xoxp-..."
}
Response: {
    "job_id": "job-123",
    "status": "started",
    "total_users": 2
}
```

## 6. セキュリティ設計

### 6.1 トークン管理
- 環境変数 `SLACK_TOKEN` での設定サポート
- Web UI での一時的なセッション保存
- メモリ上でのみ保持、ディスクに保存しない

### 6.2 入力検証
- メッセージテンプレートの不正な変数検出
- ファイルアップロードのサイズ・形式制限
- メンション解析時の不正入力フィルタリング

### 6.3 レート制限
- Slack API の制限遵守 (1 message/second)
- バッチ送信時の適切な間隔制御
- エラー時の指数バックオフ

## 7. エラーハンドリング設計

### 7.1 エラー分類
- **認証エラー**: 無効なトークン、権限不足
- **ユーザーエラー**: 存在しないユーザー、DM送信不可
- **APIエラー**: レート制限、一時的な障害
- **システムエラー**: 設定不備、内部エラー

### 7.2 リトライ戦略
- 一時的な障害: 指数バックオフで最大3回
- レート制限: 適切な待機時間後にリトライ
- 致命的エラー: 即座に停止、詳細ログ出力

## 8. ログ設計

### 8.1 ログレベル
- **INFO**: 送信開始/完了、統計情報
- **WARNING**: リトライ、部分失敗
- **ERROR**: 送信失敗、API エラー
- **DEBUG**: 詳細な処理フロー

### 8.2 ログファイル
- `logs/app.log`: アプリケーションログ
- `logs/send_results.log`: 送信結果の詳細記録

## 9. パフォーマンス設計

### 9.1 非同期処理
- FastAPI の async/await 活用
- 大量送信時のバックグラウンド処理
- WebSocket による進捗のリアルタイム通知

### 9.2 メモリ効率
- 大きなファイルのストリーミング処理
- ユーザーリストの効率的な管理
- 不要なデータの適切な解放