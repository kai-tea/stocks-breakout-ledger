import pandas as pd
#from __future__ import annotations
from datetime import datetime, date
from ledger.config import *

def read_entries(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_parquet(path)
    else:
        return pd.DataFrame()

def add_entry(ticker: str, dt: date):
    df = read_entries(ENTRIES)

    target_date = pd.to_datetime(dt).date()

    if not df.empty:
        mask = (df["ticker"] == ticker) & (df["date"] == target_date)
        if not df[mask].empty:
            print(f"Duplicate: {ticker}, {target_date} already exists")
            return False

    new_row = pd.DataFrame([{
        "ticker": ticker,
        "date": pd.to_datetime(dt).date(),
        "created_ad": datetime.today().strftime('%Y-%m-%d')
    }])

    df = pd.concat([df, new_row])
    df.to_parquet(ENTRIES)

    return True