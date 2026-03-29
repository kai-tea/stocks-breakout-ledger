from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def _safe_timestamp(value) -> pd.Timestamp | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return pd.Timestamp(value)


def _safe_float(value) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return float(value)


BREAKOUT_SMA_STYLES = {
    20: {"color": "#22c55e", "label": "SMA20"},
    50: {"color": "#fb7185", "label": "SMA50"},
    100: {"color": "#f59e0b", "label": "SMA100"},
}


def plot_setup_chart(
    df: pd.DataFrame,
    result: dict,
    benchmark_df: pd.DataFrame | None = None,
    benchmark_name: str = "QQQ",
    lookback_bars: int = 150,
    forward_bars: int = 20,
    show_until_bearish_sma100_cross: bool = False,
    use_log_scale: bool = False,
    show_volume: bool = True,
    show_sma_10: bool = True,
    show_sma_20: bool = True,
    show_sma_50: bool = True,
    show_annotations: bool = True,
) -> go.Figure:
    target_day = _safe_timestamp(result.get("target_day") or result.get("date"))
    if target_day is None:
        raise ValueError("Missing target_day for plotting.")

    if target_day not in df.index:
        raise KeyError(f"Target date {target_day} not found in index")

    target_pos = df.index.get_loc(target_day)
    start_pos = max(0, target_pos - lookback_bars + 1)
    end_pos = min(len(df) - 1, target_pos + forward_bars)

    if show_until_bearish_sma100_cross:
        sma100_series = df["close"].rolling(100).mean()
        future_df = df.loc[df.index > target_day].copy()
        future_df["sma100"] = sma100_series.loc[future_df.index]
        future_df["oc_low"] = future_df[["open", "close"]].min(axis=1)
        bearish_cross_mask = future_df["oc_low"] < future_df["sma100"]

        if bearish_cross_mask.any():
            bearish_cross_day = future_df.index[bearish_cross_mask][0]
            end_pos = df.index.get_loc(bearish_cross_day)
        else:
            end_pos = len(df) - 1

    plot_df = df.iloc[start_pos : end_pos + 1]
    plot_x = plot_df.index.strftime("%Y-%m-%d")
    sma10_series = df["close"].rolling(10).mean()
    sma20_series = df["close"].rolling(20).mean()
    benchmark_plot = None
    rs_plot = None
    moveup_low_day = _safe_timestamp(result.get("moveup_low_day"))
    moveup_low_price = _safe_float(result.get("moveup_low_price"))

    if benchmark_df is not None and not benchmark_df.empty and "close" in benchmark_df.columns:
        benchmark_slice = benchmark_df.reindex(plot_df.index)
        overlap = benchmark_slice["close"].notna() & plot_df["close"].notna()
        if overlap.any():
            base_day = plot_df.index[overlap][0]
            if (
                moveup_low_day is not None
                and moveup_low_day in plot_df.index
                and pd.notna(benchmark_slice.at[moveup_low_day, "close"])
                and pd.notna(plot_df.at[moveup_low_day, "close"])
            ):
                base_day = moveup_low_day

            benchmark_base = float(benchmark_slice.at[base_day, "close"])
            stock_base = float(plot_df.at[base_day, "close"])
            if benchmark_base > 0:
                benchmark_anchor_price = moveup_low_price if moveup_low_price is not None else stock_base
                benchmark_plot = (benchmark_slice["close"] / benchmark_base) * benchmark_anchor_price
                if stock_base > 0:
                    relative_ratio = (plot_df["close"] / benchmark_slice["close"]).replace(
                        [float("inf"), float("-inf")], pd.NA
                    )
                    base_ratio = stock_base / benchmark_base
                    if base_ratio > 0:
                        rs_plot = ((relative_ratio / base_ratio) - 1.0) * 100.0

    def x_value(day: pd.Timestamp | None) -> str | None:
        if day is None:
            return None
        return pd.Timestamp(day).strftime("%Y-%m-%d")

    rows = 2 if show_volume else 1
    row_heights = [0.75, 0.25] if show_volume else [1.0]
    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=row_heights,
        specs=[[{"secondary_y": True}]] + ([[{"secondary_y": False}]] if show_volume else []),
    )

    fig.add_trace(
        go.Candlestick(
            x=plot_x,
            open=plot_df["open"],
            high=plot_df["high"],
            low=plot_df["low"],
            close=plot_df["close"],
            name="Price",
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

    if show_sma_10:
        fig.add_trace(
            go.Scatter(
                x=plot_x,
                y=plot_df["close"].rolling(10).mean(),
                mode="lines",
                name="SMA 10",
                line=dict(color="#55cfe0", width=0.6),
            ),
            row=1,
            col=1,
        )

    if show_sma_20:
        fig.add_trace(
            go.Scatter(
                x=plot_x,
                y=plot_df["close"].rolling(20).mean(),
                mode="lines",
                name="SMA 20",
                line=dict(color="#b56bff", width=0.6),
            ),
            row=1,
            col=1,
        )

    if show_sma_50:
        fig.add_trace(
            go.Scatter(
                x=plot_x,
                y=plot_df["close"].rolling(50).mean(),
                mode="lines",
                name="SMA 50",
                line=dict(color="rgba(220, 38, 38, 0.50)", width=0.6),
            ),
            row=1,
            col=1,
        )

    if benchmark_plot is not None:
        fig.add_trace(
            go.Scatter(
                x=plot_x,
                y=benchmark_plot,
                mode="lines",
                name=benchmark_name,
                line=dict(color="rgba(250, 204, 21, 0.90)", width=1.1),
                hovertemplate=f"{benchmark_name} (scaled): "+"%{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )

    if rs_plot is not None:
        fig.add_trace(
            go.Scatter(
                x=plot_x,
                y=rs_plot,
                mode="lines",
                name="RS vs QQQ",
                line=dict(color="rgba(34, 197, 94, 0.95)", width=1.0),
                hovertemplate="RS vs QQQ: %{y:.2f}%<extra></extra>",
            ),
            row=1,
            col=1,
            secondary_y=True,
        )

    if show_volume and "volume" in plot_df.columns:
        volume_colors = [
            "#18c2a4" if close_ >= open_ else "#ff365a"
            for open_, close_ in zip(plot_df["open"], plot_df["close"])
        ]
        fig.add_trace(
            go.Bar(
                x=plot_x,
                y=plot_df["volume"],
                name="Volume",
                marker_color=volume_colors,
                opacity=0.6,
            ),
            row=2,
            col=1,
        )

    if show_annotations:
        moveup_low_day = _safe_timestamp(result.get("moveup_low_day"))
        moveup_low_price = _safe_float(result.get("moveup_low_price"))
        moveup_low_cross_day = _safe_timestamp(result.get("moveup_low_cross_day"))
        prebase_high_day = _safe_timestamp(result.get("prebase_high_day"))
        prebase_high_price = _safe_float(result.get("prebase_high_price"))
        setup_low_day = _safe_timestamp(result.get("setup_low_day"))
        setup_low_price = _safe_float(result.get("setup_low_price"))
        moveup_low_cross_price = None
        breakout_peaks = {
            sma_window: {
                "day": _safe_timestamp(result.get(f"breakout_open_to_sma{sma_window}_peak_day")),
                "price": _safe_float(result.get(f"breakout_open_to_sma{sma_window}_peak_price")),
            }
            for sma_window in BREAKOUT_SMA_STYLES
        }

        if moveup_low_cross_day is not None and moveup_low_cross_day in df.index:
            sma10_at_cross = sma10_series.loc[moveup_low_cross_day]
            sma20_at_cross = sma20_series.loc[moveup_low_cross_day]
            if not pd.isna(sma10_at_cross) and not pd.isna(sma20_at_cross):
                moveup_low_cross_price = float((sma10_at_cross + sma20_at_cross) / 2)
            else:
                moveup_low_cross_price = float(df.at[moveup_low_cross_day, "close"])

        fig.add_vline(
            x=x_value(target_day),
            line_width=1,
            line_dash="dash",
            line_color="gray",
        )

        if prebase_high_day is not None:
            fig.add_vrect(
                x0=x_value(prebase_high_day),
                x1=x_value(target_day),
                fillcolor="rgba(0, 0, 0, 0.5)",
                line_width=0,
                layer="below",
                row=1,
                col=1,
            )

        if moveup_low_day is not None and moveup_low_price is not None:
            fig.add_trace(
                go.Scatter(
                    x=[x_value(moveup_low_day)],
                    y=[moveup_low_price],
                    mode="markers+text",
                    text=["Low"],
                    textposition="bottom center",
                    marker=dict(size=8, color="green"),
                    name="Low",
                ),
                row=1,
                col=1,
            )

        if moveup_low_cross_day is not None and moveup_low_cross_price is not None:
            fig.add_trace(
                go.Scatter(
                    x=[x_value(moveup_low_cross_day)],
                    y=[moveup_low_cross_price],
                    mode="markers+text",
                    text=["Cross"],
                    textposition="top left",
                    marker=dict(size=7, color="#60a5fa", symbol="diamond"),
                    name="Cross",
                ),
                row=1,
                col=1,
            )

        if prebase_high_day is not None and prebase_high_price is not None:
            fig.add_trace(
                go.Scatter(
                    x=[x_value(prebase_high_day)],
                    y=[prebase_high_price],
                    mode="markers+text",
                    text=["High"],
                    textposition="top center",
                    marker=dict(size=8, color="orange"),
                    name="High",
                ),
                row=1,
                col=1,
            )

        if setup_low_day is not None and setup_low_price is not None:
            fig.add_trace(
                go.Scatter(
                    x=[x_value(setup_low_day)],
                    y=[setup_low_price],
                    mode="markers+text",
                    text=["Setup Low"],
                    textposition="bottom right",
                    marker=dict(size=7, color="#facc15"),
                    name="Setup Low",
                ),
                row=1,
                col=1,
            )

        for sma_window, peak_data in breakout_peaks.items():
            breakout_peak_day = peak_data["day"]
            breakout_peak_price = peak_data["price"]
            style = BREAKOUT_SMA_STYLES[sma_window]

            if breakout_peak_day is not None and breakout_peak_price is not None:
                fig.add_trace(
                    go.Scatter(
                        x=[x_value(breakout_peak_day)],
                        y=[breakout_peak_price],
                        mode="markers+text",
                        text=[f"{style['label']} Peak"],
                        textposition="top right",
                        marker=dict(size=8, color=style["color"], symbol="star"),
                        name=f"{style['label']} Peak",
                    ),
                    row=1,
                    col=1,
                )

        if (
            moveup_low_day is not None
            and moveup_low_price is not None
            and prebase_high_day is not None
            and prebase_high_price is not None
        ):
            fig.add_trace(
                go.Scatter(
                    x=[x_value(moveup_low_day), x_value(prebase_high_day)],
                    y=[moveup_low_price, prebase_high_price],
                    mode="lines",
                    line=dict(color="green", width=1),
                    name="Move-up Line",
                ),
                row=1,
                col=1,
            )

    fig.update_layout(
        height=720,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_rangeslider_visible=False,
        xaxis_rangebreaks=_build_rangebreaks(plot_df.index),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )

    # soften gridlines (scaling reference bars)
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255, 255, 255, 0.04)", gridwidth=0.5)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255, 255, 255, 0.04)", gridwidth=0.5)
    fig.update_yaxes(type="log" if use_log_scale else "linear", row=1, col=1)
    if rs_plot is not None:
        fig.update_yaxes(
            title_text="Comparison %",
            showgrid=False,
            zeroline=False,
            row=1,
            col=1,
            secondary_y=True,
        )

    return fig


def _build_rangebreaks(index: pd.Index) -> list[dict]:
    if index.empty:
        return [dict(bounds=["sat", "mon"])]

    dates = pd.to_datetime(index).normalize()
    start = dates.min()
    end = dates.max()
    if start is pd.NaT or end is pd.NaT:
        return [dict(bounds=["sat", "mon"])]

    business_days = pd.bdate_range(start=start, end=end)
    missing = business_days.difference(dates)

    rangebreaks = [dict(bounds=["sat", "mon"])]
    if len(missing) > 0:
        rangebreaks.append(dict(values=list(missing)))
    return rangebreaks
