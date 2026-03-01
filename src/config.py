from pathlib import Path

PROJECT_ROOT =  Path(__file__).resolve().parent.parent
DATA_DIR =      PROJECT_ROOT / "data"
STOOQ_DIR =     DATA_DIR / "stooq" # contains stooq stocks data
WAREHOUSE_DIR = DATA_DIR / "warehouse"
CLEAN_DIR =     WAREHOUSE_DIR / "clean" # contains cleaned parquet files that have been converted from .txt stooq files
PROCESSED_DIR = WAREHOUSE_DIR / "processed"

# ensures directory exists
CLEAN_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# PANDAS DISPLAY CONFIG
import pandas as pd
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
