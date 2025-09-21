# 🚀 デプロイガイド：Vercel vs Render

## 📊 比較結果

### ✅ **推奨：Render**
このプロジェクトにはRenderが最適です。

**理由：**
- Pythonバックエンドのフルサポート
- SQLiteデータベースの永続化対応
- 環境変数の簡単管理
- 無料プランでも十分な機能

### ❌ Vercel
- Pythonサーバーレス関数のみ（永続サーバー非対応）
- SQLite永続化が困難
- このプロジェクトの構造と不一致

## 🔧 Renderデプロイ手順

### 1. 事前準備

```bash
# requirements.txt作成
echo "# Python dependencies" > requirements.txt
echo "# No external dependencies needed" >> requirements.txt

# Gitリポジトリ初期化（未実施の場合）
git init
git add .
git commit -m "Initial commit for bank escrow system"

# GitHubにプッシュ
git remote add origin https://github.com/YOUR_USERNAME/fintech-escrow.git
git push -u origin main
```

### 2. render.yaml作成

```yaml
services:
  - type: web
    name: fintech-escrow
    runtime: python
    buildCommand: "pip install -e ."
    startCommand: "python -m src.app.web_server"
    envVars:
      - key: PORT
        value: 10000
      - key: PYTHON_VERSION
        value: 3.11.0
    disk:
      name: data
      mountPath: /app/data
      sizeGB: 1
```

### 3. プロジェクト構造調整

```bash
# データベースパスの調整
mkdir -p data
mv fintech.db data/fintech.db 2>/dev/null || true

# 静的ファイルの配置確認
cp indata.html src/app/static/indata.html
```

### 4. web_server.py調整

```python
# ポート設定の環境変数対応（既に対応済み）
PORT = int(os.environ.get('PORT', 6005))

# データベースパスの調整
DB_PATH = os.environ.get('DB_PATH', '/app/data/fintech.db')
```

### 5. Renderでのデプロイ

1. [Render](https://render.com)にサインアップ
2. "New +" → "Web Service"
3. GitHubリポジトリを接続
4. 設定：
   - **Name**: fintech-escrow
   - **Runtime**: Python
   - **Build Command**: `pip install -e .`
   - **Start Command**: `python -m src.app.web_server`
5. "Create Web Service"をクリック

### 6. デプロイ後の設定

**環境変数追加**：
- `DB_PATH`: `/app/data/fintech.db`
- `AUDIT_LOG_PATH`: `/app/data/audit.log`

**ディスクマウント**：
- Mount Path: `/app/data`
- Size: 1GB

## 🎯 アクセス方法

デプロイ完了後：
- **メイン画面**: `https://fintech-escrow.onrender.com/`
- **入金データ生成**: `https://fintech-escrow.onrender.com/indata.html`
- **入金確認**: `https://fintech-escrow.onrender.com/deposits`
- **レポート**: `https://fintech-escrow.onrender.com/reports/dashboard.html`

## ⚡ トラブルシューティング

### データベース永続化
```python
# src/app/db.pyに追加
import os
DB_DIR = os.environ.get('DB_PATH', './data/fintech.db')
os.makedirs(os.path.dirname(DB_DIR), exist_ok=True)
```

### ポート設定
```python
# Renderは自動的にPORT環境変数を設定
PORT = int(os.environ.get('PORT', 10000))
```

### 静的ファイル配信
```python
# web_server.pyで対応済み
if self.path.startswith('/static/'):
    return self.serve_static()
```

## 🔄 継続的デプロイ

GitHubにプッシュすると自動デプロイ：
```bash
git add .
git commit -m "Update features"
git push origin main
```

## 📌 注意事項

1. **無料プラン制限**：
   - 15分間アクセスがないとスリープ
   - 月750時間の実行時間制限

2. **データバックアップ**：
   ```bash
   # 定期的なバックアップ推奨
   scp render:/app/data/fintech.db ./backup/
   ```

3. **セキュリティ**：
   - 本番環境では認証機能追加推奨
   - HTTPSは自動提供

---

**推奨：Renderを使用してデプロイ**
シンプルで、このプロジェクトの要件に完全対応しています。