import pandas as pd
import pandas_ta as ta
from datetime import datetime

from src.fetch import fetch

RS_LINE_QQQ_COL = "rs_line_qqq"
CLOSE_COL = "close"


def get_qqq() -> pd.DataFrame:
    return fetch("qqq")


def get_spy() -> pd.DataFrame:
    return fetch("spy")


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


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """calculates all indicators for all dates"""

    df = df.copy()

    df = (df
        .pipe(add_sma, window=10)
        .pipe(add_sma, window=20)
        .pipe(add_sma, window=50)
        .pipe(add_rs_line, get_qqq()) # RS compared to QQQ
    )

    return df


def check_required_cols(df: pd.DataFrame, required_cols: list):
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Pipeline error: Missing {col}.")


def add_rs_line(df: pd.DataFrame, df_cmp: pd.DataFrame) -> pd.DataFrame:
    """Adds Relative Strength to df compared to df_cmp"""
    check_required_cols(df, [CLOSE_COL])
    check_required_cols(df_cmp, [CLOSE_COL])

    df["qqq_close"] = df_cmp[CLOSE_COL]

    df[RS_LINE_QQQ_COL] = df[CLOSE_COL] / df["qqq_close"]

    return df


def add_sma(df: pd.DataFrame, window=20):
    """Adds Simple Moving Average for given window"""
    df.ta.sma(length=window, append=True)
    return df
