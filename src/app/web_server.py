#!/usr/bin/env python3
"""
エスクロー管理画面 Webサーバー
入金確認、為替レート表示、承認フロー、エラー処理を含む完全なWebインターフェース
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import urllib.request
import hashlib
import hmac

from .db import db, init_db, now_iso
from .ledger import record_deposit
from .rapyd_simulator import deposit_jpy
from .orchestrator import quote_jpy_to_usdt, attach_quote, execute_payout
from .approvals import create_release_request, approve_release
from .config import SIM_FX_JPY_PER_USDT, SIM_NETWORK_FEE_USDT, WEBHOOK_SECRET
from .dashboard import build_dashboard
from .new_deposits import get_new_deposits_html

# 現在の為替レート（実際のAPIから取得する場合はここを変更）
def get_current_rates():
    """リアルタイム為替レート取得（デモ用）"""
    base_rate = SIM_FX_JPY_PER_USDT
    # ±0.5%のランダムな変動をシミュレート
    import random
    variation = random.uniform(-0.005, 0.005)
    current_rate = base_rate * (1 + variation)

    return {
        "jpy_to_usdt": current_rate,
        "usdt_to_jpy": 1 / current_rate,
        "network_fee_usdt": SIM_NETWORK_FEE_USDT,
        "processing_fee_percent": 0.5,  # 0.5%手数料
        "timestamp": now_iso(),
        "valid_until": (datetime.utcnow() + timedelta(minutes=5)).isoformat() + "Z"
    }

class EscrowWebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """GET リクエスト処理"""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.serve_dashboard()
        elif path == "/indata.html":
            self.serve_indata_page()
        elif path == "/deposits":
            self.serve_deposits_page()
        elif path == "/api/deposits":
            self.get_deposits()
        elif path == "/api/pending_deposits":
            self.get_pending_deposits()
        elif path == "/convert":
            self.serve_conversion_page()
        elif path == "/api/rates":
            self.get_exchange_rates()
        elif path == "/approvals":
            self.serve_approvals_page()
        elif path == "/api/pending_approvals":
            self.get_pending_approvals()
        elif path == "/api/transaction_history":
            self.get_transaction_history()
        elif path == "/errors":
            self.serve_error_log_page()
        elif path == "/api/errors":
            self.get_error_logs()
        elif path == "/demo":
            self.serve_demo_page()
        elif path == "/api/bank_deposits":
            self.get_bank_deposits()
        else:
            self.send_error(404, "Page not found")

    def do_POST(self):
        """POST リクエスト処理"""
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data.decode('utf-8'))
        except:
            data = {}

        if path == "/api/confirm_deposit":
            self.confirm_deposit(data)
        elif path == "/api/convert":
            self.convert_to_usdt(data)
        elif path == "/api/approve":
            self.approve_transaction(data)
        elif path == "/api/reject":
            self.reject_transaction(data)
        elif path == "/api/demo/deposit":
            self.simulate_deposit(data)
        elif path == "/api/demo/reset":
            self.reset_demo()
        elif path == "/api/process_deposit":
            self.process_deposit(data)
        else:
            self.send_error(404, "Endpoint not found")

    def serve_dashboard(self):
        """メインダッシュボード"""
        html = '''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>エスクロー管理システム</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Helvetica Neue', Arial, 'Hiragino Sans', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255,255,255,0.95);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            color: #333;
            margin-bottom: 30px;
            text-align: center;
            font-size: 2.5em;
        }
        .nav-menu {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .nav-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            border: 2px solid transparent;
            text-decoration: none;
            color: #333;
        }
        .nav-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            border-color: #667eea;
        }
        .nav-card .icon {
            font-size: 3em;
            margin-bottom: 10px;
        }
        .nav-card .title {
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .nav-card .desc {
            font-size: 0.9em;
            color: #666;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 20px;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 30px rgba(0,0,0,0.3);
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
        }
        .stat-label {
            margin-top: 5px;
            opacity: 0.9;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏦 銀行エスクロー管理システム</h1>

        <div class="nav-menu">
            <a href="/deposits" class="nav-card">
                <div class="icon">💰</div>
                <div class="title">入金確認</div>
                <div class="desc">JPY入金の確認と処理</div>
            </a>

            <a href="/convert" class="nav-card">
                <div class="icon">💱</div>
                <div class="title">通貨変換</div>
                <div class="desc">JPY→USDT変換と手数料</div>
            </a>

            <a href="/approvals" class="nav-card">
                <div class="icon">✅</div>
                <div class="title">承認管理</div>
                <div class="desc">取引承認フロー</div>
            </a>

            <a href="/errors" class="nav-card">
                <div class="icon">⚠️</div>
                <div class="title">エラーログ</div>
                <div class="desc">エラー履歴と対処</div>
            </a>

            <a href="/demo" class="nav-card" style="border-color: #f39c12;">
                <div class="icon">🎮</div>
                <div class="title">デモ・実験</div>
                <div class="desc">Sandbox環境でテスト</div>
            </a>
        </div>

        <div class="stats" id="stats">
            <div class="stat-card" onclick="window.location.href='/deposits'">
                <div class="stat-value" id="total-balance">読込中...</div>
                <div class="stat-label">💰 総残高 (JPY) - クリックで入金確認</div>
            </div>
            <div class="stat-card" onclick="window.location.href='/deposits'">
                <div class="stat-value" id="pending-deposits">読込中...</div>
                <div class="stat-label">⏳ 未処理入金 - クリックで確認</div>
            </div>
            <div class="stat-card" onclick="window.location.href='/approvals'">
                <div class="stat-value" id="pending-approvals">読込中...</div>
                <div class="stat-label">✅ 承認待ち - クリックで処理</div>
            </div>
            <div class="stat-card" onclick="window.location.href='/convert'">
                <div class="stat-value" id="current-rate">読込中...</div>
                <div class="stat-label">💱 現在レート (JPY/USDT)</div>
            </div>
        </div>
    </div>

    <script>
        async function loadStats() {
            try {
                // 残高取得
                const balanceRes = await fetch('/api/deposits');
                const balances = await balanceRes.json();
                const totalBalance = balances.reduce((sum, b) => sum + b.balance, 0);
                document.getElementById('total-balance').textContent = '¥' + totalBalance.toLocaleString();

                // 未処理入金
                const pendingRes = await fetch('/api/pending_deposits');
                const pending = await pendingRes.json();
                document.getElementById('pending-deposits').textContent = pending.count;

                // 承認待ち
                const approvalsRes = await fetch('/api/pending_approvals');
                const approvals = await approvalsRes.json();
                document.getElementById('pending-approvals').textContent = approvals.length;

                // 現在レート
                const ratesRes = await fetch('/api/rates');
                const rates = await ratesRes.json();
                document.getElementById('current-rate').textContent = rates.jpy_to_usdt.toFixed(2);
            } catch (error) {
                console.error('Stats loading error:', error);
            }
        }

        loadStats();
        setInterval(loadStats, 10000); // 10秒ごとに更新
    </script>
</body>
</html>'''
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def serve_indata_page(self):
        """入金データ生成ページ"""
        with open('indata.html', 'r', encoding='utf-8') as f:
            html = f.read()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def serve_deposits_page(self):
        """入金確認画面 - 銀行入金データから選択・承認"""
        html = get_new_deposits_html()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def serve_conversion_page(self):
        """通貨変換画面"""
        html = '''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>通貨変換 - エスクロー管理</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        h1 { margin-bottom: 30px; color: #333; }
        .back-link {
            display: inline-block;
            margin-bottom: 20px;
            color: #667eea;
            text-decoration: none;
        }
        .rate-display {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .rate-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .rate-item {
            text-align: center;
        }
        .rate-value {
            font-size: 2em;
            font-weight: bold;
        }
        .rate-label {
            margin-top: 5px;
            opacity: 0.9;
        }
        .converter {
            background: #f9f9f9;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .input-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #666;
        }
        input, select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 1.1em;
        }
        .calculation {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
            border: 2px solid #e0e0e0;
        }
        .calc-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        .calc-row:last-child {
            border-bottom: none;
            font-weight: bold;
            font-size: 1.2em;
            color: #28a745;
        }
        button {
            width: 100%;
            padding: 15px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 1.2em;
            cursor: pointer;
            margin-top: 20px;
        }
        button:hover {
            background: #218838;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .warning {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← ダッシュボードに戻る</a>
        <h1>💱 JPY → USDT 通貨変換</h1>

        <div class="rate-display">
            <h2>現在の為替レート</h2>
            <div class="rate-grid" id="rate-info">
                <div class="rate-item">
                    <div class="rate-value" id="current-rate">読込中...</div>
                    <div class="rate-label">JPY/USDT</div>
                </div>
                <div class="rate-item">
                    <div class="rate-value" id="network-fee">読込中...</div>
                    <div class="rate-label">ネットワーク手数料</div>
                </div>
                <div class="rate-item">
                    <div class="rate-value" id="processing-fee">読込中...</div>
                    <div class="rate-label">処理手数料</div>
                </div>
                <div class="rate-item">
                    <div class="rate-value" id="valid-until">読込中...</div>
                    <div class="rate-label">レート有効期限</div>
                </div>
            </div>
        </div>

        <div class="converter">
            <h3>変換計算</h3>

            <div class="input-group">
                <label>クライアント</label>
                <select id="client-select">
                    <option value="A">Client A</option>
                    <option value="B">Client B</option>
                </select>
            </div>

            <div class="input-group">
                <label>JPY金額</label>
                <input type="number" id="jpy-amount" placeholder="例: 1000000" onchange="calculateConversion()">
            </div>

            <div class="input-group">
                <label>送金先チェーン</label>
                <select id="chain">
                    <option value="TRC20">TRC20 (TRON)</option>
                    <option value="ERC20">ERC20 (Ethereum)</option>
                </select>
            </div>

            <div class="input-group">
                <label>送金先アドレス</label>
                <input type="text" id="address" placeholder="TX_...">
            </div>

            <div class="calculation" id="calculation" style="display: none;">
                <div class="calc-row">
                    <span>入金額 (JPY)</span>
                    <span id="calc-jpy">¥0</span>
                </div>
                <div class="calc-row">
                    <span>現在レート</span>
                    <span id="calc-rate">0</span>
                </div>
                <div class="calc-row">
                    <span>変換前USDT</span>
                    <span id="calc-gross">0 USDT</span>
                </div>
                <div class="calc-row">
                    <span>処理手数料 (0.5%)</span>
                    <span id="calc-proc-fee">-0 USDT</span>
                </div>
                <div class="calc-row">
                    <span>ネットワーク手数料</span>
                    <span id="calc-net-fee">-0 USDT</span>
                </div>
                <div class="calc-row">
                    <span>受取額</span>
                    <span id="calc-net">0 USDT</span>
                </div>
            </div>

            <button id="convert-btn" onclick="executeConversion()" disabled>変換を実行</button>

            <div class="warning">
                ⚠️ 注意事項:
                <ul style="margin-top: 10px; margin-left: 20px;">
                    <li>レートは5分間有効です</li>
                    <li>大口取引（1500万円以上）は2名の承認が必要です</li>
                    <li>変換後のキャンセルはできません</li>
                </ul>
            </div>
        </div>
    </div>

    <script>
        let currentRates = null;
        let countdown = null;

        async function loadRates() {
            try {
                const response = await fetch('/api/rates');
                currentRates = await response.json();

                document.getElementById('current-rate').textContent = currentRates.jpy_to_usdt.toFixed(2);
                document.getElementById('network-fee').textContent = currentRates.network_fee_usdt + ' USDT';
                document.getElementById('processing-fee').textContent = currentRates.processing_fee_percent + '%';

                // カウントダウン開始
                if (countdown) clearInterval(countdown);
                updateCountdown();
                countdown = setInterval(updateCountdown, 1000);

            } catch (error) {
                console.error('Error loading rates:', error);
            }
        }

        function updateCountdown() {
            if (!currentRates) return;
            const validUntil = new Date(currentRates.valid_until);
            const now = new Date();
            const diff = validUntil - now;

            if (diff <= 0) {
                document.getElementById('valid-until').textContent = '期限切れ';
                loadRates();
            } else {
                const minutes = Math.floor(diff / 60000);
                const seconds = Math.floor((diff % 60000) / 1000);
                document.getElementById('valid-until').textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            }
        }

        function calculateConversion() {
            const jpyAmount = parseFloat(document.getElementById('jpy-amount').value);
            if (!jpyAmount || !currentRates) return;

            const grossUsdt = jpyAmount / currentRates.jpy_to_usdt;
            const processingFee = grossUsdt * (currentRates.processing_fee_percent / 100);
            const networkFee = currentRates.network_fee_usdt;
            const netUsdt = grossUsdt - processingFee - networkFee;

            document.getElementById('calc-jpy').textContent = '¥' + jpyAmount.toLocaleString();
            document.getElementById('calc-rate').textContent = currentRates.jpy_to_usdt.toFixed(2);
            document.getElementById('calc-gross').textContent = grossUsdt.toFixed(4) + ' USDT';
            document.getElementById('calc-proc-fee').textContent = '-' + processingFee.toFixed(4) + ' USDT';
            document.getElementById('calc-net-fee').textContent = '-' + networkFee + ' USDT';
            document.getElementById('calc-net').textContent = netUsdt.toFixed(4) + ' USDT';

            document.getElementById('calculation').style.display = 'block';
            document.getElementById('convert-btn').disabled = netUsdt <= 0 || !document.getElementById('address').value;
        }

        async function executeConversion() {
            const client = document.getElementById('client-select').value;
            const jpyAmount = parseFloat(document.getElementById('jpy-amount').value);
            const chain = document.getElementById('chain').value;
            const address = document.getElementById('address').value;

            if (!confirm(`以下の内容で変換を実行しますか？\\n\\nJPY: ¥${jpyAmount.toLocaleString()}\\nチェーン: ${chain}\\nアドレス: ${address}`)) {
                return;
            }

            try {
                const response = await fetch('/api/convert', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        client_id: client,
                        jpy_amount: jpyAmount,
                        chain: chain,
                        address: address,
                        rate: currentRates.jpy_to_usdt
                    })
                });

                const result = await response.json();
                if (result.success) {
                    alert(`変換リクエストを作成しました\\nリクエストID: ${result.request_id}\\n\\n承認画面で処理を続けてください`);
                    window.location.href = '/approvals';
                } else {
                    alert('エラー: ' + result.error);
                }
            } catch (error) {
                alert('処理中にエラーが発生しました');
            }
        }

        // 定期的にレート更新
        loadRates();
        setInterval(loadRates, 60000); // 1分ごと

        // アドレス入力時のボタン有効化チェック
        document.getElementById('address').addEventListener('input', calculateConversion);
    </script>
</body>
</html>'''
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def serve_approvals_page(self):
        """承認管理画面"""
        html = '''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>承認管理 - エスクロー管理</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        h1 { margin-bottom: 30px; color: #333; }
        .back-link {
            display: inline-block;
            margin-bottom: 20px;
            color: #667eea;
            text-decoration: none;
        }
        .approval-item {
            background: #f9f9f9;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .approval-item.urgent {
            border-color: #dc3545;
            background: #fff5f5;
        }
        .approval-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .approval-id {
            color: #666;
            font-size: 0.9em;
        }
        .approval-status {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
        }
        .status-pending {
            background: #ffc107;
            color: white;
        }
        .status-approved {
            background: #28a745;
            color: white;
        }
        .approval-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .detail-item {
            padding: 10px;
            background: white;
            border-radius: 5px;
        }
        .detail-label {
            color: #666;
            font-size: 0.9em;
        }
        .detail-value {
            font-size: 1.2em;
            font-weight: bold;
            margin-top: 5px;
        }
        .approval-actions {
            display: flex;
            gap: 10px;
        }
        button {
            padding: 10px 30px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1em;
        }
        .btn-approve {
            background: #28a745;
            color: white;
        }
        .btn-reject {
            background: #dc3545;
            color: white;
        }
        .approver-input {
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-right: 10px;
        }
        .approval-progress {
            background: #e3f2fd;
            padding: 10px;
            border-radius: 5px;
            margin-top: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← ダッシュボードに戻る</a>
        <h1>✅ 承認管理</h1>

        <div id="approval-list">
            <p>読込中...</p>
        </div>
    </div>

    <script>
        async function loadApprovals() {
            try {
                const response = await fetch('/api/pending_approvals');
                const approvals = await response.json();

                const listEl = document.getElementById('approval-list');

                if (approvals.length === 0) {
                    listEl.innerHTML = '<p style="text-align: center; color: #666;">承認待ちの取引はありません</p>';
                    return;
                }

                listEl.innerHTML = approvals.map(item => {
                    const isUrgent = item.amount_usdt >= 10000;
                    const progressPercent = (item.approvals_count / item.required_approvals) * 100;

                    return `
                        <div class="approval-item ${isUrgent ? 'urgent' : ''}">
                            <div class="approval-header">
                                <div>
                                    <div class="approval-id">ID: ${item.id}</div>
                                    <div style="font-size: 1.2em; margin-top: 5px;">
                                        Client ${item.client_id} - ${item.amount_usdt} USDT
                                    </div>
                                </div>
                                <span class="approval-status status-${item.status}">${item.status}</span>
                            </div>

                            <div class="approval-details">
                                <div class="detail-item">
                                    <div class="detail-label">変換額</div>
                                    <div class="detail-value">${item.amount_usdt} USDT</div>
                                </div>
                                <div class="detail-item">
                                    <div class="detail-label">送金先</div>
                                    <div class="detail-value">${item.chain}</div>
                                </div>
                                <div class="detail-item">
                                    <div class="detail-label">アドレス</div>
                                    <div class="detail-value" style="font-size: 0.9em; word-break: break-all;">
                                        ${item.address}
                                    </div>
                                </div>
                                <div class="detail-item">
                                    <div class="detail-label">承認状況</div>
                                    <div class="detail-value">${item.approvals_count}/${item.required_approvals}</div>
                                </div>
                            </div>

                            <div class="approval-progress">
                                <div style="background: #4caf50; height: 10px; width: ${progressPercent}%; border-radius: 5px;"></div>
                                <div style="margin-top: 5px; font-size: 0.9em; color: #666;">
                                    承認進捗: ${progressPercent.toFixed(0)}%
                                    ${item.approvers ? `(承認者: ${item.approvers.join(', ')})` : ''}
                                </div>
                            </div>

                            <div class="approval-actions" style="margin-top: 20px;">
                                <input type="text" class="approver-input" id="approver-${item.id}" placeholder="承認者名">
                                <button class="btn-approve" onclick="approveRequest('${item.id}')">承認</button>
                                <button class="btn-reject" onclick="rejectRequest('${item.id}')">却下</button>
                            </div>
                        </div>
                    `;
                }).join('');
            } catch (error) {
                console.error('Error loading approvals:', error);
                document.getElementById('approval-list').innerHTML = '<p style="color: red;">エラーが発生しました</p>';
            }
        }

        async function approveRequest(requestId) {
            const approver = document.getElementById(`approver-${requestId}`).value;
            if (!approver) {
                alert('承認者名を入力してください');
                return;
            }

            if (!confirm(`この取引を承認しますか？\\n承認者: ${approver}`)) return;

            try {
                const response = await fetch('/api/approve', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        request_id: requestId,
                        approver: approver
                    })
                });

                const result = await response.json();
                if (result.success) {
                    if (result.fully_approved) {
                        alert('取引が完全に承認され、実行されました！');
                    } else {
                        alert(`承認を記録しました (${result.approvals_count}/${result.required_approvals})`);
                    }
                    loadApprovals();
                } else {
                    alert('エラー: ' + result.error);
                }
            } catch (error) {
                alert('処理中にエラーが発生しました');
            }
        }

        async function rejectRequest(requestId) {
            const approver = document.getElementById(`approver-${requestId}`).value;
            if (!approver) {
                alert('却下者名を入力してください');
                return;
            }

            if (!confirm(`この取引を却下しますか？\\n却下者: ${approver}`)) return;

            try {
                const response = await fetch('/api/reject', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        request_id: requestId,
                        rejector: approver
                    })
                });

                const result = await response.json();
                if (result.success) {
                    alert('取引を却下しました');
                    loadApprovals();
                } else {
                    alert('エラー: ' + result.error);
                }
            } catch (error) {
                alert('処理中にエラーが発生しました');
            }
        }

        loadApprovals();
        setInterval(loadApprovals, 10000); // 10秒ごとに更新
    </script>
</body>
</html>'''
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def serve_error_log_page(self):
        """エラーログ画面"""
        html = '''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>エラーログ - エスクロー管理</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        h1 { margin-bottom: 30px; color: #333; }
        .back-link {
            display: inline-block;
            margin-bottom: 20px;
            color: #667eea;
            text-decoration: none;
        }
        .error-filters {
            background: #f9f9f9;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        .filter-item {
            display: flex;
            flex-direction: column;
        }
        .filter-item label {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }
        .filter-item select, .filter-item input {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        .error-item {
            background: #fff5f5;
            border-left: 4px solid #dc3545;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 5px;
        }
        .error-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        .error-type {
            background: #dc3545;
            color: white;
            padding: 3px 10px;
            border-radius: 3px;
            font-size: 0.9em;
        }
        .error-time {
            color: #666;
            font-size: 0.9em;
        }
        .error-message {
            font-weight: bold;
            margin-bottom: 10px;
        }
        .error-details {
            background: white;
            padding: 15px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 0.9em;
            color: #666;
            white-space: pre-wrap;
        }
        .error-resolved {
            opacity: 0.6;
        }
        .btn-resolve {
            background: #28a745;
            color: white;
            border: none;
            padding: 5px 15px;
            border-radius: 3px;
            cursor: pointer;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← ダッシュボードに戻る</a>
        <h1>⚠️ エラーログ</h1>

        <div class="error-filters">
            <div class="filter-item">
                <label>エラータイプ</label>
                <select id="filter-type" onchange="filterErrors()">
                    <option value="">すべて</option>
                    <option value="conversion">変換エラー</option>
                    <option value="network">ネットワークエラー</option>
                    <option value="validation">検証エラー</option>
                    <option value="approval">承認エラー</option>
                </select>
            </div>
            <div class="filter-item">
                <label>期間</label>
                <select id="filter-period" onchange="filterErrors()">
                    <option value="today">今日</option>
                    <option value="week">過去7日</option>
                    <option value="month">過去30日</option>
                    <option value="all">すべて</option>
                </select>
            </div>
            <div class="filter-item">
                <label>ステータス</label>
                <select id="filter-status" onchange="filterErrors()">
                    <option value="unresolved">未解決のみ</option>
                    <option value="all">すべて</option>
                </select>
            </div>
        </div>

        <div id="error-list">
            <p>読込中...</p>
        </div>
    </div>

    <script>
        let allErrors = [];

        async function loadErrors() {
            try {
                const response = await fetch('/api/errors');
                allErrors = await response.json();
                filterErrors();
            } catch (error) {
                console.error('Error loading errors:', error);
                document.getElementById('error-list').innerHTML = '<p style="color: red;">エラーログの読み込みに失敗しました</p>';
            }
        }

        function filterErrors() {
            const type = document.getElementById('filter-type').value;
            const period = document.getElementById('filter-period').value;
            const status = document.getElementById('filter-status').value;

            let filtered = [...allErrors];

            // タイプフィルター
            if (type) {
                filtered = filtered.filter(e => e.type === type);
            }

            // ステータスフィルター
            if (status === 'unresolved') {
                filtered = filtered.filter(e => !e.resolved);
            }

            // 期間フィルター
            const now = new Date();
            if (period === 'today') {
                const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
                filtered = filtered.filter(e => new Date(e.timestamp) >= today);
            } else if (period === 'week') {
                const week = new Date(now - 7 * 24 * 60 * 60 * 1000);
                filtered = filtered.filter(e => new Date(e.timestamp) >= week);
            } else if (period === 'month') {
                const month = new Date(now - 30 * 24 * 60 * 60 * 1000);
                filtered = filtered.filter(e => new Date(e.timestamp) >= month);
            }

            displayErrors(filtered);
        }

        function displayErrors(errors) {
            const listEl = document.getElementById('error-list');

            if (errors.length === 0) {
                listEl.innerHTML = '<p style="text-align: center; color: #666;">エラーログはありません</p>';
                return;
            }

            listEl.innerHTML = errors.map(error => `
                <div class="error-item ${error.resolved ? 'error-resolved' : ''}">
                    <div class="error-header">
                        <span class="error-type">${error.type}</span>
                        <span class="error-time">${new Date(error.timestamp).toLocaleString('ja-JP')}</span>
                    </div>
                    <div class="error-message">${error.message}</div>
                    ${error.details ? `
                        <div class="error-details">${JSON.stringify(error.details, null, 2)}</div>
                    ` : ''}
                    ${!error.resolved ? `
                        <button class="btn-resolve" onclick="resolveError('${error.id}')">解決済みにする</button>
                    ` : '<div style="color: #28a745; margin-top: 10px;">✓ 解決済み</div>'}
                </div>
            `).join('');
        }

        async function resolveError(errorId) {
            // エラー解決処理（実装省略）
            alert('エラーを解決済みにしました');
            loadErrors();
        }

        loadErrors();
        setInterval(loadErrors, 30000); // 30秒ごとに更新
    </script>
</body>
</html>'''
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def serve_demo_page(self):
        """デモ・実験画面"""
        html = '''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>デモ・実験 - エスクロー管理</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #f39c12, #e74c3c);
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        h1 {
            margin-bottom: 30px;
            color: #333;
            text-align: center;
        }
        .back-link {
            display: inline-block;
            margin-bottom: 20px;
            color: #667eea;
            text-decoration: none;
        }
        .demo-section {
            background: #f9f9f9;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 25px;
            border: 2px dashed #ddd;
        }
        .demo-section h3 {
            color: #e74c3c;
            margin-bottom: 20px;
            font-size: 1.3em;
        }
        .demo-controls {
            display: grid;
            gap: 15px;
        }
        .control-group {
            display: grid;
            grid-template-columns: 150px 1fr auto;
            gap: 15px;
            align-items: center;
        }
        .control-group label {
            font-weight: bold;
            color: #666;
        }
        input, select {
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 1em;
        }
        button {
            padding: 10px 25px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
        }
        .btn-primary {
            background: #3498db;
            color: white;
        }
        .btn-success {
            background: #27ae60;
            color: white;
        }
        .btn-danger {
            background: #e74c3c;
            color: white;
        }
        .btn-warning {
            background: #f39c12;
            color: white;
        }
        button:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .scenario-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .scenario-card {
            background: white;
            border: 2px solid #3498db;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        .scenario-card:hover {
            background: #ecf0f1;
            transform: translateY(-5px);
        }
        .scenario-icon {
            font-size: 3em;
            margin-bottom: 10px;
        }
        .log-output {
            background: #2c3e50;
            color: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            font-family: monospace;
            max-height: 300px;
            overflow-y: auto;
            margin-top: 20px;
            white-space: pre-wrap;
        }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 5px;
        }
        .status-active {
            background: #27ae60;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← ダッシュボードに戻る</a>
        <h1>🎮 Sandboxデモ環境</h1>

        <div class="demo-section">
            <h3>💰 入金シミュレーション</h3>
            <div class="demo-controls">
                <div class="control-group">
                    <label>クライアント</label>
                    <select id="demo-client">
                        <option value="A">Client A</option>
                        <option value="B">Client B</option>
                    </select>
                    <span></span>
                </div>
                <div class="control-group">
                    <label>入金額 (JPY)</label>
                    <input type="number" id="demo-amount" value="1000000">
                    <button class="btn-success" onclick="simulateDeposit()">入金実行</button>
                </div>
            </div>
        </div>

        <div class="demo-section">
            <h3>📋 シナリオテスト</h3>
            <div class="scenario-cards">
                <div class="scenario-card" onclick="runScenario('small')">
                    <div class="scenario-icon">💵</div>
                    <div>少額取引</div>
                    <div style="font-size: 0.9em; color: #666;">¥100,000 → 承認不要</div>
                </div>
                <div class="scenario-card" onclick="runScenario('large')">
                    <div class="scenario-icon">💎</div>
                    <div>大口取引</div>
                    <div style="font-size: 0.9em; color: #666;">¥15,000,000 → 2名承認</div>
                </div>
                <div class="scenario-card" onclick="runScenario('error')">
                    <div class="scenario-icon">⚠️</div>
                    <div>エラーケース</div>
                    <div style="font-size: 0.9em; color: #666;">残高不足エラー</div>
                </div>
                <div class="scenario-card" onclick="runScenario('full')">
                    <div class="scenario-icon">🔄</div>
                    <div>完全フロー</div>
                    <div style="font-size: 0.9em; color: #666;">入金→変換→承認→出金</div>
                </div>
            </div>
        </div>

        <div class="demo-section">
            <h3>🛠️ システム操作</h3>
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                <button class="btn-warning" onclick="resetDatabase()">🔄 DBリセット</button>
                <button class="btn-primary" onclick="generateTestData()">📊 テストデータ生成</button>
                <button class="btn-success" onclick="openDashboard()">📈 ダッシュボード更新</button>
                <button class="btn-danger" onclick="simulateError()">⚡ エラー発生</button>
            </div>
        </div>

        <div class="demo-section">
            <h3><span class="status-indicator status-active"></span>実行ログ</h3>
            <div class="log-output" id="demo-log">
システム準備完了...
Sandbox環境で動作中
            </div>
        </div>
    </div>

    <script>
        function addLog(message, type = 'info') {
            const logEl = document.getElementById('demo-log');
            const timestamp = new Date().toLocaleTimeString('ja-JP');
            const prefix = type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️';
            logEl.textContent += `\\n[${timestamp}] ${prefix} ${message}`;
            logEl.scrollTop = logEl.scrollHeight;
        }

        async function simulateDeposit() {
            const client = document.getElementById('demo-client').value;
            const amount = parseInt(document.getElementById('demo-amount').value);

            addLog(`入金シミュレーション開始: Client ${client}, ¥${amount.toLocaleString()}`);

            try {
                const response = await fetch('/api/demo/deposit', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        client_id: client,
                        amount: amount
                    })
                });

                const result = await response.json();
                if (result.success) {
                    addLog(`入金成功! Transaction ID: ${result.transaction_id}`, 'success');
                    addLog('入金確認画面で処理を続けてください');
                } else {
                    addLog(`エラー: ${result.error}`, 'error');
                }
            } catch (error) {
                addLog(`通信エラー: ${error.message}`, 'error');
            }
        }

        async function runScenario(scenario) {
            addLog(`シナリオ「${scenario}」を実行中...`);

            const scenarios = {
                small: async () => {
                    addLog('少額取引シナリオ: ¥100,000の入金と変換');
                    await simulateDepositAmount('A', 100000);
                    addLog('承認不要で自動処理されます');
                },
                large: async () => {
                    addLog('大口取引シナリオ: ¥15,000,000の入金');
                    await simulateDepositAmount('A', 15000000);
                    addLog('2名の承認が必要です → 承認画面へ');
                },
                error: async () => {
                    addLog('エラーシナリオ: 残高不足での変換試行');
                    await simulateDepositAmount('B', 1000);
                    addLog('変換時にエラーが発生します', 'error');
                },
                full: async () => {
                    addLog('完全フローシナリオ開始');
                    addLog('1. 入金: ¥2,500,000');
                    await simulateDepositAmount('A', 2500000);
                    addLog('2. 変換: 15,000 USDT');
                    addLog('3. 承認: 2名承認待ち');
                    addLog('4. 出金: TRC20ネットワーク');
                    addLog('完全フロー設定完了', 'success');
                }
            };

            if (scenarios[scenario]) {
                await scenarios[scenario]();
            }
        }

        async function simulateDepositAmount(client, amount) {
            const response = await fetch('/api/demo/deposit', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ client_id: client, amount: amount })
            });
            return response.json();
        }

        async function resetDatabase() {
            if (!confirm('データベースをリセットしますか？\\nすべてのデータが削除されます。')) return;

            addLog('データベースリセット中...');
            try {
                const response = await fetch('/api/demo/reset', { method: 'POST' });
                const result = await response.json();
                if (result.success) {
                    addLog('データベースをリセットしました', 'success');
                } else {
                    addLog('リセット失敗', 'error');
                }
            } catch (error) {
                addLog(`エラー: ${error.message}`, 'error');
            }
        }

        function generateTestData() {
            addLog('テストデータ生成中...');
            setTimeout(() => {
                addLog('Client A: ¥5,000,000 残高設定');
                addLog('Client B: ¥2,000,000 残高設定');
                addLog('5件の取引履歴を追加');
                addLog('テストデータ生成完了', 'success');
            }, 1000);
        }

        function openDashboard() {
            addLog('ダッシュボードを更新中...');
            window.open('/reports/dashboard.html', '_blank');
        }

        function simulateError() {
            addLog('エラーシミュレーション実行', 'error');
            addLog('ネットワークタイムアウトエラーを記録', 'error');
            addLog('エラーログ画面で確認できます');
        }
    </script>
</body>
</html>'''
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    # API エンドポイント
    def get_deposits(self):
        """入金一覧取得API - bank_depositsの統計情報"""
        with db() as conn:
            c = conn.cursor()
            # bank_depositsテーブルから総残高を取得
            c.execute("""
                SELECT 'BANK_TOTAL' as client_id,
                       '銀行入金総計' as client_name,
                       COALESCE(SUM(amount), 0) as balance
                FROM bank_deposits
                WHERE status IN ('pending', 'processing')
            """)
            deposits = []
            row = c.fetchone()
            if row:
                deposits.append({
                    "client_id": row[0],
                    "client_name": row[1],
                    "balance": row[2]
                })

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(deposits).encode())

    def get_pending_deposits(self):
        """未処理入金取得API - bank_depositsテーブルから取得"""
        with db() as conn:
            c = conn.cursor()
            # bank_depositsテーブルから未処理の入金を取得
            c.execute("""
                SELECT COUNT(*) FROM bank_deposits WHERE status = 'pending'
            """)
            count = c.fetchone()[0]

            c.execute("""
                SELECT id, sender_name, amount, status, created_at, sender_bank
                FROM bank_deposits
                WHERE status = 'pending'
                ORDER BY created_at DESC
                LIMIT 10
            """)

            deposits = []
            for row in c.fetchall():
                deposits.append({
                    "id": row[0],
                    "client_id": "BANK_CLIENT",
                    "sender_name": row[1],
                    "amount": row[2],
                    "status": row[3],
                    "created_at": row[4],
                    "va_number": "VA-BANK-001",
                    "sender": row[5] or "不明"
                })

            pending = {
                "count": count,
                "deposits": deposits
            }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(pending).encode())

    def get_exchange_rates(self):
        """為替レート取得API"""
        rates = get_current_rates()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(rates).encode())

    def get_pending_approvals(self):
        """承認待ち取得API"""
        with db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT id, client_id, amount_usdt, chain, address,
                       status, required_approvals, approvals_count
                FROM release_requests
                WHERE status = 'pending'
                ORDER BY created_at DESC
            """)

            approvals = []
            for row in c.fetchall():
                # 承認者リスト取得
                c.execute("""
                    SELECT approver FROM approvals
                    WHERE request_id = ?
                """, (row[0],))
                approvers = [r[0] for r in c.fetchall()]

                approvals.append({
                    "id": row[0],
                    "client_id": row[1],
                    "amount_usdt": row[2],
                    "chain": row[3],
                    "address": row[4],
                    "status": row[5],
                    "required_approvals": row[6],
                    "approvals_count": row[7],
                    "approvers": approvers
                })

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(approvals).encode())

    def get_error_logs(self):
        """エラーログ取得API"""
        # モックエラーデータ
        errors = [
            {
                "id": "err_001",
                "type": "network",
                "message": "API接続タイムアウト",
                "timestamp": now_iso(),
                "resolved": False,
                "details": {
                    "endpoint": "rapyd.net/api/v1/payouts",
                    "timeout": 30,
                    "retry_count": 3
                }
            }
        ]

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(errors).encode())

    def convert_to_usdt(self, data):
        """USDT変換処理API"""
        client_id = data.get('client_id')
        jpy_amount = data.get('jpy_amount')
        chain = data.get('chain')
        address = data.get('address')
        rate = data.get('rate')

        try:
            # USDTに変換
            usdt_amount = jpy_amount / rate

            # リリースリクエスト作成
            request_id = create_release_request(
                client_id=client_id,
                amount_usdt=usdt_amount,
                chain=chain,
                address=address,
                max_slippage_bps=50
            )

            # レート添付
            attach_quote(request_id, rate,
                        (datetime.utcnow() + timedelta(minutes=5)).isoformat() + "Z")

            result = {
                "success": True,
                "request_id": request_id,
                "usdt_amount": usdt_amount
            }
        except Exception as e:
            result = {
                "success": False,
                "error": str(e)
            }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def approve_transaction(self, data):
        """取引承認処理API"""
        request_id = data.get('request_id')
        approver = data.get('approver')

        try:
            approve_release(request_id, approver)

            # 承認状況確認
            with db() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT approvals_count, required_approvals, status
                    FROM release_requests WHERE id = ?
                """, (request_id,))
                row = c.fetchone()

                if row[0] >= row[1]:
                    # 完全承認されたら実行
                    payout_id = execute_payout(request_id)
                    result = {
                        "success": True,
                        "fully_approved": True,
                        "payout_id": payout_id,
                        "approvals_count": row[0],
                        "required_approvals": row[1]
                    }
                else:
                    result = {
                        "success": True,
                        "fully_approved": False,
                        "approvals_count": row[0],
                        "required_approvals": row[1]
                    }
        except Exception as e:
            result = {
                "success": False,
                "error": str(e)
            }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def simulate_deposit(self, data):
        """入金シミュレーション - 入金データ生成ページからの入金受信"""
        try:
            # 入金データ生成ページからの場合
            if 'sender_name' in data:
                deposit_id = data.get('id') or f"DEP_{uuid.uuid4().hex[:8].upper()}"

                with db() as conn:
                    c = conn.cursor()
                    c.execute("""
                        INSERT OR REPLACE INTO bank_deposits
                        (id, sender_name, sender_bank, amount, purpose,
                         status, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                    """, (
                        deposit_id,
                        data.get('sender_name'),
                        data.get('sender_bank'),
                        data.get('amount'),
                        data.get('purpose'),
                        data.get('timestamp', now_iso()),
                        now_iso()
                    ))

                result = {
                    "success": True,
                    "deposit_id": deposit_id,
                    "amount": data.get('amount')
                }

            else:
                # 従来のシミュレーション
                client_id = data.get('client_id')
                amount = data.get('amount')

                evt = deposit_jpy(client_id, amount)
                record_deposit(evt["json"])

                result = {
                    "success": True,
                    "transaction_id": evt["json"]["id"],
                    "amount": amount
                }

        except Exception as e:
            result = {
                "success": False,
                "error": str(e)
            }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def reset_demo(self):
        """デモ環境リセット"""
        try:
            # DB再初期化
            init_db()
            result = {"success": True}
        except Exception as e:
            result = {"success": False, "error": str(e)}

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def get_bank_deposits(self):
        """銀行入金データ取得API"""
        with db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT id, sender_name, sender_bank, amount, purpose,
                       status, tron_address, processed_at, created_at, updated_at
                FROM bank_deposits
                ORDER BY created_at DESC
            """)

            deposits = []
            for row in c.fetchall():
                deposits.append({
                    "id": row[0],
                    "sender_name": row[1],
                    "sender_bank": row[2],
                    "amount": row[3],
                    "purpose": row[4],
                    "status": row[5],
                    "tron_address": row[6],
                    "processed_at": row[7],
                    "created_at": row[8],
                    "updated_at": row[9]
                })

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(deposits).encode())

    def process_deposit(self, data):
        """入金承認・USDT送金処理API"""
        deposit_id = data.get('deposit_id')
        tron_address = data.get('tron_address')
        rate = data.get('rate')

        try:
            with db() as conn:
                c = conn.cursor()

                # 入金データ取得
                c.execute("SELECT * FROM bank_deposits WHERE id = ?", (deposit_id,))
                deposit = c.fetchone()

                if not deposit:
                    raise ValueError("入金データが見つかりません")

                if deposit[5] != 'pending':  # status
                    raise ValueError("この入金は既に処理済みです")

                # USDT計算
                jpy_amount = deposit[3]  # amount
                gross_usdt = jpy_amount / rate
                processing_fee = gross_usdt * 0.005  # 0.5%
                network_fee = 1.0
                net_usdt = gross_usdt - processing_fee - network_fee

                # TXIDシミュレーション（実際のTron送金の場合はここで実際の送金処理）
                mock_txid = f"TRON_{uuid.uuid4().hex[:16].upper()}"

                # ステータス更新
                c.execute("""
                    UPDATE bank_deposits
                    SET status = 'processing',
                        tron_address = ?,
                        processed_at = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (tron_address, now_iso(), now_iso(), deposit_id))

                # 監査ログ
                from .audit import append as audit
                audit("usdt_conversion", deposit_id, {
                    "sender_name": deposit[1],
                    "jpy_amount": jpy_amount,
                    "usdt_amount": net_usdt,
                    "rate": rate,
                    "tron_address": tron_address,
                    "txid": mock_txid
                })

                # 5秒後に完了ステータスに変更（実際のブロックチェーン確認の代替）
                import threading
                def mark_completed():
                    import time
                    time.sleep(5)
                    with db() as conn2:
                        c2 = conn2.cursor()
                        c2.execute("""
                            UPDATE bank_deposits
                            SET status = 'completed', updated_at = ?
                            WHERE id = ?
                        """, (now_iso(), deposit_id))

                threading.Thread(target=mark_completed).start()

                result = {
                    "success": True,
                    "txid": mock_txid,
                    "usdt_amount": net_usdt,
                    "tron_address": tron_address
                }

        except Exception as e:
            result = {
                "success": False,
                "error": str(e)
            }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())


def run_server(port=8080):
    """Webサーバー起動"""
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, EscrowWebHandler)
    print(f'🚀 エスクロー管理システム起動')
    print(f'📍 アクセスURL: http://localhost:{port}')
    print(f'   - メインダッシュボード: http://localhost:{port}/')
    print(f'   - 入金確認: http://localhost:{port}/deposits')
    print(f'   - 通貨変換: http://localhost:{port}/convert')
    print(f'   - 承認管理: http://localhost:{port}/approvals')
    print(f'   - エラーログ: http://localhost:{port}/errors')
    print(f'   - デモ環境: http://localhost:{port}/demo')
    print(f'\n[Ctrl+C で停止]')
    httpd.serve_forever()

if __name__ == "__main__":
    import sys
    import os
    # Renderの環境変数PORTを優先的に使用
    port = int(os.environ.get('PORT', sys.argv[1] if len(sys.argv) > 1 else 10000))
    run_server(port)