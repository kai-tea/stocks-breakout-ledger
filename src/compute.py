import pandas as pd
import pandas_ta as ta
from datetime import datetime

from numba.core.target_extension import target_registry

from compute_util import check_required_cols, get_qqq, get_slope, get_sma

CLOSE_COL = "close"
QQQ_RS_LINE_COL = "qqq_rs_line"
QQQ_RS_SLOPE = "qqq_rs_slope"


def compute(df: pd.DataFrame, ticker: str, date: datetime) -> pd.DataFrame:
    """returns calculated indicators for target_date"""

    # compute all indicators
    ts = pd.Timestamp(date)
    if ts not in df.index:
        raise KeyError(f"Target date {ts} not found in index")

    df_qqq = get_qqq()

    buy_price = df.at[ts, CLOSE_COL]

    result = {
        "bo_name": f"{ticker.upper()}_{ts.year}_{ts.strftime("%b")}",
        "date": date,
        "buy_price": buy_price,
        "adr_pct": calc_adr_pct(df, date, 20, 4),
        #"SMA_10": calc_sma(df, date, 10),
        #"SMA_20": calc_sma(df, date, 20),
        #"SMA_50": calc_sma(df, date, 50),
        "qqq_rs_slope_10": calc_qqq_rs_slope(df, df_qqq, ts, 10),
        "qqq_rs_slope_20": calc_qqq_rs_slope(df, df_qqq, ts, 20),
        "qqq_rs_slope_30": calc_qqq_rs_slope(df, df_qqq, ts, 30)
    }

    result.update(calc_setup_structure(df, ts))
    result.update(calc_sma_profit(df, ts, 10))
    result.update(calc_sma_profit(df, ts, 20))

    for bars in range(2, 10):
        result.update(calc_partial_profit(df, ts, bars, 0.5))

    return pd.DataFrame([result], index=[ts])


def calc_sma(df: pd.DataFrame, date: datetime, window: int, decimals=4) -> float | None:
    ts = pd.Timestamp(date)
    pos = df.index.get_loc(ts)

    if pos < window - 1:
        return None

    return round(df[CLOSE_COL].iloc[pos - window + 1 : pos + 1].mean(), decimals)


def calc_qqq_rs_slope(df: pd.DataFrame, df_qqq: pd.DataFrame, date: datetime, window: int, decimals: int=6) -> float | None:
    ts = pd.Timestamp(date)
    pos = df.index.get_loc(ts)

    if pos < window - 1:
        return None

    qqq_close = df_qqq[CLOSE_COL].reindex(df.index)
    rs_line = df[CLOSE_COL] / qqq_close

    arr = rs_line.iloc[pos - window + 1 : pos + 1].to_numpy()
    return round(get_slope(arr), decimals)


def calc_sma_profit(df: pd.DataFrame, date: datetime, window: int) -> dict:
    """
    For the given target_date, calculates:
    - bars held until the first future close below SMA_{window}
    - profit % from buying at the target-date close and selling at that exit close

    Results are written into the target_date row in:
    - sma{window}_profit_days
    - sma{window}_profit_pct
    """
    sma = get_sma(df, window)
    ts = pd.Timestamp(date)

    if ts not in df.index:
        return {
            f"sma{window}_profit_bars": None,
            f"sma{window}_profit_pct": None,
        }

    # only consider future and get sma
    buy_price = df.at[ts, CLOSE_COL]
    future_df = df.loc[df.index > ts].copy()
    future_df[f"SMA_{window}"] = sma.loc[future_df.index]

    # mask for closes under the sma
    exit_mask = future_df[CLOSE_COL] < future_df[f"SMA_{window}"]

    # return if none are found
    if not exit_mask.any():
        return {
            f"sma{window}_profit_bars": None,
            f"sma{window}_profit_pct": None,
        }

    # calculate date and price for first close under sma
    sell_date = future_df.index[exit_mask][0]
    sell_price = future_df.at[sell_date, CLOSE_COL]
    bars_held = future_df.index.get_loc(sell_date) + 1
    profit_pct = ((sell_price / buy_price) - 1) * 100

    return {
        f"sma{window}_profit_bars": int(bars_held),
        f"sma{window}_profit_pct": round(profit_pct, 4),
    }


