# PANDAS DISPLAY CONFIG
import pandas as pd
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)

# default Paths
from pathlib import Path

PROJECT_ROOT =  Path(__file__).resolve().parent.parent
DATA_DIR =      PROJECT_ROOT / "data"
INPUT_DIR =     DATA_DIR / "input"
STOOQ_DIR =     DATA_DIR / "stooq" # contains raw stooq data
WAREHOUSE_DIR = DATA_DIR / "warehouse"
CLEAN_DIR =     WAREHOUSE_DIR / "clean" # contains cleaned parquet files of stocks
PROCESSED_DIR = WAREHOUSE_DIR / "processed"

# ensures directories exist
CLEAN_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
INPUT_DIR.mkdir(parents=True, exist_ok=True)

# Input/Output File
INPUT_FILE = INPUT_DIR / "input.csv"
OUTPUT_FILE = PROCESSED_DIR / "output.csv"
