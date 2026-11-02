"""Download and cache daily OHLCV data. Also a synthetic generator for testing the pipeline."""
import os

import numpy as np
import pandas as pd

COLS = ["Open", "High", "Low", "Close", "Volume"]


def load_ticker(ticker: str, start: str, data_dir: str = "data", refresh: bool = False) -> pd.DataFrame:
    """Daily bars for one ticker, adjusted for splits/dividends. Cached to data_dir/<ticker>.csv."""
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, f"{ticker.replace('^', '_')}.csv")
    if os.path.exists(path) and not refresh:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
    else:
        import yfinance as yf
        df = yf.download(ticker, start=start, auto_adjust=True, progress=False)
        if df.empty:
            raise RuntimeError(f"No data downloaded for {ticker}. Check the symbol or your connection.")
        if isinstance(df.columns, pd.MultiIndex):       # newer yfinance returns (field, ticker)
            df.columns = df.columns.get_level_values(0)
        df = df[COLS]
        df.to_csv(path)
    df = df[COLS].dropna()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df[df.index >= pd.Timestamp(start)]


def load_all(tickers, start, data_dir="data", refresh=False) -> dict:
    return {t: load_ticker(t, start, data_dir, refresh) for t in tickers}


def make_synthetic(n_tickers=3, start="2005-01-01", end="2026-10-30", edge=0.0, seed=0) -> dict:
    """Fake OHLCV data for testing.

    edge = 0     -> pure random walk. A correct pipeline should find NOTHING here.
    edge > 0     -> tomorrow's return leans slightly toward the sign of the last 5 days' trend.
                    A correct pipeline should find something here.
    Running both is a great sanity check that you don't have leakage.
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, end)
    n = len(dates)
    out = {}
    for k in range(n_tickers):
        vol = 0.012 * np.exp(np.cumsum(rng.normal(0, 0.03, n)) * 0.3)   # drifting volatility regimes
        vol = np.clip(vol, 0.005, 0.04)
        r = np.zeros(n)
        for t in range(n):
            trend = np.sign(r[max(0, t - 5):t].sum()) if t > 5 else 0.0
            r[t] = 0.0003 + edge * trend * vol[t] + vol[t] * rng.standard_normal()
        close = 100 * np.exp(np.cumsum(r))
        gap = rng.normal(0, 0.3, n) * vol
        open_ = close * np.exp(-r + gap)                 # open sits between yesterday's close and today's
        hi = np.maximum(open_, close) * np.exp(np.abs(rng.normal(0, 0.5, n)) * vol)
        lo = np.minimum(open_, close) * np.exp(-np.abs(rng.normal(0, 0.5, n)) * vol)
        volu = np.exp(15 + rng.normal(0, 0.3, n) + 20 * np.abs(r))
        out[f"SYN{k}"] = pd.DataFrame(
            {"Open": open_, "High": hi, "Low": lo, "Close": close, "Volume": volu}, index=dates
        )
    return out
