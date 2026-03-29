import pandas as pd
from datetime import datetime

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
        "bo_name": f"{ticker.upper()}_{ts.year}_{ts.strftime('%b')}",
        "date": date,
        "buy_price": buy_price,
        "adr_pct": calc_adr_pct(df, date, 20, 4),
        "gain_1m_pct": calc_gain(df, ts, 21),
        "gain_3m_pct": calc_gain(df, ts, 63),
        "gain_6m_pct": calc_gain(df, ts, 126),
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
    result.update(calc_breakout_open_to_sma_peak(df, ts, 20))
    result.update(calc_breakout_open_to_sma_peak(df, ts, 50))
    result.update(calc_breakout_open_to_sma_peak(df, ts, 100))

    for bars in range(2, 10):
        result.update(calc_partial_profit(df, ts, bars, 0.5))
        result.update(calc_staged_sma_profit(df, ts, bars, 0.5, 10))
        result.update(calc_staged_sma_profit(df, ts, bars, 0.5, 20))

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


def clamp_profit_pct(value: float, decimals: int = 4) -> float:
    return round(max(float(value), 0.0), decimals)


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
        f"sma{window}_profit_pct": clamp_profit_pct(profit_pct),
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
        f"{base}_profit_pct": clamp_profit_pct(profit_pct * sell_pct),
    }


def calc_breakout_open_to_sma_peak(
    df: pd.DataFrame,
    date: datetime,
    sma_window: int,
    open_col: str = "open",
    close_col: str = "close",
    decimals: int = 4,
) -> dict:
    """
    Measures the gain from the breakout-day open to the highest max(open, close)
    reached before price next breaks below SMA_{sma_window} using min(open, close).
    """
    ts = pd.Timestamp(date)
    base = f"breakout_open_to_sma{sma_window}_peak"

    if ts not in df.index:
        return {
            f"{base}_pct": None,
            f"{base}_price": None,
            f"{base}_day": None,
        }

    sma = get_sma(df, sma_window)
    breakout_open = df.at[ts, open_col]
    future_df = df.loc[df.index >= ts].copy()
    future_df[f"SMA_{sma_window}"] = sma.loc[future_df.index]
    future_df["oc_low"] = future_df[[open_col, close_col]].min(axis=1)
    future_df["oc_high"] = future_df[[open_col, close_col]].max(axis=1)

    cross_mask = future_df["oc_low"] < future_df[f"SMA_{sma_window}"]
    if cross_mask.any():
        cross_day = future_df.index[cross_mask][0]
        peak_window = future_df.loc[future_df.index < cross_day]
    else:
        peak_window = future_df

    if peak_window.empty or breakout_open <= 0:
        return {
            f"{base}_pct": None,
            f"{base}_price": None,
            f"{base}_day": None,
        }

    peak_day = peak_window["oc_high"].idxmax()
    peak_price = peak_window.at[peak_day, "oc_high"]
    gain_pct = ((peak_price / breakout_open) - 1) * 100

    return {
        f"{base}_pct": round(float(gain_pct), decimals),
        f"{base}_price": round(float(peak_price), decimals),
        f"{base}_day": peak_day,
    }


