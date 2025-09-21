"""新しい入金管理システム"""

def get_new_deposits_html():
    return '''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>入金確認 - 銀行エスクロー管理</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #2c3e50, #3498db);
            min-height: 100vh;
            padding: 20px;
            color: white;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255,255,255,0.2);
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
        }
        h1 {
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
        .back-link {
            background: rgba(255,255,255,0.2);
            padding: 10px 20px;
            border-radius: 25px;
            color: white;
            text-decoration: none;
            transition: all 0.3s;
        }
        .back-link:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
        }
        .bank-info {
            background: rgba(46, 204, 113, 0.2);
            border: 2px solid #2ecc71;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 30px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        .bank-detail {
            text-align: center;
        }
        .bank-detail strong {
            display: block;
            font-size: 1.2em;
            margin-bottom: 5px;
            color: #2ecc71;
        }
        .controls {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            flex-wrap: wrap;
            gap: 15px;
        }
        .filter-group {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .filter-btn {
            padding: 8px 16px;
            background: rgba(255,255,255,0.2);
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 20px;
            color: white;
            cursor: pointer;
            transition: all 0.3s;
        }
        .filter-btn.active {
            background: #3498db;
            border-color: #3498db;
        }
        .filter-btn:hover {
            background: rgba(255,255,255,0.3);
        }
        .refresh-btn {
            background: linear-gradient(135deg, #27ae60, #2ecc71);
            padding: 12px 25px;
            border: none;
            border-radius: 25px;
            color: white;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
        }
        .refresh-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(39, 174, 96, 0.3);
        }
        .stats-bar {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-item {
            background: rgba(255,255,255,0.15);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .stat-label {
            opacity: 0.9;
            font-size: 0.9em;
        }
        .deposits-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
        }
        .deposit-card {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 25px;
            transition: all 0.3s;
            border: 2px solid transparent;
            position: relative;
            overflow: hidden;
        }
        .deposit-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #3498db, #2ecc71);
        }
        .deposit-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            border-color: rgba(255,255,255,0.3);
        }
        .deposit-card.selected {
            border-color: #f39c12;
            background: rgba(243, 156, 18, 0.2);
        }
        .deposit-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .deposit-amount {
            font-size: 2em;
            font-weight: bold;
            color: #2ecc71;
        }
        .deposit-status {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        .status-pending {
            background: #f39c12;
            color: white;
        }
        .status-processing {
            background: #3498db;
            color: white;
        }
        .status-completed {
            background: #27ae60;
            color: white;
        }
        .deposit-details {
            margin-bottom: 20px;
        }
        .detail-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .detail-label {
            opacity: 0.8;
            font-size: 0.9em;
        }
        .detail-value {
            font-weight: bold;
        }
        .deposit-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-block;
            text-align: center;
        }
        .btn-primary {
            background: linear-gradient(135deg, #3498db, #2980b9);
            color: white;
        }
        .btn-success {
            background: linear-gradient(135deg, #27ae60, #2ecc71);
            color: white;
        }
        .btn-warning {
            background: linear-gradient(135deg, #f39c12, #e67e22);
            color: white;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.3);
        }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            backdrop-filter: blur(5px);
        }
        .modal-content {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: linear-gradient(135deg, #2c3e50, #34495e);
            padding: 40px;
            border-radius: 20px;
            max-width: 600px;
            width: 90%;
            border: 2px solid rgba(255,255,255,0.2);
        }
        .modal h2 {
            margin-bottom: 20px;
            color: #ecf0f1;
        }
        .calculation-grid {
            display: grid;
            gap: 15px;
            margin: 20px 0;
        }
        .calc-row {
            display: flex;
            justify-content: space-between;
            padding: 15px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
        }
        .calc-row.total {
            background: linear-gradient(135deg, #27ae60, #2ecc71);
            font-weight: bold;
            font-size: 1.1em;
        }
        .tron-input {
            width: 100%;
            padding: 15px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 8px;
            background: rgba(255,255,255,0.1);
            color: white;
            font-size: 1em;
            margin: 10px 0;
        }
        .tron-input:focus {
            outline: none;
            border-color: #3498db;
        }
        .rate-timer {
            text-align: center;
            font-size: 1.2em;
            margin: 15px 0;
            padding: 10px;
            background: rgba(231, 76, 60, 0.2);
            border-radius: 8px;
            border: 1px solid #e74c3c;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏦 銀行入金確認・承認システム</h1>
            <a href="/" class="back-link">← メイン画面</a>
        </div>

        <div class="bank-info">
            <div class="bank-detail">
                <strong>🏛️ エスクロー専用口座</strong>
                みずほ銀行 新宿支店<br>
                普通 1234567
            </div>
            <div class="bank-detail">
                <strong>📊 本日の入金状況</strong>
                <span id="today-summary">読込中...</span>
            </div>
            <div class="bank-detail">
                <strong>⏱️ 最終更新</strong>
                <span id="last-update">読込中...</span>
            </div>
            <div class="bank-detail">
                <strong>🎯 入金生成ツール</strong>
                <a href="http://localhost:6005/indata.html" style="color: #2ecc71;">データ生成画面</a>
            </div>
        </div>

        <div class="controls">
            <div class="filter-group">
                <button class="filter-btn active" data-filter="all">すべて</button>
                <button class="filter-btn" data-filter="pending">未処理</button>
                <button class="filter-btn" data-filter="processing">処理中</button>
                <button class="filter-btn" data-filter="completed">完了</button>
                <button class="filter-btn" data-filter="today">本日分</button>
            </div>
            <button class="refresh-btn" onclick="loadDeposits()">🔄 更新</button>
        </div>

        <div class="stats-bar">
            <div class="stat-item">
                <div class="stat-value" id="total-deposits">0</div>
                <div class="stat-label">総入金件数</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="total-amount">¥0</div>
                <div class="stat-label">総入金額</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="pending-count">0</div>
                <div class="stat-label">未処理件数</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="avg-amount">¥0</div>
                <div class="stat-label">平均金額</div>
            </div>
        </div>

        <div class="deposits-grid" id="deposits-grid">
            <p style="text-align: center; color: rgba(255,255,255,0.7);">入金データを読込中...</p>
        </div>
    </div>

    <!-- 承認モーダル -->
    <div id="approval-modal" class="modal">
        <div class="modal-content">
            <h2>💱 USDT変換・送金承認</h2>
            <div id="approval-details"></div>

            <div class="rate-timer" id="rate-timer">
                レート取得中...
            </div>

            <div class="calculation-grid" id="calculation-details">
                <!-- 計算詳細がここに表示される -->
            </div>

            <label for="tron-address">🔗 TRON送金先アドレス:</label>
            <input type="text" id="tron-address" class="tron-input"
                   placeholder="T... (TRONアドレスを入力してください)"
                   pattern="^T[A-Za-z0-9]{33}$">

            <div style="display: flex; gap: 15px; margin-top: 30px;">
                <button class="btn btn-success" onclick="executeConversion()">
                    ✅ 承認・実行
                </button>
                <button class="btn btn-warning" onclick="closeModal()">
                    ❌ キャンセル
                </button>
            </div>
        </div>
    </div>

    <script>
        let allDeposits = [];
        let currentFilter = 'all';
        let selectedDeposit = null;
        let currentRates = null;
        let rateTimer = null;

        // 初期読み込み
        loadDeposits();
        loadRates();
        setInterval(loadDeposits, 10000); // 10秒ごと
        setInterval(loadRates, 60000);    // 1分ごと

        async function loadDeposits() {
            try {
                const response = await fetch('/api/bank_deposits');
                allDeposits = await response.json();
                updateStats();
                filterDeposits();
                document.getElementById('last-update').textContent = new Date().toLocaleTimeString('ja-JP');
            } catch (error) {
                console.error('Error loading deposits:', error);
            }
        }

        async function loadRates() {
            try {
                const response = await fetch('/api/rates');
                currentRates = await response.json();
                updateRateTimer();
            } catch (error) {
                console.error('Error loading rates:', error);
            }
        }

        function updateStats() {
            const today = new Date().toDateString();
            const todayDeposits = allDeposits.filter(d =>
                new Date(d.created_at).toDateString() === today
            );

            document.getElementById('total-deposits').textContent = allDeposits.length;
            document.getElementById('total-amount').textContent =
                '¥' + allDeposits.reduce((sum, d) => sum + d.amount, 0).toLocaleString();
            document.getElementById('pending-count').textContent =
                allDeposits.filter(d => d.status === 'pending').length;

            const avgAmount = allDeposits.length > 0 ?
                allDeposits.reduce((sum, d) => sum + d.amount, 0) / allDeposits.length : 0;
            document.getElementById('avg-amount').textContent = '¥' + Math.floor(avgAmount).toLocaleString();

            document.getElementById('today-summary').textContent =
                `${todayDeposits.length}件 / ¥${todayDeposits.reduce((sum, d) => sum + d.amount, 0).toLocaleString()}`;
        }

        function filterDeposits() {
            const grid = document.getElementById('deposits-grid');
            let filtered = [...allDeposits];

            // フィルター適用
            switch(currentFilter) {
                case 'pending':
                    filtered = filtered.filter(d => d.status === 'pending');
                    break;
                case 'processing':
                    filtered = filtered.filter(d => d.status === 'processing');
                    break;
                case 'completed':
                    filtered = filtered.filter(d => d.status === 'completed');
                    break;
                case 'today':
                    const today = new Date().toDateString();
                    filtered = filtered.filter(d =>
                        new Date(d.created_at).toDateString() === today
                    );
                    break;
            }

            // 最新順にソート
            filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

            if (filtered.length === 0) {
                grid.innerHTML = '<p style="text-align: center; color: rgba(255,255,255,0.7);">該当する入金データがありません</p>';
                return;
            }

            grid.innerHTML = filtered.map(deposit => `
                <div class="deposit-card" data-id="${deposit.id}">
                    <div class="deposit-header">
                        <div class="deposit-amount">¥${deposit.amount.toLocaleString()}</div>
                        <div class="deposit-status status-${deposit.status}">
                            ${getStatusText(deposit.status)}
                        </div>
                    </div>

                    <div class="deposit-details">
                        <div class="detail-row">
                            <span class="detail-label">👤 送金者</span>
                            <span class="detail-value">${deposit.sender_name}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">🏦 送金元銀行</span>
                            <span class="detail-value">${deposit.sender_bank || '不明'}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">📋 送金目的</span>
                            <span class="detail-value">${deposit.purpose || '不明'}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">⏰ 受信時刻</span>
                            <span class="detail-value">${new Date(deposit.created_at).toLocaleString('ja-JP')}</span>
                        </div>
                        ${deposit.tron_address ? `
                        <div class="detail-row">
                            <span class="detail-label">🔗 TRON送金先</span>
                            <span class="detail-value" style="font-size: 0.8em; word-break: break-all;">
                                ${deposit.tron_address}
                            </span>
                        </div>
                        ` : ''}
                    </div>

                    <div class="deposit-actions">
                        ${deposit.status === 'pending' ? `
                            <button class="btn btn-success" onclick="openApprovalModal('${deposit.id}')">
                                💱 USDT変換承認
                            </button>
                        ` : deposit.status === 'processing' ? `
                            <button class="btn btn-primary" onclick="checkTronStatus('${deposit.id}')">
                                🔍 送金状況確認
                            </button>
                        ` : `
                            <button class="btn btn-primary" onclick="viewTransaction('${deposit.id}')">
                                📊 取引詳細
                            </button>
                        `}
                    </div>
                </div>
            `).join('');
        }

        function getStatusText(status) {
            const statusMap = {
                'pending': '未処理',
                'processing': '送金中',
                'completed': '完了'
            };
            return statusMap[status] || status;
        }

        // フィルターボタンイベント
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('filter-btn')) {
                document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
                e.target.classList.add('active');
                currentFilter = e.target.dataset.filter;
                filterDeposits();
            }
        });

        function openApprovalModal(depositId) {
            selectedDeposit = allDeposits.find(d => d.id === depositId);
            if (!selectedDeposit || !currentRates) return;

            const modal = document.getElementById('approval-modal');
            const details = document.getElementById('approval-details');
            const calculation = document.getElementById('calculation-details');

            // 計算
            const jpyAmount = selectedDeposit.amount;
            const rate = currentRates.jpy_to_usdt;
            const grossUsdt = jpyAmount / rate;
            const processingFee = grossUsdt * (currentRates.processing_fee_percent / 100);
            const networkFee = currentRates.network_fee_usdt;
            const netUsdt = grossUsdt - processingFee - networkFee;

            details.innerHTML = `
                <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <strong>送金者:</strong> ${selectedDeposit.sender_name}<br>
                    <strong>送金額:</strong> ¥${selectedDeposit.amount.toLocaleString()}<br>
                    <strong>送金元:</strong> ${selectedDeposit.sender_bank}
                </div>
            `;

            calculation.innerHTML = `
                <div class="calc-row">
                    <span>入金額 (JPY)</span>
                    <span>¥${jpyAmount.toLocaleString()}</span>
                </div>
                <div class="calc-row">
                    <span>現在レート (JPY/USDT)</span>
                    <span>${rate.toFixed(2)}</span>
                </div>
                <div class="calc-row">
                    <span>変換前USDT</span>
                    <span>${grossUsdt.toFixed(4)} USDT</span>
                </div>
                <div class="calc-row">
                    <span>処理手数料 (${currentRates.processing_fee_percent}%)</span>
                    <span>-${processingFee.toFixed(4)} USDT</span>
                </div>
                <div class="calc-row">
                    <span>ネットワーク手数料</span>
                    <span>-${networkFee} USDT</span>
                </div>
                <div class="calc-row total">
                    <span>受取額</span>
                    <span>${netUsdt.toFixed(4)} USDT</span>
                </div>
            `;

            modal.style.display = 'block';
            updateRateTimer();
        }

        function updateRateTimer() {
            if (!currentRates) return;

            const timerEl = document.getElementById('rate-timer');
            const validUntil = new Date(currentRates.valid_until);

            if (rateTimer) clearInterval(rateTimer);

            rateTimer = setInterval(() => {
                const now = new Date();
                const diff = validUntil - now;

                if (diff <= 0) {
                    timerEl.innerHTML = '⚠️ レート期限切れ - 更新中...';
                    loadRates();
                } else {
                    const minutes = Math.floor(diff / 60000);
                    const seconds = Math.floor((diff % 60000) / 1000);
                    timerEl.innerHTML = `⏰ レート有効期限: ${minutes}:${seconds.toString().padStart(2, '0')}`;
                }
            }, 1000);
        }

        async function executeConversion() {
            if (!selectedDeposit) return;

            const tronAddress = document.getElementById('tron-address').value.trim();
            if (!tronAddress || !tronAddress.startsWith('T') || tronAddress.length !== 34) {
                alert('有効なTRONアドレスを入力してください (T + 33文字)');
                return;
            }

            if (!confirm(`以下の内容でUSDT変換・送金を実行しますか？\\n\\n送金者: ${selectedDeposit.sender_name}\\n金額: ¥${selectedDeposit.amount.toLocaleString()}\\n送金先: ${tronAddress}`)) {
                return;
            }

            try {
                const response = await fetch('/api/process_deposit', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        deposit_id: selectedDeposit.id,
                        tron_address: tronAddress,
                        rate: currentRates.jpy_to_usdt
                    })
                });

                const result = await response.json();
                if (result.success) {
                    alert(`✅ 変換・送金を開始しました！\\n\\nTXID: ${result.txid}\\n\\nTronScanで確認できます。`);
                    closeModal();
                    loadDeposits();
                } else {
                    alert('❌ エラー: ' + result.error);
                }
            } catch (error) {
                alert('❌ 処理中にエラーが発生しました: ' + error.message);
            }
        }

        function closeModal() {
            document.getElementById('approval-modal').style.display = 'none';
            selectedDeposit = null;
            if (rateTimer) {
                clearInterval(rateTimer);
                rateTimer = null;
            }
        }

        async function checkTronStatus(depositId) {
            const deposit = allDeposits.find(d => d.id === depositId);
            if (!deposit || !deposit.tron_address) return;

            // TronScanで確認
            const tronScanUrl = `https://tronscan.org/#/address/${deposit.tron_address}`;
            window.open(tronScanUrl, '_blank');
        }

        function viewTransaction(depositId) {
            const deposit = allDeposits.find(d => d.id === depositId);
            if (!deposit) return;

            alert(`取引詳細\\n\\n送金者: ${deposit.sender_name}\\n金額: ¥${deposit.amount.toLocaleString()}\\n状況: ${getStatusText(deposit.status)}\\n処理日時: ${deposit.processed_at ? new Date(deposit.processed_at).toLocaleString('ja-JP') : '未処理'}`);
        }

        // モーダル外クリックで閉じる
        window.addEventListener('click', (e) => {
            const modal = document.getElementById('approval-modal');
            if (e.target === modal) {
                closeModal();
            }
        });
    </script>
</body>
</html>'''