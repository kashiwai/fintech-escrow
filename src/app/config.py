import os


# Render環境ではプロジェクトディレクトリ内にDBを配置
if os.environ.get('RENDER'):
    # Renderでは/opt/render/project/srcがワーキングディレクトリ
    DB_PATH = "/opt/render/project/src/fintech.db"
else:
    DB_PATH = os.getenv("DB_PATH", os.path.abspath("./fintech.db"))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "dev_secret")
DEFAULT_CHAIN = os.getenv("DEFAULT_CHAIN", "TRC20")

# Two-person approval threshold (USDT). <= threshold: single approval, > threshold: two approvals
SINGLE_APPROVAL_THRESHOLD_USDT = float(os.getenv("SINGLE_APPROVAL_THRESHOLD_USDT", "5000"))

# Simulated FX rate JPY per USDT (e.g., 150 JPY = 1 USDT)
SIM_FX_JPY_PER_USDT = float(os.getenv("SIM_FX_JPY_PER_USDT", "150.0"))

# Simulated network fee per payout (USDT)
SIM_NETWORK_FEE_USDT = float(os.getenv("SIM_NETWORK_FEE_USDT", "1.0"))

# Reports output dir
if os.environ.get('RENDER'):
    REPORTS_DIR = "/opt/render/project/src/reports"
else:
    REPORTS_DIR = os.getenv("REPORTS_DIR", os.path.abspath("./reports"))

# Optional Rapyd payout integration (real API)
RAPYD_EWALLET_ID = os.getenv("RAPYD_EWALLET_ID", "")
RAPYD_PAYOUT_METHOD_TYPE = os.getenv("RAPYD_PAYOUT_METHOD_TYPE", "")  # e.g., usdt_tron / usdt_erc20 (confirm with Rapyd)
RAPYD_BENEFICIARY_NAME = os.getenv("RAPYD_BENEFICIARY_NAME", "Beneficiary")
RAPYD_BENEFICIARY_COUNTRY = os.getenv("RAPYD_BENEFICIARY_COUNTRY", "JP")
RAPYD_SENDER_NAME = os.getenv("RAPYD_SENDER_NAME", "Operator")
RAPYD_SENDER_COUNTRY = os.getenv("RAPYD_SENDER_COUNTRY", "SC")
