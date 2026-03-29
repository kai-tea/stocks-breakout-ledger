from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from config import OUTPUT_FILE


FEATURE_CANDIDATES = [
    "setup_length",
    "move_up_pct",
    "setup_drop_pct",
    "adr_pct",
    "gain_1m_pct",
    "gain_3m_pct",
    "gain_6m_pct",
    "qqq_rs_slope_10",
    "qqq_rs_slope_20",
    "qqq_rs_slope_30",
    "prebase_confirm_bars_used",
    "breakout_open_to_sma20_peak_pct",
    "breakout_open_to_sma50_peak_pct",
    "breakout_open_to_sma100_peak_pct",
]

COLUMN_LABELS = {
    "breakout_open_to_sma20_peak_pct": "bo_to_sma20_peak_pct",
    "breakout_open_to_sma50_peak_pct": "bo_to_sma50_peak_pct",
    "breakout_open_to_sma100_peak_pct": "bo_to_sma100_peak_pct",
}

PREFERRED_TARGETS = [
    "sma10_profit_pct",
    "sma20_profit_pct",
    "final_50pct_after_5bars_then_sma10_total_profit_pct",
    "final_50pct_after_5bars_then_sma20_total_profit_pct",
    "breakout_open_to_sma20_peak_pct",
    "breakout_open_to_sma50_peak_pct",
    "breakout_open_to_sma100_peak_pct",
]


@st.cache_data(show_spinner=False)
def load_output_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]

    date_cols = [
        "date",
        "moveup_low_day",
        "moveup_low_cross_day",
        "prebase_high_day",
        "setup_low_day",
        "target_day",
        "breakout_open_to_sma20_peak_day",
        "breakout_open_to_sma50_peak_day",
        "breakout_open_to_sma100_peak_day",
    ]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    if "ticker" not in df.columns and "bo_name" in df.columns:
        df["ticker"] = df["bo_name"].astype(str).str.split("_").str[0]

    if "date" in df.columns:
        df["year"] = df["date"].dt.year

    return df


def get_target_metrics(df: pd.DataFrame) -> list[str]:
    return [
        col
        for col in df.columns
        if (
            col.endswith("_profit_pct")
            or (col.startswith("breakout_open_to_sma") and col.endswith("_pct"))
        )
    ]


def summarize_metric(series: pd.Series) -> pd.Series:
    clean = series.dropna()
    if clean.empty:
        return pd.Series(
            {
                "count": 0,
                "win_rate_pct": np.nan,
                "mean_pct": np.nan,
                "median_pct": np.nan,
                "avg_winner_pct": np.nan,
                "avg_loser_pct": np.nan,
                "expectancy_pct": np.nan,
            }
        )

    winners = clean[clean > 0]
    losers = clean[clean <= 0]
    win_rate = winners.size / clean.size
    avg_winner = winners.mean() if not winners.empty else 0.0
    avg_loser = losers.mean() if not losers.empty else 0.0
    expectancy = (win_rate * avg_winner) + ((1 - win_rate) * avg_loser)

    return pd.Series(
        {
            "count": int(clean.size),
            "win_rate_pct": round(win_rate * 100, 2),
            "mean_pct": round(clean.mean(), 4),
            "median_pct": round(clean.median(), 4),
            "avg_winner_pct": round(avg_winner, 4),
            "avg_loser_pct": round(avg_loser, 4),
            "expectancy_pct": round(expectancy, 4),
        }
    )


def add_numeric_range_filter(
    df: pd.DataFrame,
    column: str,
    label: str,
    key: str,
) -> pd.DataFrame:
    if column not in df.columns:
        return df

    clean = df[column].dropna()
    if clean.empty:
        return df

    min_val = float(clean.min())
    max_val = float(clean.max())
    if min_val == max_val:
        return df

    selected = st.sidebar.slider(
        label,
        min_value=min_val,
        max_value=max_val,
        value=(min_val, max_val),
        key=key,
    )
    return df[df[column].between(selected[0], selected[1]) | df[column].isna()]


def bucket_analysis(
    df: pd.DataFrame,
    feature_col: str,
    target_col: str,
    buckets: int,
) -> pd.DataFrame:
    sample = df[[feature_col, target_col]].dropna().copy()
    if sample.empty:
        return pd.DataFrame()

    if sample[feature_col].nunique() < buckets:
        sample["bucket"] = sample[feature_col]
    else:
        sample["bucket"] = pd.qcut(sample[feature_col], q=buckets, duplicates="drop")

    out = (
        sample.groupby("bucket", observed=False)[target_col]
        .agg(
            count="size",
            mean_pct="mean",
            median_pct="median",
            win_rate_pct=lambda s: (s > 0).mean() * 100,
        )
        .reset_index()
    )
    out["mean_pct"] = out["mean_pct"].round(4)
    out["median_pct"] = out["median_pct"].round(4)
    out["win_rate_pct"] = out["win_rate_pct"].round(2)
    return out


def unique_columns(columns: list[str]) -> list[str]:
    return list(dict.fromkeys(columns))


def column_label(column: str) -> str:
    return COLUMN_LABELS.get(column, column)


