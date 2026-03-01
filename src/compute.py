import pandas as pd
import pandas_ta as ta

from datetime import datetime


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """calculates all indicators for all dates"""

    compute_df = df.copy()

    compute_df = compute_sma(compute_df)

    return compute_df

def compute(df: pd.DataFrame, ticker: str, target_date: datetime) -> pd.DataFrame:
    """returns calculated indicators for target_date"""

    # compute all indicators
    df = compute_all(df)

    # get results for target_date only
    df = df.loc[[str(target_date)]]

    # add a "bo_name" column as identifier for Breakouts (eg. "AAPL_2001_Jan")
    year = target_date.year
    month = target_date.strftime("%b")
    # insert as first column
    df.insert(0, "bo_name", f"{ticker.upper()}_{year}_{month}")

    return df

def compute_sma(df: pd.DataFrame) -> pd.DataFrame:
    """computes 10 20 50 SMA and returns new df"""

    df.ta.sma(length=10, append=True)
    df.ta.sma(length=20, append=True)
    df.ta.sma(length=50, append=True)

    return df
