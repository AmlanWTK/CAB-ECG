"""E11: vendor headroom. How far above the sensitivity target should a vendor set its threshold?

The vendor ships the imported model with a threshold chosen on its own validation patients. In
E3 that threshold is the largest one certified at s* (home sensitivity ~1-2 points above s*), so
a hospital must prove a very small margin and needs thousands of septic labels to keep it (E5).
Here the vendor instead ships the threshold whose home sensitivity is s* + h, for headroom h:

  * sensitivity margin at the hospital grows with h (easier to certify),
  * the false-alert rate rises with h (the false-alert margin shrinks; this is the cost),
  * the hospital's criteria do NOT move with h: f* = home false-alert rate at the E3 vendor
    threshold + margin, as in E3.

For each direction, criterion and headroom the script reports the home cost (false-alert rate),
the true rates on the target patients, and the labels CAB's exact KEEP test needs (E5 calculator;
power 0.9 for both tests together). For the home directions it also checks the calculator by
simulating CAB's rule (models held fixed, no ADAPT) on resampled target patients.

Run from the repository root (needs the E1 models and data caches; minutes):
    python code/sepsis_e11_headroom.py [--reps 200]
Writes outputs/sepsis/E11_headroom.csv, E11_headroom_sim.csv and E11_headroom.md.
"""

import argparse
import zlib

import lightgbm as lgb
import numpy as np
import pandas as pd

from cabsepsis.cab import SiteFrame, certified_threshold, largest_threshold_for, rates
from cabsepsis.data import load_all
from cabsepsis.features import load_features
from sepsis_e3_cab import MARGINS, OUT, PRIMARY, S_STARS, VENDOR_DELTA
from sepsis_e5_labels import ALPHA, nonseptic_needed, septic_needed, simulate, total_needed

HEADROOMS = [0.00, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10]
SIM_HEADROOMS = [0.00, 0.02, 0.04, 0.06, 0.10]
SIM_BUDGETS = [1000, 2000, 4000, 8000, 16000, 32000]
DIRECTIONS = ["A->A", "B->B", "A->B", "B->A"]


def scores(booster, X, meta, mask):
    sf = SiteFrame(meta[mask])
    w, s = sf.patient_max(booster.predict(X[mask].to_numpy(np.float32)))
    return sf, w, s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--report-only", action="store_true", help="rebuild the report from the CSVs")
    a = ap.parse_args()
    if a.report_only:
        report(pd.read_csv(OUT / "E11_headroom.csv"), pd.read_csv(OUT / "E11_headroom_sim.csv"), a.reps)
        return

    print("Loading data and features ...")
    df = load_all().sort_values(["pid", "hour"]).reset_index(drop=True)
    df["split"] = df["pid"].map(pd.read_csv(OUT / "splits.csv", index_col=0)["split"])
    X, meta = load_features(df)
    boosters = {s: lgb.Booster(model_file=str(OUT / f"lgbm_site{s}.txt")) for s in ["A", "B"]}

    rows, sims = [], []
    for d in DIRECTIONS:
        src, tgt = d.split("->")
        b = boosters[src]
        sfv, wv, sv = scores(b, X, meta, (df.site.eq(src) & df.split.eq("val")).to_numpy())
        sft, wt, st = scores(b, X, meta, df.site.eq(tgt).to_numpy())
        split_pt = df.loc[df.site.eq(tgt), "split"].to_numpy()[sft.offsets]
        # home: judged on the held-out test patients; cross: on every target patient (as E3)
        base = split_pt == "test" if src == tgt else np.ones(sft.n_patients, bool)
        prev = float(sft.septic[base].mean())
        allv = np.ones(sfv.n_patients, bool)
        for s_star in S_STARS:
            tau0 = certified_threshold(wv[sfv.septic], s_star, VENDOR_DELTA)
            if tau0 is None:
                tau0 = largest_threshold_for(wv[sfv.septic], s_star)
            _, fa0 = rates(wv, sv, sfv.septic, allv, tau0)
            for h in HEADROOMS:
                tau = min(tau0, largest_threshold_for(wv[sfv.septic], s_star + h))
                hs, hf = rates(wv, sv, sfv.septic, allv, tau)
                ts, tf = rates(wt, st, sft.septic, base, tau)
                for margin in MARGINS:
                    f_star = fa0 + margin
                    k = septic_needed(ts, s_star) if ts > s_star else None
                    m = nonseptic_needed(tf, f_star) if tf < f_star else None
                    rows.append({"direction": d, "s_star": s_star, "margin": margin, "headroom": h,
                                 "threshold": tau, "home_sens": hs, "home_fa": hf,
                                 "home_fa_cost": hf - fa0, "f_star": f_star,
                                 "target_sens": ts, "target_fa": tf,
                                 "keep_feasible": bool(ts >= s_star and tf <= f_star),
                                 "septic_needed": k, "nonseptic_needed": m,
                                 "patients_needed": total_needed(k, m, prev)})
                if src != tgt or h not in SIM_HEADROOMS:
                    continue
                # calculator check: CAB's rule (KEEP / CALIBRATE / BLOCK) on resampled patients
                srcm = {"wmax": wt[base], "smax": st[base]}
                septic = sft.septic[base]
                for margin in MARGINS:
                    f_star = fa0 + margin
                    rng = np.random.default_rng(zlib.crc32(f"{d}|{s_star}|{margin}|{h}".encode()))
                    for n in SIM_BUDGETS:
                        r = simulate(srcm, None, septic, tau, s_star, f_star, n, a.reps, rng, ALPHA)
                        sims.append({"direction": d, "s_star": s_star, "margin": margin,
                                     "headroom": h, "n_labelled": n, **r})
            print(f"  {d} s*={s_star}: done")

    res, sim = pd.DataFrame(rows), pd.DataFrame(sims)
    res.to_csv(OUT / "E11_headroom.csv", index=False)
    sim.to_csv(OUT / "E11_headroom_sim.csv", index=False)
    report(res, sim, a.reps)


