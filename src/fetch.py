import pandas as pd
from pathlib import Path

from config import PROCESSED_DIR, STOOQ_DIR
from util import get_path_from_filename

def fetch_and_clean_stooq(filepath: Path):
    """fetches stooq file, cleans up columns and reformats values and returns it"""

    df = pd.read_csv(filepath)

    # to lower case and strip '<', '>'
    df.columns = df.columns.str.lower()
    df.columns = df.columns.str.replace('<', '').str.replace('>', '')

    # drop useless columns for daily
    columns = ['per', 'time', 'openint']
    df = df.drop(columns=[c for c in columns])

    # reformat date
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')

    # set index without dropping column
    df = df.set_index("date", drop=False)

    return df

def fetch(ticker: str) -> pd.DataFrame:
    # create file_name and search parquet file in warehouse
    parquet_file_name = f"{ticker}.parquet"
    parquet_file_path = get_path_from_filename(parquet_file_name, search_path=PROCESSED_DIR)

    # if parquet file was found return df
    if parquet_file_path is not None:
        return pd.read_parquet(parquet_file_path)

    # search stooq data for ticker
    stooq_file_name = f"{ticker}.us.txt"
    stooq_file_path = get_path_from_filename(stooq_file_name, search_path=STOOQ_DIR)

    # raise Error since stooq and parquet file were not found
    if stooq_file_path is None:
        raise FileNotFoundError(f"No data found for {ticker} in Warehouse or Stooq.")


    # convert stooq .txt -> df -> parquet
    df = fetch_and_clean_stooq(stooq_file_path)

    new_parquet_file_path = PROCESSED_DIR / parquet_file_name
    df.to_parquet(new_parquet_file_path)

    return df