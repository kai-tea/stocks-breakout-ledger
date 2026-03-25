from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from config import OUTPUT_FILE
from data import load_ohlcv


@st.cache_data(show_spinner=False)
def load_breakouts(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]

    required_cols = ["bo_name", "date", "breakout_open_to_sma50_peak_pct"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(
            "Breakout source is missing required columns: "
            + ", ".join(missing_cols)
        )

    df["ticker"] = df["bo_name"].astype(str).str.split("_").str[0].str.upper().str.strip()
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["date", "ticker"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_qqq() -> pd.DataFrame:
    return load_ohlcv("qqq")


def get_year_window(year: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.Timestamp(year - 1, 12, 1)
    end = pd.Timestamp(year + 1, 2, 1) - pd.Timedelta(days=1)
    return start, end


def build_breakout_chart(
    qqq_df: pd.DataFrame,
    breakout_df: pd.DataFrame,
    show_volume: bool = True,
    use_log_scale: bool = False,
) -> go.Figure:
    rows = 2 if show_volume else 1
    row_heights = [0.78, 0.22] if show_volume else [1.0]
    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
    )

    fig.add_trace(
        go.Candlestick(
            x=qqq_df.index,
            open=qqq_df["open"],
            high=qqq_df["high"],
            low=qqq_df["low"],
            close=qqq_df["close"],
            name="QQQ",
            increasing=dict(
                line=dict(color="#18c2a4", width=0.6),
                fillcolor="#18c2a4",
            ),
            decreasing=dict(
                line=dict(color="#ff365a", width=0.6),
                fillcolor="#ff365a",
            ),
        ),
        row=1,
        col=1,
    )

    for window, color, label in (
        (10, "#55cfe0", "SMA 10"),
        (20, "#b56bff", "SMA 20"),
        (50, "rgba(220, 38, 38, 0.50)", "SMA 50"),
    ):
        fig.add_trace(
            go.Scatter(
                x=qqq_df.index,
                y=qqq_df["close"].rolling(window).mean(),
                mode="lines",
                name=label,
                line=dict(color=color, width=0.6),
            ),
            row=1,
            col=1,
        )

    if show_volume and "volume" in qqq_df.columns:
        volume_colors = [
            "#18c2a4" if close_ >= open_ else "#ff365a"
            for open_, close_ in zip(qqq_df["open"], qqq_df["close"])
        ]
        fig.add_trace(
            go.Bar(
                x=qqq_df.index,
                y=qqq_df["volume"],
                name="Volume",
                marker_color=volume_colors,
                opacity=0.5,
            ),
            row=2,
            col=1,
        )

    marker_df = breakout_df.merge(
        qqq_df[["high"]],
        left_on="date",
        right_index=True,
        how="inner",
    ).copy()
    if not marker_df.empty:
        marker_df["stack_index"] = marker_df.groupby("date").cumcount()
        marker_df["marker_y"] = marker_df["high"] * (
            1.01 + (marker_df["stack_index"] * 0.018)
        )
        hover_text = [
            (
                f"{date.strftime('%Y-%m-%d')}"
                f"<br>Ticker: {ticker}"
                f"<br>SMA50 Peak %: {peak_pct:.4f}"
            )
            for date, ticker, peak_pct in zip(
                marker_df["date"],
                marker_df["ticker"],
                marker_df["breakout_open_to_sma50_peak_pct"],
            )
        ]

        fig.add_trace(
            go.Scatter(
                x=marker_df["date"],
                y=marker_df["marker_y"],
                mode="markers",
                marker=dict(
                    size=10,
                    color=marker_df["breakout_open_to_sma50_peak_pct"],
                    colorscale=[
                        [0.0, "#ff365a"],
                        [0.5, "#f59e0b"],
                        [1.0, "#22c55e"],
                    ],
                    cmin=0,
                    cmax=100,
                    line=dict(color="white", width=0.5),
                    showscale=True,
                    colorbar=dict(title="SMA50 Peak %"),
                ),
                customdata=hover_text,
                hovertemplate="%{customdata}<extra></extra>",
                name="Breakouts",
            ),
            row=1,
            col=1,
        )

    fig.update_layout(
        height=760,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_rangeslider_visible=False,
        xaxis_rangebreaks=[dict(bounds=["sat", "mon"])],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255, 255, 255, 0.04)", gridwidth=0.5)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255, 255, 255, 0.04)", gridwidth=0.5)
    fig.update_yaxes(type="log" if use_log_scale else "linear", row=1, col=1)

    return fig


def main() -> None:
    st.set_page_config(page_title="QQQ Breakouts", layout="wide")
    st.title("QQQ Breakouts")
    st.caption("All breakouts from `output.csv` plotted on top of QQQ.")

    try:
        breakouts = load_breakouts(OUTPUT_FILE)
        qqq_df = load_qqq()
    except Exception as exc:
        st.error(f"Failed to load breakout overview: {exc}")
        return

    if breakouts.empty:
        st.warning("`output.csv` has no breakout rows.")
        return

    breakout_dates = breakouts["date"].dropna()
    distinct_dates = breakout_dates.nunique()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Breakouts", f"{len(breakouts):,}")
    col2.metric("Distinct Dates", f"{distinct_dates:,}")
    col3.metric("First Date", breakout_dates.min().strftime("%Y-%m-%d"))
    col4.metric("Last Date", breakout_dates.max().strftime("%Y-%m-%d"))

    st.sidebar.header("Chart")
    available_years = sorted(breakouts["date"].dt.year.unique().tolist())
    year_options = ["All"] + [str(year) for year in available_years]
    selected_year = st.sidebar.selectbox("View", year_options, index=0)
    show_volume = st.sidebar.checkbox("Show volume", value=True)
    use_log_scale = st.sidebar.checkbox("Logarithmic chart", value=False)

    filtered_qqq_df = qqq_df
    filtered_breakouts = breakouts

    if selected_year != "All":
        year = int(selected_year)
        window_start, window_end = get_year_window(year)
        filtered_qqq_df = qqq_df.loc[
            (qqq_df.index >= window_start) & (qqq_df.index <= window_end)
        ]
        filtered_breakouts = breakouts.loc[
            (breakouts["date"] >= window_start)
            & (breakouts["date"] <= window_end)
        ]
        st.caption(
            f"Showing {year} with context window "
            f"{window_start.strftime('%Y-%m-%d')} to {window_end.strftime('%Y-%m-%d')}"
        )

    fig = build_breakout_chart(
        qqq_df=filtered_qqq_df,
        breakout_df=filtered_breakouts,
        show_volume=show_volume,
        use_log_scale=use_log_scale,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Breakouts")
    st.dataframe(
        filtered_breakouts[
            ["date", "ticker", "breakout_open_to_sma20_peak_pct", "breakout_open_to_sma50_peak_pct", "breakout_open_to_sma100_peak_pct"]
        ].reset_index(drop=True),
        use_container_width=True,
    )


if __name__ == "__main__":
    main()
