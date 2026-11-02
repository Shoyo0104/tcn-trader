"""Command-line entry point.

  python run.py backtest                       # walk-forward backtest on real data (monthly retrains)
  python run.py backtest --freq Y              # same, retraining yearly (about 12x faster)
  python run.py backtest --synthetic           # pure-noise test data (should find NOTHING)
  python run.py backtest --synthetic --edge 0.1  # test data with a planted pattern (should find it)
  python run.py signal                         # train on all history, print today's positions
"""
import argparse
import os
import warnings

import numpy as np
import pandas as pd

from backtest import (bootstrap_sharpe_gap, perf_table, plot_results, prediction_table,
                      strategy_returns, walk_forward)
from config import Config
from data import load_all, make_synthetic
from features import Scaler, build_features, make_windows, stack
from model import PlattCalibrator, predict_logits, train_tcn
from risk import position, signal_scale

warnings.filterwarnings("ignore", category=FutureWarning)
pd.set_option("display.width", 140)


def build_dataset(cfg, args):
    raw = make_synthetic(edge=args.edge, seed=args.seed) if args.synthetic else \
        load_all(cfg.tickers, cfg.start, cfg.data_dir, refresh=args.refresh)
    per = {}
    for t, df in raw.items():
        w = make_windows(build_features(df, cfg.vol_span), cfg.window)
        if w is not None:
            per[t] = w
    return stack(per)


def cmd_backtest(cfg, args):
    os.makedirs(cfg.results_dir, exist_ok=True)
    data = build_dataset(cfg, args)
    print(f"Samples: {len(data['y'])}  |  window {cfg.window} x features {data['X'].shape[-1]}")
    years = list(range(args.start_year, args.end_year + 1)) if args.end_year else None
    pred = walk_forward(data, cfg, years=years)
    pred.to_csv(os.path.join(cfg.results_dir, "predictions.csv"), index=False)

    rets, expo = strategy_returns(pred, cfg)
    perf, predq = perf_table(rets, expo), prediction_table(pred)
    p_worse, gap = bootstrap_sharpe_gap(rets)
    perf.to_csv(os.path.join(cfg.results_dir, "performance.csv"))
    predq.to_csv(os.path.join(cfg.results_dir, "prediction_quality.csv"))
    plot_results(rets, pred, cfg.results_dir)

    fmt = {"CAGR": "{:.1%}", "Volatility": "{:.1%}", "Sharpe": "{:.2f}", "Max drawdown": "{:.1%}",
           "Avg exposure": "{:.2f}", "Turnover/yr": "{:.1f}"}
    print("\n=== Strategy performance (out-of-sample, after costs) ===")
    print(perf.apply(lambda c: c.map(fmt[c.name].format)).to_string())
    print("\n=== Prediction quality ===")
    print(predq.round(4).to_string())
    print(f"\nTCN vs vol-scaled long: mean Sharpe gap {gap:+.2f}; "
          f"share of bootstrap draws where TCN is NOT better: {p_worse:.0%}")
    print("  (Below ~5% suggests a real edge. Above ~20%: indistinguishable from luck.)")
    print(f"\nSaved predictions, tables and charts to ./{cfg.results_dir}/")


def cmd_signal(cfg, args):
    """Train on all labeled history and output a suggested position for the next trading day."""
    data = build_dataset(cfg, args)
    dates = data["date"].values
    labeled = ~np.isnan(data["y"])
    window_start = dates.max() - np.timedelta64(int(cfg.train_years * 365.25), "D")
    labeled &= dates >= window_start                       # same rolling window as the backtest
    ud = np.sort(np.unique(dates[labeled]))
    cut = ud[int(len(ud) * (1 - cfg.val_frac))]
    tr, va = labeled & (dates < cut), labeled & (dates >= cut)
    sc = Scaler().fit(data["X"][tr])
    model = train_tcn(sc.transform(data["X"][tr]), data["y"][tr],
                      sc.transform(data["X"][va]), data["y"][va], cfg)
    lg_va = predict_logits(model, sc.transform(data["X"][va]))
    cal = PlattCalibrator().fit(lg_va, data["y"][va])
    scale = signal_scale(cal.predict(lg_va), cfg)

    rows = []
    for t in np.unique(data["ticker"]):
        i = np.where(data["ticker"] == t)[0][-1]            # most recent window for this ticker
        p = cal.predict(predict_logits(model, sc.transform(data["X"][i:i + 1])))[0]
        w = position(np.array([p]), np.array([data["sigma_hat"][i]]), cfg, scale)[0]
        rows.append({"ticker": t, "as_of_close": pd.Timestamp(dates[i]).date(), "p_up": round(p, 3),
                     "vol_forecast": f"{data['sigma_hat'][i]:.1%}", "suggested_weight": round(w, 2) + 0.0})
    print(pd.DataFrame(rows).to_string(index=False))
    print("\nsuggested_weight = fraction of the capital set aside for that ticker (0 = stay out).")
    print("Paper-trade this first. A backtest is not a promise.")


def main():
    ap = argparse.ArgumentParser(description="TCN + calibrated head + risk map trading research tool")
    ap.add_argument("command", choices=["backtest", "signal"])
    ap.add_argument("--synthetic", action="store_true", help="use fake data (tests the pipeline)")
    ap.add_argument("--edge", type=float, default=0.0, help="planted predictability in synthetic data")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--refresh", action="store_true", help="re-download data instead of using the cache")
    ap.add_argument("--tickers", nargs="+", help="override tickers, e.g. --tickers SPY QQQ")
    ap.add_argument("--epochs", type=int)
    ap.add_argument("--start-year", type=int, default=Config.test_start_year)
    ap.add_argument("--end-year", type=int, help="limit walk-forward to these years (faster)")
    ap.add_argument("--freq", choices=["M", "Y"], help="retrain monthly (M, default) or yearly (Y, faster)")
    args = ap.parse_args()

    cfg = Config()
    if args.freq:
        cfg.retrain_freq = args.freq
    if args.tickers:
        cfg.tickers = args.tickers
    if args.epochs:
        cfg.epochs = args.epochs
    cfg.test_start_year = args.start_year
    {"backtest": cmd_backtest, "signal": cmd_signal}[args.command](cfg, args)


if __name__ == "__main__":
    main()
