# Roadmap

The single source of truth for where this project is going. Update the checkboxes as work lands.

## Operating model (the target system)

| When | What | Where |
|---|---|---|
| Every trading day, after the close | Pull new daily bars, predict next day, log paper trades **before** the next open, update the ledger | GitHub Actions (cloud, free) |
| Monthly | Retrain on the most recent 10 years (rolling window) | Gaming laptop GPU |
| After each retrain | **Champion vs. challenger:** the new model replaces the current one only if it does at least as well on recent held-out data | Gaming laptop |
| Any time calibration drifts badly | Early retrain (e.g. model says 60% up, reality is 45% over a meaningful sample) | Gaming laptop |
| Weekly | Review of the ledger: performance vs. baselines, calibration, anything odd | Claude (chat) |

Why monthly, not daily: one extra day barely changes a 10-year training set, retraining adds training-randomness noise to positions (extra trades and fees), and a model that changes every day can't be evaluated. The model still *uses* new data daily; only its weights update monthly.

## Phase 1 - Foundation

- [x] TCN + calibrated sigmoid head + deadbanded volatility-scaled risk map
- [x] Walk-forward backtest with costs, baselines (buy & hold, vol-scaled long, logistic), bootstrap significance test
- [x] Monthly retraining on a rolling 10-year window, matching the live plan
- [x] Real data only: data quality checks, auto-refreshing cache, placebo (shuffled-label) leakage check
- [x] GitHub Actions workflow: real-data backtest + placebo in the cloud, reports committed to `reports/`
- [x] First real-data backtest (yearly mode, cloud) - review report
- [x] Project dashboard (claude.ai) fed by `dashboard_export.py`
- [x] Report AUC averaged within each retrain period, not only pooled (pooling mixes period-level base-rate shifts)
- [ ] Set up the gaming laptop (CUDA PyTorch), run the full monthly backtest
- [ ] Decide the ticker list (5-10 liquid ETFs) - currently SPY, QQQ, XIU.TO, XEQT.TO
- [ ] Save trained models with version + training-date metadata (`models/`)
- [ ] Champion vs. challenger promotion logic
- [ ] Daily job: data update -> prediction -> append to `ledger/predictions.csv` (prediction made before the open, timestamped)
- [ ] Ledger scorer: fills in realized returns the next day, tracks paper P&L vs. buy & hold and vol-scaled long
- [ ] GitHub Actions workflow for the daily job (inference only; model weights come from the latest monthly retrain)
- [ ] Monthly retrain script for the laptop (scheduled), including calibration-drift check

## Phase 2 - Insight engine (now)

Goal: move from "guess tomorrow's direction" to "tell me non-obvious, evidence-backed things about the market." Every insight states how many past cases it rests on. Same rules: walk-forward, real data only, placebo where a model is fit.

- [ ] Volatility forecasting: next-5-day realized vol from HAR (classic statistical model) and gradient boosting, vs. the EWMA estimate the risk map uses today; walk-forward, placebo, and a vol-targeting strategy test
- [ ] Market regime detection: walk-forward Gaussian mixture on SPY's market state (volatility, trend, drawdown), 4 regimes, what historically followed each
- [ ] Daily insight output: current regime, vol forecast + percentile, regime-conditional downside per ticker
- [ ] Dashboard "Market insights" section
- [ ] Plug the best vol forecast into the risk map if it beats EWMA out-of-sample
- [ ] Range forecasts: quantile regression for 5-day return ranges (e.g. 10% chance of falling more than X)
- [ ] Unusual-day detection: how unlike history today's cross-asset picture is, plus the most similar past days
- [ ] Cross-asset signals: bonds (TLT), gold, US dollar, oil; flag when usual relationships break
- [ ] Event studies: market behaviour around FOMC, CPI, jobs reports (later: earnings)
- [ ] Explainability: which inputs the models lean on, and when
- [ ] Experiment registry: log every experiment (including failures) so multiple testing can be accounted for (deflated Sharpe)

## Phase 3 - Calendar and macro features

Each addition must improve out-of-sample results vs. the version without it, or it's dropped.

