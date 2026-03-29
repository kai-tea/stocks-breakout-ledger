from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from compute import calc_setup_structure
from compute_util import get_qqq, get_sma
from config import CLEAN_DIR, STOOQ_DIR
from data import load_ohlcv


@dataclass(frozen=True)
class CandidateRuleConfig:
    min_price: float = 5.0
    min_adr_pct: float = 4.0
    min_avg_dollar_volume: float = 20_000_000.0
    min_gain_3m_pct: float = 25.0
    min_move_up_pct: float = 20.0
    max_setup_drop_pct: float = 30.0
    min_setup_length: int = 5
    max_setup_length: int = 30
    recent_high_window: int = 20
    breakout_proximity_pct: float = 3.0
    min_breakout_margin_pct: float = -1.0
    min_rs_slope_20: float = 0.0
    min_sma50_slope_pct: float = 0.0
    structure_lookback_bars: int = 40
    structure_confirm_bars: int = 8
    structure_swing_bars: int = 5


def list_available_tickers() -> list[str]:
    tickers: set[str] = set()

    for parquet_path in Path(CLEAN_DIR).rglob("*.parquet"):
        ticker = parquet_path.stem.lower()
        if ticker:
            tickers.add(ticker)

    for txt_path in Path(STOOQ_DIR).rglob("*.us.txt"):
        ticker = txt_path.name.removesuffix(".us.txt").lower()
        if ticker:
            tickers.add(ticker)

    tickers.discard("qqq")
    return sorted(tickers)


def _rolling_slope(series: pd.Series, window: int, decimals: int = 6) -> pd.Series:
    values = series.to_numpy(dtype=float)
    out = np.full(len(values), np.nan, dtype=float)

    if len(values) < window:
        return pd.Series(out, index=series.index)

    x = np.arange(window, dtype=float)
    x_centered = x - x.mean()
    denominator = float(np.sum(x_centered ** 2))

    windows = np.lib.stride_tricks.sliding_window_view(values, window_shape=window)
    valid_mask = ~np.isnan(windows).any(axis=1)
    if valid_mask.any():
        centered_windows = windows[valid_mask] - windows[valid_mask].mean(axis=1, keepdims=True)
        slopes = (centered_windows @ x_centered) / denominator
        out[window - 1 :][valid_mask] = slopes

    return pd.Series(np.round(out, decimals), index=series.index)


