import pandas as pd
import pandas_ta as ta
from datetime import datetime

from compute_util import check_required_cols, get_qqq, get_slope

CLOSE_COL = "close"
QQQ_RS_LINE_COL = "qqq_rs_line"
QQQ_RS_SLOPE = "qqq_rs_slope"


def compute(df: pd.DataFrame, ticker: str, target_date: datetime) -> pd.DataFrame:
    """returns calculated indicators for target_date"""

    # compute all indicators
    df = compute_all(df, target_date)

    # get results for target_date only
    try:
        df = df.loc[[str(target_date)]]
    except KeyError as e:
        raise e

    # add a "bo_name" column as identifier for Breakouts (eg. "AAPL_2001_Jan")
    year = target_date.year
    month = target_date.strftime("%b")
    # insert as first column
    df.insert(0, "bo_name", f"{ticker.upper()}_{year}_{month}")

    return df


def compute_all(df: pd.DataFrame, target_date: datetime) -> pd.DataFrame:
    """calculates all indicators for all dates"""
    df = df.copy()

    df = (df
        .pipe(add_sma, window=10)
        .pipe(add_sma, window=20)
        .pipe(add_sma, window=50)
        .pipe(add_qqq_rs_line, get_qqq(), target_date)
        .pipe(add_qqq_rs_slope, 10)
        .pipe(add_qqq_rs_slope, 20)
        .pipe(add_qqq_rs_slope, 30)
        .pipe(add_sma_profit, target_date, 10)
    )

    return df


def add_sma(df: pd.DataFrame, window=20, decimals=4):
    """Adds Simple Moving Average for given window"""
    df.ta.sma(length=window, append=True)
    sma_col = f"SMA_{window}"
    df[sma_col] = df[sma_col].round(decimals);
    return df


def add_qqq_rs_line(df: pd.DataFrame, df_cmp: pd.DataFrame, target_date: datetime) -> pd.DataFrame:
    """Adds Relative Strength to df compared to df_cmp"""
    check_required_cols(df, [CLOSE_COL])
    check_required_cols(df_cmp, [CLOSE_COL])

    df["qqq_close"] = df_cmp[CLOSE_COL]

    df[QQQ_RS_LINE_COL] = df[CLOSE_COL] / df["qqq_close"]

    return df


def add_qqq_rs_slope(df: pd.DataFrame, window=20):
    """Adds qqq rs trend line"""
    check_required_cols(df, [QQQ_RS_LINE_COL])

    df[f"{QQQ_RS_SLOPE}_{window}"] = df[QQQ_RS_LINE_COL].rolling(window=window).apply(get_slope, raw=False)

    return df


def add_sma_profit(df: pd.DataFrame, target_date: datetime, window: int) -> pd.DataFrame:
    """
    For the given target_date, calculates:
    - hold days until the first future close below SMA_{window}
    - profit % from buying at the target-date close and selling at that exit close

    Results are written into the target_date row in:
    - sma{window}_profit_days
    - sma{window}_profit_pct
    """
    sma_col = f"SMA_{window}"
    profit_days_col = f"sma{window}_profit_days"
    profit_pct_col = f"sma{window}_profit_pct"

    check_required_cols(df, [CLOSE_COL, sma_col])

    result = df.copy()
    target_ts = pd.Timestamp(target_date)

    if target_ts not in result.index:
        return result

    # initialize output columns only once
    if profit_days_col not in result.columns:
        result[profit_days_col] = pd.NA
    if profit_pct_col not in result.columns:
        result[profit_pct_col] = pd.NA

    buy_price = result.at[target_ts, CLOSE_COL]

    # filter closes that are under the sma
    future_df = result.loc[result.index > target_ts]
    exit_mask = future_df[CLOSE_COL] < future_df[sma_col]

    if not exit_mask.any():
        return result

    # first viable sell date
    sell_date = future_df.index[exit_mask][0]
    sell_price = future_df.at[sell_date, CLOSE_COL]

    # calculate days held and profit
    days_held = (sell_date - target_ts).days
    profit_pct = ((sell_price / buy_price) - 1) * 100

    # writes days held and profit back into result
    result.at[target_ts, profit_days_col] = int(days_held)
    result.at[target_ts, profit_pct_col] = round(profit_pct, 4)

    print(result)

    return result