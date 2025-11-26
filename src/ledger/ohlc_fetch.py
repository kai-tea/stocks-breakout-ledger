import ledger.config
import pandas as pd
from pathlib import Path

from ledger.config import NASDAQ_STOCKS_DIR

def find(name, path):
    return list(Path(path).rglob(name, case_sensitive=False))

def get_stooq_us_ohlc(ticker: str) -> pd.DataFrame:
    file_name = ticker.lower() + ".us.txt"

    files = find(file_name, NASDAQ_STOCKS_DIR)

    if len(files) == 0:
        print(f"{file_name} not found")
        return pd.DataFrame()

    file = files[0]
    print(f"fetching data from {file}")
    return stooq_txt_to_pd(file)

def stooq_txt_to_pd(file: Path) -> pd.DataFrame:
    df = pd.read_csv(file)
    return df