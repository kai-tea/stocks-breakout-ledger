from datetime import datetime
from pathlib import Path
import pandas as pd
import os

from fetch import fetch
from compute import compute

from config import PROCESSED_DIR


def add(ticker: str, target_date: datetime) -> None:
    # fetch raw data
    try:
        df = fetch(ticker)
    except FileNotFoundError as e:
        print(f"Error: {e}")

    # compute indicators
    df = compute(df, ticker, target_date)

    # save results to csv
    csv_file_name = "test.csv"
    csv_file_path = PROCESSED_DIR/csv_file_name
    append_result_to_csv(csv_file_path, df)

    print(f"saved to:\tprocessed/{csv_file_name}")

def append_result_to_csv(csv_file_path: Path, df: pd.DataFrame) -> None:
    """creates csv file if not present and appends df"""

    # creates header in csv if file does not exist yet
    # and appends df to csv
    csv_exists = os.path.isfile(csv_file_path)
    df.to_csv(csv_file_path, mode='a', header=not csv_exists, index=False)

