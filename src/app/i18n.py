import os
from typing import Any, Dict


APP_LANG = os.getenv("APP_LANG", os.getenv("LANG", "ja")).split(".")[0].lower()
SUPPORTED = {"en", "ja"}


MESSAGES: Dict[str, Dict[str, str]] = {
    "en": {
        # Dashboard
        "dashboard.title": "Escrow Sandbox Dashboard",
        "dashboard.generated": "Generated",
        "dashboard.balances.title": "Balances by Client (JPY)",
        "dashboard.balances.client": "Client",
        "dashboard.balances.jpy": "JPY",
        "dashboard.releases.title": "Release Requests",
        "common.id": "ID",
        "common.client": "Client",
        "common.usdt": "USDT",
        "common.chain": "Chain",
        "common.status": "Status",
        "common.approvals": "Approvals",
        "dashboard.payouts.title": "Payouts",
        "dashboard.payouts.txhash": "Tx Hash",
        "dashboard.alerts.title": "Alerts",
        "common.time": "Time",
        "common.severity": "Severity",
        "common.kind": "Kind",
        "common.message": "Message",
        # CLI
        "cli.init.done": "DB initialized and clients seeded (A,B)",
        "cli.deposit.ok": "deposit ok: client={client} amount={amount}",
        "cli.release.created": "release request created: {req_id} rate={rate:.4f} JPY/USDT expires={exp}",
        "cli.approve.count": "approved count={count}",
        "cli.payout.sent": "payout sent: {payout_id}",
        "cli.status.balances": "Balances:",
        "cli.status.release_requests": "Release Requests:",
        "cli.status.payouts": "Payouts:",
        "cli.addr.added": "address added: {address_id}",
        "cli.addr.approved": "address approved: {address_id}",
        # Run-all
        "run.step1": "[1/7] init db + clients...",
        "run.step2": "[2/7] simulate JPY deposit for Client A...",
        "run.step3": "[3/7] create release request + quote...",
        "run.step4": "[4/7] approvals (2x)...",
        "run.step5": "[5/7] execute payout...",
        "run.step6": "[6/7] daily reconciliation...",
        "run.step7": "[7/7] build dashboard...",
        "run.summary": "=== Summary ===",
        "run.summary.req": "request_id",
        "run.summary.payout": "payout_id",
        "run.summary.recon": "recon",
        "run.summary.dashboard": "dashboard",
        # Alerts
        "alert.high_amount": "High JPY amount detected: {amount}",
    },
    "ja": {
        # Dashboard
        "dashboard.title": "エスクロー サンドボックス ダッシュボード",
        "dashboard.generated": "生成時刻",
        "dashboard.balances.title": "クライアント別残高（JPY）",
        "dashboard.balances.client": "クライアント",
        "dashboard.balances.jpy": "JPY",
        "dashboard.releases.title": "解放リクエスト",
        "common.id": "ID",
        "common.client": "クライアント",
        "common.usdt": "USDT",
        "common.chain": "チェーン",
        "common.status": "ステータス",
        "common.approvals": "承認数",
        "dashboard.payouts.title": "出金",
        "dashboard.payouts.txhash": "Txハッシュ",
        "dashboard.alerts.title": "アラート",
        "common.time": "時刻",
        "common.severity": "重大度",
        "common.kind": "種別",
        "common.message": "メッセージ",
        # CLI
        "cli.init.done": "DBを初期化し、テストクライアント（A,B）を作成しました",
        "cli.deposit.ok": "入金処理OK: client={client} amount={amount}",
        "cli.release.created": "解放リクエストを作成: {req_id} レート={rate:.4f} JPY/USDT 失効={exp}",
        "cli.approve.count": "承認数={count}",
        "cli.payout.sent": "出金送信: {payout_id}",
        "cli.status.balances": "残高:",
        "cli.status.release_requests": "解放リクエスト:",
        "cli.status.payouts": "出金:",
        "cli.addr.added": "アドレスを追加しました: {address_id}",
        "cli.addr.approved": "アドレスを承認しました: {address_id}",
        # Run-all
        "run.step1": "[1/7] DBとクライアント初期化...",
        "run.step2": "[2/7] クライアントAへJPY入金をシミュレート...",
        "run.step3": "[3/7] 解放リクエスト作成＋見積...",
        "run.step4": "[4/7] 二人承認...",
        "run.step5": "[5/7] 出金実行...",
        "run.step6": "[6/7] 日次照合...",
        "run.step7": "[7/7] ダッシュボード生成...",
        "run.summary": "=== サマリー ===",
        "run.summary.req": "request_id",
        "run.summary.payout": "payout_id",
        "run.summary.recon": "recon",
        "run.summary.dashboard": "dashboard",
        # Alerts
        "alert.high_amount": "高額JPYが検知されました: {amount}",
    },
}


def _lang() -> str:
    return APP_LANG if APP_LANG in SUPPORTED else "en"


def t(key: str, **params: Any) -> str:
    lang = _lang()
    msg = MESSAGES.get(lang, {}).get(key) or MESSAGES["en"].get(key) or key
    try:
        return msg.format(**params)
    except Exception:
        return msg