def report(res, sim, reps):
    s0, m0 = PRIMARY
    p = res[np.isclose(res.s_star, s0) & np.isclose(res.margin, m0)]
    cols = ["direction", "headroom", "home_sens", "home_fa_cost", "target_sens", "target_fa", "f_star",
            "keep_feasible", "septic_needed", "nonseptic_needed", "patients_needed"]
    lines = ["# E11: vendor headroom", "",
             "headroom h: the vendor ships the threshold with home sensitivity s* + h (h = 0 is E3's "
             "certified threshold). home_fa_cost: extra home false-alert rate vs h = 0. "
             "*_needed: labels for CAB's exact KEEP tests to pass with probability 0.9 "
             "(E5 calculator, alpha = 0.05); patients under random labelling. Blank = KEEP not "
             "certifiable at any budget.", "",
             f"## Primary criterion (s* = {s0}, margin = {m0})", "",
             "```", p[cols].round(3).to_string(index=False), "```", ""]

    # best headroom per home direction and criterion: fewest patients needed
    h_ = res[res.direction.isin(["A->A", "B->B"]) & res.patients_needed.notna()]
    if len(h_):
        best = h_.loc[h_.groupby(["direction", "s_star", "margin"]).patients_needed.idxmin()]
        at0 = res[np.isclose(res.headroom, 0)].set_index(["direction", "s_star", "margin"])
        best = best.join(at0[["patients_needed", "septic_needed"]].add_suffix("_at_h0"),
                         on=["direction", "s_star", "margin"])
        lines += ["## Best headroom at home (fewest patients to certify KEEP)", "", "```",
                  best[["direction", "s_star", "margin", "headroom", "home_fa_cost",
                        "septic_needed", "patients_needed", "septic_needed_at_h0",
                        "patients_needed_at_h0"]].round(3).to_string(index=False), "```", ""]
    if len(sim):
        q = sim[np.isclose(sim.s_star, s0) & np.isclose(sim.margin, m0)].copy()
        q["P_approved"] = q.P_KEEP + q.P_CALIBRATE
        lines += [f"## Simulated CAB decisions at home, primary criterion ({reps} resamples, "
                  "models fixed)", "", "```",
                  q.pivot_table(index=["direction", "headroom"], columns="n_labelled",
                                values="P_KEEP").round(2).to_string(), "```", "",
                  "P(approved: KEEP or CALIBRATE):", "", "```",
                  q.pivot_table(index=["direction", "headroom"], columns="n_labelled",
                                values="P_approved").round(2).to_string(), "```", ""]
        sim = sim.assign(P_approved=sim.P_KEEP + sim.P_CALIBRATE)
        z = sim[np.isclose(sim.s_star, s0) & np.isclose(sim.headroom, 0)]
        lines += [f"## P(approved) at home by the hospital's false-alert tolerance (s* = {s0}, h = 0)",
                  "", "```", z.pivot_table(index=["direction", "margin"], columns="n_labelled",
                                           values="P_approved").round(2).to_string(), "```", "",
                  "Mean P(approved) over budgets, by tolerance and headroom:", "", "```",
                  sim[np.isclose(sim.s_star, s0)].groupby(["direction", "margin", "headroom"])
                  .P_approved.mean().unstack().round(2).to_string(), "```", ""]
    (OUT / "E11_headroom.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
