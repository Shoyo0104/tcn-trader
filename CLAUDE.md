# Notes for Claude

Read README.md (what it is, how to run it) and ROADMAP.md (plan, current phase, decision log) before starting work.

## Hard rules
- **No look-ahead leakage.** Features on row t use data up to the close of day t only. Labels are about t+1. Scalers, calibration and signal scaling are fit on training/validation data only, never test periods.
- After any change to features, model or backtest, re-run both sanity tests:
  - `python run.py backtest --synthetic --freq Y --start-year 2022 --end-year 2024` -> should barely trade, no meaningful edge
  - `python run.py backtest --synthetic --edge 0.15 --freq Y --start-year 2022 --end-year 2024` -> should find an edge
- Every new feature or model change must beat the version without it out-of-sample, or it gets dropped. Record the decision in ROADMAP.md's decision log.
- Never tune hyperparameters on test periods.
- Paper trading only. Never place real trades.

## Owner
Shoyo: Data Science (Honours, Statistics) student. Explain trade-offs plainly; prefer simple and honest over impressive.
