import uuid

from .db import db, now_iso
from .i18n import t


def raise_alert(severity: str, kind: str, message: str, metadata: dict | None = None) -> str:
    alert_id = f"al_{uuid.uuid4()}"
    with db() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO alerts(id, severity, kind, message, created_at, metadata) VALUES(?,?,?,?,?,?)",
            (alert_id, severity, kind, message, now_iso(), None if metadata is None else str(metadata)),
        )
    return alert_id


def high_amount_check_jpy(amount_jpy: int, threshold_jpy: int = 10_000_000) -> None:
    if amount_jpy >= threshold_jpy:
        raise_alert("high", "high_amount", t("alert.high_amount", amount=amount_jpy))


def failure_streak(kind: str, count: int, threshold: int = 3) -> None:
    if count >= threshold:
        raise_alert("medium", "failure_streak", f"{kind} failed {count} times consecutively")