def detect_candidates_for_ticker(
    ticker: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    config: CandidateRuleConfig,
    qqq_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    df = load_ohlcv(ticker).copy()
    if df.empty:
        return pd.DataFrame()

    qqq_df = get_qqq() if qqq_df is None else qqq_df

    df = df.sort_index()
    qqq_close = qqq_df["close"].reindex(df.index)
    oc_high = df[["open", "close"]].max(axis=1)
    daily_range_pct = ((df["high"] - df["low"]) / df["low"]) * 100.0
    gain_3m_low = df[["open", "close"]].min(axis=1).rolling(63).min()
    gain_3m_high = oc_high.rolling(63).max()
    rs_line = df["close"] / qqq_close

    df["avg_dollar_volume_20"] = (df["close"] * df["volume"]).rolling(20).mean()
    df["adr_pct_20"] = daily_range_pct.rolling(20).mean().round(4)
    df["gain_3m_pct_pre"] = (((gain_3m_high / gain_3m_low) - 1.0) * 100.0).round(4)
    df["qqq_rs_slope_20_pre"] = _rolling_slope(rs_line, 20)
    df["sma50"] = get_sma(df, 50)
    df["sma50_slope_pct_5"] = (df["sma50"] / df["sma50"].shift(5) - 1.0) * 100.0
    df["prior_pivot_high"] = oc_high.rolling(config.recent_high_window).max().shift(1)

    scan_df = df.loc[(df.index >= start_date) & (df.index <= end_date)]
    if scan_df.empty:
        return pd.DataFrame()

    candidate_mask = (
        (scan_df["close"] >= config.min_price)
        & (scan_df["adr_pct_20"] >= config.min_adr_pct)
        & (scan_df["avg_dollar_volume_20"] >= config.min_avg_dollar_volume)
        & (scan_df["gain_3m_pct_pre"] >= config.min_gain_3m_pct)
        & scan_df["sma50"].notna()
        & (scan_df["close"] >= scan_df["sma50"])
    )
    scan_df = scan_df.loc[candidate_mask]
    if scan_df.empty:
        return pd.DataFrame()

    results: list[dict] = []

    for ts in scan_df.index:
        try:
            structure = calc_setup_structure(
                df,
                ts,
                lookback_bars=config.structure_lookback_bars,
                confirm_bars=config.structure_confirm_bars,
                swing_bars=config.structure_swing_bars,
            )
        except Exception:
            continue

        close_price = float(df.at[ts, "close"])
        high_price = float(df.at[ts, "high"])
        avg_dollar_volume_20 = df.at[ts, "avg_dollar_volume_20"]
        sma50_value = df.at[ts, "sma50"]
        sma50_slope_pct_5 = df.at[ts, "sma50_slope_pct_5"]
        prior_pivot_high = df.at[ts, "prior_pivot_high"]

        adr_pct = df.at[ts, "adr_pct_20"]
        gain_3m_pct = df.at[ts, "gain_3m_pct_pre"]
        rs_slope_20 = df.at[ts, "qqq_rs_slope_20_pre"]

        if pd.isna(prior_pivot_high) or prior_pivot_high <= 0:
            breakout_margin_pct = None
            breakout_distance_pct = None
        else:
            breakout_margin_pct = ((close_price / prior_pivot_high) - 1.0) * 100.0
            breakout_distance_pct = ((prior_pivot_high / close_price) - 1.0) * 100.0

        setup_length = structure.get("setup_length")
        move_up_pct = structure.get("move_up_pct")
        setup_drop_pct = structure.get("setup_drop_pct")

        hard_rules = {
            "price_rule": close_price >= config.min_price,
            "adr_rule": adr_pct is not None and adr_pct >= config.min_adr_pct,
            "dollar_volume_rule": pd.notna(avg_dollar_volume_20)
            and float(avg_dollar_volume_20) >= config.min_avg_dollar_volume,
            "prior_gain_rule": gain_3m_pct is not None and gain_3m_pct >= config.min_gain_3m_pct,
            "setup_length_rule": setup_length is not None
            and config.min_setup_length <= int(setup_length) <= config.max_setup_length,
            "move_up_rule": move_up_pct is not None and move_up_pct >= config.min_move_up_pct,
            "setup_drop_rule": setup_drop_pct is not None and setup_drop_pct <= config.max_setup_drop_pct,
            "trend_rule": pd.notna(sma50_value) and close_price >= float(sma50_value),
        }

        soft_rules = {
            "breakout_proximity_rule": breakout_distance_pct is not None
            and breakout_distance_pct <= config.breakout_proximity_pct,
            "breakout_margin_rule": breakout_margin_pct is not None
            and breakout_margin_pct >= config.min_breakout_margin_pct,
            "rs_rule": rs_slope_20 is not None and rs_slope_20 >= config.min_rs_slope_20,
            "sma50_slope_rule": pd.notna(sma50_slope_pct_5)
            and float(sma50_slope_pct_5) >= config.min_sma50_slope_pct,
        }

        hard_passes = sum(hard_rules.values())
        soft_passes = sum(soft_rules.values())
        candidate_score = hard_passes + soft_passes

        if all(hard_rules.values()) and soft_passes >= 3:
            candidate_label = "valid"
        elif all(hard_rules.values()) and soft_passes >= 1:
            candidate_label = "borderline"
        else:
            candidate_label = "invalid"

        failed_rules = [name for name, passed in {**hard_rules, **soft_rules}.items() if not passed]

        result = {
            "ticker": ticker.upper(),
            "date": ts,
            "candidate_label": candidate_label,
            "candidate_score": int(candidate_score),
            "failed_rules": ", ".join(failed_rules),
            "close": round(close_price, 4),
            "high": round(high_price, 4),
            "avg_dollar_volume_20": round(float(avg_dollar_volume_20), 2)
            if pd.notna(avg_dollar_volume_20)
            else None,
            "adr_pct": adr_pct,
            "gain_3m_pct": gain_3m_pct,
            "qqq_rs_slope_20": rs_slope_20,
            "breakout_margin_pct": round(float(breakout_margin_pct), 4)
            if breakout_margin_pct is not None
            else None,
            "breakout_distance_pct": round(float(breakout_distance_pct), 4)
            if breakout_distance_pct is not None
            else None,
            "prior_pivot_high": round(float(prior_pivot_high), 4)
            if pd.notna(prior_pivot_high)
            else None,
            "sma50": round(float(sma50_value), 4) if pd.notna(sma50_value) else None,
            "sma50_slope_pct_5": round(float(sma50_slope_pct_5), 4)
            if pd.notna(sma50_slope_pct_5)
            else None,
        }
        result.update(structure)
        result.update(hard_rules)
        result.update(soft_rules)
        results.append(result)

    if not results:
        return pd.DataFrame()

    out = pd.DataFrame(results).sort_values(["date", "ticker"]).reset_index(drop=True)
    return out


def detect_candidates(
    tickers: list[str],
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    config: CandidateRuleConfig | None = None,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    config = CandidateRuleConfig() if config is None else config
    qqq_df = get_qqq()

    all_rows: list[pd.DataFrame] = []
    errors: list[dict] = []

    total = len(tickers)
    for idx, ticker in enumerate(tickers, start=1):
        try:
            ticker_df = detect_candidates_for_ticker(
                ticker=ticker.lower(),
                start_date=start_date,
                end_date=end_date,
                config=config,
                qqq_df=qqq_df,
            )
            if not ticker_df.empty:
                all_rows.append(ticker_df)
        except Exception as exc:
            errors.append({"ticker": ticker.upper(), "error": str(exc)})

        if progress_callback is not None:
            progress_callback(idx, total, ticker.upper())

    candidates_df = (
        pd.concat(all_rows, ignore_index=True)
        if all_rows
        else pd.DataFrame()
    )
    errors_df = pd.DataFrame(errors)
    return candidates_df, errors_df