- [ ] Calendar events known in advance: days to next FOMC decision, CPI release, jobs report, earnings-season flag
- [ ] Macro data from FRED: interest rates, yield curve (10y-2y), VIX
- [ ] Market-wide context: SPY returns as a feature for every ticker
- [ ] Ablation table: performance with / without each feature group

## Phase 4 - Research layer

- [ ] Weekly research note (Claude): earnings, news, trends for the tracked tickers
- [ ] **"Claude analyst" paper portfolio**: weekly picks from the research note, logged before results, tracked separately
- [ ] Dashboard comparing three tracks: model vs. Claude analyst vs. index
- Rule: Claude's judgment can only be evaluated going forward. Claude already knows past market history, so any backtest of its research would be leakage.

## Phase 5 - Optional: individual stocks

- [ ] Point-in-time fundamentals from SEC EDGAR (revenue, EPS, surprises), stored by **release date**, not fiscal period end
- [ ] Earnings-date features and post-earnings drift
- [ ] Mega-cap tech universe as a separate run (AAPL, MSFT, NVDA, AMD, AMZN, META, GOOGL, NFLX + 2015-era laggards INTC, IBM, CSCO, ORCL to limit hindsight bias), judged vs equal-weight buy & hold of the same basket; relative-ranking version
- [ ] Only if Phases 1-4 show something real

## Go / no-go for real money

All must be true before considering real positions (small size only):

1. At least 3 months of live paper trading
2. Beats both buy & hold and vol-scaled long on Sharpe, after realistic costs, live
3. Calibration holds up live (reliability plot near the diagonal)
4. Backtest and live results roughly agree (no big gap = no hidden leakage)

## Decision log

| Date | Decision |
|---|---|
| 2026-11-02 | Architecture: 64x12 window -> TCN -> avg pool -> calibrated sigmoid -> deadbanded vol-scaled risk map |
| 2026-11-02 | Signal rescaled by validation std before the deadband (calibrated probabilities sit near 0.5) |
| 2026-11-02 | Retrain monthly on a rolling 10-year window; champion vs. challenger promotion |
| 2026-11-02 | Long-or-flat (no shorting), no leverage, 5 bps cost assumption |
| 2026-11-02 | Phased research plan: price-only -> calendar/macro -> research layer -> optional individual stocks |
| 2026-11-02 | Real market data only; synthetic tests removed, replaced by a real-data placebo (shuffled training labels) check |
| 2026-11-02 | Floor on signal scale (`min_signal_scale` = 0.02) so near-constant predictions aren't amplified into trades |
| 2026-11-02 | First real-data backtest (SPY, QQQ, XIU.TO; 2015-2026; yearly retrain): price-only TCN shows no edge (Sharpe 0.56 vs vol-scaled 0.84; per-year AUC ~0.50). Placebo passed. Baseline established; next work aims to beat it |
| 2026-11-02 | Headline AUC is now the average within each retrain period (first run: 0.502 per period vs 0.481 pooled; pooling mixed between-period base-rate shifts into the number) |
| 2026-11-02 | Added XEQT.TO to the universe (history from Aug 2019). Re-ran backtest + placebo so results stay comparable |
| 2026-11-02 | New Phase 2 "Insight engine": refocus from next-day direction (no edge found) to evidence-backed insights; start with volatility forecasting + regime detection. Later phases renumbered 3-5 |
| 2026-11-02 | First vol-forecast run: next-week volatility IS forecastable (R2 avg per year: EWMA 0.14, recalibrated EWMA 0.20, HAR 0.23, gradient boosting 0.27; boosting beat raw EWMA in 10 of 12 years). Placebo passed (fitted models' skill vanished). Fixes before trusting variance-space results: floor range-based vol at 2% (zero-range days broke HAR's QLIKE), clip forecasts to the training range, lognormal bias correction from held-out training data (log forecasts ran low and over-sized positions) |
| 2026-11-02 | Headline vol forecast in daily insights = gradient boosting (best R2 in the walk-forward test). Note: chosen after seeing test results; the experiment registry will count it |
| 2026-11-02 | Regime statistics report separate episodes, not just days: overlapping 21-day windows overstate the evidence |