def calc_partial_profit(df: pd.DataFrame, date: datetime, hold_bars: int, sell_pct: float) -> dict:
    """
    Calculates the profit for selling `sell_pct` of the position
    after `hold_bars` future bars.

    Example:
    - buy on target-date close
    - sell 50% after 5 bars

    Returns:
    - partial sell price
    - partial profit %
    """
    if not 0 <= sell_pct <= 1:
        raise ValueError("sell_pct must be between 0 and 1")

    ts = pd.Timestamp(date)
    base = f"partial_{int(sell_pct * 100)}pct_after_{hold_bars}bars"

    if ts not in df.index:
        return {
            f"{base}_sell_price": None,
            f"{base}_profit_pct": None,
        }

    buy_price = df.at[ts, CLOSE_COL]
    future_df = df.loc[df.index > ts]

    # return if not enough future bars
    if len(future_df) < hold_bars:
        return {
            f"{base}_sell_price": None,
            f"{base}_profit_pct": None,
        }

    # calculate profit pct
    sell_date = future_df.index[hold_bars - 1]
    sell_price = future_df.at[sell_date, CLOSE_COL]
    profit_pct = ((sell_price / buy_price) - 1) * 100

    return {
        f"{base}_sell_price": round(sell_price, 4),
        f"{base}_profit_pct": round(profit_pct * sell_pct, 4),
    }


def calc_adr_pct(df: pd.DataFrame, date: datetime, window: int = 20, decimals: int = 4) -> float | None:
    """
    Calculates ADR % at `date`.

    ADR % = average of daily range percentages over `window` bars
          = mean(((high - low) / low) * 100)
    """
    ts = pd.Timestamp(date)
    pos = df.index.get_loc(ts)

    required_cols = ["high", "low"]
    check_required_cols(df, required_cols)

    if pos < window - 1:
        return None

    window_df = df.iloc[pos - window + 1 : pos + 1]
    daily_range_pct = ((window_df["high"] - window_df["low"]) / window_df["low"]) * 100

    return round(daily_range_pct.mean(), decimals)


def calc_setup_structure(
        df: pd.DataFrame,
        target_date: datetime,
        lookback_bars: int = 40,
        confirm_bars: int = 5,
        swing_left: int = 5,
        swing_right: int = 5,
        open_col: str = "open",
        close_col: str = "close",
        decimals: int = 4,
) -> dict:
    """
    Returns:
    - setup_length: number of bars from pre-base high to target date, inclusive
    - move_up_pct: % move from the prior up-move low to the pre-base high

    Definitions:
    - pre-base high: highest max(open, close) in the recent lookback window that is
      followed by at least `confirm_bars` bars with no higher max(open, close)
    - up-move low: most recent confirmed swing low before the pre-base high,
      based on min(open, close)
    """
    check_required_cols(df, [open_col, close_col])

    ts = pd.Timestamp(target_date)
    if ts not in df.index:
        raise KeyError(f"Target date {ts} not found in index")

    target_pos = df.index.get_loc(ts)
    start_pos = max(0, target_pos - lookback_bars + 1)

    oc_high = df[[open_col, close_col]].max(axis=1).to_numpy()
    oc_low = df[[open_col, close_col]].min(axis=1).to_numpy()

    # ---------- find pre-base high ----------
    prebase_high_pos = None
    prebase_high_value = float("-inf")

    for i in range(start_pos, target_pos - confirm_bars + 1):
        current_value = oc_high[i]
        future_values = oc_high[i + 1: i + 1 + confirm_bars]

        if len(future_values) < confirm_bars:
            continue

        if future_values.max() <= current_value and current_value > prebase_high_value:
            prebase_high_value = current_value
            prebase_high_pos = i

    if prebase_high_pos is None:
        return {
            "setup_length": None,
            "move_up_pct": None,
        }

    # ---------- find prior swing low before pre-base high ----------
    swing_low_pos = None

    # need enough room on both sides of the candidate swing low
    swing_start = swing_left
    swing_end = prebase_high_pos - swing_right - 1

    for i in range(swing_start, swing_end + 1):
        window = oc_low[i - swing_left: i + swing_right + 1]
        current_low = oc_low[i]

        # confirmed unique swing low
        if current_low == window.min() and (window == current_low).sum() == 1:
            swing_low_pos = i

    if swing_low_pos is None:
        return {
            "setup_length": int(target_pos - prebase_high_pos),
            "move_up_pct": None,
        }

    moveup_low_value = oc_low[swing_low_pos]
    move_up_pct = ((prebase_high_value / moveup_low_value) - 1) * 100
    setup_length = target_pos - prebase_high_pos

    return {
        "setup_length": int(setup_length),
        "move_up_pct": round(move_up_pct, decimals),
        "low_high_len": int(prebase_high_pos - swing_low_pos)
    }
