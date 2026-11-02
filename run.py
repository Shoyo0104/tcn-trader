"""Command-line entry point. Real market data only.

  python run.py backtest                  # walk-forward backtest, monthly retrains (the live plan)
  python run.py backtest --freq Y         # same, retraining yearly (about 12x faster)
  python run.py backtest --placebo        # leakage check: train on shuffled labels -> must show NO edge
  python run.py signal                    # train on the latest 10 years, print next-day positions
  python run.py vol                       # walk-forward test of volatility forecasts (EWMA vs HAR vs boosting)
  python run.py vol --placebo             # same with shuffled training targets: skill must vanish
  python run.py insights                  # market regime + vol forecasts + what history says, as of today
"""
import argparse
import json
import os
import subprocess
import warnings
from dataclasses import asdict
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from backtest import (bootstrap_sharpe_gap, perf_table, plot_results, prediction_table,
                      strategy_returns, walk_forward)
from config import Config
from data import load_all
from features import Scaler, build_features, make_windows, stack
from model import PlattCalibrator, get_device, predict_logits, train_tcn
from risk import position, signal_scale

warnings.filterwarnings("ignore", category=FutureWarning)
pd.set_option("display.width", 140)

FMT = {"CAGR": "{:.1%}", "Volatility": "{:.1%}", "Sharpe": "{:.2f}", "Max drawdown": "{:.1%}",
       "Avg exposure": "{:.2f}", "Turnover/yr": "{:.1f}"}


def build_dataset(cfg, args):
    print("Data:")
    raw = load_all(cfg.tickers, cfg.start, cfg.data_dir, refresh=args.refresh)
    per = {}
    for t, df in raw.items():
        w = make_windows(build_features(df, cfg.vol_span), cfg.window)
        if w is not None:
            per[t] = w
    return stack(per)


