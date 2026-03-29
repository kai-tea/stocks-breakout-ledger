from __future__ import annotations

from datetime import date
from time import perf_counter

import pandas as pd
import streamlit as st

import config
from detect_candidates import CandidateRuleConfig, detect_candidates, list_available_tickers


INPUT_FILE = config.INPUT_FILE
CANDIDATE_OUTPUT_FILE = getattr(
    config,
    "CANDIDATE_OUTPUT_FILE",
    config.PROCESSED_DIR / "candidate_setups.csv",
)


@st.cache_data(show_spinner=False)
def load_input_tickers() -> list[str]:
    if not INPUT_FILE.exists():
        return []

    df = pd.read_csv(INPUT_FILE)
    df.columns = [c.strip().lower() for c in df.columns]
    if "ticker" not in df.columns:
        return []

    return sorted(df["ticker"].dropna().astype(str).str.lower().unique().tolist())


@st.cache_data(show_spinner=False)
def load_available_tickers() -> list[str]:
    return list_available_tickers()


def _parse_manual_tickers(value: str) -> list[str]:
    parts = [part.strip().lower() for part in value.replace("\n", ",").split(",")]
    return sorted({part for part in parts if part})


def main() -> None:
    st.set_page_config(page_title="Candidate Detector", layout="wide")
    st.title("Candidate Detector")
    st.caption(
        "Conservative rule-based detector for plausible breakout candidates. "
        "The goal is to build a cleaner setup universe before studying winners and losers."
    )

    input_tickers = load_input_tickers()
    available_tickers = load_available_tickers()

    st.sidebar.header("Ticker Universe")
    ticker_source = st.sidebar.selectbox(
        "Ticker source",
        ["Input CSV", "Manual", "All available"],
        help="Start conservative. Input CSV or a manual list is usually easier to debug than a full universe scan.",
    )

    tickers: list[str]
    if ticker_source == "Input CSV":
        tickers = input_tickers
        st.sidebar.caption(f"{len(tickers)} tickers from `{INPUT_FILE.name}`")
    elif ticker_source == "Manual":
        manual_value = st.sidebar.text_area(
            "Manual tickers",
            value="",
            height=120,
            help="Comma- or newline-separated tickers, e.g. `nvda, amd, smci`.",
        )
        tickers = _parse_manual_tickers(manual_value)
        st.sidebar.caption(f"{len(tickers)} manual tickers")
    else:
        max_tickers = st.sidebar.number_input(
            "Max tickers",
            min_value=25,
            max_value=max(len(available_tickers), 25),
            value=min(250, max(len(available_tickers), 25)),
            step=25,
        )
        tickers = available_tickers[: int(max_tickers)]
        st.sidebar.caption(f"{len(tickers)} of {len(available_tickers)} available tickers")

    st.sidebar.header("Date Range")
    start_value = st.sidebar.date_input("Start date", value=date(2018, 1, 1), key="candidate_start_date")
    end_value = st.sidebar.date_input("End date", value=date(2025, 12, 31), key="candidate_end_date")

    st.sidebar.header("Core Rules")
    min_price = st.sidebar.slider("Min price", 1.0, 50.0, 5.0, 0.5)
    min_adr_pct = st.sidebar.slider("Min ADR %", 1.0, 12.0, 4.0, 0.25)
    min_avg_dollar_volume = st.sidebar.slider(
        "Min avg $ volume (20d, millions)",
        1,
        100,
        20,
        1,
    )
    min_gain_3m_pct = st.sidebar.slider("Min 3M gain %", 5.0, 150.0, 25.0, 5.0)
    min_move_up_pct = st.sidebar.slider("Min move-up %", 5.0, 150.0, 20.0, 5.0)
    max_setup_drop_pct = st.sidebar.slider("Max setup drop %", 5.0, 50.0, 30.0, 1.0)
    setup_length_range = st.sidebar.slider("Setup length bars", 1, 60, (5, 30))

    st.sidebar.header("Soft Rules")
    breakout_proximity_pct = st.sidebar.slider("Max distance from pivot %", 0.5, 10.0, 3.0, 0.5)
    min_breakout_margin_pct = st.sidebar.slider("Min breakout margin %", -5.0, 10.0, -1.0, 0.5)
    min_rs_slope_20 = st.sidebar.slider("Min RS slope 20", -0.02, 0.02, 0.0, 0.001, format="%.3f")
    min_sma50_slope_pct = st.sidebar.slider("Min SMA50 slope % (5 bars)", -5.0, 5.0, 0.0, 0.25)

    config = CandidateRuleConfig(
        min_price=min_price,
        min_adr_pct=min_adr_pct,
        min_avg_dollar_volume=float(min_avg_dollar_volume) * 1_000_000.0,
        min_gain_3m_pct=min_gain_3m_pct,
        min_move_up_pct=min_move_up_pct,
        max_setup_drop_pct=max_setup_drop_pct,
        min_setup_length=setup_length_range[0],
        max_setup_length=setup_length_range[1],
        breakout_proximity_pct=breakout_proximity_pct,
        min_breakout_margin_pct=min_breakout_margin_pct,
        min_rs_slope_20=min_rs_slope_20,
        min_sma50_slope_pct=min_sma50_slope_pct,
    )

    if "candidate_detector_results" not in st.session_state:
        st.session_state.candidate_detector_results = None
    if "candidate_detector_errors" not in st.session_state:
        st.session_state.candidate_detector_errors = None

    run_detector = st.sidebar.button("Run detector", type="primary")
    if run_detector:
        if not tickers:
            st.warning("No tickers selected for the detector.")
        elif pd.Timestamp(start_value) > pd.Timestamp(end_value):
            st.warning("Start date must be before end date.")
        else:
            progress_bar = st.progress(0.0)
            status_placeholder = st.empty()
            started_at = perf_counter()

            def update_progress(current: int, total: int, current_ticker: str) -> None:
                progress_value = current / max(total, 1)
                progress_bar.progress(progress_value)

                elapsed = perf_counter() - started_at
                avg_seconds = elapsed / max(current, 1)
                remaining_seconds = max(total - current, 0) * avg_seconds
                eta_minutes = int(remaining_seconds // 60)
                eta_seconds = int(remaining_seconds % 60)

                status_placeholder.caption(
                    f"Scanning {current_ticker} • {current}/{total} tickers • "
                    f"ETA {eta_minutes:02d}:{eta_seconds:02d}"
                )

            with st.spinner(f"Scanning {len(tickers)} tickers for candidate setups..."):
                candidates_df, errors_df = detect_candidates(
                    tickers=tickers,
                    start_date=pd.Timestamp(start_value),
                    end_date=pd.Timestamp(end_value),
                    config=config,
                    progress_callback=update_progress,
                )
            progress_bar.progress(1.0)
            elapsed = perf_counter() - started_at
            elapsed_minutes = int(elapsed // 60)
            elapsed_seconds = int(elapsed % 60)
            status_placeholder.caption(
                f"Finished scanning {len(tickers)} tickers in "
                f"{elapsed_minutes:02d}:{elapsed_seconds:02d}"
            )
            st.session_state.candidate_detector_results = candidates_df
            st.session_state.candidate_detector_errors = errors_df

    candidates_df = st.session_state.candidate_detector_results
    errors_df = st.session_state.candidate_detector_errors

    if candidates_df is None:
        st.info("Run the detector to build a candidate universe.")
        st.markdown(
            "- `valid`: passed all hard rules and most soft rules\n"
            "- `borderline`: passed the hard rules but only some soft rules\n"
            "- `invalid`: structurally informative, but not something you’d want in the candidate set yet"
        )
        return

    if candidates_df.empty:
        st.warning("The detector ran but found no candidate rows in the selected window.")
        if errors_df is not None and not errors_df.empty:
            st.subheader("Errors")
            st.dataframe(errors_df, use_container_width=True)
        return

    summary_counts = (
        candidates_df["candidate_label"]
        .value_counts(dropna=False)
        .reindex(["valid", "borderline", "invalid"], fill_value=0)
    )
    summary_cols = st.columns(4)
    summary_cols[0].metric("Rows", f"{len(candidates_df):,}")
    summary_cols[1].metric("Valid", f"{summary_counts['valid']:,}")
    summary_cols[2].metric("Borderline", f"{summary_counts['borderline']:,}")
    summary_cols[3].metric("Invalid", f"{summary_counts['invalid']:,}")

    st.subheader("Candidate Quality")
    quality_fig = (
        candidates_df.groupby("candidate_label", observed=False)["candidate_score"]
        .agg(["count", "mean"])
        .reset_index()
    )
    st.dataframe(quality_fig, use_container_width=True)

    visible_labels = st.multiselect(
        "Visible labels",
        ["valid", "borderline", "invalid"],
        default=["valid", "borderline"],
        help="Keep invalid rows hidden by default so the review list stays cleaner.",
    )
    visible_df = candidates_df[candidates_df["candidate_label"].isin(visible_labels)].copy()

    st.subheader("Candidates")
    st.dataframe(
        visible_df,
        use_container_width=True,
        hide_index=True,
    )

    export_cols = [
        "ticker",
        "date",
        "candidate_label",
        "candidate_score",
        "failed_rules",
        "setup_length",
        "move_up_pct",
        "setup_drop_pct",
        "adr_pct",
        "gain_3m_pct",
        "qqq_rs_slope_20",
        "breakout_margin_pct",
        "breakout_distance_pct",
        "avg_dollar_volume_20",
    ]
    export_df = visible_df[[col for col in export_cols if col in visible_df.columns]].copy()

    save_col, download_col = st.columns(2)
    if save_col.button("Save visible candidates"):
        export_df.to_csv(CANDIDATE_OUTPUT_FILE, index=False)
        st.success(f"Saved {len(export_df)} rows to `{CANDIDATE_OUTPUT_FILE}`")

    download_col.download_button(
        "Download visible candidates",
        export_df.to_csv(index=False).encode("utf-8"),
        file_name="candidate_setups.csv",
        mime="text/csv",
    )

    if errors_df is not None and not errors_df.empty:
        st.subheader("Errors")
        st.dataframe(errors_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
