"""E14: what if the hospital's sepsis labels are imperfect?

CAB's guarantee assumes correct labels (assumption A2). In practice some septic patients are
never recognised as septic. Here a share q of the labelled septic patients is recorded as
non-septic in the data CAB sees: the gate, the ADAPT fit and the comparators use the noisy labels,
while safety is still judged with the true labels on the unlabelled patients.

Mislabelled septic patients drop out of the sensitivity test and enter the false-alert test
(where they are usually alerted), so CAB is expected to become MORE cautious, not less; RECALIBRATE
sets its threshold on fewer, cleaner septic patients and may become less safe.

Same labelled samples and seeds as E3mac100 (sepsis_worked_example.labelled_sample).
Run from the repository root (needs the E1 models and data caches; about an hour):
    python code/sepsis_e14_label_noise.py [--reps 20]
Writes outputs/sepsis/E14_label_noise.csv and E14_label_noise.md.
"""

import argparse
import time

import lightgbm as lgb
import numpy as np
import pandas as pd

from cabsepsis.cab import cab_select, largest_threshold_for, rates
from cabsepsis.data import load_all
from cabsepsis.features import load_features
from sepsis_e3_cab import (OUT, PRIMARY, fit_adapt, model_dict, parse_direction, prepare_direction,
                           split_patients)
from sepsis_worked_example import labelled_sample

CASES = [("A->B", 12000), ("B->A", 4000)]
NOISE = [0.0, 0.05, 0.10, 0.20]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=20)
    a = ap.parse_args()
    s_star, margin = PRIMARY

    df = load_all().sort_values(["pid", "hour"]).reset_index(drop=True)
    df["split"] = df["pid"].map(pd.read_csv(OUT / "splits.csv", index_col=0)["split"])
    X, meta = load_features(df)
    boosters = {s: lgb.Booster(model_file=str(OUT / f"lgbm_site{s}.txt")) for s in ["A", "B"]}

    rows = []
    for d, n in CASES:
        src, tgt, unit = parse_direction(d)
        P = prepare_direction(src, tgt, X, meta, df, boosters, unit)
        sf, srcd = P["sf"], P["srcd"]
        f_star = P["home"][s_star]["fa"] + margin
        tau_home = P["home"][s_star]["tau"]
        t0 = time.time()
        for rep in range(a.reps):
            seed, lab, cert = labelled_sample(P, n, rep)
            comp = P["eligible"] & ~lab
            lab_sep = np.flatnonzero(lab & sf.septic)
            order = np.random.default_rng(seed + 99).permutation(lab_sep)   # nested: 5% within 10% ...
            for q in NOISE:
                missed = order[: int(round(q * len(order)))]
                septic_seen = sf.septic.copy()
                septic_seen[missed] = False
                y_seen = P["y"].copy()
                y_seen[np.isin(sf.row_patient, missed)] = 0
                src_seen = dict(srcd, septic=septic_seen)
                tr, es = split_patients(np.flatnonzero(lab & ~cert), sf.n_patients, seed)
                _, p_ad = fit_adapt(P["Xn"], y_seen, sf.row_patient, tr, es, P["booster"], P["src_raw"], seed)
                ada = dict(model_dict(sf, p_ad), septic=septic_seen)
                remedy, tau = cab_select(lab, cert, src_seen, ada, tau_home, s_star, f_star, 0.05)
                tau_rc = largest_threshold_for(srcd["wmax"][lab & septic_seen], s_star)
                for pol, mdl, t in (("CAB", {"KEEP": srcd, "CALIBRATE": srcd, "ADAPT": ada}.get(remedy), tau),
                                    ("RECALIBRATE", srcd, tau_rc)):
                    r = {"direction": d, "n_labelled": n, "rep": rep, "noise": q, "policy": pol,
                         "remedy": remedy if pol == "CAB" else "CALIBRATE", "oracle": P["oracle"][PRIMARY],
                         "activated": mdl is not None, "unsafe": False, "sens": np.nan, "false_alert": np.nan}
                    if mdl is not None:
                        s, f = rates(mdl["wmax"], mdl["smax"], sf.septic, comp, t)   # judged on TRUE labels
                        r.update(sens=s, false_alert=f, unsafe=bool(s < s_star or f > f_star))
                    rows.append(r)
            print(f"  {d} n={n} rep {rep}: {time.time() - t0:.0f}s")
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "E14_label_noise.csv", index=False)
    g = res.groupby(["direction", "policy", "noise"]).agg(
        runs=("unsafe", "size"), switched_on=("activated", "mean"), unsafe=("unsafe", "mean"),
        sens=("sens", "mean"), false_alert=("false_alert", "mean")).reset_index()
    cab = res[res.policy == "CAB"]
    mix = cab.groupby(["direction", "noise"]).remedy.value_counts(normalize=True).unstack(fill_value=0)
    lines = ["# E14: imperfect sepsis labels (primary criterion)", "",
             "noise: share of labelled septic patients recorded as non-septic in the data CAB sees. "
             "Safety is judged with the true labels on the unlabelled patients. "
             f"{a.reps} repeats per cell, same samples as E3mac100.", "",
             "```", g.round(3).to_string(index=False), "```", "",
             "CAB decisions:", "", "```", mix.round(2).to_string(), "```", ""]
    (OUT / "E14_label_noise.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
