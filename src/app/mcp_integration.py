"""MCP Serena Integration Module for Bank Escrow Service"""

import json
import os
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from datetime import datetime
from .audit import append as log_event
from .db import db, now_iso

# Environment variables are loaded automatically via config module

class MCPSerenaClient:
    def __init__(self):
        self.host = os.getenv("MCP_SERENA_HOST", "localhost")
        self.port = os.getenv("MCP_SERENA_PORT", "3000")
        self.api_key = os.getenv("MCP_SERENA_API_KEY", "")
        self.base_url = f"http://{self.host}:{self.port}/api"

    def _make_request(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to MCP Serena"""
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }

        req_data = json.dumps(data).encode() if data else None
        request = urllib.request.Request(url, data=req_data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(request) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            log_event("mcp_serena_error", "system", {
                "endpoint": endpoint,
                "error": str(e),
                "timestamp": now_iso()
            })
            # Return mock response for sandbox mode
            return {"status": "sandbox_mode", "message": "MCP Serena not connected in sandbox mode"}

    def notify_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Notify Serena about new escrow transaction"""
        return self._make_request("escrow/transaction", "POST", transaction_data)

    def get_compliance_check(self, client_id: str, amount: float, currency: str) -> Dict[str, Any]:
        """Get compliance check from Serena"""
        data = {
            "client_id": client_id,
            "amount": amount,
            "currency": currency,
            "timestamp": now_iso()
        }
        return self._make_request("compliance/check", "POST", data)

    def sync_balance(self, wallet_id: str, balance: float, currency: str) -> Dict[str, Any]:
        """Sync balance information with Serena"""
        data = {
            "wallet_id": wallet_id,
            "balance": balance,
            "currency": currency,
            "timestamp": now_iso()
        }
        return self._make_request("wallet/balance", "POST", data)

    def register_webhook(self, event_type: str, callback_url: str) -> Dict[str, Any]:
        """Register webhook for Serena events"""
        data = {
            "event_type": event_type,
            "callback_url": callback_url,
            "active": True
        }
        return self._make_request("webhooks/register", "POST", data)

mcp_client = MCPSerenaClient()

def integrate_with_escrow_flow(request_id: str, action: str, metadata: Dict[str, Any]) -> bool:
    """Integrate MCP Serena with escrow flow"""
    with db() as conn:
        c = conn.cursor()

        # Get request details
        c.execute("""
            SELECT r.*, c.wallet_id, c.name as client_name
            FROM release_requests r
            JOIN clients c ON r.client_id = c.id
            WHERE r.id = ?
        """, (request_id,))
        request = c.fetchone()

        if not request:
            return False

        try:
            # Perform compliance check for large transactions
            if action == "release_request" and request["amount_usdt"] >= 10000:
                compliance = mcp_client.get_compliance_check(
                    request["client_id"],
                    request["amount_usdt"],
                    "USDT"
                )
                if not compliance.get("approved", False):
                    log_event("compliance_failed", {
                        "request_id": request_id,
                        "reason": compliance.get("reason", "Unknown")
                    })
                    return False

            # Notify about transaction
            transaction_data = {
                "request_id": request_id,
                "action": action,
                "client_id": request["client_id"],
                "client_name": request["client_name"],
                "wallet_id": request["wallet_id"],
                "amount": request["amount_usdt"],
                "currency": "USDT",
                "chain": request["chain"],
                "address": request["address"],
                "status": request["status"],
                "metadata": metadata,
                "timestamp": now_iso()
            }

            result = mcp_client.notify_transaction(transaction_data)

            # Log integration event
            log_event("mcp_integration", request_id, {
                "action": action,
                "result": result,
                "timestamp": now_iso()
            })

            # Store integration record
            c.execute("""
                INSERT INTO mcp_integrations (
                    request_id, action, response, created_at
                ) VALUES (?, ?, ?, ?)
            """, (request_id, action, json.dumps(result), now_iso()))

            return True

        except Exception as e:
            log_event("mcp_integration_error", request_id, {
                "action": action,
                "error": str(e),
                "timestamp": now_iso()
            })
            return False

def setup_mcp_webhooks():
    """Setup MCP Serena webhooks for escrow events"""
    webhook_base = f"http://{os.getenv('WEBHOOK_HOST', 'localhost')}:{os.getenv('WEBHOOK_PORT', '8000')}"

    webhooks = [
        ("deposit_received", f"{webhook_base}/mcp/deposit"),
        ("approval_required", f"{webhook_base}/mcp/approval"),
        ("payout_completed", f"{webhook_base}/mcp/payout"),
        ("compliance_alert", f"{webhook_base}/mcp/compliance")
    ]

    for event_type, callback_url in webhooks:
        try:
            result = mcp_client.register_webhook(event_type, callback_url)
            print(f"Registered webhook for {event_type}: {result}")
        except Exception as e:
            print(f"Failed to register webhook for {event_type}: {e}")

def sync_all_balances():
    """Sync all client balances with MCP Serena"""
    with db() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT c.id, c.wallet_id,
                   COALESCE(SUM(l.amount), 0) as balance
            FROM clients c
            LEFT JOIN ledger_entries l ON c.id = l.client_id
            WHERE l.currency = 'JPY'
            GROUP BY c.id, c.wallet_id
        """)

        for row in c.fetchall():
            try:
                mcp_client.sync_balance(
                    row["wallet_id"],
                    row["balance"],
                    "JPY"
                )
            except Exception as e:
                print(f"Failed to sync balance for {row['id']}: {e}")