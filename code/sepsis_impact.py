"""Clinical impact of each deployment policy, per 100 ICU admissions at the target hospital.

Reads the per-run results of E3v2 (or E4 / an extended tag) and translates the primary
criterion into numbers a clinician reads directly:

  missed septic       septic patients not alerted in [onset - 12 h, onset + 3 h], per 100 admissions
  excess missed       missed septic patients beyond what the sensitivity target allows
  false-alerted       non-septic patients alerted at least once, per 100 admissions
  alarms/patient-day  new alarms per patient-day (from the run files)
  unsafe per 100      deployments (hospitals) out of 100 that switch on an unsafe model

When a policy switches nothing on (CAB's BLOCK), the hospital keeps its bedside score: the
modified NEWS2 >= 5 that the runs record as the fallback. Its alarms are counted the same way.

Prevalence = share of septic patients at the target hospital (cohort table in E1_E2_report.md:
A 8.8%, B 5.7%); override with --prevalence.

Run from the repository root (needs only outputs/sepsis/<tag>_runs.csv):
    python code\\sepsis_impact.py                 (E3v2)
    python code\\sepsis_impact.py --tag E4enr50
Writes outputs/sepsis/<tag>_impact.csv and <tag>_impact.md.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "outputs" / "sepsis"
PRIMARY = (0.80, 0.05)
PREVALENCE = {"A": 0.088, "B": 0.057}
POLICIES = ["AS-IS", "LABEL-FREE", "RECALIBRATE", "FINE-TUNE", "RETRAIN", "CAB"]


def per_run(runs, prevalence, s_star):
    """One row per run with the effective (deployed or fallback) patient-level rates."""
    r = runs.copy()
    act = r["activated"].astype(str).str.lower().eq("true")
    r["activated"] = act
    r["unsafe"] = r["unsafe"].astype(str).str.lower().eq("true")
    r["eff_sens"] = np.where(act, r["sens"], r["fallback_sens"])
    r["eff_fa"] = np.where(act, r["false_alert"], r["fallback_false_alert"])
    pi = r["direction"].str.split("->").str[1].map(prevalence)
    r["prevalence"] = pi
    r["missed_septic"] = 100 * pi * (1 - r["eff_sens"])
    r["excess_missed"] = 100 * pi * np.clip(s_star - r["eff_sens"], 0, None)
    r["false_alerted"] = 100 * (1 - pi) * r["eff_fa"]
    return r


def summarise(r):
    g = r.groupby(["direction", "n_labelled", "policy"], sort=True)
    s = g.agg(reps=("rep", "size"), activated_pct=("activated", "mean"),
              unsafe_per_100=("unsafe", "mean"), missed_septic=("missed_septic", "mean"),
              excess_missed=("excess_missed", "mean"), false_alerted=("false_alerted", "mean"),
              alarms_per_day=("alarms_per_day", "mean")).reset_index()
    s["activated_pct"] *= 100
    s["unsafe_per_100"] *= 100
    s["policy"] = pd.Categorical(s["policy"], POLICIES, ordered=True)
    return s.sort_values(["direction", "n_labelled", "policy"]).reset_index(drop=True)


def versus_cab(s):
    """Per direction and budget: comparator minus CAB (positive = CAB better)."""
    cab = s[s.policy == "CAB"].set_index(["direction", "n_labelled"])
    rows = []
    for _, q in s[s.policy != "CAB"].iterrows():
        c = cab.loc[(q.direction, q.n_labelled)]
        rows.append({"direction": q.direction, "n_labelled": q.n_labelled, "comparator": q.policy,
                     "unsafe_prevented_per_100": q.unsafe_per_100 - c.unsafe_per_100,
                     "missed_septic_prevented": q.missed_septic - c.missed_septic,
                     "excess_missed_prevented": q.excess_missed - c.excess_missed,
                     "false_alerted_prevented": q.false_alerted - c.false_alerted,
                     "alarms_per_day_prevented": q.alarms_per_day - c.alarms_per_day})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="E3v2")
    ap.add_argument("--prevalence", default=None,
                    help="septic share per target hospital, e.g. A=0.088,B=0.057")
    a = ap.parse_args()
    prevalence = dict(PREVALENCE)
    if a.prevalence:
        prevalence.update({k: float(v) for k, v in (p.split("=") for p in a.prevalence.split(","))})

    s_star, margin = PRIMARY
    runs = pd.read_csv(OUT / f"{a.tag}_runs.csv")
    runs = runs[np.isclose(runs.s_star, s_star) & np.isclose(runs.margin, margin)]
    r = per_run(runs, prevalence, s_star)
    s = summarise(r)
    vs = versus_cab(s)
    s.to_csv(OUT / f"{a.tag}_impact.csv", index=False)
    vs.to_csv(OUT / f"{a.tag}_impact_vs_cab.csv", index=False)

    cols = ["n_labelled", "policy", "reps", "activated_pct", "unsafe_per_100", "missed_septic",
            "excess_missed", "false_alerted", "alarms_per_day"]
    lines = [f"# {a.tag}: clinical impact per 100 ICU admissions (s* = {s_star}, margin = {margin})", "",
             "missed_septic / excess_missed / false_alerted: patients per 100 admissions at the target.",
             "excess_missed: missed septic patients beyond what the sensitivity target allows.",
             "unsafe_per_100: hospitals out of 100 that would switch on an unsafe model.",
             "When nothing is switched on (CAB BLOCK) the bedside score (modified NEWS2 >= 5) is used.",
             f"Prevalence used: {', '.join(f'{k} {v:.1%}' for k, v in prevalence.items())}.", ""]
    for d in sorted(s.direction.unique()):
        lines += [f"## {d}", "", "```", s[s.direction == d][cols].round(2).to_string(index=False), "```", ""]

    lines += ["## Comparator minus CAB, per 100 admissions (positive = CAB better)", ""]
    for d in sorted(vs.direction.unique()):
        lines += [f"### {d}", "", "```", vs[vs.direction == d].drop(columns="direction").round(2)
                  .to_string(index=False), "```", ""]
    (OUT / f"{a.tag}_impact.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"Wrote {OUT / f'{a.tag}_impact.md'}")


if __name__ == "__main__":
    main()