def calc_staged_sma_profit(
    df: pd.DataFrame,
    date: datetime,
    hold_bars: int,
    sell_pct: float,
    final_sma_window: int,
) -> dict:
    """
    Calculates a staged exit:
    - sell `sell_pct` after `hold_bars` future bars
    - sell the remaining position on the first future close below SMA_{final_sma_window}
      after that partial exit

    Returns weighted profit percentages on the original full position size.
    """
    if not 0 <= sell_pct <= 1:
        raise ValueError("sell_pct must be between 0 and 1")

    ts = pd.Timestamp(date)
    remaining_pct = 1 - sell_pct
    base = (
        f"final_{int(sell_pct * 100)}pct_after_{hold_bars}bars"
        f"_then_sma{final_sma_window}"
    )

    empty_result = {
        f"{base}_partial_sell_price": None,
        f"{base}_partial_profit_pct": None,
        f"{base}_final_sell_price": None,
        f"{base}_final_profit_pct": None,
        f"{base}_final_bars": None,
        f"{base}_total_profit_pct": None,
    }

    if ts not in df.index:
        return empty_result

    future_df = df.loc[df.index > ts].copy()
    if len(future_df) < hold_bars:
        return empty_result

    buy_price = df.at[ts, CLOSE_COL]
    partial_sell_date = future_df.index[hold_bars - 1]
    partial_sell_price = future_df.at[partial_sell_date, CLOSE_COL]
    partial_profit_pct = ((partial_sell_price / buy_price) - 1) * 100

    sma = get_sma(df, final_sma_window)
    remaining_df = future_df.loc[future_df.index > partial_sell_date].copy()
    remaining_df[f"SMA_{final_sma_window}"] = sma.loc[remaining_df.index]

    exit_mask = remaining_df[CLOSE_COL] < remaining_df[f"SMA_{final_sma_window}"]
    if not exit_mask.any():
        return {
            f"{base}_partial_sell_price": round(float(partial_sell_price), 4),
            f"{base}_partial_profit_pct": clamp_profit_pct(partial_profit_pct * sell_pct),
            f"{base}_final_sell_price": None,
            f"{base}_final_profit_pct": None,
            f"{base}_final_bars": None,
            f"{base}_total_profit_pct": None,
        }

    final_sell_date = remaining_df.index[exit_mask][0]
    final_sell_price = remaining_df.at[final_sell_date, CLOSE_COL]
    final_bars = df.index.get_loc(final_sell_date) - df.index.get_loc(ts)
    final_profit_pct = ((final_sell_price / buy_price) - 1) * 100
    total_profit_pct = (partial_profit_pct * sell_pct) + (final_profit_pct * remaining_pct)

    return {
        f"{base}_partial_sell_price": round(float(partial_sell_price), 4),
        f"{base}_partial_profit_pct": clamp_profit_pct(partial_profit_pct * sell_pct),
        f"{base}_final_sell_price": round(float(final_sell_price), 4),
        f"{base}_final_profit_pct": clamp_profit_pct(final_profit_pct * remaining_pct),
        f"{base}_final_bars": int(final_bars),
        f"{base}_total_profit_pct": clamp_profit_pct(total_profit_pct),
    }


def calc_adr_pct(df: pd.DataFrame, date: datetime, window: int = 20, decimals: int = 2) -> float | None:
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


def calc_gain(
    df: pd.DataFrame,
    date: datetime,
    window: int,
    open_col: str = "open",
    close_col: str = "close",
    decimals: int = 4,
) -> float | None:
    """
    Calculates the percentage gain from the lowest min(open, close) to the
    highest max(open, close) inside the trailing `window` bars ending at `date`.
    """
    ts = pd.Timestamp(date)
    pos = df.index.get_loc(ts)

    check_required_cols(df, [open_col, close_col])

    if pos < window - 1:
        return None

    window_df = df.iloc[pos - window + 1 : pos + 1]
    oc_low = window_df[[open_col, close_col]].min(axis=1).min()
    oc_high = window_df[[open_col, close_col]].max(axis=1).max()

    if oc_low <= 0:
        return None

    gain_pct = ((oc_high / oc_low) - 1) * 100
    return round(float(gain_pct), decimals)


