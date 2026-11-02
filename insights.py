"""Insight engine: volatility forecasting and market-regime detection (real data, walk-forward).

Volatility forecasting
    Target: realized volatility over the NEXT 5 trading days (close-to-close, annualized), in logs.
    Models: EWMA (what the risk map uses today, no fitting), HAR (Corsi 2009: a regression on
    daily / weekly / monthly volatility, the standard benchmark), and gradient boosting on HAR
    inputs plus return-based features. Walk-forward by year on a rolling 10-year window, with an
    embargo so no training label overlaps the test period.

Market regimes
    A Gaussian mixture on SPY's market state (volatility, trend, drawdown, volatility change),
    fit each year only on the 10 years before it, with posteriors smoothed over the last 5 days
    (past only). Regimes are named by their volatility rank: Calm, Normal, Elevated, Stressed.
    For each regime: what historically followed it, measured only on out-of-sample labels.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.mixture import GaussianMixture

EPS = 1e-10
H = 5                                   # forecast horizon in trading days
VOL_FLOOR = 0.02                        # 2% annualized: floor for range-based daily vol
VOL_X_HAR = ["lv_d", "lv_w", "lv_m"]
VOL_X_GBM = VOL_X_HAR + ["lv_ewma", "ret_1", "ret_5", "ret_22", "ma50_dist", "abs_gap", "vol_ratio"]
REGIME_X = ["lv21", "ret63", "drawdown", "volchg"]
VOL_MODELS = {"ewma": "EWMA (current risk map)", "ewmacal": "EWMA recalibrated", "har": "HAR",
              "gbm": "Gradient boosting"}
REGIME_NAMES = ["Calm", "Normal", "Elevated", "Stressed"]


# ----------------------------------------------------------------------------- features
def vol_features(df: pd.DataFrame, vol_span: int = 20) -> pd.DataFrame:
    """Everything on row t uses data up to the close of day t. Targets look forward and are
    clearly marked (fwd_*); they are never features."""
    o, h, l, c = df["Open"], df["High"], df["Low"], df["Close"]
    r = np.log(c).diff()
    pk = np.log(h / l) ** 2 / (4 * np.log(2))          # Parkinson daily variance (uses the day's range)
    # Floor: a day whose high equals its low (a data glitch or a halted session) gives zero range,
    # and log(0) would send the forecasts wild. Treat anything below 2% annualized vol as 2%.
    pk = pk.clip(lower=VOL_FLOOR ** 2 / 252)
    f = pd.DataFrame(index=df.index)
    f["lv_d"] = 0.5 * np.log(pk * 252 + EPS)
    f["lv_w"] = 0.5 * np.log(pk.rolling(5).mean() * 252 + EPS)
    f["lv_m"] = 0.5 * np.log(pk.rolling(22).mean() * 252 + EPS)
    f["sigma_hat"] = np.sqrt((r ** 2).ewm(span=vol_span, adjust=False).mean() * 252)   # EWMA, as in the risk map
    f["lv_ewma"] = np.log(f["sigma_hat"] + EPS)
    f["ret_1"] = r
    f["ret_5"] = r.rolling(5).sum()
    f["ret_22"] = r.rolling(22).sum()
    f["ma50_dist"] = np.log(c / c.rolling(50).mean())
    f["abs_gap"] = np.log(o / c.shift(1)).abs()
    f["vol_ratio"] = r.rolling(5).std() / r.rolling(22).std()
    # ---- forward-looking targets / outcomes (NOT features)
    f["fwd_rv5"] = np.sqrt((r ** 2).rolling(H).mean().shift(-H) * 252)                 # next 5 days' realized vol
    f["y_lv"] = np.log(f["fwd_rv5"] + EPS)
    f["fwd_ret1"] = c.shift(-1) / c - 1
    f["fwd_ret5"] = c.shift(-5) / c - 1
    f["fwd_ret21"] = c.shift(-21) / c - 1
    f["fwd_rv21"] = np.sqrt((r ** 2).rolling(21).mean().shift(-21) * 252)
    return f.replace([np.inf, -np.inf], np.nan)


def market_state(df: pd.DataFrame) -> pd.DataFrame:
    c = df["Close"]
    r = np.log(c).diff()
    s = pd.DataFrame(index=df.index)
    s["lv21"] = np.log(r.rolling(21).std() * np.sqrt(252) + EPS)
    s["ret63"] = r.rolling(63).sum()
    s["drawdown"] = np.log(c / c.rolling(252, min_periods=126).max())
    s["volchg"] = np.log(r.rolling(21).std() / r.rolling(63).std())
    s["close"] = c
    return s.replace([np.inf, -np.inf], np.nan)


def stack_vol(raw: dict, vol_span: int) -> pd.DataFrame:
    parts = []
    for t, df in raw.items():
        f = vol_features(df, vol_span)
        f["ticker"] = t
        parts.append(f)
    out = pd.concat(parts)
    out.index.name = "date"
    return out.reset_index()


# ----------------------------------------------------------------------------- vol models
def _models(seed):
    # EWMA recalibrated: the same EWMA signal, with scale and bias fitted on training data. Raw EWMA
    # in log space is biased (the log of a noisy 5-day realized vol averages below the log of the
    # true vol), so HAR must beat this fair version, not just correct that bias.
    return {
        "ewmacal": (["lv_ewma"], lambda: LinearRegression()),
        "har": (VOL_X_HAR, lambda: LinearRegression()),
        "gbm": (VOL_X_GBM, lambda: HistGradientBoostingRegressor(
            max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=100,
            l2_regularization=1.0, random_state=seed)),
    }


def _fit_predict(train: pd.DataFrame, test: pd.DataFrame, seed: int, placebo_rng=None):
    """Fit each model on the training window and forecast log vol for `test`.

    Also returns s2 per model: the variance of forecast errors on held-out data (fit on the first
    80% of the training window, measured on the last 20%). Forecasts are made in log space, which
    targets the median, not the mean; turning them back into a variance needs the lognormal
    correction exp(2f + 2*s2), or the forecasts run systematically low and size positions too big.
    Forecasts are clipped to the range of targets seen in training."""
    y = train["y_lv"].values
    if placebo_rng is not None:
        y = placebo_rng.permutation(y)
    lo, hi = np.percentile(y, 0.5), np.percentile(y, 99.5)
    order = np.argsort(train["date"].values, kind="stable")
    cut = order[: int(len(order) * 0.8)]
    hold = order[int(len(order) * 0.8):]
    out = {}
    for k, (cols, make) in _models(seed).items():
        Xtr = train[cols].values
        m_hold = make().fit(Xtr[cut], y[cut])
        resid = y[hold] - np.clip(m_hold.predict(Xtr[hold]), lo, hi)
        out[f"s2_{k}"] = float(np.var(resid))
        m = make().fit(Xtr, y)
        out[k] = np.clip(m.predict(test[cols].values), lo, hi)
    return out


def variance_forecast(f_log, s2=0.0):
    """Log-vol forecast -> annualized variance forecast, with the lognormal correction."""
    return np.exp(2 * np.asarray(f_log) + 2 * s2)


def vol_walk_forward(raw: dict, cfg, years=None, placebo=False, verbose=True) -> pd.DataFrame:
    d = stack_vol(raw, cfg.vol_span)
    feat_ok = d[VOL_X_GBM].notna().all(axis=1)
    lab_ok = feat_ok & d["y_lv"].notna()
    all_years = sorted(d.loc[lab_ok, "date"].dt.year.unique())
    years = years or [y for y in all_years if y >= cfg.test_start_year]
    rng = np.random.default_rng(cfg.seed) if placebo else None
    rows = []
    if verbose:
        print(f"Vol walk-forward: {len(years)} yearly retrains, rolling {cfg.train_years}-year window, "
              f"horizon {H} days" + ("   [PLACEBO]" if placebo else ""))
    for Y in years:
        start = pd.Timestamp(f"{Y}-01-01")
        end = pd.Timestamp(f"{Y + 1}-01-01")
        tr_dates = np.sort(d.loc[lab_ok & (d["date"] < start) &
                                 (d["date"] >= start - pd.DateOffset(years=cfg.train_years)), "date"].unique())
        tr_dates = tr_dates[: len(tr_dates) - H]                         # embargo: labels look 5 days ahead
        tr = d[lab_ok & d["date"].isin(tr_dates)]
        te = d[lab_ok & (d["date"] >= start) & (d["date"] < end)]
        if len(te) == 0 or len(tr) < 1000:
            continue
        pred = _fit_predict(tr, te, cfg.seed, rng)
        out = te[["date", "ticker", "y_lv", "fwd_rv5", "fwd_ret1", "sigma_hat"]].copy()
        out["f_ewma"] = te["lv_ewma"].values
        out["s2_ewma"] = 0.0                      # raw EWMA already estimates variance directly
        for k in ["ewmacal", "har", "gbm"]:
            out[f"f_{k}"] = pred[k]
            out[f"s2_{k}"] = pred[f"s2_{k}"]
        out["period"] = str(Y)
        if verbose:
            r2 = {k: 1 - np.mean((out["y_lv"] - out[f"f_{k}"]) ** 2) / np.var(out["y_lv"]) for k in VOL_MODELS}
            print(f"  {Y}: train {len(tr):>6}  test {len(te):>5}   R2 ewma {r2['ewma']:+.3f}  "
                  f"ewma-cal {r2['ewmacal']:+.3f}  har {r2['har']:+.3f}  gbm {r2['gbm']:+.3f}")
        rows.append(out)
    return pd.concat(rows, ignore_index=True)


def vol_metrics(pred: pd.DataFrame) -> pd.DataFrame:
    """Out-of-sample forecast quality. R2 on log vol (higher is better; 0 = no better than the
    test-period average), RMSE on log vol and QLIKE on variance (both lower is better).
    QLIKE is the standard loss for comparing volatility forecasts: it punishes under-forecasting
    risk more than over-forecasting it."""
    y = pred["y_lv"].values
    rows = {}
    for k, name in VOL_MODELS.items():
        f = pred[f"f_{k}"].values
        rv2, h2 = np.exp(2 * y), variance_forecast(f, pred[f"s2_{k}"].values)
        per = [1 - np.mean((g["y_lv"] - g[f"f_{k}"]) ** 2) / np.var(g["y_lv"]) for _, g in pred.groupby("period")]
        rows[name] = {
            "R2 (log vol)": 1 - np.mean((y - f) ** 2) / np.var(y),
            "R2 (avg per year)": float(np.mean(per)),
            "RMSE (log vol)": float(np.sqrt(np.mean((y - f) ** 2))),
            "QLIKE": float(np.mean(rv2 / h2 - np.log(rv2 / h2) - 1)),
            "Correlation": float(np.corrcoef(y, f)[0, 1]),
        }
    return pd.DataFrame(rows).T


def vol_target_strategies(pred: pd.DataFrame, cfg) -> tuple:
    """The economic test: a vol-targeting position w = clip(target / forecast) per ticker,
    equal weight across tickers, after costs. A better forecast should hit the risk target
    more accurately (smaller yearly miss) and avoid big drawdowns, at similar or better Sharpe."""
    names = {f"f_{k}": v for k, v in VOL_MODELS.items()}
    rets = {}
    for col, name in names.items():
        parts = []
        for t, g in pred.sort_values("date").groupby("ticker"):
            vol = np.sqrt(variance_forecast(g[col].values, g[col.replace("f_", "s2_")].values))
            w = np.clip(cfg.target_vol / np.maximum(vol, 1e-4), cfg.w_min, cfg.w_max)
            cost = cfg.cost_bps / 1e4 * np.abs(np.diff(w, prepend=0.0))
            parts.append(pd.DataFrame({"date": g["date"].values, "ret": w * g["fwd_ret1"].values - cost}))
        rets[name] = pd.concat(parts).groupby("date")["ret"].mean()
    rets = pd.DataFrame(rets).fillna(0.0)
    rows = {}
    for k, r in rets.items():
        eq = (1 + r).cumprod()
        yearly_vol = r.groupby(r.index.year).std() * np.sqrt(252)
        vol = r.std() * np.sqrt(252)
        rows[k] = {
            "CAGR": eq.iloc[-1] ** (252 / len(r)) - 1,
            "Volatility": vol,
            "Sharpe": r.mean() * 252 / vol if vol > 0 else np.nan,
            "Max drawdown": (eq / eq.cummax() - 1).min(),
            "Yearly vol miss": float(np.sqrt(np.mean((yearly_vol - cfg.target_vol) ** 2))),
            "Worst month": r.groupby(r.index.to_period("M")).apply(lambda x: (1 + x).prod() - 1).min(),
        }
    return pd.DataFrame(rows).T, rets


def fit_current_vol(raw: dict, cfg):
    """Fit HAR + GBM on the latest 10 years (labels complete up to 5 days ago) and forecast
    next-5-day vol from each ticker's latest close."""
    d = stack_vol(raw, cfg.vol_span)
    feat_ok = d[VOL_X_GBM].notna().all(axis=1)
    lab_ok = feat_ok & d["y_lv"].notna()
    last = d["date"].max()
    tr = d[lab_ok & (d["date"] >= last - pd.DateOffset(years=cfg.train_years))]
    latest = d[feat_ok].sort_values("date").groupby("ticker").tail(1)
    pred = _fit_predict(tr, latest, cfg.seed)
    out = latest[["date", "ticker", "sigma_hat"]].copy()
    out["vol_har"] = np.sqrt(variance_forecast(pred["har"], pred["s2_har"]))
    out["vol_gbm"] = np.sqrt(variance_forecast(pred["gbm"], pred["s2_gbm"]))
    # Headline forecast = HAR. After the data fixes, HAR and gradient boosting are essentially tied
    # out-of-sample (R2 per year 0.277 vs 0.265), so the simpler, more transparent model leads
    # (decision log, 2026-11-02).
    out["vol_forecast"] = out["vol_har"]
    # where today's forecast sits within each ticker's own last-10-year realized 5-day vol
    hist = d[lab_ok & (d["date"] >= last - pd.DateOffset(years=cfg.train_years))]
    out["vol_pctile"] = [float((hist.loc[hist["ticker"] == t, "fwd_rv5"] < v).mean())
                         for t, v in zip(out["ticker"], out["vol_forecast"])]
    return out


