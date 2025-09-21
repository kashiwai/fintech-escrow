import argparse
import json
import uuid

from .db import db, now_iso
from .rapyd_client import rapyd_request
from .i18n import t


def provision_client(client_id: str, name: str, email: str, country: str = "JP", currency: str = "JPY") -> None:
    # Create eWallet (simple payload; adjust fields per Rapyd account requirements)
    status_w, resp_w = rapyd_request("POST", "/v1/ewallets", {
        "name": name,
        "type": "company",
        "email": email,
    })
    if status_w >= 300:
        raise SystemExit(f"ewallet error: {status_w} {resp_w}")
    ewallet_id = resp_w.get("data", {}).get("id") or resp_w.get("id")
    if not ewallet_id:
        raise SystemExit("ewallet id not found in response")

    # Issue a virtual bank account (Virtual Account / Issuing), endpoint may vary by program
    body_va = {
        "ewallet": ewallet_id,
        "currency": currency,
        "country": country,
        "description": f"VA for {client_id}",
    }
    status_va, resp_va = rapyd_request("POST", "/v1/issuing/bankaccounts", body_va)
    if status_va >= 300:
        raise SystemExit(f"virtual account error: {status_va} {resp_va}")
    va_number = None
    data_va = resp_va.get("data") or {}
    # Common shapes: data.account_number or data.bank_account.account_number
    va_number = data_va.get("account_number") or (data_va.get("bank_account") or {}).get("account_number")
    if not va_number:
        # Fallback to token/id if number masked
        va_number = data_va.get("id") or data_va.get("token")

    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM clients WHERE id=?", (client_id,))
        if c.fetchone() is None:
            c.execute(
                "INSERT INTO clients(id, name, wallet_id, va_number, created_at) VALUES(?,?,?,?,?)",
                (client_id, name, ewallet_id, va_number, now_iso()),
            )
        else:
            c.execute(
                "UPDATE clients SET name=?, wallet_id=?, va_number=? WHERE id=?",
                (name, ewallet_id, va_number, client_id),
            )
    print(json.dumps({"client_id": client_id, "ewallet_id": ewallet_id, "va_number": va_number}, ensure_ascii=False))


def add_address_cli(client_id: str, chain: str, address: str, label: str | None):
    from .addresses import add_address
    addr_id = add_address(client_id, chain, address, label)
    print(json.dumps({"address_id": addr_id}, ensure_ascii=False))


def approve_address_cli(address_id: str, risk_score: int | None):
    from .addresses import set_address_status
    set_address_status(address_id, "approved", risk_score)
    print(t("cli.approve.count", count="approved"))


def main():
    p = argparse.ArgumentParser(description="Rapyd operations: provision clients, manage addresses")
    sub = p.add_subparsers(dest="cmd")

    pr = sub.add_parser("provision-client")
    pr.add_argument("--client", required=True)
    pr.add_argument("--name", required=True)
    pr.add_argument("--email", required=True)
    pr.add_argument("--country", default="JP")
    pr.add_argument("--currency", default="JPY")

    pa = sub.add_parser("add-address")
    pa.add_argument("--client", required=True)
    pa.add_argument("--chain", required=True)
    pa.add_argument("--address", required=True)
    pa.add_argument("--label")

    pv = sub.add_parser("approve-address")
    pv.add_argument("--address_id", required=True)
    pv.add_argument("--risk_score", type=int, default=None)

    args = p.parse_args()
    if args.cmd == "provision-client":
        provision_client(args.client, args.name, args.email, args.country, args.currency)
    elif args.cmd == "add-address":
        add_address_cli(args.client, args.chain, args.address, args.label)
    elif args.cmd == "approve-address":
        approve_address_cli(args.address_id, args.risk_score)
    else:
        p.print_help()


if __name__ == "__main__":
    main()

