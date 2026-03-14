import pandas as pd
import pandas_ta as ta

from fetch import fetch

from scipy.stats import linregress
import numpy as np


def check_required_cols(df: pd.DataFrame, required_cols: list):
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Compute error: Missing {col}.")


def get_sma(df: pd.DataFrame, window=20, decimals=4):
    """Returns Simple Moving Average for given window"""
    return ta.sma(df["close"], length=window).round(decimals);


def get_qqq() -> pd.DataFrame:
    return fetch("qqq")


def get_spy() -> pd.DataFrame:
    return fetch("spy")


def get_slope(arr) -> float:
    y = np.array(arr)
    x = np.arange(len(y))
    slope, _, _, _, _ = linregress(x, y)
    return slope
