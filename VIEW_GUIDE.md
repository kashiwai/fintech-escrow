# エスクローサービス 操作・閲覧ガイド

## 画面・実行画面の確認方法

### 1. ダッシュボード（Web画面）

**場所**: `/Users/kotarokashiwai/fintech/reports/dashboard.html`

**開き方**:
```bash
open /Users/kotarokashiwai/fintech/reports/dashboard.html
```

**表示内容**:
- クライアント別残高（JPY）
- リリースリクエスト一覧
- ペイアウト履歴
- アラート情報

### 2. MCP Inspector（管理画面）

**URL**: http://localhost:6274/
**トークン**: セッション毎に生成

現在実行中のインスペクター画面で、MCPサーバーの状態を確認できます。

### 3. コマンドライン実行画面

**基本操作コマンド**:

```bash
# データベース初期化
python -m src.app.simulate init

# JPY入金シミュレーション
python -m src.app.simulate deposit --client A --amount 1000000

# USDT解放リクエスト
python -m src.app.simulate release \
  --client A \
  --amount_usdt 5000 \
  --chain TRC20 \
  --address TX_SANDBOX_TEST_001 \
  --max_slippage_bps 50

# 承認処理（2人承認必要）
python -m src.app.simulate approve --request_id REQ_ID --approver user1
python -m src.app.simulate approve --request_id REQ_ID --approver user2

# ペイアウト実行
python -m src.app.simulate payout --request_id REQ_ID
```

### 4. 状態確認コマンド

```bash
# 現在の残高確認
sqlite3 fintech.db "SELECT * FROM balances;"

# 取引履歴確認
sqlite3 fintech.db "SELECT * FROM release_requests ORDER BY created_at DESC LIMIT 10;"

# MCP統合ログ確認
sqlite3 fintech.db "SELECT * FROM mcp_integrations;"

# 監査ログ確認
tail -n 20 audit.log
```

### 5. レポート生成

```bash
# ダッシュボード再生成
python -m src.app.dashboard build

# 日次照合レポート生成
python -m src.app.reconciliation run --date today

# 完全なE2Eテスト実行
python -m src.app.run_all
```

### 6. ログファイル

**監査ログ**: `/Users/kotarokashiwai/fintech/audit.log`
- ハッシュチェーン形式の改ざん防止ログ

**データベース**: `/Users/kotarokashiwai/fintech/fintech.db`
- SQLiteデータベース（全取引データ）

**レポート**: `/Users/kotarokashiwai/fintech/reports/`
- `dashboard.html` - HTML形式のダッシュボード
- `recon_YYYY-MM-DD.csv` - 日次照合CSV

### 7. 環境設定確認

```bash
# 環境変数確認
cat .env

# 設定値確認
python -c "from src.app.config import *; print(f'DB: {DB_PATH}'); print(f'Chain: {DEFAULT_CHAIN}')"
```

## トラブルシューティング

### ダッシュボードが開かない場合
```bash
# ダッシュボードを再生成
python -m src.app.dashboard build
# ブラウザで直接開く
open -a "Google Chrome" /Users/kotarokashiwai/fintech/reports/dashboard.html
```

### データベースエラーの場合
```bash
# データベースをリセット
rm -f fintech.db audit.log
python -m src.app.simulate init
```

### MCP接続エラーの場合
現在はSandboxモードで動作しているため、MCP Serenaへの実接続は不要です。
本番環境では、MCPサーバーを起動してから実行してください。