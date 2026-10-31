"""Challenge hospital B (Emory) as an open external target for WP3 (analysis plan, section 4).

Two parts, both run before the full MIMIC-IV / eICU data arrive:

1. Harmonisation check. A model trained on our extracted tables and moved to B should meet
   B's patients, not differences between our extraction and the Challenge's processing. Hospital
   A is the MIMIC hospital in earlier years, processed by the Challenge organisers, so for each
   variable our MIMIC-IV extraction is compared with A: share of stay-hours measured, and median
   and quartiles of the measured values. Large gaps point to an extraction difference (item
   choice, units, aggregation) to fix before the full run. B and the eICU demo are shown
   alongside. Only inputs and stay lengths are compared; no model performance is looked at.
2. Dry run. A model trained on the MIMIC-IV demo (Challenge-rule labels) is imported by B and
   put through the gate, to check that the target side of the pipeline runs. The demo source
   has 5 septic stays, so the numbers mean nothing.

Run from the repository root after mimiciv_sepsis.py (--definition challenge) and eicu_sepsis.py
(relaxed):
    python q1_journal_plan/code/challenge_b.py
Writes outputs/sepsis_q1/B_harmonisation.md and B_harmonisation.csv.
"""

import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code"))
from cabsepsis.cab import SiteFrame, cab_select, largest_threshold_for, rates  # noqa: E402
from cabsepsis.data import LABS, VITALS, load_all, patient_table  # noqa: E402
from cabsepsis.features import build_features  # noqa: E402

OUT = REPO / "outputs/sepsis_q1"
S_STAR, MARGIN, ALPHA = 0.80, 0.05, 0.05
VARS = VITALS + LABS + ["Age", "HospAdmTime"]
RATE_GAP = 2.0    # measured share differs from A by more than this factor
MEDIAN_GAP = 0.5  # median differs from A's by more than this many of A's IQRs


def sources():
    """Stay-hour tables: Challenge A and B, our MIMIC-IV demo (Challenge rule) and eICU demo
    (relaxed rule, hospitals passing the recording check)."""
    ch = load_all()
    mim = pd.read_pickle(OUT / "mimiciv_demo_challenge_challenge.pkl")
    # eICU under the relaxed rule: the inputs do not depend on the rule, and its cohort is larger
    eic = pd.read_pickle(OUT / "eicu_demo_relaxed_challenge.pkl")
    hosp = pd.read_csv(OUT / "eicu_demo_relaxed_hospitals.csv", dtype={"hospitalid": str})
    eic = eic[eic.site.isin(hosp[hosp.adequate].hospitalid)]
    return {"A": ch[ch.site == "A"], "B": ch[ch.site == "B"], "MIMIC-IV demo": mim, "eICU demo": eic}


def describe(d):
    """Per variable: share of hours measured, quartiles of measured values."""
    rows = {}
    for v in VARS:
        x = d[v].dropna().to_numpy(dtype=float)
        q = np.percentile(x, [25, 50, 75]) if len(x) else [np.nan] * 3
        rows[v] = {"measured": len(x) / len(d), "q1": q[0], "median": q[1], "q3": q[2]}
    return pd.DataFrame(rows).T


def stays(d):
    pt = patient_table(d)
    return {"stays": len(pt), "hours": len(d), "median hours": float(pt.n_hours.median()),
            "septic": float(pt.septic.mean())}


def flags(ref, ours):
    """Variables where ours differs from the reference (A) beyond the fixed gaps."""
    out = []
    for v in VARS:
        r, o = ref.loc[v], ours.loc[v]
        why = []
        if r.measured > 0 and o.measured > 0:
            ratio = o.measured / r.measured
            if ratio > RATE_GAP or ratio < 1 / RATE_GAP:
                why.append(f"measured {o.measured:.1%} vs {r.measured:.1%}")
        elif r.measured > 0 or o.measured > 0:
            why.append(f"measured {o.measured:.1%} vs {r.measured:.1%}")
        iqr = r.q3 - r.q1
        if np.isfinite(o["median"]) and np.isfinite(r["median"]) and iqr > 0 \
                and abs(o["median"] - r["median"]) > MEDIAN_GAP * iqr:
            why.append(f"median {o['median']:.3g} vs {r['median']:.3g} (A's IQR {r.q1:.3g}-{r.q3:.3g})")
        if why:
            out.append((v, "; ".join(why)))
    return out


