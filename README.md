# TCN Trader

A deep learning research system that forecasts next-day market direction with a Temporal Convolutional Network, sizes positions with a volatility-scaled risk map, and tracks its own live paper-trading performance every day.

## Goal

Build a trading model the honest way: train on 5-10 years of daily data, test it on periods it has never seen, then prove (or disprove) it on live data before any real money is involved. The question this project answers:

> **Can this model beat simply holding the market, after costs, on data it didn't train on?**

If the honest answer is "no," that is still a successful data science project. See [ROADMAP.md](ROADMAP.md) for the plan.

## How it works

```
64 days x 12 features  ->  TCN  ->  global avg pool  ->  sigmoid head  ->  calibration  ->  p_hat
p_hat  ->  w = clip( sigma* / sigma_hat * g_tau(signal), w_min, w_max )  ->  position
```

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Works on CPU. Uses an NVIDIA GPU (CUDA) or Apple Silicon (MPS) automatically if available. For an NVIDIA GPU, install the CUDA build of PyTorch from pytorch.org first, then the rest of the requirements.

## Commands

| Command | What it does |
|---|---|
All commands use real market data (Yahoo Finance, adjusted for splits and dividends).

| Command | What it does |
|---|---|
| `python run.py backtest` | Walk-forward test on real tickers (2015 onward), retraining monthly on a rolling 10-year window, exactly like the live plan. |
| `python run.py backtest --freq Y` | Same, but retrains yearly. About 12x faster; good for quick experiments. |
| `python run.py backtest --placebo` | **Leakage check.** Trains on shuffled labels and tests on the real ones. A model that learned nothing real must show no edge. If it does, something is leaking. Run it after every significant change. |
| `python run.py signal` | Trains on the latest 10 years and prints a suggested position for the next trading day. |
| `python run.py vol` | **Insight engine.** Walk-forward test of next-5-day volatility forecasts: EWMA (what the risk map uses), recalibrated EWMA, HAR, gradient boosting. Includes a vol-targeting strategy test. `--placebo` shuffles training targets (skill must vanish). |
| `python run.py insights` | **Insight engine.** Today's market regime (Calm / Normal / Elevated / Stressed, from SPY), volatility forecasts and their percentile, and what historically followed this regime for each ticker, with sample sizes. |

Useful flags: `--tickers SPY QQQ XIU.TO`, `--epochs 15`, `--start-year 2020 --end-year 2022` (faster), `--refresh` (re-download data), `--out reports/my-run` (output folder).

A full monthly backtest retrains ~140 times. That's hours on a CPU but much faster on a GPU. Use `--freq Y` while experimenting.

### Running in the cloud (GitHub Actions)

The **Real-data research runs** workflow runs jobs on GitHub's servers and commits each report to `reports/`. Start it from the repo's Actions tab ("Run workflow", pick a suite), or push a commit with a tag in the message: `[backtest]` (TCN backtest + placebo) or `[insights]` (volatility forecasts + placebo + market insights). Yearly mode takes minutes; monthly mode is better on the laptop GPU.

## Files

| File | Job |
|---|---|
| `config.py` | Every setting. Change things here. |
| `data.py` | Downloads, caches and quality-checks daily data (Yahoo Finance). Refreshes the cache automatically when it's behind. |
| `features.py` | The 12 features, the label, 64-day windows, the scaler. |
| `model.py` | TCN, training with early stopping, Platt calibration, logistic baseline. |
| `risk.py` | The deadbanded volatility-scaled risk map. |
| `backtest.py` | Walk-forward loop, costs, metrics, bootstrap test, charts. |
| `insights.py` | Insight engine: volatility forecasting (EWMA / HAR / boosting) and walk-forward market regimes. |
| `dashboard_export.py` | Turns `reports/` and `ROADMAP.md` into the dashboard's data files. |
| `run.py` | Command line. |

## How it avoids fooling you

- **No look-ahead.** Every feature on day t uses data up to day t's close; the label is day t+1. Convolutions are causal (they only look backward).
- **Walk-forward.** For each test month, the model is trained only on the 10 years before it, with a validation slice at the end for early stopping, calibration and signal scaling, plus a 1-day embargo.
- **Scaler fit on training data only.**
- **Costs included** (`cost_bps`, default 5 bps per 100% of position traded).
- **Baselines.** The TCN must beat: buy & hold, a vol-scaled always-long position (the risk map with no prediction), and a logistic regression through the same risk map. If it can't beat the logistic, the deep learning isn't adding anything.
- **Bootstrap test.** Re-draws history 2,000 times to see how often TCN would *not* beat the vol-scaled baseline. Above ~20% means you can't tell it from luck.
- **Placebo run.** Same pipeline, shuffled training labels, real test labels. Must show no edge.
- **Data quality checks.** Warns about non-positive prices, impossible bars, >25% daily moves (bad split adjustments), long gaps, and short histories.

## Outputs (in `results/`, or the `--out` folder)

- `summary.md` - the full report in one readable page: performance, prediction quality, Sharpe by year, significance, charts, and the exact config used
- `performance.csv` - CAGR, volatility, Sharpe, max drawdown, exposure, turnover
- `yearly_sharpe.csv` - Sharpe ratio per strategy per year (does the edge hold up every year, or come from one lucky year?)
- `prediction_quality.csv` - AUC, accuracy, Brier score, log loss vs. the base rate
- `equity.png` - growth of $1 for every strategy
- `calibration.png` - predicted vs. actual up-day rate (dots on the diagonal = honest probabilities)
- `predictions.csv` - every out-of-sample prediction, for your own analysis

## One deviation from the original diagram

Calibrated probabilities on real markets sit very close to 50% (often 0.47-0.53). Fed straight into the deadband, the strategy would almost never trade. So the raw signal `2p - 1` is first divided by `signal_sd` x its standard deviation **on the validation set** (never the test set), then clipped to [-1, 1]. `tau` is applied to that rescaled signal. The divisor has a floor (`min_signal_scale`) so a model whose predictions barely move can't have its tiny wiggles amplified into full-conviction trades.

## Research rules

- Tune `tau`, `target_vol`, `signal_sd` and model settings **on validation folds only**. Every knob tuned on test periods makes the backtest more optimistic and less true.
- Every new feature or change must beat the version without it, or it gets dropped.
- Paper trade for at least 2-3 months before any real money.

Not financial advice. Most strategies that look good in backtests fail live.
