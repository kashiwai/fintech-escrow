import uuid
from typing import Optional

from .db import db, now_iso


def add_address(client_id: str, chain: str, address: str, label: Optional[str] = None) -> str:
    addr_id = f"addr_{uuid.uuid4()}"
    with db() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO addresses(id, client_id, chain, address, label, risk_score, status, created_at, updated_at)"
            " VALUES(?,?,?,?,?,?,?, ?, ?)",
            (addr_id, client_id, chain, address, label, None, "pending", now_iso(), now_iso()),
        )
        # fetch id (unique constraint might have ignored insert)
        c.execute(
            "SELECT id FROM addresses WHERE client_id=? AND chain=? AND address=?",
            (client_id, chain, address),
        )
        row = c.fetchone()
        return row["id"]


def set_address_status(addr_id: str, status: str, risk_score: Optional[int] = None) -> None:
    assert status in ("pending", "approved", "rejected")
    with db() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE addresses SET status=?, risk_score=COALESCE(?, risk_score), updated_at=? WHERE id=?",
            (status, risk_score, now_iso(), addr_id),
        )


def get_approved_address(client_id: str, chain: str, address: str) -> Optional[str]:
    with db() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id FROM addresses WHERE client_id=? AND chain=? AND address=? AND status='approved'",
            (client_id, chain, address),
        )
        row = c.fetchone()
        return row["id"] if row else None

