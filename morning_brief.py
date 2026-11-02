"""Write the morning brief from the latest ledger and insights (real data only).

    python morning_brief.py          # prints it and saves reports/morning_brief.md
"""
import glob
import json
import os
import re


def _latest_insights():
    cands = []
    for f in glob.glob("reports/*insights/insights.json"):
        summ = open(os.path.join(os.path.dirname(f), "summary.md")).read()
        m = re.search(r"\*\*run_utc:\*\* (\d{4}-\d{2}-\d{2} \d{2}:\d{2})", summ)
        cands.append((m.group(1) if m else "", f))
    return json.load(open(sorted(cands)[-1][1])) if cands else None


def pct(x, signed=False):
    return "n/a" if x is None else (f"{x:+.1%}" if signed else f"{x:.0%}")


def main():
    lines = ["# TCN Trader morning brief", ""]
    ins = _latest_insights()
    if ins:
        s = ins["summary"]
        lines += [f"## Market (as of the {s['as_of']} close)", "",
                  f"- **Regime: {s['regime']}** ({pct(s['regime_prob'])} confidence, day {s['days_in_regime']}). "
                  f"Stretches like this last ~{s['avg_run_days']:.0f} trading days; "
                  f"{pct(s['p_same_regime_21d'])} were still {s['regime']} 21 days later."]
        for t in ins["tickers"]:
            lines.append(f"- **{t['ticker']}**: next-week volatility forecast {pct(t['vol_forecast_5d'])} "
                         f"(higher than {pct(t['vol_pctile'])} of the last 10 years). After past {s['regime']} days "
                         f"({t.get('regime_episodes') or '?'} episodes): next 21 days averaged {pct(t['fwd21_mean'], True)}, "
                         f"fell over 5% in {pct(t['p_drop5_21d'])} of cases.")
        lines.append("")
    lp = os.path.join("ledger", "summary.json")
    if os.path.exists(lp):
        L = json.load(open(lp))
        lines += ["## Paper trading", ""]
        if L.get("strategies"):
            lines.append(f"Scored days: {L.get('first_scored')} to {L.get('last_scored')}.")
            for st in L["strategies"]:
                lines.append(f"- {st['strategy']}: {st['total_return']:+.2%} over {st['days']} day(s); "
                             f"worst day {st['worst_day']:+.2%}")
        else:
            lines.append("No positions scored yet (the first ones are scored after the next close).")
        cur = L.get("current_positions", [])
        if cur:
            lines += ["", f"**Positions for the next session** (decided from the {L.get('latest_decision_date')} close, "
                          f"model {L.get('model_version')}):", ""]
            by_t = {}
            for p in cur:
                by_t.setdefault(p["ticker"], {})[p["strategy"]] = p
            for t, d in by_t.items():
                tcn = d.get("TCN + risk map", {})
                lines.append(f"- {t}: TCN {tcn.get('weight', 0):.0%} invested (P(up) {tcn.get('p_up') or 0:.1%}) · "
                             f"vol-scaled {d.get('Vol-scaled long', {}).get('weight', 0):.0%} · buy & hold 100%")
        lines.append("")
    lines.append("_Paper trading only. Statistics are out-of-sample; small episode counts mean rough estimates._")
    text = "\n".join(lines)
    os.makedirs("reports", exist_ok=True)
    with open(os.path.join("reports", "morning_brief.md"), "w") as f:
        f.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
