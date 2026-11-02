"""Live paper-trading ledger. Real market data, fake money.

Run once per trading day, after the close (the daily GitHub workflow does this):

    python ledger.py

1. Score: every logged position whose next trading day has now closed gets its realized return.
2. Decide: for each ticker, positions for the NEXT trading day are computed from data up to the
   latest close and appended to ledger/positions.csv. The git commit timestamp proves each
   decision was recorded before the market opened. Decisions are never edited afterwards.
3. Summarize: ledger/equity.csv (growth of $1 per strategy) and ledger/summary.json.

Strategies (equal weight across tickers, after the same costs as the backtest):
  - TCN + risk map : the live TCN model, retrained at the start of each month on the latest 10 years
  - Vol-scaled long: always long, sized by EWMA volatility (the best backtest baseline so far)
  - Buy & hold     : always fully invested
"""
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import torch

from config import Config
from data import load_all
from features import FEATURES, Scaler, build_features, make_windows, stack
from model import PlattCalibrator, TCNClassifier, predict_logits, train_tcn
from risk import position, signal_scale, vol_scaled_long

LEDGER_DIR = "ledger"
MODEL_DIR = "models"
POS = os.path.join(LEDGER_DIR, "positions.csv")
STRATS = ["TCN + risk map", "Vol-scaled long", "Buy & hold"]
POS_COLS = ["decided_at_utc", "decision_date", "ticker", "strategy", "weight", "turnover", "p_up",
            "sigma_hat", "model_version", "target_date", "ticker_return", "strategy_return", "scored_at_utc"]


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def drop_unfinished_bar(raw: dict) -> dict:
    """If run during market hours, Yahoo can return a partial bar for today. Never decide on it."""
    now_et = pd.Timestamp.now(tz="America/New_York")
    today = pd.Timestamp(now_et.date())
    if now_et.hour * 60 + now_et.minute < 16 * 60 + 15:
        return {t: df[df.index < today] for t, df in raw.items()}
    return raw


# ----------------------------------------------------------------------------- live TCN model
def _model_path():
    return os.path.join(MODEL_DIR, "tcn_live.pt")


def train_live_model(data: dict, cfg) -> dict:
    """Train on the most recent rolling window (same recipe as the backtest) and package
    everything needed for inference: weights, scaler, calibration and signal scale."""
    dates = data["date"].values
    labeled = ~np.isnan(data["y"])
    window_start = dates[labeled].max() - np.timedelta64(int(cfg.train_years * 365.25), "D")
    labeled &= dates >= window_start
    ud = np.sort(np.unique(dates[labeled]))
    cut = ud[int(len(ud) * (1 - cfg.val_frac))]
    tr, va = labeled & (dates < cut), labeled & (dates >= cut)
    sc = Scaler().fit(data["X"][tr])
    model = train_tcn(sc.transform(data["X"][tr]), data["y"][tr], sc.transform(data["X"][va]), data["y"][va], cfg)
    lg_va = predict_logits(model, sc.transform(data["X"][va]))
    cal = PlattCalibrator().fit(lg_va, data["y"][va])
    trained_through = str(pd.Timestamp(ud[-1]).date())
    return {
        "state_dict": {k: v.cpu() for k, v in model.state_dict().items()},
        "arch": {"n_features": len(FEATURES), "channels": cfg.channels, "levels": cfg.levels,
                 "k": cfg.kernel_size, "dropout": cfg.dropout},
        "scaler_mu": sc.mu, "scaler_sd": sc.sd,
        "cal_coef": float(cal.lr.coef_[0][0]), "cal_intercept": float(cal.lr.intercept_[0]),
        "signal_scale": float(signal_scale(cal.predict(lg_va), cfg)),
        "trained_through": trained_through,
        "version": f"tcn-{trained_through}",
        "n_train": int(tr.sum()), "n_val": int(va.sum()),
        "trained_at_utc": now_utc(),
    }


def save_model(m: dict):
    os.makedirs(MODEL_DIR, exist_ok=True)
    torch.save(m, _model_path())
    meta = {k: v for k, v in m.items() if k not in ("state_dict", "scaler_mu", "scaler_sd")}
    with open(os.path.join(MODEL_DIR, "tcn_live.json"), "w") as f:
        json.dump(meta, f, indent=2)