# ----------------------------------------------------------------------------- regimes
def _fit_gmm(X, seed):
    mu, sd = X.mean(0), X.std(0) + 1e-9
    g = GaussianMixture(n_components=4, covariance_type="full", n_init=5, random_state=seed).fit((X - mu) / sd)
    order = np.argsort(g.means_[:, 0])          # rank components by volatility (feature 0 = lv21)
    return g, mu, sd, order


def _posterior(g, mu, sd, order, X):
    p = g.predict_proba((X - mu) / sd)[:, order]  # columns now Calm..Stressed
    return p


def regime_walk_forward(state: pd.DataFrame, cfg, smooth: int = 5, verbose=True) -> pd.DataFrame:
    """Out-of-sample regime label for every day from test_start_year on."""
    s = state.dropna(subset=REGIME_X)
    years = sorted(y for y in s.index.year.unique() if y >= cfg.test_start_year)
    out = []
    for Y in years:
        start, end = pd.Timestamp(f"{Y}-01-01"), pd.Timestamp(f"{Y + 1}-01-01")
        tr = s[(s.index < start) & (s.index >= start - pd.DateOffset(years=cfg.train_years))]
        if len(tr) < 500:
            continue
        g, mu, sd, order = _fit_gmm(tr[REGIME_X].values, cfg.seed)
        # include the few days before the year so the causal smoothing has history
        win = s[(s.index >= start - pd.Timedelta(days=14)) & (s.index < end)]
        p = pd.DataFrame(_posterior(g, mu, sd, order, win[REGIME_X].values), index=win.index)
        p = p.rolling(smooth, min_periods=1).mean()          # past-only smoothing
        p = p[p.index >= start]
        lab = p.values.argmax(1)
        out.append(pd.DataFrame({"regime_id": lab, "regime_prob": p.values.max(1)}, index=p.index))
        if verbose:
            share = np.bincount(lab, minlength=4) / len(lab)
            print(f"  {Y}: " + "  ".join(f"{REGIME_NAMES[i]} {share[i]:.0%}" for i in range(4)))
    r = pd.concat(out)
    r["regime"] = [REGIME_NAMES[i] for i in r["regime_id"]]
    return r


