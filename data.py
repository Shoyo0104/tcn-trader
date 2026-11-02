"""Download, cache and quality-check real daily OHLCV data (Yahoo Finance via yfinance)."""
import os
import time

import numpy as np
import pandas as pd

COLS = ["Open", "High", "Low", "Close", "Volume"]


def _download(ticker: str, start: str, tries: int = 3) -> pd.DataFrame:
    import yfinance as yf
    last_err = None
    for i in range(tries):
        try:
            df = yf.download(ticker, start=start, auto_adjust=True, progress=False, threads=False)
            if isinstance(df.columns, pd.MultiIndex):        # newer yfinance returns (field, ticker)
                df.columns = df.columns.get_level_values(0)
            if not df.empty:
                return df[COLS]
        except Exception as e:                               # network hiccups: retry with backoff
            last_err = e
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"No data downloaded for {ticker} ({last_err}). Check the symbol or your connection.")


def _is_stale(df: pd.DataFrame) -> bool:
    """Cache is stale if it doesn't include the most recent completed business day."""
    last_bday = (pd.Timestamp.now().normalize() - pd.offsets.BDay(1))
    return df.index.max() < last_bday


def load_ticker(ticker: str, start: str, data_dir: str = "data", refresh: bool = False) -> pd.DataFrame:
    """Daily bars for one ticker, adjusted for splits/dividends. Cached to data_dir/<ticker>.csv
    and re-downloaded automatically when the cache is behind (so live runs always see yesterday)."""
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, f"{ticker.replace('^', '_')}.csv")
    df = None
    if os.path.exists(path) and not refresh:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        if _is_stale(df):
            df = None
    if df is None:
        # Full re-download (not append): adjusted prices change whenever a dividend/split happens,
        # so mixing old and new adjusted history would corrupt returns.
        df = _download(ticker, start)
        df.to_csv(path)
    df = df[COLS].dropna()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df[df.index >= pd.Timestamp(start)]


def quality_report(ticker: str, df: pd.DataFrame) -> list:
    """Flags data problems that would silently poison features."""
    issues = []
    if (df[["Open", "High", "Low", "Close"]] <= 0).any().any():
        issues.append("non-positive prices")
    if (df["High"] < df[["Open", "Close", "Low"]].max(axis=1) - 1e-9).any():
        issues.append("High below Open/Close/Low on some days")
    r = np.log(df["Close"]).diff().abs()
    big = r[r > 0.25]
    if len(big):
        issues.append(f"{len(big)} daily moves >25% (check splits): {', '.join(str(d.date()) for d in big.index[:3])}")
    gaps = df.index.to_series().diff().dt.days
    if (gaps > 7).any():
        issues.append(f"{int((gaps > 7).sum())} gaps longer than a week")
    if (df["Volume"] == 0).mean() > 0.5:
        issues.append("volume mostly zero (volume feature will be neutral)")
    years = (df.index.max() - df.index.min()).days / 365.25
    if years < 5:
        issues.append(f"only {years:.1f} years of history (need 5+)")
    return issues


def load_all(tickers, start, data_dir="data", refresh=False, verbose=True) -> dict:
    out = {}
    for t in tickers:
        df = load_ticker(t, start, data_dir, refresh)
        if verbose:
            issues = quality_report(t, df)
            span = f"{df.index.min().date()} -> {df.index.max().date()} ({len(df)} days)"
            print(f"  {t:<8} {span}" + (f"   WARNING: {'; '.join(issues)}" if issues else ""))
        out[t] = df
    return out
