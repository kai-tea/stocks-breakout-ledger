import pandas as pd

from fetch import fetch


def load_ohlcv(ticker: str) -> pd.DataFrame:
    """
    Loads OHLCV data for a ticker and ensures it is date-indexed and sorted.
    """
    df = fetch(ticker)
    if "volume" not in df.columns and "vol" in df.columns:
        df = df.rename(columns={"vol": "volume"})
    if not df.index.is_monotonic_increasing:
        df = df.sort_index()
    return df