def main() -> None:
    st.set_page_config(page_title="Strategy Analytics", layout="wide")
    st.title("Strategy Analytics")
    st.caption("Interactive research dashboard for `output.csv`.")

    try:
        df = load_output_data(OUTPUT_FILE)
    except Exception as exc:
        st.error(f"Failed to load analytics dataset: {exc}")
        return

    if df.empty:
        st.warning("`output.csv` is empty.")
        return

    target_metrics = get_target_metrics(df)
    if not target_metrics:
        st.warning("No target metrics found in `output.csv`.")
        return

    st.sidebar.header("Dataset")

    filtered_df = df.copy()

    if "date" in filtered_df.columns:
        min_date = filtered_df["date"].min().date()
        max_date = filtered_df["date"].max().date()
        date_range = st.sidebar.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        if len(date_range) == 2:
            start_date, end_date = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
            filtered_df = filtered_df[
                filtered_df["date"].between(start_date, end_date)
            ]

    if "year" in filtered_df.columns:
        years = sorted(filtered_df["year"].dropna().astype(int).unique().tolist())
        year_pending_key = "analytics_selected_years_pending"
        year_applied_key = "analytics_selected_years_applied"

        if year_pending_key not in st.session_state:
            st.session_state[year_pending_key] = years
        else:
            st.session_state[year_pending_key] = [
                year for year in st.session_state[year_pending_key] if year in years
            ]

        if year_applied_key not in st.session_state:
            st.session_state[year_applied_key] = years
        else:
            st.session_state[year_applied_key] = [
                year for year in st.session_state[year_applied_key] if year in years
            ]

        year_button_cols = st.sidebar.columns(2)
        if year_button_cols[0].button("All", key="analytics_years_all"):
            st.session_state[year_pending_key] = years
        if year_button_cols[1].button("None", key="analytics_years_none"):
            st.session_state[year_pending_key] = []

        st.sidebar.multiselect(
            "Years",
            years,
            key=year_pending_key,
        )
        if st.sidebar.button("Apply", key="analytics_years_apply"):
            st.session_state[year_applied_key] = list(st.session_state[year_pending_key])

        applied_years = st.session_state[year_applied_key]
        filtered_df = filtered_df[filtered_df["year"].isin(applied_years)]

    if "ticker" in filtered_df.columns:
        tickers = sorted(filtered_df["ticker"].dropna().astype(str).unique().tolist())
        selected_tickers = st.sidebar.multiselect("Tickers", tickers, default=[])
        if selected_tickers:
            filtered_df = filtered_df[filtered_df["ticker"].isin(selected_tickers)]

    st.sidebar.header("Feature Filters")
    filtered_df = add_numeric_range_filter(filtered_df, "setup_length", "Setup length", "setup_length_filter")
    filtered_df = add_numeric_range_filter(filtered_df, "move_up_pct", "Move-up %", "move_up_pct_filter")
    filtered_df = add_numeric_range_filter(filtered_df, "setup_drop_pct", "Setup drop %", "setup_drop_pct_filter")
    filtered_df = add_numeric_range_filter(filtered_df, "adr_pct", "ADR %", "adr_pct_filter")
    filtered_df = add_numeric_range_filter(filtered_df, "qqq_rs_slope_20", "QQQ RS slope 20", "qqq_rs_20_filter")
    filtered_df = add_numeric_range_filter(filtered_df, "gain_3m_pct", "3M gain %", "gain_3m_filter")
    filtered_df = add_numeric_range_filter(filtered_df, "gain_6m_pct", "6M gain %", "gain_6m_filter")

    if filtered_df.empty:
        st.warning("No rows match the current filters.")
        return

    default_target = next((col for col in PREFERRED_TARGETS if col in target_metrics), target_metrics[0])
    target_col = st.sidebar.selectbox(
        "Target metric",
        target_metrics,
        index=target_metrics.index(default_target),
        format_func=column_label,
    )

    feature_options = [col for col in FEATURE_CANDIDATES if col in filtered_df.columns]
    feature_col = st.sidebar.selectbox(
        "Feature for scatter / buckets",
        feature_options,
        index=feature_options.index("setup_drop_pct") if "setup_drop_pct" in feature_options else 0,
        format_func=column_label,
    )
    pair_plot_options = unique_columns(feature_options + [target_col])
    pair_plot_default = [
        col
        for col in [feature_col, target_col, "move_up_pct", "setup_length"]
        if col in pair_plot_options
    ]
    pair_plot_cols = st.sidebar.multiselect(
        "Pair plot columns",
        pair_plot_options,
        default=pair_plot_default[:4],
        format_func=column_label,
        help="Choose 2-6 numeric columns for the scatter-matrix pair plot.",
    )
    bucket_count = st.sidebar.slider("Bucket count", 3, 10, 5)

    target_summary = summarize_metric(filtered_df[target_col])

    top_row = st.columns(6)
    top_row[0].metric("Rows", f"{len(filtered_df):,}")
    top_row[1].metric("Tickers", f"{filtered_df['ticker'].nunique() if 'ticker' in filtered_df.columns else 0:,}")
    top_row[2].metric("Mean %", f"{target_summary['mean_pct']:.2f}")
    top_row[3].metric("Median %", f"{target_summary['median_pct']:.2f}")
    top_row[4].metric("Win Rate %", f"{target_summary['win_rate_pct']:.2f}")
    top_row[5].metric("Expectancy %", f"{target_summary['expectancy_pct']:.2f}")

    st.subheader("Target Distribution")
    hist_df = filtered_df[[target_col]].dropna()
    fig = px.histogram(
        hist_df,
        x=target_col,
        nbins=40,
        title=f"Distribution of {target_col}",
        template="plotly_dark",
    )
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Exit Comparison")
    comparison_df = (
        filtered_df[target_metrics]
        .apply(summarize_metric)
        .T.sort_values(["expectancy_pct", "median_pct"], ascending=False)
    )
    st.dataframe(comparison_df, use_container_width=True)

    st.subheader("Feature Scatter")
    scatter_cols = [feature_col, target_col]
    hover_cols = [col for col in ["ticker", "bo_name", "date", "year", "setup_length", "move_up_pct", "setup_drop_pct"] if col in filtered_df.columns]
    scatter_df = filtered_df[unique_columns(scatter_cols + hover_cols)].dropna(subset=[feature_col, target_col])
    scatter_placeholder = st.empty()

    highlighted_years: list[int] = []
    if "year" in scatter_df.columns:
        available_scatter_years = (
            scatter_df["year"].dropna().astype(int).sort_values().unique().tolist()
        )
        highlighted_years = st.multiselect(
            "Highlight years",
            available_scatter_years,
            default=[],
            key="analytics_scatter_highlight_years",
            help="Highlight one or more years and mute the rest of the scatter points.",
        )

    scatter_plot_df = scatter_df.copy()
    if highlighted_years and "year" in scatter_plot_df.columns:
        scatter_plot_df["highlight_group"] = scatter_plot_df["year"].apply(
            lambda year: str(int(year)) if pd.notna(year) and int(year) in highlighted_years else "Other"
        )
        color_order = [str(year) for year in highlighted_years] + ["Other"]
        color_map = {str(year): color for year, color in zip(highlighted_years, px.colors.qualitative.Set2, strict=False)}
        color_map["Other"] = "rgba(148, 163, 184, 0.25)"
        scatter_fig = px.scatter(
            scatter_plot_df,
            x=feature_col,
            y=target_col,
            color="highlight_group",
            category_orders={"highlight_group": color_order},
            color_discrete_map=color_map,
            hover_data=hover_cols,
            opacity=0.85,
            title=f"{feature_col} vs {target_col}",
            template="plotly_dark",
        )
    else:
        scatter_fig = px.scatter(
            scatter_plot_df,
            x=feature_col,
            y=target_col,
            hover_data=hover_cols,
            opacity=0.7,
            title=f"{feature_col} vs {target_col}",
            template="plotly_dark",
        )
    scatter_fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    scatter_placeholder.plotly_chart(scatter_fig, use_container_width=True)

    st.subheader("Pair Plot")
    valid_pair_plot_cols = [col for col in pair_plot_cols if col in filtered_df.columns]
    if len(valid_pair_plot_cols) < 2:
        st.caption("Select at least two columns in `Pair plot columns` to display the pair plot.")
    else:
        if len(valid_pair_plot_cols) > 6:
            st.caption("Using the first 6 selected columns to keep the scatter matrix readable.")
            valid_pair_plot_cols = valid_pair_plot_cols[:6]

        pair_plot_df = filtered_df[unique_columns(valid_pair_plot_cols + [col for col in ["year", "ticker"] if col in filtered_df.columns])].dropna(subset=valid_pair_plot_cols)
        if len(pair_plot_df) > 1200:
            pair_plot_df = pair_plot_df.sample(1200, random_state=42)

        pair_color = "year" if "year" in pair_plot_df.columns else None
        pair_fig = px.scatter_matrix(
            pair_plot_df,
            dimensions=valid_pair_plot_cols,
            color=pair_color,
            hover_data=[col for col in ["ticker", "date"] if col in pair_plot_df.columns],
            template="plotly_dark",
        )
        pair_fig.update_traces(diagonal_visible=False, marker=dict(size=4, opacity=0.55))
        pair_fig.update_layout(height=900, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(pair_fig, use_container_width=True)

    st.subheader("Bucket Analysis")
    bucket_df = bucket_analysis(filtered_df, feature_col, target_col, bucket_count)
    st.dataframe(bucket_df, use_container_width=True)

    st.subheader("Best And Worst Setups")
    display_cols = unique_columns([col for col in ["ticker", "bo_name", "date", feature_col, target_col] if col in filtered_df.columns])
    ranked_df = filtered_df[display_cols].dropna(subset=[target_col]).sort_values(target_col, ascending=False)
    best_col, worst_col = st.columns(2)
    best_col.markdown("**Top 15**")
    best_col.dataframe(ranked_df.head(15), use_container_width=True)
    worst_col.markdown("**Bottom 15**")
    worst_col.dataframe(ranked_df.tail(15).sort_values(target_col), use_container_width=True)


if __name__ == "__main__":
    main()
