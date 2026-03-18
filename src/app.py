from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from compute import compute
from config import INPUT_FILE, OUTPUT_FILE
from data import load_ohlcv
from plot_setup import plot_setup_chart


@st.cache_data(show_spinner=False)
def load_input_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_data(show_spinner=False)
def load_ohlcv_cached(ticker: str) -> pd.DataFrame:
    return load_ohlcv(ticker)


@st.cache_data(show_spinner=False)
def compute_for_row(ticker: str, date: datetime) -> pd.DataFrame:
    df = load_ohlcv_cached(ticker)
    return compute(df, ticker, date)


def _ensure_index_bounds(index: int, max_index: int) -> int:
    if max_index < 0:
        return 0
    return max(0, min(index, max_index))


def _format_date(value) -> str:
    if pd.isna(value):
        return ""
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def run_batch(input_df: pd.DataFrame) -> tuple[pd.DataFrame | None, pd.DataFrame]:
    results = []
    errors = []
    total = len(input_df)
    progress = st.progress(0)

    for i, row in input_df.iterrows():
        ticker = str(row.get("ticker", "")).strip().lower()
        date = row.get("date")

        try:
            df = load_ohlcv_cached(ticker)
            result_df = compute(df, ticker, date)
            result_df = result_df.copy()
            result_df.insert(0, "input_index", i)
            results.append(result_df)
        except Exception as exc:
            errors.append(
                {
                    "index": i,
                    "ticker": ticker,
                    "date": _format_date(date),
                    "error": str(exc),
                }
            )

        progress.progress(min((i + 1) / max(total, 1), 1.0))

    output_df = pd.concat(results, ignore_index=True) if results else None
    error_df = pd.DataFrame(errors)
    return output_df, error_df


def main() -> None:
    st.set_page_config(page_title="Setup Review", layout="wide")
    st.title("Setup Review")

    st.sidebar.header("Input")
    uploaded = st.sidebar.file_uploader("Load input.csv", type=["csv"])
    input_path = INPUT_FILE if uploaded is None else None

    if input_path is not None:
        try:
            input_df = load_input_csv(input_path)
            st.sidebar.caption(f"Using `{input_path}`")
        except Exception as exc:
            st.error(f"Failed to load input file: {exc}")
            return
    else:
        input_df = pd.read_csv(uploaded)
        input_df.columns = [c.strip().lower() for c in input_df.columns]
        if "date" in input_df.columns:
            input_df["date"] = pd.to_datetime(input_df["date"])

    if "ticker" not in input_df.columns or "date" not in input_df.columns:
        st.error("Input CSV must contain `ticker` and `date` columns.")
        return
    if input_df.empty:
        st.warning("Input CSV has no rows.")
        return

    if "row_idx" not in st.session_state:
        st.session_state.row_idx = 0

    max_index = len(input_df) - 1
    st.sidebar.caption(f"{len(input_df)} setups")

    nav_col1, nav_col2 = st.sidebar.columns(2)
    if nav_col1.button("Previous"):
        st.session_state.row_idx = _ensure_index_bounds(
            st.session_state.row_idx - 1, max_index
        )
    if nav_col2.button("Next"):
        st.session_state.row_idx = _ensure_index_bounds(
            st.session_state.row_idx + 1, max_index
        )

    row_idx = st.sidebar.number_input(
        "Row index",
        min_value=0,
        max_value=max_index if max_index >= 0 else 0,
        value=_ensure_index_bounds(st.session_state.row_idx, max_index),
        step=1,
    )
    st.session_state.row_idx = row_idx

    st.sidebar.header("Options")
    lookback_bars = st.sidebar.slider("Chart lookback bars", 50, 300, 150, 10)
    forward_bars = st.sidebar.slider("Forward bars", 0, 60, 20, 5)
    show_sma_10 = st.sidebar.checkbox("Show SMA 10", value=True)
    show_sma_20 = st.sidebar.checkbox("Show SMA 20", value=True)
    show_sma_50 = st.sidebar.checkbox("Show SMA 50", value=False)
    show_annotations = st.sidebar.checkbox("Show annotations", value=True)
    show_volume = st.sidebar.checkbox("Show volume", value=True)

    if st.sidebar.button("Run / Recompute"):
        st.cache_data.clear()

    if st.sidebar.button("Refresh data"):
        st.cache_data.clear()

    selected = input_df.iloc[int(row_idx)]
    ticker = str(selected["ticker"]).strip().lower()
    target_date = pd.Timestamp(selected["date"])

    st.subheader(f"{ticker.upper()} • {target_date.strftime('%Y-%m-%d')}")

    try:
        result_df = compute_for_row(ticker, target_date)
        result_row = result_df.iloc[0].to_dict()
    except Exception as exc:
        st.error(f"Compute failed: {exc}")
        st.dataframe(pd.DataFrame([selected]))
        return

    bo_name = result_row.get("bo_name", "")
    st.caption(bo_name)

    try:
        ohlcv_df = load_ohlcv_cached(ticker)
        fig = plot_setup_chart(
            ohlcv_df,
            result_row,
            lookback_bars=lookback_bars,
            forward_bars=forward_bars,
            show_volume=show_volume,
            show_sma_10=show_sma_10,
            show_sma_20=show_sma_20,
            show_sma_50=show_sma_50,
            show_annotations=show_annotations,
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.error(f"Chart failed: {exc}")

    stats_fields = [
        "setup_length",
        "move_up_pct",
        "setup_drop_pct",
        "adr_pct",
        "qqq_rs_slope_10",
        "qqq_rs_slope_20",
        "qqq_rs_slope_30",
        "sma10_profit_bars",
        "sma10_profit_pct",
        "sma20_profit_bars",
        "sma20_profit_pct",
        "final_50pct_after_5bars_then_sma10_final_bars",
        "final_50pct_after_5bars_then_sma10_total_profit_pct",
        "final_50pct_after_5bars_then_sma20_final_bars",
        "final_50pct_after_5bars_then_sma20_total_profit_pct",
        "moveup_low_day",
        "moveup_low_price",
        "moveup_low_cross_day",
        "prebase_confirm_bars_used",
        "prebase_high_day",
        "prebase_high_price",
        "setup_low_day",
        "setup_low_price",
        "target_day",
        "target_price",
    ]
    stats = {k: result_row.get(k) for k in stats_fields if k in result_row}
    stats_df = pd.DataFrame(list(stats.items()), columns=["metric", "value"])

    st.subheader("Stats")
    st.dataframe(stats_df, use_container_width=True)

    st.subheader("Selected Row")
    st.dataframe(pd.DataFrame([selected]), use_container_width=True)

    st.subheader("Batch Run")
    if st.button("Run all setups"):
        output_df, error_df = run_batch(input_df)
        if output_df is not None:
            output_df.to_csv(OUTPUT_FILE, index=False)
            st.success(f"Saved {len(output_df)} rows to `{OUTPUT_FILE}`")
            st.dataframe(output_df.head(20), use_container_width=True)
        if not error_df.empty:
            st.warning(f"{len(error_df)} errors")
            st.dataframe(error_df, use_container_width=True)


if __name__ == "__main__":
    main()
