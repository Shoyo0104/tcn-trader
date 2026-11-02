"""Turn reports/ and ROADMAP.md into small JSON files for the project dashboard.

  python dashboard_export.py            # writes dashboard_data/*.json

Every number on the dashboard comes from these files, which come only from real backtest
reports in reports/ and the checklist in ROADMAP.md.
"""
import glob
import gzip
import json
import os
import re

import numpy as np
import pandas as pd

from backtest import period_auc, strategy_returns
from config import Config

OUT = "dashboard_data"
STRATS = ["Buy & hold", "Vol-scaled long", "Logistic + risk map", "TCN + risk map"]

# Placebo passes if the shuffled-label model shows no edge: AUC close to 0.5 and the
# TCN-vs-vol-scaled gap indistinguishable from luck.
PLACEBO_AUC_TOL = 0.02
PLACEBO_MIN_P_NOT_BETTER = 0.20


def _num(s):
    return None if s is None or (isinstance(s, float) and np.isnan(s)) else float(s)


def parse_report(folder):
    """Read one report folder into a dict of everything the dashboard needs."""
    name = os.path.basename(folder.rstrip("/"))
    # Folder names: <date>[-<HHMM UTC>]-<freq>-<mode>, e.g. 2026-11-02-1145-Y-real
    m = re.match(r"(\d{4}-\d{2}-\d{2})(?:-(\d{4}))?-([MY])-(real|placebo)$", name)
    if not m:
        return None
    rep = {"run": name, "date": m.group(1), "time": m.group(2) or "0000", "freq": m.group(3),
           "mode": m.group(4), "folder": folder}
    summ = os.path.join(folder, "summary.md")
    if not os.path.exists(summ):
        return None
    text = open(summ).read()
    for key in ["test_period", "commit", "device", "samples"]:
        mm = re.search(rf"\*\*{key}:\*\* (.+)", text)
        rep[key] = mm.group(1).strip() if mm else None
    mm = re.search(r"mean Sharpe gap ([+-]?[\d.]+); share of bootstrap draws where TCN is NOT better: (\d+)%", text)
    rep["sharpe_gap"] = float(mm.group(1)) if mm else None
    rep["p_not_better"] = int(mm.group(2)) / 100 if mm else None
    mm = re.search(r"-> \*\*(.+?)\*\*", text)
    rep["verdict"] = mm.group(1) if mm else None

    perf = pd.read_csv(os.path.join(folder, "performance.csv"), index_col=0)
    predq = pd.read_csv(os.path.join(folder, "prediction_quality.csv"), index_col=0)
    rep["perf"] = perf
    rep["predq"] = predq
    yp = os.path.join(folder, "yearly_sharpe.csv")
    rep["yearly"] = pd.read_csv(yp, index_col=0) if os.path.exists(yp) else None
    pp = os.path.join(folder, "predictions.csv.gz")
    if not os.path.exists(pp):
        pp = os.path.join(folder, "predictions.csv")
    rep["pred"] = pd.read_csv(pp, parse_dates=["date"]) if os.path.exists(pp) else None
    # Within-period AUC (older reports don't have the column: compute it from their predictions)
    col = "AUC (avg per period)"
    if col not in predq.columns:
        predq[col] = np.nan
        predq.loc["Always 'up' (base rate)", col] = 0.5
        if rep["pred"] is not None:
            for name, pc in [("Logistic", "p_lr"), ("TCN (calibrated)", "p_tcn")]:
                if name in predq.index:
                    predq.loc[name, col] = period_auc(rep["pred"], pc)
    return rep


def run_row(r):
    perf, predq = r["perf"], r["predq"]
    g = lambda s, c: _num(perf.loc[s, c]) if s in perf.index else None
    return {
        "run": r["run"], "date": r["date"], "time_utc": f"{r['time'][:2]}:{r['time'][2:]}",
        "mode": r["mode"].capitalize(), "freq": r["freq"],
        "retrain": {"Y": "Yearly", "M": "Monthly"}[r["freq"]],
        "test_period": r["test_period"], "commit": r["commit"],
        "tcn_sharpe": g("TCN + risk map", "Sharpe"), "lr_sharpe": g("Logistic + risk map", "Sharpe"),
        "vol_sharpe": g("Vol-scaled long", "Sharpe"), "bh_sharpe": g("Buy & hold", "Sharpe"),
        "tcn_auc": _num(predq.loc["TCN (calibrated)", "AUC (avg per period)"]) if "TCN (calibrated)" in predq.index else None,
        "tcn_auc_pooled": _num(predq.loc["TCN (calibrated)", "AUC"]) if "TCN (calibrated)" in predq.index else None,
        "sharpe_gap": r["sharpe_gap"], "p_not_better": r["p_not_better"], "verdict": r["verdict"],
    }


