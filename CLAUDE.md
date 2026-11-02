# Notes for Claude

Read README.md (what it is, how to run it) and ROADMAP.md (plan, current phase, decision log) before starting work. Recent results live in `reports/`.

## Hard rules
- **Real market data only.** No synthetic or simulated price data anywhere in the project.
- **No look-ahead leakage.** Features on row t use data up to the close of day t only. Labels are about t+1. Scalers, calibration and signal scaling are fit on training/validation data only, never test periods. Fundamentals/events must be keyed by their public release date.
- After any change to features, model or backtest, run the placebo check on real data:
  `python run.py backtest --placebo --freq Y` -> must show no edge (AUC ~0.5, TCN not better than vol-scaled long).
- Every new feature or model change must beat the version without it out-of-sample, or it gets dropped. Record the decision in ROADMAP.md's decision log.
- Never tune hyperparameters on test periods.
- Paper trading only. Never place real trades.

## Owner
Shoyo: Data Science (Honours, Statistics) student. This project gets maximum effort: be thorough, explain trade-offs plainly, prefer simple and honest over impressive.
