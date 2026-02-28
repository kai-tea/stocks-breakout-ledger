from pathlib import Path

PROJECT_ROOT =  Path(__file__).resolve().parent.parent
DATA_DIR =      PROJECT_ROOT / "data"
STOOQ_DIR =     DATA_DIR / "stooq" # contains stooq stocks data
WAREHOUSE_DIR = DATA_DIR / "warehouse" # contains parquet files that have been converted from .txt stooq files

# ensures warehouse directory exists
WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)