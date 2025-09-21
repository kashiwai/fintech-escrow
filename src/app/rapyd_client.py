import base64
import hashlib
import hmac
import json
import time
import uuid
import urllib.request
import urllib.error
import urllib.parse
import os
from typing import Any, Dict, Optional, Tuple


RAPYD_BASE_URL = os.getenv("RAPYD_BASE_URL", "https://sandboxapi.rapyd.net")
RAPYD_ACCESS_KEY = os.getenv("RAPYD_ACCESS_KEY", "")
RAPYD_SECRET_KEY = os.getenv("RAPYD_SECRET_KEY", "")


def _canonical_body(body: Optional[Dict[str, Any]]) -> str:
    if not body:
        return ""
    return json.dumps(body, separators=(",", ":"), ensure_ascii=False)


def _signature(method: str, path: str, body: Optional[Dict[str, Any]], salt: str, timestamp: str) -> str:
    if not RAPYD_SECRET_KEY:
        raise RuntimeError("RAPYD_SECRET_KEY is not set")
    to_sign = method.lower() + path + salt + timestamp + RAPYD_ACCESS_KEY + RAPYD_SECRET_KEY + _canonical_body(body)
    h = hmac.new(RAPYD_SECRET_KEY.encode("utf-8"), to_sign.encode("utf-8"), hashlib.sha256)
    return base64.b64encode(h.digest()).decode("utf-8")


def rapyd_request(method: str, path: str, body: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Tuple[int, Dict[str, Any]]:
    if not RAPYD_ACCESS_KEY or not RAPYD_SECRET_KEY:
        raise RuntimeError("RAPYD_ACCESS_KEY / RAPYD_SECRET_KEY must be set in env")
    if not path.startswith("/"):
        raise ValueError("path must start with '/'")
    salt = uuid.uuid4().hex
    timestamp = str(int(time.time()))
    sig = _signature(method, path, body, salt, timestamp)

    url = RAPYD_BASE_URL.rstrip("/") + path
    data_bytes = _canonical_body(body).encode("utf-8") if body else None

    headers = {
        "Content-Type": "application/json",
        "access_key": RAPYD_ACCESS_KEY,
        "salt": salt,
        "timestamp": timestamp,
        "signature": sig,
    }
    req = urllib.request.Request(url=url, method=method.upper(), headers=headers, data=data_bytes)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.getcode()
            text = resp.read().decode("utf-8")
            try:
                return status, json.loads(text)
            except Exception:
                return status, {"raw": text}
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="ignore")
        try:
            return e.code, json.loads(text)
        except Exception:
            return e.code, {"error": text}


def verify_webhook(headers: Dict[str, str], body: bytes) -> bool:
    """Verify Rapyd webhook signature using env RAPYD_SECRET_KEY.
    Expected headers: signature, salt, timestamp, access_key.
    """
    try:
        signature = headers.get("signature") or headers.get("Signature")
        salt = headers.get("salt") or headers.get("Salt")
        timestamp = headers.get("timestamp") or headers.get("Timestamp")
        access_key = headers.get("access_key") or headers.get("Access-Key")
        if not (signature and salt and timestamp and access_key):
            return False
        if access_key != RAPYD_ACCESS_KEY:
            return False
        body_str = body.decode("utf-8") if body else ""
        to_sign = (
            (headers.get(":method") or "post").lower()
            + (headers.get(":path") or "")
            + salt
            + timestamp
            + RAPYD_ACCESS_KEY
            + RAPYD_SECRET_KEY
            + body_str
        )
        h = hmac.new(RAPYD_SECRET_KEY.encode("utf-8"), to_sign.encode("utf-8"), hashlib.sha256)
        calc = base64.b64encode(h.digest()).decode("utf-8")
        return hmac.compare_digest(calc, signature)
    except Exception:
        return False

