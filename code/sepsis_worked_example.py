"""Worked example for the chapter: CAB's evidence, step by step, for single real runs of E3mac100.

Reproduces the labelled sample and the ADAPT fit of a given (direction, n, rep) exactly as
sepsis_e3_cab.one_run() does (same seed), runs the explained gate (cabsepsis/deploy.py, which a
test checks against cab_select), and reports the counts, the one-sided exact bounds at alpha/4 and
the true rates of the deployed configuration on the unlabelled target patients.

Run from the repository root (needs the E1 models and data caches; a few minutes):
    python code/sepsis_worked_example.py [--cases "A->B:12000:0,B->A:1000:0"]
Writes outputs/sepsis/worked_example.md.
"""

import argparse
import zlib

import lightgbm as lgb
import numpy as np
import pandas as pd

from cabsepsis.cab import rates
from cabsepsis.data import load_all
from cabsepsis.deploy import gate_explained
from cabsepsis.features import load_features
from sepsis_e3_cab import (OUT, PRIMARY, SEEDS, fit_adapt, model_dict, parse_direction,
                           prepare_direction, split_patients)


def labelled_sample(P, n, rep):
    sf = P["sf"]
    base = SEEDS.get(P["name"], 10 + zlib.crc32(P["name"].encode()) % 1000)
    seed = base * 10_000_000 + n * 1000 + rep
    rng = np.random.default_rng(seed)
    lab_idx = rng.choice(P["pool"], size=n, replace=False)
    lab = np.zeros(sf.n_patients, bool); lab[lab_idx] = True
    cert = np.zeros_like(lab)
    for grp in (lab_idx[sf.septic[lab_idx]], lab_idx[~sf.septic[lab_idx]]):
        g = rng.permutation(grp)
        cert[g[: len(g) // 2]] = True
    return seed, lab, cert


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="A->B:12000:0,B->A:1000:0")
    a = ap.parse_args()
    s_star, margin = PRIMARY

    df = load_all().sort_values(["pid", "hour"]).reset_index(drop=True)
    df["split"] = df["pid"].map(pd.read_csv(OUT / "splits.csv", index_col=0)["split"])
    X, meta = load_features(df)
    boosters = {s: lgb.Booster(model_file=str(OUT / f"lgbm_site{s}.txt")) for s in ["A", "B"]}

    lines = ["# Worked example: CAB's evidence for single runs (primary criterion)", "",
             f"s* = {s_star}, false-alert limit f* = home rate + {margin}. Each test at alpha/4 = 0.0125; "
             "'bound' is the one-sided exact (Clopper-Pearson) bound at that level.", ""]
    prepared = {}
    for case in a.cases.split(","):
        d, n, rep = case.rsplit(":", 2)
        n, rep = int(n), int(rep)
        if d not in prepared:
            prepared[d] = prepare_direction(*parse_direction(d)[:2], X, meta, df, boosters,
                                            parse_direction(d)[2])
        P = prepared[d]
        sf = P["sf"]
        f_star = P["home"][s_star]["fa"] + margin
        tau_home = P["home"][s_star]["tau"]
        seed, lab, cert = labelled_sample(P, n, rep)
        fit = lab & ~cert

        def get_ada():
            tr, es = split_patients(np.flatnonzero(fit), sf.n_patients, seed)
            _, p = fit_adapt(P["Xn"], P["y"], sf.row_patient, tr, es, P["booster"], P["src_raw"], seed)
            return model_dict(sf, p)

        remedy, tau, steps, ada = gate_explained(lab, cert, P["srcd"], get_ada, tau_home, s_star, f_star)
        comp = P["eligible"] & ~lab
        lines += [f"## {d}, {n:,} labelled patients (repeat {rep})", "",
                  f"Labelled: {int(sf.septic[lab].sum())} septic, {int((~sf.septic[lab]).sum())} non-septic. "
                  f"Certification half: {int(sf.septic[cert].sum())} septic, "
                  f"{int((~sf.septic[cert]).sum())} non-septic. Vendor threshold {tau_home:.4f}; "
                  f"home false-alert rate {P['home'][s_star]['fa']:.3f}, so f* = {f_star:.3f}.", "",
                  "| Step | Data | Threshold | Septic detected | Sensitivity (lower bound) | "
                  "Non-septic alerted | False-alert rate (upper bound) | Passed |",
                  "|---|---|---|---|---|---|---|---|"]
        for s in steps:
            if "note" in s:
                lines.append(f"| {s['step']} | {s['data']} | – | – | – | – | – | no: {s['note']} |")
                continue
            lines.append(
                f"| {s['step']} | {s['data']} | {s['threshold']:.4f} | {s['detected']}/{s['septic_n']} | "
                f"{s['sens_observed']:.3f} ({s['sens_lower_bound']:.3f}) | {s['alerted']}/{s['nonseptic_n']} | "
                f"{s['fa_observed']:.3f} ({s['fa_upper_bound']:.3f}) | {'yes' if s['passed'] else 'no'} |")
        lines.append("")
        if remedy != "BLOCK":
            mdl = ada if remedy == "ADAPT" else P["srcd"]
            ts, tf = rates(mdl["wmax"], mdl["smax"], sf.septic, comp, tau)
            lines.append(f"Decision: **{remedy}** at threshold {tau:.4f}. On the {int(comp.sum()):,} unlabelled "
                         f"target patients: sensitivity {ts:.3f} (target {s_star}), false-alert rate {tf:.3f} "
                         f"(limit {f_star:.3f}): {'safe' if ts >= s_star and tf <= f_star else 'UNSAFE'}.")
        else:
            lines.append(f"Decision: **BLOCK** (correct remedy from full data: {P['oracle'][PRIMARY]}).")
        lines.append("")
        print(f"  {case}: {remedy}")
    (OUT / "worked_example.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
