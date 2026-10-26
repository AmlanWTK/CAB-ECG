"""Can a bedside score stand in when CAB blocks the imported model?

For every direction and safety criterion of E3, each bedside score (modified NEWS2, MEWS, SIRS,
qSOFA) is checked at every integer cut-off on the target's eligible patients, with the same
patient-level criteria the imported model must meet:
  sensitivity  >= s_star   (septic patients alerted in [onset - 12 h, onset + 3 h])
  false-alert  <= f_star   (non-septic patients ever alerted)
This is a large-sample check (no labels, no test): if no cut-off meets both criteria even on all
eligible patients, no certification procedure could switch the score on, and BLOCK means usual
clinical care without automated alerts rather than a weaker automated score.

Run from the repository root (needs the E1 models and data caches):
    python code\\sepsis_fallback.py
    python code\\sepsis_fallback.py --directions A->B:MICU,A->B:SICU,B->A:MICU,B->A:SICU
Writes outputs/sepsis/E7_fallback.csv and E7_fallback.md.
"""

import argparse

import lightgbm as lgb
import numpy as np
import pandas as pd

from cabsepsis.cab import rates
from cabsepsis.data import load_all
from cabsepsis.features import load_features
from cabsepsis.scores import compute_scores
from sepsis_e3_cab import MARGINS, OUT, S_STARS, parse_direction, prepare_direction

SCORES = ["NEWS2_mod", "MEWS_mod", "SIRS_mod", "qSOFA_mod"]
CUTOFFS = range(1, 16)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--directions", default="A->B,B->A,A->A,B->B,A->B:MICU,A->B:SICU,B->A:MICU,B->A:SICU")
    ap.add_argument("--tag", default="E7_fallback")
    a = ap.parse_args()

    print("Loading data and features ...")
    df = load_all().sort_values(["pid", "hour"]).reset_index(drop=True)
    df["split"] = df["pid"].map(pd.read_csv(OUT / "splits.csv", index_col=0)["split"])
    X, meta = load_features(df)
    boosters = {s: lgb.Booster(model_file=str(OUT / f"lgbm_site{s}.txt")) for s in ["A", "B"]}

    curves, best = [], []
    for d in a.directions.split(","):
        src, tgt, unit = parse_direction(d)
        P = prepare_direction(src, tgt, X, meta, df, boosters, unit)
        sf, el = P["sf"], P["eligible"]
        mt = df["site"].eq(tgt).to_numpy()
        if unit:
            mt &= df["unit"].eq(unit).to_numpy()
        sc = compute_scores(X[mt])
        pts = {}
        for name in SCORES:
            w, s = sf.patient_max(sc[name].to_numpy())
            for c in CUTOFFS:
                se, fa = rates(w, s, sf.septic, el, c)
                pts[(name, c)] = (se, fa)
                curves.append({"direction": d, "score": name, "cutoff": c, "sens": se, "false_alert": fa})
        for s_star in S_STARS:
            for margin in MARGINS:
                f_star = P["home"][s_star]["fa"] + margin
                ok = [(k, v) for k, v in pts.items() if v[0] >= s_star and v[1] <= f_star]
                # closest miss: the cut-off reaching s_star with the fewest false alerts
                reach = [(k, v) for k, v in pts.items() if v[0] >= s_star]
                k, (se, fa) = min(reach, key=lambda kv: kv[1][1]) if reach else (("-", 0), (np.nan, np.nan))
                best.append({"direction": d, "s_star": s_star, "margin": margin, "f_star": f_star,
                             "oracle_remedy": P["oracle"][(s_star, margin)],
                             "any_score_meets_both": bool(ok),
                             "best_score": k[0], "best_cutoff": k[1], "best_sens": se,
                             "best_false_alert": fa, "excess_false_alert": fa - f_star})
    curves, best = pd.DataFrame(curves), pd.DataFrame(best)
    curves.to_csv(OUT / f"{a.tag}_curves.csv", index=False)
    best.to_csv(OUT / f"{a.tag}.csv", index=False)

    n_ok = int(best.any_score_meets_both.sum())
    lines = [f"# {a.tag}: can a bedside score replace a blocked model?", "",
             "Each row: the bedside score and cut-off that reaches the sensitivity target with the",
             "fewest false alerts on the target's eligible patients (large-sample check, no labels).",
             f"Criteria where some bedside score meets both targets: {n_ok} of {len(best)}.", "",
             "```", best.round(3).to_string(index=False), "```", ""]
    prim = best[np.isclose(best.s_star, 0.80) & np.isclose(best.margin, 0.05)]
    lines += ["## Primary criterion (s* = 0.80, margin = 0.05)", "", "```",
              prim[["direction", "oracle_remedy", "f_star", "best_score", "best_cutoff", "best_sens",
                    "best_false_alert", "excess_false_alert"]].round(3).to_string(index=False), "```", ""]
    (OUT / f"{a.tag}.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
