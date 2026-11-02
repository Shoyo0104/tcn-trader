"""Walk-forward backtest: retrain once per year, only ever predict a year the model hasn't seen."""
import os

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from features import Scaler
from model import (PlattCalibrator, baseline_features, predict_logits, train_logistic, train_tcn)
from risk import position, signal_scale, vol_scaled_long

# Fixed series colors (the color follows the strategy, never its rank)
COLORS = {"Buy & hold": "#8a8983", "Vol-scaled long": "#eda100",
          "Logistic + risk map": "#eb6834", "TCN + risk map": "#2a78d6"}


def split_train_val(dates, mask, cfg, test_start):
    """Chronological split of the rolling training window before test_start into train / validation,
    with an embargo so no label can overlap the test period."""
    window_start = test_start - np.timedelta64(int(cfg.train_years * 365.25), "D")
    train_dates = np.sort(np.unique(dates[mask & (dates < test_start) & (dates >= window_start)]))
    train_dates = train_dates[: len(train_dates) - cfg.embargo_days]          # embargo before test
    cut = train_dates[int(len(train_dates) * (1 - cfg.val_frac))]
    in_train = np.isin(dates, train_dates) & mask
    return in_train & (dates < cut), in_train & (dates >= cut)


def test_periods(dates, cfg, years=None):
    """The retraining schedule: one period per month (or year) from test_start_year onward."""
    first_ok = pd.Timestamp(dates.min()) + pd.DateOffset(years=cfg.min_train_years)
    start = max(pd.Timestamp(f"{cfg.test_start_year}-01-01"), first_ok)
    periods = pd.period_range(start, pd.Timestamp(dates.max()), freq=cfg.retrain_freq)
    if years:
        periods = [p for p in periods if p.start_time.year in years]
    return periods


def walk_forward(data, cfg, years=None, verbose=True, placebo=False):
    """placebo=True: shuffle the TRAINING labels (test labels stay real). A model that learned
    from shuffled labels has nothing real to know, so it must show no edge on the real test data.
    If it does, something is leaking. This is the real-data leakage check."""
    dates = data["date"].values
    labeled = ~np.isnan(data["y"])
    periods = test_periods(dates[labeled], cfg, years)
    rng = np.random.default_rng(cfg.seed)
    if verbose:
        print(f"Walk-forward: {len(periods)} retrains ({cfg.retrain_freq}), "
              f"rolling {cfg.train_years}-year training window" + ("   [PLACEBO]" if placebo else ""))
    rows = []
    for P in periods:
        test_start = np.datetime64(P.start_time.normalize())
        test_end = np.datetime64(P.end_time.normalize() + pd.Timedelta(days=1))
        tr, va = split_train_val(dates, labeled, cfg, test_start)
        te = labeled & (dates >= test_start) & (dates < test_end)
        if te.sum() == 0:
            continue
        sc = Scaler().fit(data["X"][tr])
        Xtr, Xva, Xte = (sc.transform(data["X"][m]) for m in (tr, va, te))
        ytr, yva = data["y"][tr], data["y"][va]
        if placebo:
            ytr, yva = rng.permutation(ytr), rng.permutation(yva)

        tcn = train_tcn(Xtr, ytr, Xva, yva, cfg)
        lg_va = predict_logits(tcn, Xva)
        cal = PlattCalibrator().fit(lg_va, yva)
        p_tcn = cal.predict(predict_logits(tcn, Xte))
        sc_tcn = signal_scale(cal.predict(lg_va), cfg)

        lr = train_logistic(Xtr, ytr)
        p_lr = lr.predict_proba(baseline_features(Xte))[:, 1]
        sc_lr = signal_scale(lr.predict_proba(baseline_features(Xva))[:, 1], cfg)

        if verbose:
            auc = roc_auc_score(data["y"][te], p_tcn) if len(set(data["y"][te])) > 1 else np.nan
            print(f"  {P}: train {tr.sum():>6}  val {va.sum():>5}  test {te.sum():>5}   TCN AUC {auc:.3f}")
        rows.append(pd.DataFrame({
            "date": dates[te], "ticker": data["ticker"][te], "y": data["y"][te],
            "fwd_ret": data["fwd_ret"][te], "sigma_hat": data["sigma_hat"][te],
            "p_tcn": p_tcn, "p_lr": p_lr, "scale_tcn": sc_tcn, "scale_lr": sc_lr,
        }))
    return pd.concat(rows, ignore_index=True)


# ---------------------------------------------------------------- strategy returns
def strategy_returns(pred, cfg):
    """Daily net returns per strategy, equal-weighted across tickers, after trading costs."""
    weights = {
        "Buy & hold": lambda d: np.ones(len(d)),
        "Vol-scaled long": lambda d: vol_scaled_long(d["sigma_hat"], cfg),
        "Logistic + risk map": lambda d: position(d["p_lr"], d["sigma_hat"], cfg, d["scale_lr"].values),
        "TCN + risk map": lambda d: position(d["p_tcn"], d["sigma_hat"], cfg, d["scale_tcn"].values),
    }
    out, expo = {}, {}
    for name, wfun in weights.items():
        per_ticker = []
        for t, d in pred.sort_values("date").groupby("ticker"):
            w = wfun(d)
            cost = cfg.cost_bps / 1e4 * np.abs(np.diff(w, prepend=0.0))
            per_ticker.append(pd.DataFrame({"date": d["date"].values, "ret": w * d["fwd_ret"].values - cost,
                                            "w": w, "turn": np.abs(np.diff(w, prepend=0.0))}))
        df = pd.concat(per_ticker).groupby("date").mean()
        out[name] = df["ret"]
        expo[name] = (df["w"].abs().mean(), df["turn"].sum() / (len(df) / 252))
    return pd.DataFrame(out).fillna(0.0), expo


