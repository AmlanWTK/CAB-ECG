"""E13: how early do the alerts come? Lead time before sepsis onset, per deployed configuration.

For each septic patient detected in the window (onset -12 h to +3 h), the lead time is the onset
hour minus the hour of the first alert in that window. Reported for the configuration CAB switched
on and for the comparators in the same runs (A->B, primary criterion, the E3mac100 samples), plus
the target hospital's own local model (trained on its training split; threshold reaching s* on its
test patients) and modified NEWS2 >= 5 as references. All on the unlabelled target patients.

Run from the repository root (needs the E1 models and data caches; about 20 minutes):
    python code/sepsis_e13_leadtime.py [--reps 20 --n 12000]
Writes outputs/sepsis/E13_leadtime.csv and E13_leadtime.md.
"""

import argparse

import lightgbm as lgb
import numpy as np
import pandas as pd

from cabsepsis.cab import cab_select, largest_threshold_for
from cabsepsis.data import load_all
from cabsepsis.features import load_features
from cabsepsis.metrics import _patient_frame
from sepsis_e3_cab import (OUT, PRIMARY, RETRAIN_PARAMS, boost, fit_adapt, model_dict, parse_direction,
                           prepare_direction, split_patients)
from sepsis_worked_example import labelled_sample


def lead_times(sf, t_s, hour, score, tau, mask):
    """Lead time (h) of each septic patient in mask: NaN if not alerted within the window."""
    alert = sf.in_win & (np.nan_to_num(score, nan=-np.inf) >= tau)
    first = pd.Series(np.where(alert, hour, np.inf)).groupby(sf.row_patient).min().to_numpy()
    onset = t_s[sf.offsets]
    lt = onset - first
    lt[~np.isfinite(first)] = np.nan
    return lt[mask & sf.septic]


def summary(lt):
    det = lt[np.isfinite(lt)]
    return {"septic": len(lt), "detected": float(np.isfinite(lt).mean()),
            "lead_median": float(np.median(det)) if len(det) else np.nan,
            "lead_q1": float(np.quantile(det, 0.25)) if len(det) else np.nan,
            "lead_q3": float(np.quantile(det, 0.75)) if len(det) else np.nan,
            "share_6h_early": float((lt >= 6).mean())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=20)
    ap.add_argument("--n", type=int, default=12000)
    ap.add_argument("--direction", default="A->B")
    a = ap.parse_args()
    s_star, margin = PRIMARY

    df = load_all().sort_values(["pid", "hour"]).reset_index(drop=True)
    df["split"] = df["pid"].map(pd.read_csv(OUT / "splits.csv", index_col=0)["split"])
    X, meta = load_features(df)
    boosters = {s: lgb.Booster(model_file=str(OUT / f"lgbm_site{s}.txt")) for s in ["A", "B"]}
    src, tgt, unit = parse_direction(a.direction)
    P = prepare_direction(src, tgt, X, meta, df, boosters, unit)
    sf, srcd = P["sf"], P["srcd"]
    hour = sf.meta["hour"].to_numpy(dtype=float)
    _, t_s = _patient_frame(sf.meta)
    f_star = P["home"][s_star]["fa"] + margin
    tau_home = P["home"][s_star]["tau"]

    rows = []
    # references: modified NEWS2 >= 5, and the target's own local model (training split)
    split_pt = df.loc[df.site.eq(tgt), "split"].to_numpy()[sf.offsets]
    tr, va = split_pt == "train", split_pt == "val"
    b_loc = boost(P["Xn"], P["y"], tr[sf.row_patient], va[sf.row_patient], RETRAIN_PARAMS, 0,
                  rounds=3000, patience=100)
    loc = model_dict(sf, b_loc.predict(P["Xn"], num_iteration=b_loc.best_iteration or None))
    test = split_pt == "test"
    tau_loc = largest_threshold_for(loc["wmax"][test & sf.septic], s_star)
    rows.append({"policy": "Local model (reference)", "rep": -1,
                 **summary(lead_times(sf, t_s, hour, loc["score"], tau_loc, test))})
    rows.append({"policy": "NEWS2 >= 5 (reference)", "rep": -1,
                 **summary(lead_times(sf, t_s, hour, P["news2"], 5.0, test))})

    for rep in range(a.reps):
        seed, lab, cert = labelled_sample(P, a.n, rep)
        comp = P["eligible"] & ~lab
        trp, esp = split_patients(np.flatnonzero(lab & ~cert), sf.n_patients, seed)
        _, p_ad = fit_adapt(P["Xn"], P["y"], sf.row_patient, trp, esp, P["booster"], P["src_raw"], seed)
        ada = model_dict(sf, p_ad)
        remedy, tau = cab_select(lab, cert, srcd, ada, tau_home, s_star, f_star, 0.05)
        conf = {"AS-IS": (srcd, tau_home),
                "RECALIBRATE": (srcd, largest_threshold_for(srcd["wmax"][lab & sf.septic], s_star)),
                "FINE-TUNE": (ada, largest_threshold_for(ada["wmax"][cert & sf.septic], s_star))}
        if remedy != "BLOCK":
            conf["CAB"] = ({"KEEP": srcd, "CALIBRATE": srcd, "ADAPT": ada}[remedy], tau)
        for pol, (m, t) in conf.items():
            rows.append({"policy": pol, "rep": rep, "remedy": remedy if pol == "CAB" else None,
                         **summary(lead_times(sf, t_s, hour, m["score"], t, comp))})
        print(f"  rep {rep}: CAB {remedy}")
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "E13_leadtime.csv", index=False)
    g = res.groupby("policy", sort=False).agg(runs=("rep", "size"), detected=("detected", "mean"),
                                              lead_median=("lead_median", "mean"), lead_q1=("lead_q1", "mean"),
                                              lead_q3=("lead_q3", "mean"),
                                              share_6h_early=("share_6h_early", "mean")).reset_index()
    lines = [f"# E13: lead time before sepsis onset ({a.direction}, {a.n:,} labels, primary criterion)", "",
             "Lead time = onset hour - first alert within onset -12 h to +3 h, among detected septic "
             "patients (median and quartiles, averaged over runs). share_6h_early: share of ALL septic "
             "patients alerted at least 6 h before onset. CAB rows: runs where CAB switched something on. "
             "References are on the target's test patients.", "",
             "```", g.round(3).to_string(index=False), "```", ""]
    (OUT / "E13_leadtime.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