def md_table(df, fmt=None):
    """DataFrame -> markdown table (no extra dependencies)."""
    cols = list(df.columns)
    lines = ["| | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
    for idx, row in df.iterrows():
        cells = [(fmt[c].format(row[c]) if fmt and c in fmt else f"{row[c]:.4f}") for c in cols]
        lines.append(f"| {idx} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def yearly_sharpe(rets):
    g = rets.groupby(rets.index.year)
    return g.apply(lambda r: r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0.0)


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unknown"


def cmd_backtest(cfg, args):
    out = args.out or cfg.results_dir
    os.makedirs(out, exist_ok=True)
    data = build_dataset(cfg, args)
    print(f"Samples: {len(data['y'])}  |  window {cfg.window} x features {data['X'].shape[-1]}"
          f"  |  device {get_device()}")
    years = list(range(args.start_year, args.end_year + 1)) if args.end_year else None
    pred = walk_forward(data, cfg, years=years, placebo=args.placebo)
    pred.to_csv(os.path.join(out, "predictions.csv"), index=False)

    rets, expo = strategy_returns(pred, cfg)
    perf, predq = perf_table(rets, expo), prediction_table(pred)
    p_worse, gap = bootstrap_sharpe_gap(rets)
    ysh = rets.apply(yearly_sharpe)
    perf.to_csv(os.path.join(out, "performance.csv"))
    predq.to_csv(os.path.join(out, "prediction_quality.csv"))
    ysh.to_csv(os.path.join(out, "yearly_sharpe.csv"))
    plot_results(rets, pred, out)

    print("\n=== Strategy performance (out-of-sample, after costs) ===")
    print(perf.apply(lambda c: c.map(FMT[c.name].format)).to_string())
    print("\n=== Prediction quality ===")
    print(predq.round(4).to_string())
    print("\n=== Sharpe by year ===")
    print(ysh.round(2).to_string())
    verdict = ("looks like a real edge" if p_worse < 0.05 else
               "inconclusive" if p_worse < 0.20 else "indistinguishable from luck")
    print(f"\nTCN vs vol-scaled long: mean Sharpe gap {gap:+.2f}; "
          f"bootstrap draws where TCN is NOT better: {p_worse:.0%} -> {verdict}")

    # A self-contained report that can be read straight from GitHub
    meta = {"run_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), "commit": git_commit(),
            "placebo": args.placebo, "device": str(get_device()),
            "test_period": f"{pred['date'].min().date()} -> {pred['date'].max().date()}",
            "samples": int(len(data["y"]))}
    with open(os.path.join(out, "summary.md"), "w") as f:
        f.write(f"# Backtest report{' (PLACEBO - should show no edge)' if args.placebo else ''}\n\n")
        f.write("\n".join(f"- **{k}:** {v}" for k, v in meta.items()) + "\n\n")
        f.write("## Strategy performance (out-of-sample, after costs)\n\n" + md_table(perf, FMT) + "\n\n")
        f.write("## Prediction quality\n\n" + md_table(predq) + "\n\n")
        f.write("## Sharpe by year\n\n" + md_table(ysh, {c: "{:.2f}" for c in ysh.columns}) + "\n\n")
        f.write(f"## Significance\n\nTCN vs vol-scaled long: mean Sharpe gap {gap:+.2f}; share of bootstrap "
                f"draws where TCN is NOT better: {p_worse:.0%} -> **{verdict}**.\n\n")
        f.write("![equity](equity.png)\n\n![calibration](calibration.png)\n\n")
        f.write("## Config\n\n```json\n" + json.dumps(asdict(cfg), indent=2) + "\n```\n")
    print(f"\nSaved report, tables and charts to ./{out}/")


def cmd_signal(cfg, args):
    """Train on the latest rolling window and output a suggested position for the next trading day."""
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


def _write_report(out, title, meta, sections, cfg):
    with open(os.path.join(out, "summary.md"), "w") as f:
        f.write(f"# {title}\n\n" + "\n".join(f"- **{k}:** {v}" for k, v in meta.items()) + "\n\n")
        for head, body in sections:
            f.write(f"## {head}\n\n{body}\n\n")
        f.write("## Config\n\n```json\n" + json.dumps(asdict(cfg), indent=2) + "\n```\n")


def cmd_vol(cfg, args):
    import insights as ins
    out = args.out or os.path.join(cfg.results_dir, "vol")
    os.makedirs(out, exist_ok=True)
    print("Data:")
    raw = load_all(cfg.tickers, cfg.start, cfg.data_dir, refresh=args.refresh)
    years = list(range(args.start_year, args.end_year + 1)) if args.end_year else None
    pred = ins.vol_walk_forward(raw, cfg, years=years, placebo=args.placebo)
    pred.to_csv(os.path.join(out, "vol_predictions.csv"), index=False)
    met = ins.vol_metrics(pred)
    strat, rets = ins.vol_target_strategies(pred, cfg)
    yearly_r2 = pred.groupby("period").apply(
        lambda g: pd.Series({name: 1 - np.mean((g["y_lv"] - g[f"f_{k}"]) ** 2) / np.var(g["y_lv"])
                             for k, name in ins.VOL_MODELS.items()}))
    met.to_csv(os.path.join(out, "vol_metrics.csv"))
    strat.to_csv(os.path.join(out, "vol_strategy.csv"))
    yearly_r2.to_csv(os.path.join(out, "vol_yearly_r2.csv"))
    (1 + rets).cumprod().to_csv(os.path.join(out, "vol_equity.csv"))

    best = met["QLIKE"].idxmin()
    print("\n=== Forecast quality (out-of-sample) ===")
    print(met.round(4).to_string())
    print("\n=== Vol-targeting strategy using each forecast (after costs) ===")
    sfmt = {"CAGR": "{:.1%}", "Volatility": "{:.1%}", "Sharpe": "{:.2f}", "Max drawdown": "{:.1%}",
            "Yearly vol miss": "{:.1%}", "Worst month": "{:.1%}"}
    print(strat.apply(lambda c: c.map(sfmt[c.name].format)).to_string())
    print("\n=== R2 by year ===")
    print(yearly_r2.round(3).to_string())
    print(f"\nBest forecast by QLIKE: {best}")
    meta = {"run_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), "commit": git_commit(),
            "placebo": args.placebo, "horizon_days": ins.H,
            "test_period": f"{pred['date'].min().date()} -> {pred['date'].max().date()}",
            "samples": int(len(pred)), "best_by_qlike": best}
    _write_report(out, "Volatility forecast report" + (" (PLACEBO - skill should vanish)" if args.placebo else ""),
                  meta, [("Forecast quality (out-of-sample)", md_table(met)),
                         ("Vol-targeting strategy using each forecast (after costs)", md_table(strat, sfmt)),
                         ("R2 by year", md_table(yearly_r2, {c: "{:.3f}" for c in yearly_r2.columns}))], cfg)
    print(f"\nSaved report to ./{out}/")


def cmd_insights(cfg, args):
    import insights as ins
    out = args.out or os.path.join(cfg.results_dir, "insights")
    os.makedirs(out, exist_ok=True)
    print("Data:")
    raw = load_all(cfg.tickers, cfg.start, cfg.data_dir, refresh=args.refresh)
    mkt = "SPY" if "SPY" in raw else list(raw)[0]
    state = ins.market_state(raw[mkt])
    print(f"Market regimes from {mkt} (walk-forward, out-of-sample labels):")
    regimes = ins.regime_walk_forward(state, cfg)
    stats = ins.regime_stats(raw, regimes, cfg)
    trans = ins.transition_matrix(regimes["regime"])
    cur = ins.current_regime(state, cfg)
    vol_now = ins.fit_current_vol(raw, cfg)

    hist = regimes.join(state[["close"]], how="left")
    hist.index.name = "date"
    hist.reset_index()[["date", "regime", "regime_prob", "close"]].to_csv(os.path.join(out, "regime_history.csv"), index=False)
    stats.to_csv(os.path.join(out, "regime_stats.csv"), index=False)
    trans.to_csv(os.path.join(out, "regime_transitions.csv"))
    cur["profile"].to_csv(os.path.join(out, "regime_profile.csv"), index=False)

    # ---- per-ticker insight rows
    rows = []
    for _, v in vol_now.iterrows():
        st = stats[(stats["ticker"] == v["ticker"]) & (stats["regime"] == cur["regime"])]
        st = st.iloc[0] if len(st) else None
        rows.append({
            "ticker": v["ticker"], "as_of_close": str(pd.Timestamp(v["date"]).date()),
            "vol_now": float(v["sigma_hat"]), "vol_forecast_5d": float(v["vol_forecast"]),
            "vol_forecast_5d_har": float(v["vol_har"]), "vol_pctile": float(v["vol_pctile"]),
            "regime": cur["regime"],
            "regime_days_hist": int(st["days"]) if st is not None else None,
            "regime_episodes": int(st["episodes"]) if st is not None else None,
            "fwd21_mean": float(st["fwd21_mean"]) if st is not None else None,
            "p_up_21d": float(st["p_up_21d"]) if st is not None else None,
            "p_drop5_21d": float(st["p_drop5_21d"]) if st is not None else None,
            "q10_5d": float(st["q10_5d"]) if st is not None else None,
        })
    tick = pd.DataFrame(rows)
    tick.to_csv(os.path.join(out, "ticker_insights.csv"), index=False)
    lens = ins.run_lengths(regimes["regime"])
    stay = float(trans.loc[cur["regime"], cur["regime"]]) if cur["regime"] in trans.index else None
    summary = {"as_of": cur["as_of"], "market": mkt, "regime": cur["regime"], "regime_prob": cur["prob"],
               "days_in_regime": cur["days_in_regime"], "avg_run_days": float(lens.get(cur["regime"], np.nan)),
               "p_same_regime_21d": stay, "test_start": str(regimes.index.min().date()),
               "regime_days_total": int(len(regimes))}
    with open(os.path.join(out, "insights.json"), "w") as f:
        json.dump({"summary": summary, "tickers": rows}, f, indent=2)

    pct, f1 = "{:.0%}".format, "{:+.1%}".format
    lines = [f"Market regime ({mkt}) as of {cur['as_of']}: **{cur['regime']}** "
             f"(confidence {pct(cur['prob'])}, {cur['days_in_regime']} trading days so far; "
             f"stretches of this regime have lasted ~{summary['avg_run_days']:.0f} days on average)."]
    if stay is not None:
        lines.append(f"Historically, {pct(stay)} of {cur['regime']} days were still {cur['regime']} 21 trading days later.")
    for r in rows:
        s = (f"**{r['ticker']}**: volatility forecast for the next 5 days {pct(r['vol_forecast_5d'])} "
             f"(higher than {pct(r['vol_pctile'])} of the last 10 years)")
        if r["fwd21_mean"] is not None:
            s += (f". In past {cur['regime']} periods ({r['regime_days_hist']} days in {r['regime_episodes']} separate "
                  f"episodes since {summary['test_start'][:4]}), "
                  f"the next 21 days averaged {f1(r['fwd21_mean'])}, were up {pct(r['p_up_21d'])} of the time, and fell "
                  f"more than 5% {pct(r['p_drop5_21d'])} of the time; the worst 10% of 5-day moves were below {f1(r['q10_5d'])}.")
        lines.append(s)
    st_fmt = {c: ("{:.1%}" if c not in ("days", "episodes", "avg_run_days") else "{:.0f}") for c in stats.columns if c not in ("ticker", "regime")}
    mkt_stats = stats[stats["ticker"] == mkt].set_index("regime").drop(columns="ticker")
    meta = {"run_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), "commit": git_commit(),
            "as_of": cur["as_of"], "market": mkt, "regime_test_period": f"{summary['test_start']} -> {cur['as_of']}"}
    _write_report(out, "Market insights", meta, [
        ("Today", "\n\n".join(lines) + "\n\nHow much evidence: overlapping 21-day windows are not independent, "
         "so the episode count, not the day count, is closer to the real sample size. Treat regime "
         "statistics built on few episodes as rough."),
        (f"What followed each regime ({mkt}, out-of-sample labels)", md_table(mkt_stats, st_fmt)),
        ("Regime profiles (latest fit)", md_table(cur["profile"].set_index("regime"),
                                                   {"typical_vol": "{:.1%}", "typical_3m_return": "{:+.1%}",
                                                    "typical_drawdown": "{:.1%}"})),
        ("Chance of being in each regime 21 trading days later", md_table(trans, {c: "{:.0%}" for c in trans.columns})),
    ], cfg)
    print("\n" + "\n\n".join(l.replace("**", "") for l in lines))
    print(f"\nSaved insights to ./{out}/")


def main():
    ap = argparse.ArgumentParser(description="TCN + calibrated head + risk map trading research tool")
    ap.add_argument("command", choices=["backtest", "signal", "vol", "insights"])
    ap.add_argument("--placebo", action="store_true",
                    help="leakage check: train on shuffled labels, test on real ones (expect no edge)")
    ap.add_argument("--refresh", action="store_true", help="re-download data instead of using the cache")
    ap.add_argument("--tickers", nargs="+", help="override tickers, e.g. --tickers SPY QQQ")
    ap.add_argument("--epochs", type=int)
    ap.add_argument("--start-year", type=int, default=Config.test_start_year)
    ap.add_argument("--end-year", type=int, help="limit walk-forward to these years (faster)")
    ap.add_argument("--freq", choices=["M", "Y"], help="retrain monthly (M, default) or yearly (Y, faster)")
    ap.add_argument("--out", help="output folder for the report (default: results/)")
    args = ap.parse_args()

    cfg = Config()
    if args.freq:
        cfg.retrain_freq = args.freq
    if args.tickers:
        cfg.tickers = args.tickers
    if args.epochs:
        cfg.epochs = args.epochs
    cfg.test_start_year = args.start_year
    {"backtest": cmd_backtest, "signal": cmd_signal, "vol": cmd_vol, "insights": cmd_insights}[args.command](cfg, args)


if __name__ == "__main__":
    main()