def perf_table(rets, expo):
    rows = {}
    for k, r in rets.items():
        eq = (1 + r).cumprod()
        yrs = len(r) / 252
        dd = (eq / eq.cummax() - 1).min()
        vol = r.std() * np.sqrt(252)
        rows[k] = {
            "CAGR": eq.iloc[-1] ** (1 / yrs) - 1,
            "Volatility": vol,
            "Sharpe": r.mean() * 252 / vol if vol > 0 else np.nan,
            "Max drawdown": dd,
            "Avg exposure": expo[k][0],
            "Turnover/yr": expo[k][1],
        }
    return pd.DataFrame(rows).T


def prediction_table(pred):
    y = pred["y"].values
    base = np.full(len(y), y.mean())
    rows = {"Always 'up' (base rate)": {"AUC": 0.5, "Accuracy": max(y.mean(), 1 - y.mean()),
                                        "Brier": brier_score_loss(y, base), "Log loss": log_loss(y, base)}}
    for name, col in [("Logistic", "p_lr"), ("TCN (calibrated)", "p_tcn")]:
        p = pred[col].values
        rows[name] = {"AUC": roc_auc_score(y, p), "Accuracy": ((p > 0.5) == y).mean(),
                      "Brier": brier_score_loss(y, p), "Log loss": log_loss(y, np.clip(p, 1e-6, 1 - 1e-6))}
    return pd.DataFrame(rows).T


def bootstrap_sharpe_gap(rets, a="TCN + risk map", b="Vol-scaled long", n=2000, block=20, seed=0):
    """How often would the Sharpe gap between a and b be <= 0 if we re-drew history?
    Block bootstrap keeps short-term autocorrelation. Small value = the edge looks real."""
    rng = np.random.default_rng(seed)
    x = rets[[a, b]].values
    T = len(x)
    gaps = []
    for _ in range(n):
        starts = rng.integers(0, T - block, T // block + 1)
        idx = (starts[:, None] + np.arange(block)).ravel()[:T]
        s = x[idx]
        sh = s.mean(0) / (s.std(0) + 1e-12) * np.sqrt(252)
        gaps.append(sh[0] - sh[1])
    gaps = np.array(gaps)
    return float(np.mean(gaps <= 0)), float(np.mean(gaps))


# ---------------------------------------------------------------- charts
def plot_results(rets, pred, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#c3c2b7", "axes.labelcolor": "#3d3d3a",
                         "xtick.color": "#5f5e5a", "ytick.color": "#5f5e5a"})

    # Equity curves (one axis, log scale so % moves are comparable)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for k in rets.columns:
        eq = (1 + rets[k]).cumprod()
        ax.plot(eq.index, eq.values, lw=2, color=COLORS[k], label=k)
        ax.annotate(f"{k}  {eq.iloc[-1]:.2f}x", (eq.index[-1], eq.iloc[-1]), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=9, color="#3d3d3a")
    ax.set_yscale("log")
    from matplotlib.ticker import FuncFormatter, LogLocator
    ax.yaxis.set_major_locator(LogLocator(base=10, subs=(1, 1.25, 1.5, 2, 3, 4, 5, 7)))
    ax.yaxis.set_minor_locator(LogLocator(base=10, subs=()))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:.2f}"))
    ax.set_ylabel("Growth of $1 (log scale, after costs)")
    ax.grid(axis="y", color="#e7e6e1", lw=0.8)
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("Walk-forward backtest - equal weight across tickers", loc="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "equity.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Reliability diagram: are the probabilities honest?
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    for col, name, c in [("p_lr", "Logistic", COLORS["Logistic + risk map"]),
                         ("p_tcn", "TCN (calibrated)", COLORS["TCN + risk map"])]:
        bins = pd.qcut(pred[col], 10, duplicates="drop")
        g = pred.groupby(bins, observed=True).agg(p=(col, "mean"), y=("y", "mean"))
        ax.plot(g["p"], g["y"], marker="o", ms=8, lw=2, color=c, label=name)
    lo = min(pred["p_tcn"].min(), pred["p_lr"].min(), 0.4)
    hi = max(pred["p_tcn"].max(), pred["p_lr"].max(), 0.6)
    ax.plot([lo, hi], [lo, hi], ls="--", lw=1, color="#8a8983", label="Perfectly calibrated")
    ax.set_xlabel("Predicted probability of an up day")
    ax.set_ylabel("Actual share of up days")
    ax.grid(color="#e7e6e1", lw=0.8)
    ax.legend(frameon=False)
    ax.set_title("Calibration (out-of-sample, by decile)", loc="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "calibration.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
