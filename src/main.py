from datetime import datetime
from pathlib import Path

from util import get_path_from_filename
from fetch import fetch
from compute import compute

from config import STOOQ_DIR


def add(ticker: str, target_date: datetime) -> None:
    try:
        df = fetch(ticker)
    except FileNotFoundError as e:
        print(f"Error: {e}")

    print(df.head(10))

    new = compute(df, target_date)

    print(new)

    return None

