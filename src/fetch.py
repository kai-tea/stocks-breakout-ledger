import pandas as pd
from pathlib import Path

from config import WAREHOUSE_DIR, STOOQ_DIR
from util import get_path_from_filename


def fetch(ticker: str) -> pd.DataFrame:
    # create file_name and search parquet file in warehouse
    parquet_file_name = f"{ticker}.parquet"
    parquet_file_path = get_path_from_filename(parquet_file_name, search_path=WAREHOUSE_DIR)

    # if parquet file was found return df
    if parquet_file_path is not None:
        return pd.read_parquet(parquet_file_path)

    # parquet file not found
    # search stooq data for ticker
    stooq_file_name = f"{ticker}.us.txt"
    stooq_file_path = get_path_from_filename(stooq_file_name, search_path=STOOQ_DIR)

    # raise Error since stooq and parquet file were not found
    if stooq_file_path is None:
        raise FileNotFoundError(f"No data found for {ticker} in Warehouse or Stooq.")

    # convert stooq txt file -> df -> parquet
    df = pd.read_csv(stooq_file_path)

    new_parquet_file_path = WAREHOUSE_DIR / parquet_file_name
    df.to_parquet(new_parquet_file_path)

    return df