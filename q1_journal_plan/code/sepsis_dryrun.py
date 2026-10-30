"""Pipeline check on the open demos: MIMIC-IV-trained sepsis model imported by eICU hospitals.

Checks that the Challenge-format tables (challenge_format.py) run through the chapter's code
unchanged: features (cabsepsis.features), a LightGBM model, per-patient scores (cabsepsis.cab.
SiteFrame) and the gate (cabsepsis.cab.cab_select). The demos are far too small for the numbers to
mean anything (MIMIC-IV demo: 114 stays in the cohort); this is a dry run for WP3.

Run from the repository root after mimiciv_sepsis.py and eicu_sepsis.py (relaxed definition):
    python q1_journal_plan/code/sepsis_dryrun.py
"""

import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code"))
from cabsepsis.cab import SiteFrame, cab_select, largest_threshold_for, rates  # noqa: E402
from cabsepsis.features import build_features  # noqa: E402

OUT = REPO / "outputs/sepsis_q1"
S_STAR, MARGIN, ALPHA = 0.80, 0.05, 0.05   # the chapter's primary criterion


def main():
    mim = pd.read_pickle(OUT / "mimiciv_demo_relaxed_challenge.pkl")
    eic = pd.read_pickle(OUT / "eicu_demo_relaxed_challenge.pkl")
    hosp = pd.read_csv(OUT / "eicu_demo_relaxed_hospitals.csv", dtype={"hospitalid": str})
    eic = eic[eic.site.isin(hosp[hosp.adequate].hospitalid)]
    df = pd.concat([mim, eic], ignore_index=True).sort_values(["pid", "hour"]).reset_index(drop=True)
    X, meta = build_features(df)
    print(f"features: {X.shape[1]} columns, {len(X)} rows; MIMIC-IV {mim.pid.nunique()} stays, "
          f"eICU (adequate hospitals) {eic.pid.nunique()} stays in {eic.site.nunique()} hospitals")

    home = (meta.site == "MIMIC-IV").to_numpy()
    params = dict(objective="binary", learning_rate=0.05, num_leaves=15, min_data_in_leaf=50, verbose=-1, seed=0)
    booster = lgb.train(params, lgb.Dataset(X[home].to_numpy(np.float32), meta.SepsisLabel[home]), num_boost_round=100)

    sf_h = SiteFrame(meta[home])
    w_h, s_h = sf_h.patient_max(booster.predict(X[home].to_numpy(np.float32)))
    tau_home = largest_threshold_for(w_h[sf_h.septic], S_STAR)
    sens_h, fa_h = rates(w_h, s_h, sf_h.septic, np.ones(sf_h.n_patients, bool), tau_home)
    print(f"home (in-sample, dry run only): {int(sf_h.septic.sum())} septic, threshold {tau_home:.3f}, "
          f"sensitivity {sens_h:.2f}, false-alert rate {fa_h:.2f}")

    tgt = ~home
    sf = SiteFrame(meta[tgt])
    w, s = sf.patient_max(booster.predict(X[tgt].to_numpy(np.float32)))
    src = {"wmax": w, "smax": s, "septic": sf.septic}
    sens_t, fa_t = rates(w, s, sf.septic, np.ones(sf.n_patients, bool), tau_home)
    print(f"eICU as supplied: {int(sf.septic.sum())} septic of {sf.n_patients}; sensitivity {sens_t:.2f}, "
          f"false-alert rate {fa_t:.2f}")

    rng = np.random.default_rng(0)
    lab = np.zeros(sf.n_patients, bool)
    lab[rng.choice(sf.n_patients, size=sf.n_patients // 2, replace=False)] = True
    cert = lab & (rng.random(sf.n_patients) < 0.5)
    remedy, tau = cab_select(lab, cert, src, None, tau_home, S_STAR, fa_h + MARGIN, ALPHA)
    print(f"CAB with {int(lab.sum())} labelled eICU stays ({int((lab & sf.septic).sum())} septic): {remedy}"
          + (f" at threshold {tau:.3f}" if np.isfinite(tau) else ""))
    print("Pipeline ran end to end.")


if __name__ == "__main__":
    main()
