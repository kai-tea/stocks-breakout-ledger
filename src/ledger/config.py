from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR =           PROJECT_ROOT / "src"
DATA_DIR =          PROJECT_ROOT / "data"
STOOQ_DIR =         DATA_DIR / "stooq"
DAILY_DIR =         STOOQ_DIR / "daily"
NASDAQ_STOCKS_DIR = DAILY_DIR / "us/nasdaq stocks"
WAREHOUSE_DIR =     DATA_DIR / "warehouse"
ENTRIES =           WAREHOUSE_DIR / "entries.parquet"

# ensure directory exists
WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
