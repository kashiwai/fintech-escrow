import math
import uuid
from datetime import datetime, timedelta
from typing import Tuple

from .audit import append as audit
from .config import (
    SIM_FX_JPY_PER_USDT,
    SIM_NETWORK_FEE_USDT,
    RAPYD_EWALLET_ID,
    RAPYD_PAYOUT_METHOD_TYPE,
    RAPYD_BENEFICIARY_NAME,
    RAPYD_BENEFICIARY_COUNTRY,
    RAPYD_SENDER_NAME,
    RAPYD_SENDER_COUNTRY,
)
from .rapyd_client import rapyd_request
from .db import db, now_iso
from .mcp_integration import integrate_with_escrow_flow


def quote_jpy_to_usdt(amount_usdt: float, max_slippage_bps: int) -> Tuple[float, str]:
    """Return (rate_jpy_per_usdt, expires_at_iso). Simulate small variability within slippage."""
    base = SIM_FX_JPY_PER_USDT
    # Simulate a small movement up to +/- 10 bps
    drift = (max_slippage_bps / 10000.0) * 0.2  # 20% of allowed slippage
    rate = base * (1.0 + drift)
    expires = (datetime.utcnow() + timedelta(minutes=2)).replace(microsecond=0).isoformat() + "Z"
    return (rate, expires)


def attach_quote(request_id: str, rate_jpy_per_usdt: float, expires_at: str) -> None:
    with db() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE release_requests SET quote_rate=?, quote_expires_at=?, updated_at=? WHERE id=?",
            (rate_jpy_per_usdt, expires_at, now_iso(), request_id),
        )
    audit("quote_attached", request_id, {"rate_jpy_per_usdt": rate_jpy_per_usdt, "expires": expires_at})


def execute_payout(request_id: str) -> str:
    now = now_iso()
    with db() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT client_id, amount_usdt, chain, status, quote_rate, max_slippage_bps FROM release_requests WHERE id=?",
            (request_id,),
        )
        req = c.fetchone()
        if not req:
            raise ValueError("release request not found")
        if req["status"] != "approved":
            raise ValueError("release request not approved")
        if req["quote_rate"] is None:
            raise ValueError("no quote attached")
        client_id = req["client_id"]
        amount_usdt = float(req["amount_usdt"])
        rate = float(req["quote_rate"])
        jpy_required = math.ceil(amount_usdt * rate)
        # Check balance
        c.execute(
            "SELECT available FROM balances WHERE client_id=? AND currency='JPY'",
            (client_id,),
        )
        row = c.fetchone()
        available = int(row["available"]) if row else 0
        if available < jpy_required:
            raise ValueError("insufficient JPY balance for payout")
        # Deduct internal balance (escrow release)
        tx_id = f"tx_{uuid.uuid4()}"
        c.execute(
            "INSERT INTO transactions(id, client_id, type, status, amount, currency, created_at, updated_at, metadata)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (
                tx_id,
                client_id,
                "payout",
                "processing",
                jpy_required,
                "JPY",
                now,
                now,
                None,
            ),
        )
        le_id = f"le_{uuid.uuid4()}"
        c.execute(
            "INSERT INTO ledger_entries(id, tx_id, client_id, direction, amount, currency, created_at) VALUES(?,?,?,?,?,?,?)",
            (le_id, tx_id, client_id, "debit", jpy_required, "JPY", now),
        )
        c.execute(
            "UPDATE balances SET available = available - ? WHERE client_id=? AND currency='JPY'",
            (jpy_required, client_id),
        )
        # Update simulated Rapyd custodial balance: reduce JPY
        c.execute(
            "UPDATE rapyd_balances SET available = available - ? WHERE currency='JPY'",
            (jpy_required,),
        )
        # Create payout record (USDT network fee applied later in event)
        payout_id = f"po_{uuid.uuid4()}"
        c.execute(
            "INSERT INTO payouts(id, request_id, status, chain, created_at, updated_at) VALUES(?,?,?,?,?,?)",
            (payout_id, request_id, "sent", req["chain"], now, now),
        )
        # Mark request as completed
        c.execute(
            "UPDATE release_requests SET status='completed', updated_at=? WHERE id=?",
            (now, request_id),
        )
    # Optional: attempt real Rapyd payout if env is configured
    try:
        if RAPYD_EWALLET_ID and RAPYD_PAYOUT_METHOD_TYPE:
            # Mapping chain to blockchain tag used by Rapyd (confirm values with AM)
            blockchain = (req["chain"] or "").lower()
            body = {
                "ewallet": RAPYD_EWALLET_ID,
                "payout_method_type": RAPYD_PAYOUT_METHOD_TYPE,
                "amount": amount_usdt,
                "currency": "USDT",
                "description": f"Escrow release {request_id}",
                "beneficiary": {
                    "name": RAPYD_BENEFICIARY_NAME,
                    "country": RAPYD_BENEFICIARY_COUNTRY,
                    "crypto_address": "",  # set in caller if known
                    "blockchain": blockchain,
                },
                "sender": {
                    "name": RAPYD_SENDER_NAME,
                    "country": RAPYD_SENDER_COUNTRY,
                },
            }
            # Address must be pulled from release request
            with db() as conn:
                c = conn.cursor()
                c.execute("SELECT address FROM release_requests WHERE id=?", (request_id,))
                row = c.fetchone()
                if row:
                    body["beneficiary"]["crypto_address"] = row["address"]
            status, resp = rapyd_request("POST", "/v1/payouts", body)
            audit("rapyd_payout_api", request_id, {"status": status, "resp": resp})
    except Exception as e:
        audit("rapyd_payout_api_error", request_id, {"error": str(e)})

    # Integrate with MCP Serena
    integrate_with_escrow_flow(request_id, "payout_completed", {
        "payout_id": payout_id,
        "jpy": jpy_required,
        "usdt": amount_usdt,
        "rate": rate,
        "chain": req["chain"]
    })

    audit("payout_executed", request_id, {"payout_id": payout_id, "jpy": jpy_required, "usdt": amount_usdt, "rate": rate})
    return payout_id
