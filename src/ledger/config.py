from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2] # bo_fetch/
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"
STOOQ_DIR = PROJECT_ROOT / "stooq"
RAW_DIR = PROJECT_ROOT / "stooq/raw"
WAREHOUSE_DIR = PROJECT_ROOT / "warehouse"

# ensure directory exists
WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