def dry_run(mim, b):
    df = pd.concat([mim, b], ignore_index=True).sort_values(["pid", "hour"]).reset_index(drop=True)
    X, meta = build_features(df)
    home = (meta.site == "MIMIC-IV").to_numpy()
    params = dict(objective="binary", learning_rate=0.05, num_leaves=15, min_data_in_leaf=50, verbose=-1, seed=0)
    booster = lgb.train(params, lgb.Dataset(X[home].to_numpy(np.float32), meta.SepsisLabel[home]),
                        num_boost_round=100)
    sf_h = SiteFrame(meta[home])
    w_h, s_h = sf_h.patient_max(booster.predict(X[home].to_numpy(np.float32)))
    tau_home = largest_threshold_for(w_h[sf_h.septic], S_STAR)
    _, fa_h = rates(w_h, s_h, sf_h.septic, np.ones(sf_h.n_patients, bool), tau_home)

    sf = SiteFrame(meta[~home])
    w, s = sf.patient_max(booster.predict(X[~home].to_numpy(np.float32)))
    rng = np.random.default_rng(0)
    lab = np.zeros(sf.n_patients, bool)
    lab[rng.choice(sf.n_patients, size=2000, replace=False)] = True
    cert = lab & (rng.random(sf.n_patients) < 0.5)
    remedy, tau = cab_select(lab, cert, {"wmax": w, "smax": s, "septic": sf.septic}, None,
                             tau_home, S_STAR, fa_h + MARGIN, ALPHA)
    return (f"MIMIC-IV demo model ({int(sf_h.septic.sum())} septic stays) imported by B "
            f"({sf.n_patients:,} stays); gate with 2,000 labelled B stays "
            f"({int((lab & sf.septic).sum())} septic): {remedy}. Pipeline ran end to end.")


def main():
    src = sources()
    desc = {k: describe(d) for k, d in src.items()}
    st = pd.DataFrame({k: stays(d) for k, d in src.items()}).T

    wide = pd.concat({k: v for k, v in desc.items()}, axis=1)
    wide.to_csv(OUT / "B_harmonisation.csv")

    lines = ["# Challenge hospital B: harmonisation check and dry run", "",
             "Our extraction compared with the Challenge's processing. Hospital A is the MIMIC hospital "
             "in earlier years, so it is the reference for our MIMIC-IV extraction. Only inputs and stay "
             "lengths are compared. The demos are small (MIMIC-IV demo about 130 stays), so small gaps "
             f"mean little; flags use fixed gaps (measured share off by more than {RATE_GAP:g}x, or median "
             f"off by more than {MEDIAN_GAP:g} of A's IQR).", "", "## Stays", "",
             "| | stays | hours | median hours per stay | septic |", "|---|---|---|---|---|"]
    for k, r in st.iterrows():
        lines.append(f"| {k} | {int(r.stays):,} | {int(r.hours):,} | {r['median hours']:.0f} | {r.septic:.1%} |")

    for name in ["MIMIC-IV demo", "eICU demo", "B"]:
        f = flags(desc["A"], desc[name])
        lines += ["", f"## {name} against A: {len(f)} of {len(VARS)} variables flagged", ""]
        lines += [f"- {v}: {why}" for v, why in f] or ["None."]

    lines += ["", "## Per variable: share of hours measured (median)", "",
              "| variable | " + " | ".join(src) + " |", "|---" * (len(src) + 1) + "|"]
    for v in VARS:
        cells = [f"{desc[k].loc[v, 'measured']:.1%} ({desc[k].loc[v, 'median']:.3g})" for k in src]
        lines.append(f"| {v} | " + " | ".join(cells) + " |")

    lines += ["", "## Dry run", "", dry_run(src["MIMIC-IV demo"], src["B"])]
    (OUT / "B_harmonisation.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