def current_regime(state: pd.DataFrame, cfg, smooth: int = 5) -> dict:
    s = state.dropna(subset=REGIME_X)
    last = s.index.max()
    tr = s[s.index >= last - pd.DateOffset(years=cfg.train_years)]
    g, mu, sd, order = _fit_gmm(tr[REGIME_X].values, cfg.seed)
    p = pd.DataFrame(_posterior(g, mu, sd, order, tr[REGIME_X].values), index=tr.index).rolling(smooth, min_periods=1).mean()
    lab = p.values.argmax(1)
    days_in = 1
    for k in range(len(lab) - 2, -1, -1):
        if lab[k] != lab[-1]:
            break
        days_in += 1
    # what each regime looks like (in plain units), from this latest fit
    means = g.means_[order] * sd + mu
    profile = pd.DataFrame({"regime": REGIME_NAMES, "typical_vol": np.exp(means[:, 0]),
                            "typical_3m_return": np.exp(means[:, 1]) - 1,
                            "typical_drawdown": np.exp(means[:, 2]) - 1})
    return {"as_of": str(last.date()), "regime": REGIME_NAMES[lab[-1]], "prob": float(p.values[-1].max()),
            "days_in_regime": int(days_in), "profile": profile}


def _runs(labels):
    runs, cur, n = {}, None, 0
    for v in labels:
        if v == cur:
            n += 1
        else:
            if cur is not None:
                runs.setdefault(cur, []).append(n)
            cur, n = v, 1
    runs.setdefault(cur, []).append(n)
    return runs


