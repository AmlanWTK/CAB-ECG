"""E2 with confidence intervals: how much does an imported sepsis model lose at the new hospital?

For each target hospital, its own (local) LightGBM and the other hospital's (imported) LightGBM
are scored on the SAME target test patients, each with its own home threshold. Differences are
paired; 95% CIs come from a patient-level bootstrap (resampling patients, not hours).

Also reports calibration of the imported model at the target (observed/expected event rate,
calibration slope), which is what the CALIBRATE remedy corrects.

Needs the models from sepsis_e1_baselines.py. Run from the repository root:
    python code\\sepsis_e2_ci.py
Writes outputs/sepsis/E2_ci.csv and outputs/sepsis/E2_ci.md.
"""

import json

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from cabsepsis.cab import SiteFrame
from cabsepsis.data import REPO, load_all
from cabsepsis.features import load_features

OUT = REPO / "outputs" / "sepsis"
N_BOOT = 2000
N_BOOT_AUC = 200
SEED = 1


def load_model(site):
    booster = lgb.Booster(model_file=str(OUT / f"lgbm_site{site}.txt"))
    thr = json.load(open(OUT / f"lgbm_site{site}.json"))["threshold_80sens"]
    return booster, thr


def per_patient(sf, score, tau):
    s = np.nan_to_num(score, nan=-np.inf)
    a = s >= tau
    prev = np.r_[False, a[:-1]] & ~sf.first_row
    wmax, smax = sf.patient_max(score)
    return pd.DataFrame({
        "obs": np.add.reduceat(np.where(a, sf.u1, sf.u0), sf.offsets),
        "best": np.add.reduceat(sf.ubest, sf.offsets),
        "worst": np.add.reduceat(sf.u0, sf.offsets),
        "alarms": np.add.reduceat((a & ~prev).astype(float), sf.offsets),
        "hours": sf.hours.astype(float),
        "septic": sf.septic,
        "detected": sf.septic & (wmax >= tau),
        "any_alert": smax >= tau,
    })


def summarise(pp, idx):
    d = pp.iloc[idx]
    sep = d["septic"].to_numpy()
    return {
        "utility": (d["obs"].sum() - d["worst"].sum()) / (d["best"].sum() - d["worst"].sum()),
        "sensitivity_patient": d["detected"].to_numpy()[sep].mean(),
        "false_alert_patients": d["any_alert"].to_numpy()[~sep].mean(),
        "alarms_per_patient_day": d["alarms"].sum() / (d["hours"].sum() / 24.0),
    }


def calibration(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    lr = LogisticRegression(C=1e6, max_iter=1000).fit(np.log(p / (1 - p)).reshape(-1, 1), y)
    return {"observed_rate": y.mean(), "mean_predicted": p.mean(),
            "O_E_ratio": y.mean() / p.mean(), "calibration_slope": float(lr.coef_[0, 0])}


def main():
    rng = np.random.default_rng(SEED)
    df = load_all().sort_values(["pid", "hour"]).reset_index(drop=True)
    split = pd.read_csv(OUT / "splits.csv", index_col=0)["split"]
    df["split"] = df["pid"].map(split)
    X, meta = load_features(df)
    models = {s: load_model(s) for s in ["A", "B"]}
    rows, calib, lines = [], [], ["# E2: imported vs local model at each hospital (paired, 95% bootstrap CI)", ""]

    for tgt, src in [("B", "A"), ("A", "B")]:
        m = (df["site"].eq(tgt) & df["split"].eq("test")).to_numpy()
        sf = SiteFrame(meta[m])
        Xt = X[m]
        y = sf.meta["SepsisLabel"].to_numpy()
        p_loc = models[tgt][0].predict(Xt)
        p_imp = models[src][0].predict(Xt)
        pp_loc = per_patient(sf, p_loc, models[tgt][1])
        pp_imp = per_patient(sf, p_imp, models[src][1])
        P = sf.n_patients

        point_loc, point_imp = summarise(pp_loc, np.arange(P)), summarise(pp_imp, np.arange(P))
        boot = {k: [] for k in point_loc}
        boot_l = {k: [] for k in point_loc}
        boot_i = {k: [] for k in point_loc}
        for _ in range(N_BOOT):
            idx = rng.integers(0, P, P)
            a, b = summarise(pp_loc, idx), summarise(pp_imp, idx)
            for k in a:
                boot[k].append(b[k] - a[k]); boot_l[k].append(a[k]); boot_i[k].append(b[k])

        auc_l, auc_i = roc_auc_score(y, p_loc), roc_auc_score(y, p_imp)
        bd, bl, bi = [], [], []
        starts, lens = sf.offsets, sf.hours
        for _ in range(N_BOOT_AUC):
            idx = rng.integers(0, P, P)
            r = np.concatenate([np.arange(starts[i], starts[i] + lens[i]) for i in idx])
            if y[r].min() == y[r].max():
                continue
            a, b = roc_auc_score(y[r], p_loc[r]), roc_auc_score(y[r], p_imp[r])
            bd.append(b - a); bl.append(a); bi.append(b)
        point_loc["AUROC_hourly"], point_imp["AUROC_hourly"] = auc_l, auc_i
        boot["AUROC_hourly"], boot_l["AUROC_hourly"], boot_i["AUROC_hourly"] = bd, bl, bi

        def ci(v):
            return f"[{np.percentile(v, 2.5):.3f}, {np.percentile(v, 97.5):.3f}]"

        for k in ["AUROC_hourly", "utility", "sensitivity_patient", "false_alert_patients", "alarms_per_patient_day"]:
            rows.append({"target": tgt, "imported_from": src, "metric": k,
                         "local": point_loc[k], "local_CI": ci(boot_l[k]),
                         "imported": point_imp[k], "imported_CI": ci(boot_i[k]),
                         "difference": point_imp[k] - point_loc[k], "difference_CI": ci(boot[k]),
                         "relative_change_pct": 100 * (point_imp[k] - point_loc[k]) / point_loc[k]})
        c_imp, c_loc = calibration(y, p_imp), calibration(y, p_loc)
        calib.append({"target": tgt, "model": f"imported from {src}", **c_imp})
        calib.append({"target": tgt, "model": "local", **c_loc})
        print(f"done: target {tgt}")

    res = pd.DataFrame(rows)
    cal = pd.DataFrame(calib)
    res.to_csv(OUT / "E2_ci.csv", index=False)
    cal.to_csv(OUT / "E2_calibration.csv", index=False)
    lines += ["Test patients of the target hospital only. Each model uses its home threshold "
              "(80% patient sensitivity on its own hospital's validation set).", "",
              "```", res.round(3).to_string(index=False), "```", "",
              "## Calibration at the target (hourly)", "", "```", cal.round(4).to_string(index=False), "```", ""]
    (OUT / "E2_ci.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"Wrote {OUT / 'E2_ci.md'}")


if __name__ == "__main__":
    main()
