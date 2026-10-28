"""E12: does CAB keep its promise? Measured unsafe rates against the nominal alpha, setting by setting.

CAB's guarantee (chapter/guarantee.md): whatever the shift, the probability of switching on a model
whose true sensitivity is below s* or whose true false-alert rate is above f* is at most alpha.
Every setting (direction x labels x s* x margin) was repeated R times, so its measured unsafe rate
is a binomial proportion. For each run file this script reports, per setting:

  * the unsafe count, the rate and its exact (Clopper-Pearson) 95% interval;
  * 'exceeds': the interval lies wholly above alpha (a significant violation at 2.5%, one-sided);
  * the septic patients left to judge safety (the unlabelled eligible patients). A run is judged
    unsafe on these patients only, so a small judging set adds noise of its own: a model whose
    true sensitivity is exactly s* is judged unsafe about half the time.

and, per group (cross-hospital / home / ICU unit), the mean and maximum rate, the number of
settings above alpha, the number expected above alpha if EVERY setting sat exactly at alpha (the
worst case the guarantee allows), and the pooled rate over all runs with its interval.

Run from the repository root (seconds):
    python code/sepsis_e12_validity.py [--tags E3mac100:0.05,E6units:0.05,E12alpha01:0.01,E12alpha10:0.10]
Writes outputs/sepsis/E12_validity.csv, E12_validity_groups.csv and E12_validity.md.
"""

import argparse

import numpy as np
import pandas as pd
from scipy.stats import beta, binom

from cabsepsis.data import load_all, patient_table
from sepsis_e3_cab import OUT, PRIMARY

DEFAULT_TAGS = "E3mac100:0.05,E6units:0.05,E12alpha01:0.01,E12alpha10:0.10"
POLICIES = ["CAB", "CERT-RECAL", "LTT-DIRECT"]


def cp(k, n, conf=0.95):
    lo = beta.ppf((1 - conf) / 2, k, n - k + 1) if k > 0 else 0.0
    hi = beta.ppf(1 - (1 - conf) / 2, k + 1, n - k) if k < n else 1.0
    return lo, hi


def group(direction):
    src, tgt = direction.split(":")[0].split("->")
    return "ICU unit" if ":" in direction else "home" if src == tgt else "cross-hospital"


def judging_septic(pt):
    """Septic patients eligible for judging per direction (before removing the labelled ones)."""
    out = {}
    for d in ["A->B", "B->A", "A->A", "B->B"] + [f"{a}:{u}" for a in ["A->B", "B->A"] for u in ["MICU", "SICU"]]:
        src, tgt = d.split(":")[0].split("->")
        m = pt.site.eq(tgt)
        if ":" in d:
            m &= pt.unit.eq(d.split(":")[1])
        if src == tgt:
            m &= pt.split.eq("test")
        out[d] = int(pt.septic[m].sum())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", default=DEFAULT_TAGS)
    a = ap.parse_args()

    df = load_all()
    pt = patient_table(df)
    pt["split"] = pd.read_csv(OUT / "splits.csv", index_col=0)["split"].reindex(pt.index)
    jsep = judging_septic(pt)

    rows, groups = [], []
    for item in a.tags.split(","):
        tag, alpha = item.split(":")
        alpha = float(alpha)
        f = OUT / f"{tag}_runs.csv"
        if not f.exists():
            print(f"  {tag}: no runs file, skipped")
            continue
        r = pd.read_csv(f, usecols=["direction", "n_labelled", "rep", "s_star", "margin", "policy",
                                    "activated", "unsafe", "n_septic_labelled"])
        r = r[r.policy.isin(POLICIES)]
        g = r.groupby(["policy", "direction", "n_labelled", "s_star", "margin"])
        s = g.agg(reps=("unsafe", "size"), unsafe=("unsafe", "sum"), activated=("activated", "mean"),
                  septic_labelled=("n_septic_labelled", "mean")).reset_index()
        s["tag"], s["alpha"], s["group"] = tag, alpha, s.direction.map(group)
        s["rate"] = s.unsafe / s.reps
        ci = [cp(int(k), int(n)) for k, n in zip(s.unsafe, s.reps)]
        s["ci_lo"], s["ci_hi"] = [c[0] for c in ci], [c[1] for c in ci]
        s["exceeds"] = s.ci_lo > alpha
        s["judging_septic"] = s.direction.map(jsep) - s.septic_labelled
        rows.append(s)
        for (pol, grp), q in s.groupby(["policy", "group"]):
            reps = int(q.reps.iloc[0])
            k, n = int(q.unsafe.sum()), int(q.reps.sum())
            lo, hi = cp(k, n)
            groups.append({"tag": tag, "alpha": alpha, "policy": pol, "group": grp,
                           "settings": len(q), "reps": reps, "mean_rate": q.rate.mean(),
                           "max_rate": q.rate.max(), "above_alpha": int((q.rate > alpha).sum()),
                           "expected_above_if_at_alpha": len(q) * binom.sf(np.floor(alpha * reps), reps, alpha),
                           "exceeds": int(q.exceeds.sum()), "pooled_rate": k / n,
                           "pooled_lo": lo, "pooled_hi": hi,
                           "min_judging_septic": q.judging_septic.min()})
        print(f"  {tag}: {len(s)} policy-settings")
    res, grp = pd.concat(rows, ignore_index=True), pd.DataFrame(groups)
    res.to_csv(OUT / "E12_validity.csv", index=False)
    grp.to_csv(OUT / "E12_validity_groups.csv", index=False)

    lines = ["# E12: measured unsafe rates against the nominal alpha", "",
             "One setting = direction x labelled patients x s* x margin, repeated `reps` times. "
             "above_alpha: settings whose measured rate exceeds alpha. expected_above_if_at_alpha: "
             "how many would, by chance, if every setting's true rate were exactly alpha (the worst "
             "case the guarantee allows). exceeds: settings whose exact 95% interval lies wholly above "
             "alpha. pooled: all runs of the group together, with its 95% interval.", "",
             "## By group", "", "```",
             grp.round(4).to_string(index=False), "```", ""]
    for tag in res.tag.unique():
        q = res[(res.tag == tag) & (res.policy == "CAB")]
        top = q.sort_values("rate", ascending=False).head(10)
        lines += [f"## {tag}: the ten CAB settings with the highest measured rate", "", "```",
                  top[["direction", "n_labelled", "s_star", "margin", "unsafe", "reps", "rate",
                       "ci_lo", "ci_hi", "exceeds", "judging_septic"]].round(3).to_string(index=False),
                  "```", ""]
    # alpha sensitivity at the primary criterion: unsafe and activation by alpha
    s0, m0 = PRIMARY
    p = res[(res.policy == "CAB") & np.isclose(res.s_star, s0) & np.isclose(res.margin, m0)
            & res.group.ne("ICU unit")]
    if p.alpha.nunique() > 1:
        lines += [f"## Alpha sensitivity, CAB, primary criterion (s* = {s0}, margin = {m0})", "",
                  "Unsafe rate:", "", "```",
                  p.pivot_table(index=["direction", "alpha"], columns="n_labelled", values="rate")
                  .round(2).to_string(), "```", "", "Share of runs switched on:", "", "```",
                  p.pivot_table(index=["direction", "alpha"], columns="n_labelled", values="activated")
                  .round(2).to_string(), "```", ""]
    (OUT / "E12_validity.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