def equity_rows(r, cfg):
    """Weekly-sampled growth of $1 per strategy (recomputed from the saved predictions)."""
    if r["pred"] is None:
        return []
    rets, _ = strategy_returns(r["pred"], cfg)
    eq = (1 + rets).cumprod()
    eq = eq.resample("W-FRI").last().dropna(how="all")
    rows = []
    for d, row in eq.iterrows():
        for s in STRATS:
            if s in row and not np.isnan(row[s]):
                rows.append({"date": d.strftime("%Y-%m-%d"), "strategy": s, "value": round(float(row[s]), 5)})
    return rows


def calib_rows(r):
    if r["pred"] is None:
        return []
    rows = []
    for col, model in [("p_tcn", "TCN (calibrated)"), ("p_lr", "Logistic")]:
        bins = pd.qcut(r["pred"][col], 10, duplicates="drop")
        g = r["pred"].groupby(bins, observed=True).agg(p=(col, "mean"), actual=("y", "mean"), n=("y", "size"))
        for i, (_, row) in enumerate(g.iterrows()):
            rows.append({"model": model, "decile": i + 1, "predicted": round(float(row["p"]), 4),
                         "actual": round(float(row["actual"]), 4), "n": int(row["n"])})
    return rows


def roadmap_rows(path="ROADMAP.md"):
    rows, phase, current = [], None, False
    for line in open(path):
        h = re.match(r"## (Phase \d+) - (.+)", line)
        if h:
            phase = f"{h.group(1)}: {h.group(2).split('(')[0].strip()}"
            current = "(now)" in h.group(2)
            continue
        if line.startswith("## "):
            phase = None
        c = re.match(r"- \[( |x)\] (.+)", line)
        if c and phase:
            rows.append({"order": len(rows) + 1, "phase": phase, "item": c.group(2).strip(),
                         "done": c.group(1) == "x", "status": "Done" if c.group(1) == "x" else "To do",
                         "current": current})
    return rows


def _latest_folder(kind):
    """Newest reports/<date>-<HHMM>-<kind>/ folder (kind: vol, volplacebo, insights)."""
    found = []
    for f in glob.glob(f"reports/*-{kind}/"):
        m = re.match(rf"(\d{{4}}-\d{{2}}-\d{{2}})-(\d{{4}})-{kind}$", os.path.basename(f.rstrip("/")))
        if m:
            found.append((m.group(1), m.group(2), f))
    return sorted(found)[-1] if found else None


