import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from .config import DB_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with db() as conn:
        c = conn.cursor()
        # Clients and balances
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                wallet_id TEXT,
                va_number TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS balances (
                client_id TEXT NOT NULL,
                currency TEXT NOT NULL,
                available INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (client_id, currency),
                FOREIGN KEY (client_id) REFERENCES clients(id)
            );
            """
        )
        # Transactions and ledger
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                type TEXT NOT NULL, -- deposit|release|payout
                status TEXT NOT NULL,
                amount INTEGER NOT NULL,
                currency TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (client_id) REFERENCES clients(id)
            );
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS ledger_entries (
                id TEXT PRIMARY KEY,
                tx_id TEXT NOT NULL,
                client_id TEXT NOT NULL,
                direction TEXT NOT NULL, -- credit|debit
                amount INTEGER NOT NULL,
                currency TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (tx_id) REFERENCES transactions(id),
                FOREIGN KEY (client_id) REFERENCES clients(id)
            );
            """
        )
        # Approvals and payouts
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS release_requests (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                amount_usdt REAL NOT NULL,
                chain TEXT NOT NULL,
                address TEXT NOT NULL,
                status TEXT NOT NULL,
                required_approvals INTEGER NOT NULL,
                approvals_count INTEGER NOT NULL DEFAULT 0,
                max_slippage_bps INTEGER NOT NULL,
                quote_rate REAL,
                quote_expires_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (client_id) REFERENCES clients(id)
            );
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS release_approvals (
                request_id TEXT NOT NULL,
                approver_id TEXT NOT NULL,
                approved_at TEXT NOT NULL,
                PRIMARY KEY (request_id, approver_id),
                FOREIGN KEY (request_id) REFERENCES release_requests(id)
            );
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS payouts (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                status TEXT NOT NULL,
                chain TEXT NOT NULL,
                tx_hash TEXT,
                network_fee_usdt REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (request_id) REFERENCES release_requests(id)
            );
            """
        )
        # Idempotency and incoming events
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS idempotency (
                event_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                processed_at TEXT NOT NULL
            );
            """
        )
        # Simulated Rapyd balances (custodial)
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS rapyd_balances (
                currency TEXT PRIMARY KEY,
                available INTEGER NOT NULL
            );
            """
        )
        # Alerts
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                severity TEXT NOT NULL,
                kind TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                metadata TEXT
            );
            """
        )

        # Address whitelist for crypto payouts
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS addresses (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                chain TEXT NOT NULL,
                address TEXT NOT NULL,
                label TEXT,
                risk_score INTEGER,
                status TEXT NOT NULL, -- pending|approved|rejected
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE (client_id, chain, address),
                FOREIGN KEY (client_id) REFERENCES clients(id)
            );
            """
        )

        # MCP Serena integration table
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS mcp_integrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL,
                action TEXT NOT NULL,
                response TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (request_id) REFERENCES release_requests(id)
            );
            """
        )

        # Bank deposits from external sources
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS bank_deposits (
                id TEXT PRIMARY KEY,
                sender_name TEXT NOT NULL,
                sender_bank TEXT,
                amount INTEGER NOT NULL,
                purpose TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                tron_address TEXT,
                processed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
