"""The 12 engineered features, the label, and the 64-day windows.

RULE: every feature on row t may only use information available at the CLOSE of day t.
The label on row t is about day t+1. Breaking this rule = look-ahead leakage = fake results.
"""
import numpy as np
import pandas as pd

FEATURES = [
    "ret_1", "ret_5", "ret_20",      # momentum at 3 horizons
    "vol_20", "vol_ratio",           # volatility level and whether it's rising
    "hl_range", "intraday", "gap",   # shape of today's bar
    "volume_z",                      # unusual volume
    "ma20_dist", "ma50_dist",        # distance from moving averages (trend / mean reversion)
    "rsi_14",                        # overbought / oversold
]


def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def build_features(df: pd.DataFrame, vol_span: int = 20) -> pd.DataFrame:
    o, h, l, c, v = (df[k] for k in ["Open", "High", "Low", "Close", "Volume"])
    r = np.log(c).diff()
    f = pd.DataFrame(index=df.index)
    f["ret_1"] = r
    f["ret_5"] = r.rolling(5).sum()
    f["ret_20"] = r.rolling(20).sum()
    f["vol_20"] = r.rolling(20).std()
    f["vol_ratio"] = r.rolling(5).std() / f["vol_20"]
    f["hl_range"] = np.log(h / l)
    f["intraday"] = np.log(c / o)
    f["gap"] = np.log(o / c.shift(1))
    lv = np.log(v.replace(0, np.nan)).ffill()
    f["volume_z"] = (lv - lv.rolling(20).mean()) / lv.rolling(20).std()
    f["ma20_dist"] = np.log(c / c.rolling(20).mean())
    f["ma50_dist"] = np.log(c / c.rolling(50).mean())
    f["rsi_14"] = (_rsi(c) - 50) / 50
    f = f.replace([np.inf, -np.inf], np.nan)
    # Some indices report zero volume -> volume_z is all NaN; neutral 0 instead of dropping everything
    if f["volume_z"].isna().mean() > 0.5:
        f["volume_z"] = 0.0

    # Volatility forecast for the risk map (annualized), known at close t
    f["sigma_hat"] = np.sqrt((r ** 2).ewm(span=vol_span, adjust=False).mean()) * np.sqrt(252)

    # Label and forward return: about day t+1 (NOT a feature)
    f["fwd_ret"] = c.shift(-1) / c - 1
    f["y"] = (f["fwd_ret"] > 0).astype(float)
    f.loc[f["fwd_ret"].isna(), "y"] = np.nan
    return f


def make_windows(f: pd.DataFrame, window: int):
    """Turn one ticker's feature table into (N, window, 12) samples.

    Returns X (raw, un-normalized), y, dates (the decision date t), fwd_ret, sigma_hat.
    The last row (today) has no label yet, so y can be NaN there - useful for live signals.
    """
    base = f[FEATURES].to_numpy(dtype=np.float32)
    ok = ~np.isnan(base).any(axis=1)
    first = int(np.argmax(ok))                       # first row where every feature exists
    base, idx = base[first:], f.index[first:]
    if np.isnan(base).any():                         # forward-fill rare interior gaps
        base = pd.DataFrame(base).ffill().fillna(0).to_numpy(dtype=np.float32)
    if len(base) < window:
        return None
    X = np.lib.stride_tricks.sliding_window_view(base, (window, base.shape[1]))[:, 0]
    end = idx[window - 1:]
    sub = f.loc[end]
    return {
        "X": np.ascontiguousarray(X),
        "y": sub["y"].to_numpy(dtype=np.float32),
        "date": end,
        "fwd_ret": sub["fwd_ret"].to_numpy(),
        "sigma_hat": sub["sigma_hat"].to_numpy(),
    }


def stack(per_ticker: dict) -> dict:
    """Combine every ticker's windows into one dataset (the model is trained on all of them)."""
    keys = ["X", "y", "date", "fwd_ret", "sigma_hat"]
    out = {k: [] for k in keys}
    out["ticker"] = []
    for t, w in per_ticker.items():
        for k in keys:
            out[k].append(np.asarray(w[k]))
        out["ticker"].append(np.full(len(w["y"]), t))
    out = {k: np.concatenate(v) for k, v in out.items()}
    out["date"] = pd.to_datetime(out["date"])
    return out


class Scaler:
    """Z-score each feature using statistics from the TRAINING rows only."""

    def fit(self, X):
        flat = X.reshape(-1, X.shape[-1])
        self.mu = flat.mean(0)
        self.sd = flat.std(0) + 1e-8
        return self

    def transform(self, X):
        return np.clip((X - self.mu) / self.sd, -5, 5).astype(np.float32)
