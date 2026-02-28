from datetime import datetime
from pathlib import Path

from config import STOOQ_DIR
from util import get_path_from_filename
from fetch import fetch

def add(ticker: str, date: datetime) -> None:

    try:
        df = fetch(ticker)
    except FileNotFoundError as e:
        print(f"Error: {e}")

    print(df.head)

    return None

