import pandas as pd
#from __future__ import annotations
from pathlib import Path
from datetime import datetime, date
import uuid

WAREHOUSE = Path("data/warehouse")
WAREHOUSE.mkdir(parents=True, exist_ok=True)
ENTRIES = WAREHOUSE / "entries.parquet"

def read_entries(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_parquet(path)
    else:
        return pd.DataFrame()

def add_entry(ticker: str, date: date):
    df = read_entries(ENTRIES)
    entry_id = str(uuid.uuid4())

    row = {
        "entry_id": entry_id,
        "ticker": ticker,
        "date": pd.to_datetime(date).date(),
        "created_ad": datetime.today().strftime('%Y-%m-%d')
    }

    df = pd.concat([df, pd.DataFrame([row])])
    df.to_parquet(ENTRIES)
    return entry_id
