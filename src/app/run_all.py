import uuid
from datetime import date

from .db import db, init_db, now_iso
from .rapyd_simulator import deposit_jpy
from .ledger import record_deposit
from .approvals import create_release_request, approve_release
from .orchestrator import quote_jpy_to_usdt, attach_quote, execute_payout
from .reconciliation import run_for_date
from .dashboard import build_dashboard
from .i18n import t


def ensure_clients():
    with db() as conn:
        c = conn.cursor()
        for cid, name in [("A", "Client A"), ("B", "Client B")]:
            c.execute("SELECT id FROM clients WHERE id=?", (cid,))
            if c.fetchone() is None:
                c.execute(
                    "INSERT INTO clients(id, name, wallet_id, va_number, created_at) VALUES(?,?,?,?,?)",
                    (cid, name, f"wal_{uuid.uuid4()}", f"VA{uuid.uuid4().hex[:10]}", now_iso()),
                )


def main():
    print(t("run.step1"))
    init_db()
    ensure_clients()

    print(t("run.step2"))
    evt = deposit_jpy("A", 2_500_000)
    record_deposit(evt["json"])  # webhook path is simulated inline

    print(t("run.step3"))
    req_id = create_release_request(
        client_id="A",
        amount_usdt=15_000,
        chain="TRC20",
        address="TX_SANDBOX_TEST_001",
        max_slippage_bps=50,
    )
    rate, exp = quote_jpy_to_usdt(15_000, 50)
    attach_quote(req_id, rate, exp)

    print(t("run.step4"))
    approve_release(req_id, "approver_user1")
    approve_release(req_id, "approver_user2")

    print(t("run.step5"))
    payout_id = execute_payout(req_id)

    print(t("run.step6"))
    recon_path = run_for_date(date.today())

    print(t("run.step7"))
    dash_path = build_dashboard()

    print("\n" + t("run.summary"))
    print(f"{t('run.summary.req')}: {req_id}")
    print(f"{t('run.summary.payout')}: {payout_id}")
    print(f"{t('run.summary.recon')}: {recon_path}")
    print(f"{t('run.summary.dashboard')}: {dash_path}")


if __name__ == "__main__":
    main()
