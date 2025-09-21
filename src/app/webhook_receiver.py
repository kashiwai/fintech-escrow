import hashlib
import hmac
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from .config import WEBHOOK_SECRET
from .ledger import record_deposit
from .db import db
from .rapyd_client import verify_webhook as rapyd_verify


def verify_signature(body: bytes, signature: str) -> bool:
    calc = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(calc, signature)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        signature = self.headers.get("X-Signature", "")
        # Prefer Rapyd webhook verification when Rapyd headers exist; fallback to dev signature
        if self.headers.get("signature") and self.headers.get("salt") and self.headers.get("timestamp"):
            ok = rapyd_verify({k: self.headers.get(k) for k in ["signature", "salt", "timestamp", "access_key"]}, body)
        else:
            ok = verify_signature(body, signature)
        if not ok:
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"invalid signature")
            return
        try:
            evt = json.loads(body.decode("utf-8"))
        except Exception:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"invalid json")
            return
        etype = evt.get("type")
        if etype == "payment.completed":
            record_deposit(evt)
        elif etype == "payout.sent":
            data = evt.get("data", {})
            with db() as conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE payouts SET tx_hash=?, updated_at=datetime('now') WHERE request_id=?",
                    (data.get("tx_hash"), data.get("request_id")),
                )
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")


def run(host: str = "127.0.0.1", port: int = 8080):
    httpd = HTTPServer((host, port), Handler)
    print(f"listening on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