def run_lengths(labels: pd.Series) -> pd.Series:
    """Average length (trading days) of uninterrupted stretches in each regime."""
    return pd.Series({k: float(np.mean(v)) for k, v in _runs(labels).items()})


def episode_counts(labels: pd.Series, min_days: int = 5) -> pd.Series:
    """Number of separate stretches (of at least `min_days`) in each regime. Day counts overstate
    the evidence: 300 days from 4 episodes is really ~4 observations of what that regime does."""
    return pd.Series({k: int(sum(1 for n in v if n >= min_days)) for k, v in _runs(labels).items()})


def regime_stats(raw: dict, regimes: pd.DataFrame, cfg) -> pd.DataFrame:
    """For each ticker and regime: what followed, on days whose outcome window has completed.
    Uses only out-of-sample regime labels."""
    lens = run_lengths(regimes["regime"])
    eps = episode_counts(regimes["regime"])
    rows = []
    for t, df in raw.items():
        f = vol_features(df, cfg.vol_span).join(regimes["regime"], how="inner")
        for name in REGIME_NAMES:
            g = f[f["regime"] == name]
            g21, g5 = g.dropna(subset=["fwd_ret21"]), g.dropna(subset=["fwd_ret5"])
            if len(g21) < 20:
                continue
            rows.append({
                "ticker": t, "regime": name, "days": int(len(g)), "episodes": int(eps.get(name, 0)),
                "share": len(g) / len(f), "avg_run_days": float(lens.get(name, np.nan)),
                "fwd21_mean": float(g21["fwd_ret21"].mean()), "fwd21_median": float(g21["fwd_ret21"].median()),
                "p_up_21d": float((g21["fwd_ret21"] > 0).mean()),
                "p_drop5_21d": float((g21["fwd_ret21"] < -0.05).mean()),
                "fwd21_vol": float(g21["fwd_rv21"].mean()),
                "q10_5d": float(g5["fwd_ret5"].quantile(0.10)),
                "p_drop3_5d": float((g5["fwd_ret5"] < -0.03).mean()),
            })
    return pd.DataFrame(rows)


def transition_matrix(labels: pd.Series, horizon: int = 21) -> pd.DataFrame:
    """P(regime in `horizon` trading days | regime today), out-of-sample labels."""
    a = labels.values[:-horizon]
    b = labels.values[horizon:]
    m = pd.crosstab(pd.Series(a, name="today"), pd.Series(b, name="in_21d"), normalize="index")
    return m.reindex(index=REGIME_NAMES, columns=REGIME_NAMES).fillna(0.0)