def load_model():
    if not os.path.exists(_model_path()):
        return None
    return torch.load(_model_path(), weights_only=False)


def needs_retrain(m, decision_date: pd.Timestamp) -> bool:
    """Monthly retrain: retrain when there is no model, or the model was trained for an earlier
    month than the latest close (i.e. exactly once, on the first run of each new month)."""
    if m is None or "trained_for_month" not in m:
        return True
    return pd.Period(m["trained_for_month"], "M") < decision_date.to_period("M")


def predict_p_up(m: dict, X: np.ndarray) -> np.ndarray:
    a = m["arch"]
    net = TCNClassifier(a["n_features"], a["channels"], a["levels"], a["k"], a["dropout"])
    net.load_state_dict(m["state_dict"])
    Xs = np.clip((X - m["scaler_mu"]) / m["scaler_sd"], -5, 5).astype(np.float32)
    logits = predict_logits(net, Xs)
    return 1 / (1 + np.exp(-(m["cal_coef"] * logits + m["cal_intercept"])))


# ----------------------------------------------------------------------------- ledger
TEXT_COLS = ["decided_at_utc", "decision_date", "ticker", "strategy", "model_version", "target_date", "scored_at_utc"]
NUM_COLS = ["weight", "turnover", "p_up", "sigma_hat", "ticker_return", "strategy_return"]


def load_positions() -> pd.DataFrame:
    if os.path.exists(POS):
        pos = pd.read_csv(POS, dtype={c: str for c in TEXT_COLS}, keep_default_na=False)
    else:
        pos = pd.DataFrame(columns=POS_COLS)
    for c in TEXT_COLS:
        pos[c] = pos[c].fillna("").astype(str)
    for c in NUM_COLS:
        pos[c] = pd.to_numeric(pos[c], errors="coerce").astype(float)
    return pos


def score(pos: pd.DataFrame, raw: dict, cfg) -> int:
    """Fill in realized returns for positions whose next trading day has closed."""
    n = 0
    for i in pos.index[pos["target_date"] == ""]:
        df = raw.get(pos.at[i, "ticker"])
        if df is None:
            continue
        d0 = pd.Timestamp(pos.at[i, "decision_date"])
        after = df.index[df.index > d0]
        if d0 not in df.index or len(after) == 0:
            continue
        d1 = after[0]
        r = float(df.at[d1, "Close"] / df.at[d0, "Close"] - 1)
        w, turn = float(pos.at[i, "weight"]), float(pos.at[i, "turnover"])
        pos.at[i, "target_date"] = str(d1.date())
        pos.at[i, "ticker_return"] = r
        pos.at[i, "strategy_return"] = w * r - cfg.cost_bps / 1e4 * turn
        pos.at[i, "scored_at_utc"] = now_utc()
        n += 1
    return n


def decide(pos: pd.DataFrame, raw: dict, cfg) -> tuple:
    """Append next-day positions for every ticker whose latest close has no decision yet."""
    per, last_close = {}, {}
    for t, df in raw.items():
        f = build_features(df, cfg.vol_span)
        w = make_windows(f, cfg.window)
        if w is not None:
            per[t] = w
            last_close[t] = df.index.max()
    data = stack(per)
    m = load_model()
    latest = max(last_close.values())
    retrained = False
    if needs_retrain(m, latest):
        print(f"Training live TCN (no model, or new month) on data through {latest.date()} ...")
        m = train_live_model(data, cfg)
        m["trained_for_month"] = str(latest.to_period("M"))
        save_model(m)
        retrained = True
    new = []
    for t in per:
        d = last_close[t]
        ds = str(d.date())
        if ((pos["decision_date"] == ds) & (pos["ticker"] == t)).any():
            continue                                    # already decided for this close: never overwrite
        i = np.where((data["ticker"] == t) & (data["date"] == d))[0]
        if len(i) == 0:
            continue
        i = i[0]
        sig = float(data["sigma_hat"][i])
        p = float(predict_p_up(m, data["X"][i:i + 1])[0])
        weights = {
            "TCN + risk map": float(position(np.array([p]), np.array([sig]), cfg, m["signal_scale"])[0]),
            "Vol-scaled long": float(vol_scaled_long(np.array([sig]), cfg)[0]),
            "Buy & hold": 1.0,
        }
        for s, w in weights.items():
            prev = pos[(pos["ticker"] == t) & (pos["strategy"] == s)]
            w_prev = float(prev.iloc[-1]["weight"]) if len(prev) else 0.0
            new.append({"decided_at_utc": now_utc(), "decision_date": ds, "ticker": t, "strategy": s,
                        "weight": round(w + 0.0, 6), "turnover": round(abs(w - w_prev), 6),
                        "p_up": round(p, 6) if s == "TCN + risk map" else np.nan,
                        "sigma_hat": round(sig, 6), "model_version": m["version"] if s == "TCN + risk map" else "",
                        "target_date": "", "ticker_return": np.nan, "strategy_return": np.nan, "scored_at_utc": ""})
    if new:
        pos = pd.concat([pos, pd.DataFrame(new)], ignore_index=True)
    return pos, len(new), m, retrained


