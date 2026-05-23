from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
SAMPLE_DATA_DIR = DATA_DIR / "sample"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
REPORTS_DIR = OUTPUTS_DIR / "reports"
PLOTS_DIR = OUTPUTS_DIR / "plots"
MODELS_DIR = OUTPUTS_DIR / "models"

RANDOM_STATE = 42

MONEY_TOLERANCE = 0.01

POSTED_STATUS = "posted"

SAMPLE_SIZE_CONFIG = {
    "tiny": {
        "customers": 1_000,
        "operations": 10_000,
    },
    "small": {
        "customers": 5_000,
        "operations": 50_000,
    },
    "medium": {
        "customers": 20_000,
        "operations": 250_000,
    },
}

PRODUCT_TYPES = [
    "card_payments",
    "domestic_transfers",
    "cash_withdrawals",
    "account_service",
    "merchant_acquiring",
]

CHANNELS = [
    "mobile",
    "web",
    "branch",
    "atm",
    "pos",
]

CLIENT_SEGMENTS = [
    "mass",
    "affluent",
    "sme",
    "corporate",
]

OPERATION_STATUSES = [
    "posted",
    "reversed",
    "pending",
    "failed",
]
