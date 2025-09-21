import hashlib
import hmac
import json
import os
import uuid
from typing import Dict

from .config import WEBHOOK_SECRET
from .db import db, now_iso


def _sign(body: str) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()


def ensure_balance_row(currency: str) -> None:
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT currency FROM rapyd_balances WHERE currency=?", (currency,))
        if c.fetchone() is None:
            c.execute(
                "INSERT INTO rapyd_balances(currency, available) VALUES(?, ?)",
                (currency, 0),
            )


def deposit_jpy(client_id: str, amount_jpy: int) -> Dict:
    """Simulate a JPY deposit to client's virtual account and emit a webhook payload."""
    ensure_balance_row("JPY")
    # Update simulated Rapyd balance (custodial)
    with db() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE rapyd_balances SET available = available + ? WHERE currency='JPY'",
            (amount_jpy,),
        )
    payload = {
        "id": str(uuid.uuid4()),
        "type": "payment.completed",
        "created_at": now_iso(),
        "data": {
            "client_id": client_id,
            "amount": amount_jpy,
            "currency": "JPY",
        },
    }
    body = json.dumps(payload, separators=(",", ":"))
    signature = _sign(body)
    return {"signature": signature, "body": body, "json": payload}


def payout_usdt_sent(request_id: str, chain: str, amount_usdt: float, network_fee_usdt: float) -> Dict:
    payload = {
        "id": str(uuid.uuid4()),
        "type": "payout.sent",
        "created_at": now_iso(),
        "data": {
            "request_id": request_id,
            "chain": chain,
            "amount_usdt": amount_usdt,
            "network_fee_usdt": network_fee_usdt,
            "tx_hash": str(uuid.uuid4()).replace("-", "")[:32],
        },
    }
    body = json.dumps(payload, separators=(",", ":"))
    signature = _sign(body)
    return {"signature": signature, "body": body, "json": payload}

