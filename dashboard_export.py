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

from backtest import strategy_returns
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
    m = re.match(r"(\d{4}-\d{2}-\d{2})(?:-\d{4})?-([MY])-(real|placebo)$", name)
    if not m:
        return None
    rep = {"run": name, "date": m.group(1), "freq": m.group(2), "mode": m.group(3), "folder": folder}
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
    return rep


def run_row(r):
    perf, predq = r["perf"], r["predq"]
    g = lambda s, c: _num(perf.loc[s, c]) if s in perf.index else None
    return {
        "run": r["run"], "date": r["date"], "mode": r["mode"].capitalize(), "freq": r["freq"],
        "retrain": {"Y": "Yearly", "M": "Monthly"}[r["freq"]],
        "test_period": r["test_period"], "commit": r["commit"],
        "tcn_sharpe": g("TCN + risk map", "Sharpe"), "lr_sharpe": g("Logistic + risk map", "Sharpe"),
        "vol_sharpe": g("Vol-scaled long", "Sharpe"), "bh_sharpe": g("Buy & hold", "Sharpe"),
        "tcn_auc": _num(predq.loc["TCN (calibrated)", "AUC"]) if "TCN (calibrated)" in predq.index else None,
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
    rows, phase = [], None
    for line in open(path):
        h = re.match(r"## (Phase \d+) - (.+)", line)
        if h:
            phase = f"{h.group(1)}: {h.group(2).split('(')[0].strip()}"
            continue
        if line.startswith("## "):
            phase = None
        c = re.match(r"- \[( |x)\] (.+)", line)
        if c and phase:
            rows.append({"order": len(rows) + 1, "phase": phase, "item": c.group(2).strip(),
                         "done": c.group(1) == "x", "status": "Done" if c.group(1) == "x" else "To do"})
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    cfg = Config()
    reports = [r for r in (parse_report(f) for f in sorted(glob.glob("reports/*/"))) if r]
    reports.sort(key=lambda r: (r["date"], r["run"]))
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
            predq.append({"mode": r["mode"], "model": s, "auc": _num(row["AUC"]),
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
            "tcn_auc": lr["tcn_auc"], "placebo_auc": lp.get("tcn_auc"),
            "placebo_p_not_better": lp.get("p_not_better"),
            "placebo_check": {True: "Passed", False: "Failed", None: "Not run"}[placebo_pass],
            "phase1_done": sum(r["done"] for r in p1), "phase1_total": len(p1),
        })

    files = {"status": status, "runs": runs, "perf": perf, "predq": predq, "yearly": yearly,
             "equity": equity_rows(latest, cfg) if latest else [],
             "calibration": calib_rows(latest) if latest else [], "roadmap": road}
    for k, v in files.items():
        with open(os.path.join(OUT, f"{k}.json"), "w") as f:
            json.dump(v, f, separators=(",", ":"))
        print(f"  {k:<12} {len(v):>5} rows")


if __name__ == "__main__":
    main()
