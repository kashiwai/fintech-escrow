import argparse
import os
import sys
import uuid

from . import rapyd_simulator
from .approvals import approve_release, create_release_request
from .db import db, init_db, now_iso
from .ledger import record_deposit
from .orchestrator import attach_quote, execute_payout, quote_jpy_to_usdt
from .alerts import high_amount_check_jpy
from .i18n import t


def _ensure_clients():
    with db() as conn:
        c = conn.cursor()
        for cid, name in [("A", "Client A"), ("B", "Client B")]:
            c.execute("SELECT id FROM clients WHERE id=?", (cid,))
            if c.fetchone() is None:
                c.execute(
                    "INSERT INTO clients(id, name, wallet_id, va_number, created_at) VALUES(?,?,?,?,?)",
                    (cid, name, f"wal_{uuid.uuid4()}", f"VA{uuid.uuid4().hex[:10]}", now_iso()),
                )


def cmd_init():
    init_db()
    _ensure_clients()
    print(t("cli.init.done"))


def cmd_deposit(client: str, amount: int):
    if amount <= 0:
        raise SystemExit("amount must be positive (JPY)")
    high_amount_check_jpy(amount)
    evt = rapyd_simulator.deposit_jpy(client, amount)
    # In a real deployment, the webhook receiver would verify signature; here we trust simulator
    record_deposit(evt["json"])  # process event
    print(t("cli.deposit.ok", client=client, amount=amount))


def cmd_release(client: str, amount_usdt: float, chain: str, address: str, max_slippage_bps: int):
    req_id = create_release_request(client, amount_usdt, chain, address, max_slippage_bps)
    rate, exp = quote_jpy_to_usdt(amount_usdt, max_slippage_bps)
    attach_quote(req_id, rate, exp)
    print(t("cli.release.created", req_id=req_id, rate=rate, exp=exp))


def cmd_approve(request_id: str, approver: str):
    cnt = approve_release(request_id, approver)
    print(t("cli.approve.count", count=cnt))


def cmd_payout(request_id: str):
    payout_id = execute_payout(request_id)
    # simulate a payout.sent webhook
    from .config import SIM_NETWORK_FEE_USDT
    with db() as conn:
        c = conn.cursor()
        c.execute("UPDATE payouts SET tx_hash=?, network_fee_usdt=? WHERE id=?", (uuid.uuid4().hex[:32], SIM_NETWORK_FEE_USDT, payout_id))
    print(t("cli.payout.sent", payout_id=payout_id))


def cmd_status():
    with db() as conn:
        c = conn.cursor()
        print(t("cli.status.balances"))
        for row in c.execute("SELECT client_id, currency, available FROM balances ORDER BY client_id, currency"):
            print(dict(row))
        print("\n" + t("cli.status.release_requests"))
        for row in c.execute("SELECT id, client_id, amount_usdt, chain, address, status, approvals_count, required_approvals FROM release_requests ORDER BY created_at DESC"):
            print(dict(row))
        print("\n" + t("cli.status.payouts"))
        for row in c.execute("SELECT * FROM payouts ORDER BY created_at DESC"):
            print(dict(row))


def main():
    parser = argparse.ArgumentParser(description="Escrow sandbox simulator")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("init")

    p_dep = sub.add_parser("deposit")
    p_dep.add_argument("--client", required=True)
    p_dep.add_argument("--amount", type=int, required=True)

    p_rel = sub.add_parser("release")
    p_rel.add_argument("--client", required=True)
    p_rel.add_argument("--amount_usdt", type=float, required=True)
    p_rel.add_argument("--chain", default="TRC20")
    p_rel.add_argument("--address", required=True)
    p_rel.add_argument("--max_slippage_bps", type=int, default=50)

    p_apr = sub.add_parser("approve")
    p_apr.add_argument("--request_id", required=True)
    p_apr.add_argument("--approver", required=True)

    p_po = sub.add_parser("payout")
    p_po.add_argument("--request_id", required=True)

    sub.add_parser("status")

    args = parser.parse_args()
    if args.cmd == "init":
        cmd_init()
    elif args.cmd == "deposit":
        cmd_deposit(args.client, args.amount)
    elif args.cmd == "release":
        cmd_release(args.client, args.amount_usdt, args.chain, args.address, args.max_slippage_bps)
    elif args.cmd == "approve":
        cmd_approve(args.request_id, args.approver)
    elif args.cmd == "payout":
        cmd_payout(args.request_id)
    elif args.cmd == "status":
        cmd_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
