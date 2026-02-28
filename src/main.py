from datetime import datetime
from pathlib import Path

from config import STOOQ_DIR
from util import find_file
from fetch import fetch

def add(ticker: str, date: datetime) -> None:

    ticker_filename = ticker + ".us.txt"
    ticker_path = find_file(ticker_filename, start_path=STOOQ_DIR)

    if ticker_path is None:
        raise ValueError(f"No data found for {ticker} ({ticker_path}).")

    df = fetch(ticker_path)
    if df is None:
        raise ValueError(f"No data found for {ticker} ({ticker_path}).")

    return None

