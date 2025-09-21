# Fintech Sandbox (Rapyd Escrow MVP)

This repository contains a self-contained Python sandbox to model an escrow flow using Rapyd-like events end-to-end, without external dependencies. It simulates JPY virtual account deposits, two-person approvals, FX quote to USDT, and USDT payouts with reconciliation, alerts, and a simple dashboard generator.

Scope (sandbox):
- Client onboarding: create client, assign virtual account (simulated)
- Inbound payment: simulate JPY deposit webhook, idempotent processing
- Escrow release: request release, two-person approval policy
- USDT payout: quote with max slippage, execute payout (simulated hash)
- Reconciliation: daily three-way (internal ledger vs simulated Rapyd balances)
- Audit: append-only hash-chain log
- Alerts: high-amount, failure streaks
- Dashboard: static HTML from DB metrics

Requirements:
- Python 3.10+
- No external packages; uses sqlite3 and stdlib only

Quick start:
0) One command full E2E (auto)
   `python -m src.app.run_all`

1) Initialize DB and seed two test clients
   `python -m src.app.simulate init`

2) Simulate an inbound JPY deposit for Client A
   `python -m src.app.simulate deposit --client A --amount 2500000`

3) Request escrow release to USDT (TRC20)
   `python -m src.app.simulate release --client A --amount_usdt 15000 --chain TRC20 --address TX_TEST_ADDR --max_slippage_bps 50`

4) Approve twice (two-person approval)
   `python -m src.app.simulate approve --request_id <ID> --approver user1`
   `python -m src.app.simulate approve --request_id <ID> --approver user2`

5) Execute payout (quote + send)
   `python -m src.app.simulate payout --request_id <ID>`

6) Run daily reconciliation and generate dashboard
   `python -m src.app.reconciliation run --date today`
   `python -m src.app.dashboard build`

Configuration (env):
- `DB_PATH` (default: `./fintech.db`)
- `WEBHOOK_SECRET` (HMAC for simulated webhook; default: `dev_secret`)
- `DEFAULT_CHAIN` (TRC20/ETH; default: TRC20)

Notes:
- All Rapyd integrations are simulated; you can later swap `rapyd_simulator.py` for a real API client and enable real webhooks.
- Audit log is stored at `./audit.log` with a hash chain; do not edit manually.

Directory:
- `src/app/*` modules (db, ledger, simulator, orchestrator, etc.)
- `sample_data/` example payloads

Safety:
- Two-person approval enforced for high-value releases (configurable).
- Idempotent processing for webhooks/payout events.

Limitations:
- No PDF; reports are CSV/HTML. Replace with your preferred generator later.

Using Rapyd API (real sandbox):
- Set environment variables (do NOT commit keys):
  - `export RAPYD_BASE_URL=https://sandboxapi.rapyd.net`
  - `export RAPYD_ACCESS_KEY=...`
  - `export RAPYD_SECRET_KEY=...`
- Optional for crypto payouts from your Rapyd eWallet:
  - `export RAPYD_EWALLET_ID=ewallet_xxx`
  - `export RAPYD_PAYOUT_METHOD_TYPE=usdt_tron` (confirm exact value with Rapyd; ERC20例: `usdt_erc20`)
  - `export RAPYD_BENEFICIARY_NAME=...`, `RAPYD_BENEFICIARY_COUNTRY=JP`
  - `export RAPYD_SENDER_NAME=...`, `RAPYD_SENDER_COUNTRY=SC`
- Verify credentials with a safe endpoint:
  - `python -m src.app.rapyd_cli verify`
- Generic signed request (example):
  - `python -m src.app.rapyd_cli request --method GET --path /v1/data/countries`
- Webhook receiver can validate Rapyd signatures (headers: `signature`, `salt`, `timestamp`, `access_key`). Point Rapyd Console webhooks to your endpoint and use this server.

Client provisioning (Rapyd eWallet + JPY virtual account):
- `python -m src.app.rapyd_ops provision-client --client A --name "Client A" --email client-a@example.com --country JP --currency JPY`
  - 保存先: `clients.wallet_id`, `clients.va_number`

Address whitelist (USDT出金に必須):
- 追加: `python -m src.app.rapyd_ops add-address --client A --chain TRC20 --address TX_xxx --label main`
- 承認: `python -m src.app.rapyd_ops approve-address --address_id addr_xxx --risk_score 5`
- 承認済みでないアドレスは解放リクエスト時に拒否されます。

Wiring the escrow flow to real Rapyd calls:
- Use `rapyd_client.rapyd_request` in place of the simulator for:
  - JPY deposits: create Virtual Accounts per client and process real webhooks in `webhook_receiver`.
  - USDT payouts: set the env above; `orchestrator.execute_payout` will attempt `POST /v1/payouts` with your parameters and log the response to audit.
- Because payout method schemas vary, confirm the exact `payout_method_type` and required `beneficiary/sender` fields with Rapyd; adjust `orchestrator.execute_payout` payload if needed.

Notes on integrating escrow with Rapyd:
- Create customer/wallet per client, issue JPY Virtual Account, receive payment webhooks, then trigger payout (USDT or fiat). This repo provides the ledger, approvals, reconciliation, and dashboard. Swap the simulator calls for real Rapyd endpoints using `rapyd_client.rapyd_request`.
- USDT payout requires a correct `payout_method_type` (varies by chain, e.g., TRON/ERC20). Confirm with Rapyd AM and call `/v1/payouts` with the appropriate beneficiary fields (address/chain) and sender details. Use the CLI to test the exact payloads.

Language settings:
- 既定は日本語（`APP_LANG=ja`）。英語にする場合は `export APP_LANG=en` を設定してください。