def insight_exports():
    out = {k: [] for k in ["vol_metrics", "vol_strategy", "vol_yearly", "insight_summary", "ticker_insights",
                           "regime_stats", "regime_history", "regime_transitions", "regime_profile"]}
    for kind, mode in [("vol", "Real"), ("volplacebo", "Placebo")]:
        lf = _latest_folder(kind)
        if not lf:
            continue
        date, hhmm, f = lf
        met = pd.read_csv(os.path.join(f, "vol_metrics.csv"), index_col=0)
        for m, r in met.iterrows():
            out["vol_metrics"].append({"mode": mode, "model": m, "r2": _num(r["R2 (log vol)"]),
                                       "r2_year": _num(r["R2 (avg per year)"]), "rmse": _num(r["RMSE (log vol)"]),
                                       "qlike": _num(r["QLIKE"]), "corr": _num(r["Correlation"]),
                                       "run": f"{date} {hhmm[:2]}:{hhmm[2:]}"})
        if mode == "Real":
            st = pd.read_csv(os.path.join(f, "vol_strategy.csv"), index_col=0)
            for m, r in st.iterrows():
                out["vol_strategy"].append({"model": m, "cagr": _num(r["CAGR"]), "volatility": _num(r["Volatility"]),
                                            "sharpe": _num(r["Sharpe"]), "max_drawdown": _num(r["Max drawdown"]),
                                            "vol_miss": _num(r["Yearly vol miss"]), "worst_month": _num(r["Worst month"])})
            yr = pd.read_csv(os.path.join(f, "vol_yearly_r2.csv"), index_col=0)
            for y, r in yr.iterrows():
                for m in yr.columns:
                    out["vol_yearly"].append({"year": str(y), "model": m, "r2": round(float(r[m]), 4)})
    lf = _latest_folder("insights")
    if lf:
        date, hhmm, f = lf
        ins = json.load(open(os.path.join(f, "insights.json")))
        s = ins["summary"]
        s["run"] = f"{date} {hhmm[:2]}:{hhmm[2:]}"
        out["insight_summary"] = [s]
        out["ticker_insights"] = ins["tickers"]
        out["regime_stats"] = pd.read_csv(os.path.join(f, "regime_stats.csv")).to_dict("records")
        h = pd.read_csv(os.path.join(f, "regime_history.csv"), parse_dates=["date"])
        out["regime_history"] = [{"date": d.strftime("%Y-%m-%d"), "regime": g, "close": round(float(c), 3)}
                                 for d, g, c in zip(h["date"], h["regime"], h["close"])]
        tr = pd.read_csv(os.path.join(f, "regime_transitions.csv"), index_col=0)
        out["regime_transitions"] = [{"today": a, "in_21d": b, "prob": round(float(tr.loc[a, b]), 4)}
                                     for a in tr.index for b in tr.columns]
        out["regime_profile"] = pd.read_csv(os.path.join(f, "regime_profile.csv")).to_dict("records")
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    cfg = Config()
    reports = [r for r in (parse_report(f) for f in sorted(glob.glob("reports/*/"))) if r]
    reports.sort(key=lambda r: (r["date"], r["time"], r["mode"]))
    real = [r for r in reports if r["mode"] == "real"]
    placebo = [r for r in reports if r["mode"] == "placebo"]
    latest, latest_p = (real[-1] if real else None), (placebo[-1] if placebo else None)

    runs = [run_row(r) for r in reports]

    perf, predq = [], []
    for r in [x for x in (latest, latest_p) if x]:
        for s, row in r["perf"].iterrows():
            perf.append({"mode": r["mode"], "strategy": s, "cagr": _num(row["CAGR"]),
                         "volatility": _num(row["Volatility"]), "sharpe": _num(row["Sharpe"]),
                         "max_drawdown": _num(row["Max drawdown"]), "exposure": _num(row["Avg exposure"]),
                         "turnover": _num(row["Turnover/yr"])})
        for s, row in r["predq"].iterrows():
            predq.append({"mode": r["mode"], "model": s, "auc_period": _num(row["AUC (avg per period)"]),
                          "auc": _num(row["AUC"]),
                          "accuracy": _num(row["Accuracy"]), "brier": _num(row["Brier"]),
                          "log_loss": _num(row["Log loss"])})

    yearly = []
    if latest is not None and latest["yearly"] is not None:
        for y, row in latest["yearly"].iterrows():
            for s in STRATS:
                if s in row:
                    yearly.append({"year": str(int(y)), "strategy": s, "sharpe": round(float(row[s]), 3)})

    road = roadmap_rows()
    p1 = [r for r in road if r["phase"].startswith("Phase 1")]
    status = []
    if latest is not None:
        lr = run_row(latest)
        lp = run_row(latest_p) if latest_p else {}
        placebo_pass = None
        if latest_p is not None and lp.get("tcn_auc") is not None and lp.get("p_not_better") is not None:
            placebo_pass = bool(abs(lp["tcn_auc"] - 0.5) <= PLACEBO_AUC_TOL
                                and lp["p_not_better"] >= PLACEBO_MIN_P_NOT_BETTER)
        tperf = latest["perf"].loc["TCN + risk map"]
        status.append({
            "latest_run": latest["date"], "test_period": latest["test_period"],
            "retrain": {"Y": "Yearly", "M": "Monthly"}[latest["freq"]],
            "verdict": latest["verdict"], "p_not_better": latest["p_not_better"],
            "sharpe_gap": latest["sharpe_gap"], "tcn_sharpe": lr["tcn_sharpe"], "bh_sharpe": lr["bh_sharpe"],
            "vol_sharpe": lr["vol_sharpe"], "lr_sharpe": lr["lr_sharpe"],
            "tcn_cagr": _num(tperf["CAGR"]), "tcn_max_drawdown": _num(tperf["Max drawdown"]),
            "tcn_auc": lr["tcn_auc"], "tcn_auc_pooled": lr["tcn_auc_pooled"], "placebo_auc": lp.get("tcn_auc"),
            "placebo_p_not_better": lp.get("p_not_better"),
            "placebo_check": {True: "Passed", False: "Failed", None: "Not run"}[placebo_pass],
            "phase1_done": sum(r["done"] for r in p1), "phase1_total": len(p1),
        })

    files = {"status": status, "runs": runs, "perf": perf, "predq": predq, "yearly": yearly,
             "equity": equity_rows(latest, cfg) if latest else [],
             "calibration": calib_rows(latest) if latest else [], "roadmap": road}
    files.update(insight_exports())
    for k, v in files.items():
        with open(os.path.join(OUT, f"{k}.json"), "w") as f:
            json.dump(v, f, separators=(",", ":"))
        print(f"  {k:<12} {len(v):>5} rows")


if __name__ == "__main__":
    main()
