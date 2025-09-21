import json
import uuid
from typing import Dict

from .audit import append as audit
from .db import db, now_iso


def _record_id(kind: str) -> str:
    return f"{kind}_{uuid.uuid4()}"


def record_deposit(event: Dict) -> str:
    # event: {id, type, created_at, data:{client_id, amount, currency}}
    evt_id = event["id"]
    with db() as conn:
        c = conn.cursor()
        # idempotency
        c.execute("SELECT event_id FROM idempotency WHERE event_id=?", (evt_id,))
        if c.fetchone():
            return evt_id
        client_id = event["data"]["client_id"]
        amount = int(event["data"]["amount"])
        currency = event["data"]["currency"]
        now = now_iso()
        tx_id = _record_id("tx")
        c.execute(
            "INSERT INTO transactions(id, client_id, type, status, amount, currency, created_at, updated_at, metadata)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (
                tx_id,
                client_id,
                "deposit",
                "completed",
                amount,
                currency,
                now,
                now,
                json.dumps({"evt": evt_id}),
            ),
        )
        le_id = _record_id("le")
        c.execute(
            "INSERT INTO ledger_entries(id, tx_id, client_id, direction, amount, currency, created_at)"
            " VALUES(?,?,?,?,?,?,?)",
            (le_id, tx_id, client_id, "credit", amount, currency, now),
        )
        # balance
        c.execute(
            "INSERT INTO balances(client_id, currency, available) VALUES(?,?,?)"
            " ON CONFLICT(client_id, currency) DO UPDATE SET available = available + excluded.available",
            (client_id, currency, amount),
        )
        c.execute(
            "INSERT INTO idempotency(event_id, kind, processed_at) VALUES(?,?,?)",
            (evt_id, event["type"], now),
        )
    audit("deposit", client_id, {"evt": evt_id, "amount": amount, "currency": currency})
    return tx_id

