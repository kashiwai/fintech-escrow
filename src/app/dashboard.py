import os
from datetime import datetime

from .config import REPORTS_DIR
from .i18n import t
from .db import db


def build_dashboard() -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, "dashboard.html")
    with db() as conn, open(path, "w", encoding="utf-8") as f:
        c = conn.cursor()
        f.write(f"<html><head><meta charset='utf-8'><title>{t('dashboard.title')}</title></head><body>")
        f.write(f"<h1>{t('dashboard.title')}</h1><p>{t('dashboard.generated')}: {datetime.utcnow().isoformat()}Z</p>")

        # Inbound deposits by client
        f.write(f"<h2>{t('dashboard.balances.title')}</h2><table border='1'><tr><th>{t('dashboard.balances.client')}</th><th>{t('dashboard.balances.jpy')}</th></tr>")
        c.execute(
            "SELECT client_id, available FROM balances WHERE currency='JPY' ORDER BY client_id"
        )
        for row in c.fetchall():
            f.write(f"<tr><td>{row['client_id']}</td><td>{row['available']}</td></tr>")
        f.write("</table>")

        # Release requests summary
        f.write(f"<h2>{t('dashboard.releases.title')}</h2><table border='1'><tr><th>{t('common.id')}</th><th>{t('common.client')}</th><th>{t('common.usdt')}</th><th>{t('common.chain')}</th><th>{t('common.status')}</th><th>{t('common.approvals')}</th></tr>")
        c.execute(
            "SELECT id, client_id, amount_usdt, chain, status, approvals_count, required_approvals FROM release_requests ORDER BY created_at DESC LIMIT 50"
        )
        for row in c.fetchall():
            f.write(
                f"<tr><td>{row['id']}</td><td>{row['client_id']}</td><td>{row['amount_usdt']}</td><td>{row['chain']}</td>"
                f"<td>{row['status']}</td><td>{row['approvals_count']}/{row['required_approvals']}</td></tr>"
            )
        f.write("</table>")

        # Recent payouts
        f.write(f"<h2>{t('dashboard.payouts.title')}</h2><table border='1'><tr><th>{t('common.id')}</th><th>Request</th><th>{t('common.chain')}</th><th>{t('common.status')}</th><th>{t('dashboard.payouts.txhash')}</th></tr>")
        c.execute(
            "SELECT id, request_id, chain, status, tx_hash FROM payouts ORDER BY created_at DESC LIMIT 50"
        )
        for row in c.fetchall():
            f.write(
                f"<tr><td>{row['id']}</td><td>{row['request_id']}</td><td>{row['chain']}</td><td>{row['status']}</td><td>{row['tx_hash'] or ''}</td></tr>"
            )
        f.write("</table>")

        # Alerts
        f.write(f"<h2>{t('dashboard.alerts.title')}</h2><table border='1'><tr><th>{t('common.time')}</th><th>{t('common.severity')}</th><th>{t('common.kind')}</th><th>{t('common.message')}</th></tr>")
        c.execute("SELECT created_at, severity, kind, message FROM alerts ORDER BY created_at DESC LIMIT 50")
        for row in c.fetchall():
            f.write(
                f"<tr><td>{row['created_at']}</td><td>{row['severity']}</td><td>{row['kind']}</td><td>{row['message']}</td></tr>"
            )
        f.write("</table>")

        f.write("</body></html>")
    return path


def main():
    out = build_dashboard()
    print(out)


if __name__ == "__main__":
    main()
