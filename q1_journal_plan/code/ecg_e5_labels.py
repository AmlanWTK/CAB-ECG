"""E5 (ECG): how many labels CAB needs per transfer, and what a switched-on finding means on the ward.

Reads the E3 runs (ecg_e3_cab.py) and, per transfer (target x finding), under the primary criterion:
  - prevalence at the target and whether a safe remedy exists at all (oracle, whole cohort):
      CALIBRATE  imported score, threshold for s* on all positives, FPR against f*
      ADAPT      head fitted on a random half, threshold for s* on the other half's positives
  - the label floor: positives the exact binomial test needs at delta = alpha/4 even with no
    misses, divided by prevalence (CALIBRATE uses all labels, ADAPT certifies on half of them)
  - the smallest budget at which CAB switches the finding on in at least half of the runs
  - on the whole cohort (the primary judge) in switched-on runs: median sensitivity, FPR, positive predictive
    value and alerts per 1,000 ECGs, next to the vendor's home values (PTB-XL fold 10)

Run from the repository root after E3:
    python q1_journal_plan/code/ecg_e5_labels.py [--tag E3 --scores scores]
Writes outputs/ecg/<tag>_E5_labels.csv and .md.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binom

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ecg_e3_cab as E  # noqa: E402


def positives_floor(s_star, delta):
    """Smallest number of positives for which zero misses passes the exact test of sens >= s*."""
    k = 1
    while binom.sf(k - 1, k, s_star) > delta:  # P(all k detected | sens = s*) = s*^k
        k += 1
    return k


def oracle(score, emb, y, s_star, f_star, rng):
    tau = E.largest_threshold_for(score[y], s_star)
    cal_fpr = float((score[~y] >= tau).mean())
    half = rng.random(len(y)) < 0.5
    p_ad = E.fit_adapt(np.column_stack([emb, E.logit(score)]), y, half)
    if p_ad is None:
        return cal_fpr, np.nan
    tau_a = E.largest_threshold_for(p_ad[~half & y], s_star)
    return cal_fpr, float((p_ad[~half & ~y] >= tau_a).mean())


def ward(sens, fpr, prev):
    calls = sens * prev + fpr * (1 - prev)
    return sens * prev / calls if calls > 0 else np.nan, 1000 * calls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="E3")
    ap.add_argument("--scores", default="scores")
    a = ap.parse_args()
    E.SCORES = E.OUT / a.scores
    s_star, margin = E.PRIMARY
    idx = pd.read_csv(E.INDEX_CSV, low_memory=False).set_index("record_id")
    home = E.home_operating_points(idx)
    p_h, _, m_h = E.load_scores("ptbxl", idx)
    te = m_h["strat_fold"].to_numpy() == 10
    floor = positives_floor(s_star, E.ALPHA / 4)
    secondary = {name: (f, col) for v in E.SECONDARY.values() for name, f, col in v}

    rows = []
    for t in E.TARGETS:
        f_csv = E.OUT / f"{a.tag}_runs_{t}.csv"
        if not f_csv.exists():
            continue
        runs = pd.read_csv(f_csv)
        runs = runs[(runs.s_star == s_star) & (runs.margin == margin) & (runs.policy == "CAB")]
        p_all, emb, meta = E.load_scores(t, idx)
        n_rec = len(meta)
        for f, g in runs.groupby("finding"):
            pf, col = secondary.get(f, (f, f))
            k = E.PANEL.index(pf)
            y = np.nan_to_num(meta[col].to_numpy(dtype=float)).astype(bool)
            prev = y.mean()
            h = home[(pf, s_star)]
            f_star = E.MARGINS[margin](h["fpr"])
            cal_fpr, ada_fpr = oracle(p_all[:, k], emb, y, s_star, f_star, np.random.default_rng(0))
            on = g.groupby("n_labelled").activated.mean()
            reached = on[on >= 0.5]
            act = g[g.activated]
            ppv, alerts = zip(*[ward(r.sens_cohort, r.fpr_cohort, prev)
                                for r in act.itertuples()]) if len(act) else ([np.nan], [np.nan])
            y_h = m_h[pf].to_numpy()[te].astype(bool)
            home_ppv, home_alerts = ward(1.0 * (p_h[te][y_h, k] >= h["tau"]).mean(), h["fpr"], y_h.mean())
            rows.append({
                "target": t, "finding": f, "secondary": f in secondary, "prevalence": prev,
                "oracle_cal_fpr": cal_fpr, "oracle_adapt_fpr": ada_fpr, "f_star": f_star,
                "safe_remedy_exists": bool(cal_fpr <= f_star or ada_fpr <= f_star),
                "floor_labels_calibrate": int(np.ceil(floor / prev)),
                "floor_labels_adapt": int(np.ceil(2 * floor / prev)),
                "largest_budget": int(on.index.max()), "on_at_largest": float(on.iloc[-1]),
                "budget_half_on": int(reached.index.min()) if len(reached) else np.nan,
                "runs_on": len(act),
                "sens": float(act.sens_cohort.median()) if len(act) else np.nan,
                "fpr": float(act.fpr_cohort.median()) if len(act) else np.nan,
                "ppv": float(np.median(ppv)), "alerts_per_1000": float(np.median(alerts)),
                "home_ppv": home_ppv, "home_alerts_per_1000": home_alerts,
            })
    res = pd.DataFrame(rows)
    res.to_csv(E.OUT / f"{a.tag}_E5_labels.csv", index=False)

    def why(r):
        if r.budget_half_on == r.budget_half_on:
            return "switched on"
        if not r.safe_remedy_exists:
            return "no safe remedy"
        if r.largest_budget < min(r.floor_labels_calibrate, r.floor_labels_adapt):
            return "below label floor"
        return "too few labels"
    res["outcome"] = res.apply(why, axis=1)
    show = res[["target", "finding", "prevalence", "safe_remedy_exists", "floor_labels_calibrate",
                "largest_budget", "on_at_largest", "budget_half_on", "outcome"]]
    ward_t = res[res.runs_on > 0][["target", "finding", "runs_on", "sens", "fpr", "ppv",
                                   "alerts_per_1000", "home_ppv", "home_alerts_per_1000"]]
    lines = [f"# {a.tag} E5 (ECG): labels needed and ward numbers", "",
             f"Primary criterion (s* = {s_star}, {margin} margin), CAB, scores `{a.scores}`. "
             f"Label floor: {floor} positives with no misses pass the exact test at delta = "
             f"alpha/4 = {E.ALPHA / 4}; floor labels = {floor} / prevalence for CALIBRATE, twice that "
             "for ADAPT. A safe remedy exists if the oracle CALIBRATE or ADAPT threshold for s* meets "
             "f* on the target.", "",
             "Outcome per transfer:", "", "```", show.round(3).to_string(index=False), "```", "",
             "Outcomes: " + ", ".join(f"{k} {v}" for k, v in res[~res.secondary].outcome.value_counts().items())
             + " (primary transfers).", "",
             "Switched-on runs, medians on the whole cohort (all budgets):", "", "```",
             ward_t.round(3).to_string(index=False), "```", ""]
    (E.OUT / f"{a.tag}_E5_labels.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
