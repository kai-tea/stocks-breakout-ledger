from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR =       PROJECT_ROOT / "src"
DATA_DIR =      PROJECT_ROOT / "data"
STOOQ_DIR =     PROJECT_ROOT / "data/stooq"
RAW_DIR =       PROJECT_ROOT / "data/stooq/raw"
WAREHOUSE_DIR = PROJECT_ROOT / "data/warehouse"
ENTRIES =       PROJECT_ROOT / "data/warehouse/entries.parquet"

# ensure directory exists
WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