def summarize(pos: pd.DataFrame, m: dict):
    scored = pos[pos["strategy_return"].notna() & (pos["target_date"] != "")].copy()
    eq_rows, summ = [], {"updated_utc": now_utc(), "model_version": m["version"] if m else None,
                         "model_trained_through": m["trained_through"] if m else None, "strategies": []}
    # Growth of $1 starts at 1.0 on the first decision date (before any session is scored)
    first_dec = pos["decision_date"].min() if len(pos) else None
    if first_dec:
        for s in STRATS:
            eq_rows.append({"date": first_dec, "strategy": s, "value": 1.0})
    if len(scored):
        daily = scored.groupby(["target_date", "strategy"])["strategy_return"].mean().unstack()
        daily = daily.sort_index()
        eq = (1 + daily.fillna(0)).cumprod()
        for d, row in eq.iterrows():
            for s in eq.columns:
                eq_rows.append({"date": d, "strategy": s, "value": round(float(row[s]), 6)})
        for s in STRATS:
            if s in daily:
                r = daily[s].dropna()
                summ["strategies"].append({
                    "strategy": s, "days": int(len(r)), "total_return": float(eq[s].iloc[-1] - 1),
                    "best_day": float(r.max()), "worst_day": float(r.min()),
                    "hit_rate": float((r > 0).mean()),
                })
        summ["first_scored"] = str(daily.index.min())
        summ["last_scored"] = str(daily.index.max())
    else:
        summ["strategies"] = [{"strategy": s, "days": 0, "total_return": 0.0, "best_day": None,
                               "worst_day": None, "hit_rate": None} for s in STRATS]
    latest_dec = pos["decision_date"].max() if len(pos) else None
    summ["latest_decision_date"] = latest_dec
    if latest_dec:
        cur = pos[pos["decision_date"] == latest_dec]
        summ["current_positions"] = [
            {"ticker": r["ticker"], "strategy": r["strategy"], "weight": float(r["weight"]),
             "p_up": None if pd.isna(r["p_up"]) else float(r["p_up"])} for _, r in cur.iterrows()]
    pd.DataFrame(eq_rows, columns=["date", "strategy", "value"]).to_csv(os.path.join(LEDGER_DIR, "equity.csv"), index=False)
    with open(os.path.join(LEDGER_DIR, "summary.json"), "w") as f:
        json.dump(summ, f, indent=2)
    return summ


def main():
    cfg = Config()
    os.makedirs(LEDGER_DIR, exist_ok=True)
    print("Data:")
    raw = drop_unfinished_bar(load_all(cfg.tickers, cfg.start, cfg.data_dir, refresh=True))
    pos = load_positions()
    n_scored = score(pos, raw, cfg)
    pos, n_new, m, retrained = decide(pos, raw, cfg)
    pos[POS_COLS].to_csv(POS, index=False)
    summ = summarize(pos, m)
    print(f"\nScored {n_scored} positions; logged {n_new} new positions"
          f"{' (model retrained)' if retrained else ''}. Model: {m['version']}")
    for s in summ["strategies"]:
        print(f"  {s['strategy']:<16} {s['days']:>3} days  total {s['total_return']:+.2%}")
    for p in summ.get("current_positions", []):
        extra = f"  p_up {p['p_up']:.3f}" if p["p_up"] is not None else ""
        print(f"  next day {p['ticker']:<8} {p['strategy']:<16} weight {p['weight']:.2f}{extra}")


if __name__ == "__main__":
    main()
