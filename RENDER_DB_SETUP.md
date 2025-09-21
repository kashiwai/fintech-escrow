# 🔧 RenderでのDB設定手順

## 重要：ディスクマウントの設定が必要です

### 1️⃣ Renderダッシュボードで設定

1. [Renderダッシュボード](https://dashboard.render.com)にログイン
2. `fintech-escrow`サービスをクリック
3. **Disks**タブを開く
4. **Add Persistent Disk**をクリック
5. 以下を設定：
   - **Name**: `fintech-data`
   - **Mount Path**: `/app/data`
   - **Size**: `1 GB`
6. **Save**

### 2️⃣ 環境変数の確認

**Environment**タブで以下が設定されているか確認：

```
RENDER=true
DB_PATH=/app/data/fintech.db
AUDIT_LOG_PATH=/app/data/audit.log
PORT=10000
```

### 3️⃣ 再デプロイ

1. **Manual Deploy** → **Clear build cache & deploy**をクリック
2. ビルドログで`Initializing database...`が表示されることを確認

## ✅ 動作確認

デプロイ後、以下のURLで確認：

- https://fintech-escrow.onrender.com/ - ダッシュボード
- https://fintech-escrow.onrender.com/indata.html - 入金データ生成
- https://fintech-escrow.onrender.com/deposits - 入金確認

## 🔍 トラブルシューティング

### DBが読み込めない場合

1. ディスクがマウントされているか確認
2. Build Commandが正しく実行されているか確認：
   ```
   python -m pip install --upgrade pip && python init_db.py
   ```

### 承認画面が表示されない場合

DBが初期化されていない可能性があります。
**Clear build cache & deploy**で再デプロイしてください。

---

これで永続的なDBが使用できるようになります。