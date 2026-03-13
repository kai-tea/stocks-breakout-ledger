import pandas as pd
import pandas_ta as ta
from datetime import datetime

from compute_util import check_required_cols, get_qqq, get_slope, QQQ

CLOSE_COL = "close"
QQQ_RS_LINE_COL = "qqq_rs_line"
QQQ_RS_SLOPE = "qqq_rs_slope"


def compute(df: pd.DataFrame, ticker: str, target_date: datetime) -> pd.DataFrame:
    """returns calculated indicators for target_date"""

    # compute all indicators
    target_ts = pd.Timestamp(target_date)
    result = compute_all(df, target_ts)

    if target_ts not in result.index:
        raise KeyError(target_ts)

    result = result.loc[[target_ts]].copy()

    # add a "bo_name" column as identifier for Breakouts (eg. "AAPL_2001_Jan") and insert as first col
    year = target_date.year
    month = target_date.strftime("%b")
    result.insert(0, "bo_name", f"{ticker.upper()}_{year}_{month}")

    return result

def compute_all(df: pd.DataFrame, target_date: datetime) -> pd.DataFrame:
    """Calculates all indicators for all dates"""

    df = df.copy()

    add_sma(df, 10)
    add_sma(df, 20)
    add_sma(df, 50)

    add_qqq_rs_line(df, QQQ)
    add_qqq_rs_slope(df, 10)
    add_qqq_rs_slope(df, 20)
    add_qqq_rs_slope(df, 30)

    add_sma_profit(df, target_date, 10)
    add_sma_profit(df, target_date, 20)

    return df


def add_sma(df: pd.DataFrame, window=20, decimals=4):
    """Adds Simple Moving Average for given window"""
    sma_col = f"SMA_{window}"
    df[sma_col] = ta.sma(df[CLOSE_COL], length=window).round(decimals);


def add_qqq_rs_line(df: pd.DataFrame, target_date: datetime) -> None:
    """Adds Relative Strength to df compared to df_cmp"""
    qqq_df = QQQ.copy()

    check_required_cols(df, [CLOSE_COL])
    check_required_cols(qqq_df, [CLOSE_COL])

    aligned_cmp = qqq_df[CLOSE_COL].reindex(df.index)

    if aligned_cmp.isna().any():
        return
        # raise ValueError(f"QQQ close is missing for one or more dates.")

    df[QQQ_RS_LINE_COL] = (df[CLOSE_COL] / aligned_cmp)


def add_qqq_rs_slope(df: pd.DataFrame, window=20):
    """Adds qqq rs trend line"""
    check_required_cols(df, [QQQ_RS_LINE_COL])

    df[f"{QQQ_RS_SLOPE}_{window}"] = ta.linreg(
        df[QQQ_RS_LINE_COL],
        length=window,
        slope=True
    )


def add_sma_profit(df: pd.DataFrame, target_date: datetime, window: int) -> pd.DataFrame:
    """
    For the given target_date, calculates:
    - bars held until the first future close below SMA_{window}
    - profit % from buying at the target-date close and selling at that exit close

    Results are written into the target_date row in:
    - sma{window}_profit_days
    - sma{window}_profit_pct
    """
    target_ts = pd.Timestamp(target_date)
    sma_col = f"SMA_{window}"
    profit_bars_col = f"sma{window}_profit_bars"
    profit_pct_col = f"sma{window}_profit_pct"

    check_required_cols(df, [CLOSE_COL, sma_col])

    if target_ts not in df.index:
        return

    # initialize output columns only once
    if profit_bars_col not in df.columns:
        df[profit_bars_col] = pd.NA
    if profit_pct_col not in df.columns:
        df[profit_pct_col] = pd.NA

    buy_price = df.at[target_ts, CLOSE_COL]

    # filter closes that are under the sma
    future_df = df.loc[df.index > target_ts]
    exit_mask = future_df[CLOSE_COL] < future_df[sma_col]

    if not exit_mask.any():
        return

    # first viable sell date
    sell_date = future_df.index[exit_mask][0]
    sell_price = future_df.at[sell_date, CLOSE_COL]

    # calculate bars held and profit
    # days_held = (sell_date - target_ts).days
    bars_held = future_df.index.get_loc(sell_date) + 1
    profit_pct = ((sell_price / buy_price) - 1) * 100

    # writes days held and profit back into result
    df.at[target_ts, profit_bars_col] = int(bars_held)
    df.at[target_ts, profit_pct_col] = round(profit_pct, 4)