def calc_setup_structure(
        df: pd.DataFrame,
        target_date: datetime,
        lookback_bars: int = 40,
        confirm_bars: int = 8,
        swing_bars: int = 5,
        open_col: str = "open",
        close_col: str = "close",
        decimals: int = 4,
) -> dict:
    """
    Returns:
    - setup_length: number of bars from pre-base high to target date, inclusive
    - move_up_pct: % move from the prior up-move low to the pre-base high

    Definitions:
    - pre-base high: breakout reference high, using a hybrid approach:
      recent pivot high first, ascending setup boundary second
    - up-move low: the latest meaningful swing low that launches the move into the
      chosen reference high, with the bullish SMA 10 / SMA 20 cross retained as
      context rather than the sole anchor driver
    """
    check_required_cols(df, [open_col, close_col])

    ts = pd.Timestamp(target_date)
    if ts not in df.index:
        raise KeyError(f"Target date {ts} not found in index")

    target_pos = df.index.get_loc(ts)
    start_pos = max(0, target_pos - lookback_bars + 1)

    price_high = df["high"].to_numpy() if "high" in df.columns else df[[open_col, close_col]].max(axis=1).to_numpy()
    price_low = df["low"].to_numpy() if "low" in df.columns else df[[open_col, close_col]].min(axis=1).to_numpy()
    oc_low = df[[open_col, close_col]].min(axis=1).to_numpy()
    sma10 = get_sma(df, 10)
    sma20 = get_sma(df, 20)

    min_pivot_pullback_pct = 3.0
    min_base_bars_after_high = 3
    ascending_window_bars = 12
    min_ascending_up_ratio = 0.55
    max_ascending_range_pct = 18.0
    breakout_near_top_pct = 3.0
    min_impulse_pct = 15.0

    def is_unique_swing_high(pos: int, allow_ties: bool) -> bool:
        window = price_high[pos - swing_bars: pos + swing_bars + 1]
        current_value = price_high[pos]
        if current_value != window.max():
            return False
        if not allow_ties and (window == current_value).sum() != 1:
            return False
        return True

    def is_unique_swing_low(pos: int) -> bool:
        window = price_low[pos - swing_bars: pos + swing_bars + 1]
        current_value = price_low[pos]
        return current_value == window.min() and (window == current_value).sum() == 1

    def find_latest_bullish_cross(before_pos: int) -> int | None:
        sma10_values = sma10.to_numpy()
        sma20_values = sma20.to_numpy()
        chosen_cross_pos = None

        for i in range(1, before_pos):
            prev_sma10 = sma10_values[i - 1]
            prev_sma20 = sma20_values[i - 1]
            current_sma10 = sma10_values[i]
            current_sma20 = sma20_values[i]

            if pd.isna(prev_sma10) or pd.isna(prev_sma20) or pd.isna(current_sma10) or pd.isna(current_sma20):
                continue

            crossed_up = prev_sma10 <= prev_sma20 and current_sma10 > current_sma20
            if crossed_up:
                chosen_cross_pos = i

        return chosen_cross_pos

    def find_prebase_high(allow_ties: bool) -> tuple[int | None, float, int | None, str | None, int | None]:
        for current_confirm_bars in range(confirm_bars, 0, -1):
            high_start = max(start_pos, swing_bars)
            high_end = target_pos - max(swing_bars, current_confirm_bars) - 1

            for i in range(high_end, high_start - 1, -1):
                current_value = price_high[i]

                if not is_unique_swing_high(i, allow_ties):
                    continue

                future_values = price_high[i + 1: i + 1 + current_confirm_bars]
                if len(future_values) < current_confirm_bars:
                    continue

                future_lows = price_low[i + 1: target_pos + 1]
                if len(future_lows) < min_base_bars_after_high:
                    continue

                pullback_pct = ((current_value - future_lows.min()) / current_value) * 100 if current_value > 0 else 0.0
                if future_values.max() <= current_value and pullback_pct >= min_pivot_pullback_pct:
                    return i, current_value, current_confirm_bars, "pivot", None

        asc_start = max(start_pos, target_pos - ascending_window_bars)
        if target_pos - asc_start >= max(swing_bars + 1, 4):
            recent_highs = price_high[asc_start:target_pos]
            recent_lows = price_low[asc_start:target_pos]

            if len(recent_highs) >= 4:
                high_diffs = [recent_highs[j] - recent_highs[j - 1] for j in range(1, len(recent_highs))]
                low_diffs = [recent_lows[j] - recent_lows[j - 1] for j in range(1, len(recent_lows))]
                high_up_ratio = sum(diff >= 0 for diff in high_diffs) / len(high_diffs)
                low_up_ratio = sum(diff >= 0 for diff in low_diffs) / len(low_diffs)
                recent_range_pct = (
                    ((recent_highs.max() - recent_lows.min()) / recent_highs.max()) * 100
                    if recent_highs.max() > 0 else float("inf")
                )
                breakout_close = df.at[ts, close_col]
                near_top = breakout_close >= recent_highs.max() * (1 - breakout_near_top_pct / 100)

                if (
                    high_up_ratio >= min_ascending_up_ratio
                    and low_up_ratio >= min_ascending_up_ratio
                    and recent_range_pct <= max_ascending_range_pct
                    and near_top
                ):
                    relative_high_pos = max(
                        idx for idx, value in enumerate(recent_highs)
                        if value == recent_highs.max()
                    )
                    high_pos = asc_start + relative_high_pos
                    return high_pos, price_high[high_pos], 0, "ascending", asc_start

        return None, float("-inf"), None, None, None

    def find_moveup_low(prebase_high_pos: int, high_mode: str | None, ascending_start_pos: int | None) -> tuple[int | None, int | None, str | None]:
        chosen_cross_pos = find_latest_bullish_cross(prebase_high_pos)

        if high_mode == "ascending" and ascending_start_pos is not None:
            search_end_pos = ascending_start_pos
        elif chosen_cross_pos is not None and chosen_cross_pos - start_pos >= swing_bars + 1:
            search_end_pos = chosen_cross_pos
        else:
            search_end_pos = prebase_high_pos

        low_start = max(start_pos, swing_bars)
        low_end = search_end_pos - swing_bars - 1
        latest_local_min_pos = None

        if low_end >= low_start:
            for i in range(low_start, low_end + 1):
                if not is_unique_swing_low(i):
                    continue

                current_low = price_low[i]
                if current_low <= 0:
                    continue

                advance_high = price_high[i: prebase_high_pos + 1].max()
                advance_pct = ((advance_high / current_low) - 1) * 100
                if advance_pct >= min_impulse_pct:
                    latest_local_min_pos = i

        if latest_local_min_pos is not None:
            return latest_local_min_pos, chosen_cross_pos, "swing"

        fallback_lows = price_low[start_pos:search_end_pos] if search_end_pos > start_pos else []
        if len(fallback_lows) == 0:
            return None, chosen_cross_pos, None

        fallback_low_pos = start_pos + int(fallback_lows.argmin())
        return fallback_low_pos, chosen_cross_pos, "fallback"

    # ---------- find pre-base high ----------
    prebase_high_pos, prebase_high_value, confirm_bars_used, prebase_high_mode, ascending_start_pos = find_prebase_high(allow_ties=False)
    if prebase_high_pos is None:
        prebase_high_pos, prebase_high_value, confirm_bars_used, prebase_high_mode, ascending_start_pos = find_prebase_high(allow_ties=True)
    if prebase_high_pos is None and target_pos > start_pos:
        fallback_highs = price_high[start_pos:target_pos]
        if len(fallback_highs) > 0:
            prebase_high_pos = start_pos + int(fallback_highs.argmax())
            prebase_high_value = price_high[prebase_high_pos]
            confirm_bars_used = 0
            prebase_high_mode = "fallback"
            ascending_start_pos = None

    target_price = df.at[ts, close_col]

    if prebase_high_pos is None:
        return {
            "setup_length": None,
            "move_up_pct": None,
            "setup_drop_pct": None,
            "low_high_len": None,
            "moveup_low_day": None,
            "moveup_low_price": None,
            "moveup_low_cross_day": None,
            "moveup_low_mode": None,
            "prebase_confirm_bars_used": None,
            "prebase_high_day": None,
            "prebase_high_price": None,
            "prebase_high_mode": None,
            "setup_low_day": None,
            "setup_low_price": None,
            "target_day": ts,
            "target_price": round(float(target_price), decimals),
        }

    # ---------- find move-up low ----------
    swing_low_pos, moveup_cross_pos, moveup_low_mode = find_moveup_low(
        prebase_high_pos,
        prebase_high_mode,
        ascending_start_pos,
    )
    if swing_low_pos is None and prebase_high_pos > start_pos:
        fallback_lows = price_low[start_pos:prebase_high_pos]
        if len(fallback_lows) > 0:
            swing_low_pos = start_pos + int(fallback_lows.argmin())
            moveup_low_mode = "fallback"

    prebase_high_day = df.index[prebase_high_pos]
    prebase_high_price = prebase_high_value
    setup_window_lows = oc_low[prebase_high_pos : target_pos + 1]
    setup_low_offset = int(setup_window_lows.argmin())
    setup_low_pos = prebase_high_pos + setup_low_offset
    setup_low_value = oc_low[setup_low_pos]
    setup_drop_pct = ((prebase_high_price - setup_low_value) / prebase_high_price) * 100

    if swing_low_pos is None:
        return {
            "setup_length": int(target_pos - prebase_high_pos),
            "move_up_pct": None,
            "setup_drop_pct": round(float(setup_drop_pct), decimals),
            "low_high_len": None,
            "moveup_low_day": None,
            "moveup_low_price": None,
            "moveup_low_cross_day": None,
            "moveup_low_mode": None,
            "prebase_confirm_bars_used": int(confirm_bars_used),
            "prebase_high_day": prebase_high_day,
            "prebase_high_price": round(float(prebase_high_price), decimals),
            "prebase_high_mode": prebase_high_mode,
            "setup_low_day": df.index[setup_low_pos],
            "setup_low_price": round(float(setup_low_value), decimals),
            "target_day": ts,
            "target_price": round(float(target_price), decimals),
        }

    moveup_low_value = price_low[swing_low_pos]
    move_up_pct = ((prebase_high_value / moveup_low_value) - 1) * 100
    setup_length = target_pos - prebase_high_pos

    return {
        "setup_length": int(setup_length),
        "move_up_pct": round(move_up_pct, decimals),
        "setup_drop_pct": round(float(setup_drop_pct), decimals),
        "low_high_len": int(prebase_high_pos - swing_low_pos),
        "moveup_low_day": df.index[swing_low_pos],
        "moveup_low_price": round(float(moveup_low_value), decimals),
        "moveup_low_cross_day": df.index[moveup_cross_pos] if moveup_cross_pos is not None else None,
        "moveup_low_mode": moveup_low_mode,
        "prebase_confirm_bars_used": int(confirm_bars_used),
        "prebase_high_day": prebase_high_day,
        "prebase_high_price": round(float(prebase_high_price), decimals),
        "prebase_high_mode": prebase_high_mode,
        "setup_low_day": df.index[setup_low_pos],
        "setup_low_price": round(float(setup_low_value), decimals),
        "target_day": ts,
        "target_price": round(float(target_price), decimals),
    }
