from datetime import datetime

import pandas as pd

from fetch import fetch

from scipy.stats import linregress
import numpy as np


def check_required_cols(df: pd.DataFrame, required_cols: list):
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Pipeline error: Missing {col}.")


def get_qqq() -> pd.DataFrame:
    return fetch("qqq")


def get_spy() -> pd.DataFrame:
    return fetch("spy")


def get_slope(arr) -> float:
    y = np.array(arr)
    x = np.arange(len(y))
    slope, _, _, _, _ = linregress(x, y)
    return slope
