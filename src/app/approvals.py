import uuid
from datetime import datetime, timedelta
from typing import Optional

from .audit import append as audit
from .config import (
    SIM_FX_JPY_PER_USDT,
    SINGLE_APPROVAL_THRESHOLD_USDT,
)
from .db import db, now_iso
from .addresses import get_approved_address


def create_release_request(
    client_id: str,
    amount_usdt: float,
    chain: str,
    address: str,
    max_slippage_bps: int = 50,
) -> str:
    # Enforce approved address exists
    if not get_approved_address(client_id, chain, address):
        raise ValueError("address not approved for this client/chain")
    req_id = f"req_{uuid.uuid4()}"
    required = 1 if amount_usdt <= SINGLE_APPROVAL_THRESHOLD_USDT else 2
    now = now_iso()
    with db() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO release_requests(id, client_id, amount_usdt, chain, address, status, required_approvals, "
            "approvals_count, max_slippage_bps, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                req_id,
                client_id,
                float(amount_usdt),
                chain,
                address,
                "pending",
                required,
                0,
                int(max_slippage_bps),
                now,
                now,
            ),
        )
    audit("release_request", req_id, {
        "client_id": client_id,
        "amount_usdt": amount_usdt,
        "chain": chain,
        "address": address,
        "required": required,
        "max_slippage_bps": max_slippage_bps,
    })
    return req_id


def approve_release(request_id: str, approver_id: str) -> int:
    now = now_iso()
    with db() as conn:
        c = conn.cursor()
        # upsert approval actor
        c.execute(
            "INSERT OR IGNORE INTO release_approvals(request_id, approver_id, approved_at) VALUES(?,?,?)",
            (request_id, approver_id, now),
        )
        # recalc approvals_count
        c.execute(
            "SELECT COUNT(*) as cnt FROM release_approvals WHERE request_id=?",
            (request_id,),
        )
        cnt = int(c.fetchone()["cnt"])
        c.execute(
            "UPDATE release_requests SET approvals_count=?, updated_at=? WHERE id=?",
            (cnt, now, request_id),
        )
        # if met required, move to approved
        c.execute(
            "SELECT required_approvals, status FROM release_requests WHERE id=?",
            (request_id,),
        )
        row = c.fetchone()
        if row and cnt >= int(row["required_approvals"]) and row["status"] == "pending":
            c.execute(
                "UPDATE release_requests SET status='approved', updated_at=? WHERE id=?",
                (now, request_id),
            )
    audit("release_approved", request_id, {"approver": approver_id, "count": cnt})
    return cnt
