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

## Phase 1 - Foundation (now)

- [x] TCN + calibrated sigmoid head + deadbanded volatility-scaled risk map
- [x] Walk-forward backtest with costs, baselines (buy & hold, vol-scaled long, logistic), bootstrap significance test
- [x] Monthly retraining on a rolling 10-year window, matching the live plan
- [x] Real data only: data quality checks, auto-refreshing cache, placebo (shuffled-label) leakage check
- [x] GitHub Actions workflow: real-data backtest + placebo in the cloud, reports committed to `reports/`
- [ ] First real-data backtest (yearly mode, cloud) - review report
- [ ] Set up the gaming laptop (CUDA PyTorch), run the full monthly backtest
- [ ] Decide the ticker list (5-10 liquid ETFs)
- [ ] Save trained models with version + training-date metadata (`models/`)
- [ ] Champion vs. challenger promotion logic
- [ ] Daily job: data update -> prediction -> append to `ledger/predictions.csv` (prediction made before the open, timestamped)
- [ ] Ledger scorer: fills in realized returns the next day, tracks paper P&L vs. buy & hold and vol-scaled long
- [ ] GitHub Actions workflow for the daily job (inference only; model weights come from the latest monthly retrain)
- [ ] Monthly retrain script for the laptop (scheduled), including calibration-drift check

## Phase 2 - Calendar and macro features

Each addition must improve out-of-sample results vs. the version without it, or it's dropped.

- [ ] Calendar events known in advance: days to next FOMC decision, CPI release, jobs report, earnings-season flag
- [ ] Macro data from FRED: interest rates, yield curve (10y-2y), VIX
- [ ] Market-wide context: SPY returns as a feature for every ticker
- [ ] Ablation table: performance with / without each feature group

## Phase 3 - Research layer

- [ ] Weekly research note (Claude): earnings, news, trends for the tracked tickers
- [ ] **"Claude analyst" paper portfolio**: weekly picks from the research note, logged before results, tracked separately
- [ ] Dashboard comparing three tracks: model vs. Claude analyst vs. index
- Rule: Claude's judgment can only be evaluated going forward. Claude already knows past market history, so any backtest of its research would be leakage.

## Phase 4 - Optional: individual stocks

- [ ] Point-in-time fundamentals from SEC EDGAR (revenue, EPS, surprises), stored by **release date**, not fiscal period end
- [ ] Earnings-date features and post-earnings drift
- [ ] Only if Phases 1-3 show something real

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
