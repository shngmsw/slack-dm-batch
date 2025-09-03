# Slack DM Batch Sender

Slackで複数のユーザーに一括でダイレクトメッセージを送信するWebアプリケーションです。埋め込み変数に対応し、ユーザーごとにパーソナライズされたメッセージを送信できます。

## 主な機能

- 🎯 **複数ユーザー一括送信**: 複数のSlackユーザーに同時にDMを送信
- 📝 **メンションコピペ対応**: Slackから`@Misawa.もせ @田中太郎`形式のメンションをコピーして使用
- 🔧 **変数テンプレート**: `{name}` `{company}`などの埋め込み変数でメッセージをパーソナライズ
- 📊 **CSV/JSONインポート**: ファイルから送信対象や変数データをインポート
- 🖥️ **直感的なWeb UI**: 5段階のステップ形式で簡単操作
- 📈 **リアルタイム進捗**: 送信状況をリアルタイムで監視
- ⚡ **非同期処理**: バックグラウンドで高速送信
- 🛡️ **エラーハンドリング**: 詳細なログと送信結果レポート

## 必要な環境

- Python 3.8以上
- Slack User Token (xoxp-形式)

## インストール

1. **リポジトリのクローン**
```bash
git clone <repository-url>
cd slack-dm-batch
```

2. **依存関係のインストール**
```bash
pip install -r requirements.txt
```

3. **環境変数の設定** (オプション)
```bash
# .envファイルを作成
SLACK_TOKEN=xoxp-your-token-here
DEBUG=true
PORT=8000
```

## Slack Token の取得方法

1. [Slack Apps](https://api.slack.com/apps) にアクセス
2. 「Create New App」→「From scratch」を選択
3. App名とワークスペースを選択して作成
4. 「OAuth & Permissions」で以下のスコープを追加:
   - `chat:write`
   - `users:read`
   - `im:write`
5. 「Install to Workspace」でインストール
6. 「User OAuth Token」(xoxp-で始まる) をコピー

## 起動方法

```bash
# 開発環境での起動
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# または直接実行
cd app
python main.py
```

ブラウザで `http://localhost:8000` にアクセス

## 使用方法

### Step 1: 認証設定
- Slack User Token (xoxp-...) を入力
- 「トークン検証」ボタンでトークンの有効性を確認

### Step 2: 送信対象設定
3つの方法から選択:

**A. メンション貼り付け**
```
@Misawa.もせ @田中太郎 @john.doe こんにちは
```
Slackからこのようなメンションをコピペして「解析」

**B. CSVファイル**
```csv
user_id,name,company
U123ABC456,田中さん,株式会社A
U456DEF789,佐藤さん,株式会社B
```

**C. 手動入力**
ユーザー名を個別に入力

### Step 3: メッセージ作成
```
こんにちは {name} さん、
{company} の件でご連絡させていただきます。

お忙しい中恐れ入りますが、よろしくお願いいたします。
```
`{variable}` 形式で変数を埋め込み

### Step 4: 変数設定
- 各ユーザーの変数値を入力
- CSVから変数データをインポート可能
- 一括設定機能も利用可能

### Step 5: 送信実行
- 最終プレビューを確認
- 「送信開始」でバッチ送信開始
- リアルタイムで進捗を監視

## ファイル形式

### ユーザーリスト CSV
```csv
user_id,name,company,department
U123ABC456,田中太郎,株式会社A,営業部
U456DEF789,佐藤花子,株式会社B,開発部
```

### 変数データ CSV
```csv
user_id,name,company,message
U123ABC456,田中さん,株式会社A,プロジェクトの件
U456DEF789,佐藤さん,株式会社B,会議の件
```

### JSON形式
```json
[
  {
    "user_id": "U123ABC456",
    "name": "田中さん",
    "company": "株式会社A"
  },
  {
    "user_id": "U456DEF789", 
    "name": "佐藤さん",
    "company": "株式会社B"
  }
]
```

## API エンドポイント

- `POST /api/parse-mentions` - メンション解析
- `POST /api/preview` - メッセージプレビュー
- `POST /api/import-variables` - 変数データインポート
- `POST /api/send-messages` - メッセージ送信開始
- `GET /api/status/{job_id}` - 送信状況確認
- `GET /docs` - API ドキュメント (開発時のみ)

## 設定オプション

環境変数で以下を設定可能:

```bash
# アプリケーション設定
DEBUG=true                          # デバッグモード
HOST=0.0.0.0                       # ホスト
PORT=8000                          # ポート

# Slack API設定
SLACK_TOKEN=xoxp-...               # デフォルトトークン
SLACK_RATE_LIMIT_DELAY=1.0         # API呼び出し間隔(秒)
SLACK_MAX_RETRIES=3                # 最大リトライ回数

# ファイル設定
MAX_FILE_SIZE=10485760             # 最大ファイルサイズ(10MB)

# ログ設定
LOG_LEVEL=INFO                     # ログレベル
LOG_FILE=logs/app.log              # アプリログファイル
SEND_RESULTS_LOG_FILE=logs/send_results.log  # 送信結果ログ
```

## トラブルシューティング

### よくある問題

**1. トークンが無効です**
- User Token (xoxp-形式) を使用していることを確認
- 必要なスコープ (chat:write, users:read, im:write) が設定されていることを確認

**2. ユーザーが見つかりません**
- ユーザーが同じワークスペースに存在することを確認
- 表示名が正確であることを確認
- 非アクティブユーザーは検索できない場合があります

**3. 送信に失敗します**
- レート制限に達している可能性があります（1秒間隔で送信）
- ユーザーがDMを受け取れない設定になっている可能性があります

**4. 変数が反映されません**
- 変数名が `{name}` 形式で正しく記述されていることを確認
- 変数値が正しく入力されていることを確認

### ログの確認

```bash
# アプリケーションログ
tail -f logs/app.log

# 送信結果詳細ログ  
tail -f logs/send_results.log
```

## 開発者向け情報

### プロジェクト構造
```
slack-dm-batch/
├── app/                    # バックエンドコード
│   ├── main.py            # FastAPIアプリケーション
│   ├── models.py          # データモデル
│   ├── slack_client.py    # Slack APIクライアント
│   ├── message_processor.py  # メッセージ処理
│   ├── user_parser.py     # ユーザー解析
│   └── config.py          # 設定管理
├── static/                # 静的ファイル
│   ├── css/style.css      # スタイルシート
│   └── js/app.js          # フロントエンド
├── templates/             # HTMLテンプレート
│   └── index.html
├── logs/                  # ログファイル
└── requirements.txt       # 依存関係
```

### 技術スタック
- **バックエンド**: FastAPI, Python 3.8+
- **フロントエンド**: HTML, CSS, JavaScript (バニラ)
- **Slack API**: slack-sdk
- **非同期処理**: asyncio
- **ログ**: Python logging

## ライセンス

MIT License

## サポート

問題が発生した場合は、以下の情報を含めてお知らせください：
- エラーメッセージ
- 使用したSlackトークンの形式
- ログファイルの関連部分
- 実行環境の情報