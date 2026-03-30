# Breakout Review And Research App

Streamlit app for reviewing, annotating, and analyzing breakout setups with a workflow inspired by Qullamaggie-style momentum breakouts.

The project combines:

- a single-setup review page
- batch metric computation from `input.csv`
- a QQQ breakout overview page
- a strategy analytics page for exploring `output.csv`

## Features

### Setup Review

Review one setup at a time from `data/input/input.csv`.

- previous / next navigation
- row index selection
- candlestick + volume chart
- SMA overlays
- setup annotations for:
  - low
  - cross
  - high
  - setup low
  - SMA20 / SMA50 / SMA100 peak markers
- QQQ overlay and RS line
- logarithmic chart toggle
- batch `Run all setups` export

### QQQ Breakouts

Visualize all breakout dates from `output.csv` on top of a QQQ chart.

- year filter with context window
- stacked markers for multiple breakouts on the same day
- marker color based on `breakout_open_to_sma50_peak_pct`
- QQQ SMA10 / SMA20 / SMA50 overlays

### Strategy Analytics

Explore the computed dataset in `output.csv`.

- date / year / ticker filters
- numeric feature filters
- target metric selector
- histogram of the selected metric
- exit comparison table
- feature scatter
- pair plot
- bucket analysis
- best / worst setups table

## Project Structure

### Core App

- `src/app.py` — main Streamlit setup review page
- `src/compute.py` — setup metrics, anchors, profits, breakout metrics
- `src/plot_setup.py` — Plotly chart rendering
- `src/data.py` — OHLCV loading

### Streamlit Pages

- `src/pages/2_QQQ_Breakouts.py` — QQQ breakout overview
- `src/pages/3_Strategy_Analytics.py` — dataset analytics dashboard

### Data

- `data/input/input.csv` — setup review input file
- `data/warehouse/processed/output.csv` — batch-computed metrics
- `data/stooq/` — raw Stooq source data
- `data/warehouse/clean/` — cleaned parquet files

### Research

- `notebooks/output_analysis.ipynb` — notebook-based analysis

## Getting Started

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2. Run the app

```bash
streamlit run src/app.py
```

Streamlit will automatically expose the additional pages in the sidebar.

## Typical Workflow

### Review Existing Setups

1. Put setups into `data/input/input.csv`
2. Open the main Streamlit page
3. Review setups visually
4. Run batch compute
5. Inspect `data/warehouse/processed/output.csv`
6. Explore the results on the analytics page

### Analyze Results

1. Run `Run all setups`
2. Open `Strategy Analytics`
3. Compare exit metrics
4. Use scatter plots, pair plots, and bucket analysis to explore relationships
5. Open `QQQ Breakouts` to inspect breakout clustering against QQQ context

## Current Metrics

Examples of the current metrics:

- setup structure:
  - `setup_length`
  - `move_up_pct`
  - `setup_drop_pct`
  - low / high anchor days and prices
- market-relative context:
  - `qqq_rs_slope_10`
  - `qqq_rs_slope_20`
  - `qqq_rs_slope_30`
- prior gains:
  - `gain_1m_pct`
  - `gain_3m_pct`
  - `gain_6m_pct`
- exit metrics:
  - `sma10_profit_pct`
  - `sma20_profit_pct`
  - staged partial / final profit metrics
- breakout opportunity metrics:
  - `breakout_open_to_sma20_peak_pct`
  - `breakout_open_to_sma50_peak_pct`
  - `breakout_open_to_sma100_peak_pct`

## Notes And Caveats

This is a research tool, not a production trading system.

Important caveats:

- the dataset may still be curated and therefore selection-biased
- some metrics are opportunity metrics, not always executable exits
- current anchor logic is an approximation of QM-style visual structure
- volume dry-up / breakout volume logic is still limited
- market regime filters are still basic

Treat the outputs as research inputs, not final truth.

## Recommended Next Steps

Highest-impact improvements:

1. breakout volume expansion
2. base volume dry-up
3. tighter base / volatility-contraction metrics
4. stronger RS quality measures
5. market regime filters
6. clearer separation of:
   - executable exits
   - opportunity / run-up metrics

## Development

Useful syntax checks:

```bash
python3 -m py_compile src/app.py
python3 -m py_compile src/compute.py
python3 -m py_compile src/plot_setup.py
python3 -m py_compile src/pages/2_QQQ_Breakouts.py
python3 -m py_compile src/pages/3_Strategy_Analytics.py
```

## Summary

This repo is best thought of as a breakout research workspace:

- review setups visually
- export structured metrics
- analyze features and exits
- compare breakouts to QQQ context
- iterate toward a cleaner breakout definition
