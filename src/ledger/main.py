# src/main.py
from pathlib import Path
from typing import Annotated

from ledger.date_util import parse_date

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

def find_ticker_files(ticker: str, data_dir: Path) -> Path | None:
    """
    Searches for TXT files that match {ticker}.us.txt
    """
    t = ticker.strip().casefold()
    if not t:
        return None

    for path in data_dir.rglob("*.txt"):
        stem = path.stem.casefold()  # e.g., "aapl.us"
        if stem.startswith(t + "."):
            return path

    return None


def main() -> None:
    if not DATA_DIR.exists():
        print(f"data directory not found: {DATA_DIR}")
        return

    ticker = input("Enter ticker: ").strip()
    match = find_ticker_files(ticker, DATA_DIR)

    if match:
        print(f"Found {match}")
    else:
        print(f"No TXT file found for that ticker in /data.")
        # Optional: suggest close matches by filename stem
        stems = {p.stem for p in DATA_DIR.rglob('*.csv')}

    date = parse_date(input("Enter date: ").strip())
    print(date)

if __name__ == "__main__":
    print(PROJECT_ROOT)
    print(DATA_DIR)
    while True:
        main()