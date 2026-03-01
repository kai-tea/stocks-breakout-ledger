import pandas as pd
import pandas_ta as ta

from datetime import datetime

def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """calculates all indicators for all dates"""

    compute_df = df.copy()

    compute_df.ta.sma(length=10, append=True)
    compute_df.ta.sma(length=20, append=True)
    compute_df.ta.sma(length=50, append=True)

    return compute_df

def compute(df: pd.DataFrame, target_date: datetime) -> pd.DataFrame:
    """returns calculated indicators for target_date"""

    df = compute_all(df)

    return df.loc[str(target_date.date())]
