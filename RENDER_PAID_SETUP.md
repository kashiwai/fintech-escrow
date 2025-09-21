# 🎯 Render有料版セットアップ

## ✅ 永続ディスク設定

### 1️⃣ Renderダッシュボードで設定

1. [Renderダッシュボード](https://dashboard.render.com)にログイン
2. `fintech-escrow`サービスを選択
3. **Disks**タブを開く
4. **Add Disk**をクリック
5. 以下を設定：
   - **Name**: `fintech-data`
   - **Mount Path**: `/render/data`
   - **Size**: `1 GB` (必要に応じて増やせます)
6. **Save**

### 2️⃣ 環境変数の確認

**Environment**タブで以下が設定されているか確認：

```
RENDER=true
DB_PATH=/render/data/fintech.db
AUDIT_LOG_PATH=/render/data/audit.log
PORT=10000
```

### 3️⃣ 再デプロイ

**Manual Deploy** → **Clear build cache & deploy**

## 📊 データの永続化

有料版では以下が永続化されます：
- 銀行入金データ
- USDT送金履歴
- 監査ログ
- レポート

## 🔧 初回セットアップ

初回デプロイ時にDBが自動初期化されます。
ビルドログで確認：
```
Initializing database...
Database initialized at: /render/data/fintech.db
```

## 🚀 アクセスURL

- https://fintech-escrow.onrender.com/ - メインダッシュボード
- https://fintech-escrow.onrender.com/indata.html - 入金データ生成
- https://fintech-escrow.onrender.com/deposits - 入金確認
- https://fintech-escrow.onrender.com/reports/dashboard.html - レポート

## 💾 バックアップ

定期的にバックアップを取ることを推奨：
1. Renderダッシュボード → Disks
2. Download Snapshotでバックアップ

---

これでデータが永続化され、本格的な運用が可能です！