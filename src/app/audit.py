import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


AUDIT_PATH = os.path.abspath("./audit.log")


@dataclass
class AuditEvent:
    ts: str
    kind: str
    entity_id: str
    data: dict
    prev_hash: Optional[str]


def _line_hash(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def append(kind: str, entity_id: str, data: dict) -> str:
    os.makedirs(os.path.dirname(AUDIT_PATH) or ".", exist_ok=True)
    prev_hash = None
    if os.path.exists(AUDIT_PATH):
        with open(AUDIT_PATH, "rb") as f:
            try:
                f.seek(-4096, os.SEEK_END)
            except OSError:
                f.seek(0)
            tail = f.read().decode("utf-8", errors="ignore").splitlines()
            if tail:
                last = tail[-1]
                try:
                    prev_hash = json.loads(last)["hash"]
                except Exception:
                    prev_hash = None
    evt = AuditEvent(
        ts=datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        kind=kind,
        entity_id=entity_id,
        data=data,
        prev_hash=prev_hash,
    )
    payload = {
        "ts": evt.ts,
        "kind": evt.kind,
        "entity_id": evt.entity_id,
        "data": evt.data,
        "prev": evt.prev_hash,
    }
    line = json.dumps(payload, sort_keys=True)
    h = _line_hash(line)
    rec = json.dumps({"hash": h, **payload}, separators=(",", ":"))
    with open(AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write(rec + "\n")
    return h

