"""E1/E2: source models, bedside scores, and zero-shot transfer between hospitals.

  E1  each hospital's own model vs modified qSOFA / SIRS / NEWS2 / MEWS (internal test)
  E2  the imported model: trained at one hospital, applied unchanged at the other

Splits are by patient, within each hospital: 60% train / 20% validation / 20% test, stratified
by sepsis. The target hospital's train/validation parts are kept untouched for the later
calibrate / adapt / block experiments; E2 evaluates only on the target's test part.

Alert threshold for every method: chosen on the SOURCE hospital's validation set to detect 80%
of septic patients (the imported model arrives with its home threshold). Bedside scores are
also reported at their conventional cut-offs.

Run from the repository root:
    python code\\sepsis_e1_baselines.py
Writes outputs/sepsis/E1_E2_results.csv and outputs/sepsis/E1_E2_report.md.
"""

import json

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from cabsepsis.data import REPO, load_all, patient_table
from cabsepsis.features import build_features
from cabsepsis.metrics import evaluate, threshold_for_sensitivity
from cabsepsis.scores import STANDARD_CUTOFFS, compute_scores

OUT = REPO / "outputs" / "sepsis"
SEED = 0
TARGET_SENS = 0.80
LGB_PARAMS = dict(objective="binary", learning_rate=0.05, num_leaves=63, min_child_samples=200,
                  colsample_bytree=0.8, subsample=0.8, subsample_freq=1, reg_lambda=1.0,
                  n_estimators=3000, n_jobs=-1, random_state=SEED, verbose=-1)


def make_splits(pt):
    split = pd.Series(index=pt.index, dtype=object)
    for site, d in pt.groupby("site"):
        train, rest = train_test_split(d.index, test_size=0.4, stratify=d["septic"], random_state=SEED)
        val, test = train_test_split(rest, test_size=0.5, stratify=d.loc[rest, "septic"], random_state=SEED)
        split[train], split[val], split[test] = "train", "val", "test"
    return split


def describe(pt, df):
    rows = []
    for site, d in pt.groupby("site"):
        rows.append({
            "site": {"A": "A (Beth Israel)", "B": "B (Emory)"}[site],
            "patients": len(d), "septic_pct": round(100 * d["septic"].mean(), 1),
            "median_icu_hours": int(d["n_hours"].median()),
            "patient_hours": int(d["n_hours"].sum()),
            "MICU_pct": round(100 * (d["unit"] == "MICU").mean(), 1),
            "SICU_pct": round(100 * (d["unit"] == "SICU").mean(), 1),
            "unit_unknown_pct": round(100 * (d["unit"] == "unknown").mean(), 1),
            "median_age": float(d["age"].median()),
        })
    return pd.DataFrame(rows).set_index("site")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("Loading data ...")
    df = load_all()
    df = df.sort_values(["pid", "hour"]).reset_index(drop=True)
    pt = patient_table(df)
    split = make_splits(pt)
    split.rename("split").to_csv(OUT / "splits.csv")
    df["split"] = df["pid"].map(split)

    print("Building features ...")
    X, meta = build_features(df)
    meta = meta.assign(split=df["split"].to_numpy())
    scores = compute_scores(X)

    report = ["# E1/E2 results", "", "## Cohorts", "", "```", describe(pt, df).to_string(), "```", ""]
    results = []

    def add(method, train_site, rule, thr, eval_site, score):
        m = meta["split"].eq("test") & meta["site"].eq(eval_site)
        r = evaluate(meta[m].reset_index(drop=True), np.asarray(score)[m.to_numpy()], thr)
        r.update(method=method, trained_at=train_site, threshold_rule=rule, evaluated_at=eval_site,
                 setting="internal" if train_site in (eval_site, "-") else "imported (zero-shot)")
        results.append(r)
        print(f"  {method:12s} {train_site}->{eval_site} [{rule}] AUROC {r['AUROC_hourly']:.3f} "
              f"utility {r['utility']:.3f} sens {r['sensitivity_patient']:.2f} alarms/day {r['alarms_per_patient_day']:.2f}")

    models = {}
    for src in ["A", "B"]:
        print(f"Training LightGBM at hospital {src} ...")
        tr = meta["site"].eq(src) & meta["split"].eq("train")
        va = meta["site"].eq(src) & meta["split"].eq("val")
        model = lgb.LGBMClassifier(**LGB_PARAMS)
        model.fit(X[tr], meta.loc[tr, "SepsisLabel"], eval_set=[(X[va], meta.loc[va, "SepsisLabel"])],
                  eval_metric="auc", callbacks=[lgb.early_stopping(100, verbose=False)])
        models[src] = model
        p = model.predict_proba(X)[:, 1]
        thr = threshold_for_sensitivity(meta[va].reset_index(drop=True), p[va.to_numpy()], TARGET_SENS)
        for tgt in ["A", "B"]:
            add("LightGBM", src, f"{int(TARGET_SENS*100)}% sens @ {src} val", thr, tgt, p)
        model.booster_.save_model(str(OUT / f"lgbm_site{src}.txt"))
        json.dump({"threshold_80sens": thr, "best_iteration": int(model.best_iteration_)},
                  open(OUT / f"lgbm_site{src}.json", "w"))

        for name in scores.columns:
            s = scores[name].to_numpy()
            thr_s = threshold_for_sensitivity(meta[va].reset_index(drop=True), s[va.to_numpy()], TARGET_SENS)
            for tgt in ["A", "B"]:
                add(name, src, f"{int(TARGET_SENS*100)}% sens @ {src} val", thr_s, tgt, s)

    for name, cut in STANDARD_CUTOFFS.items():
        for tgt in ["A", "B"]:
            add(name, "-", f"standard >= {cut}", cut, tgt, scores[name].to_numpy())

    res = pd.DataFrame(results)
    cols = ["method", "trained_at", "evaluated_at", "setting", "threshold_rule", "AUROC_hourly",
            "AUPRC_hourly", "utility", "sensitivity_patient", "median_lead_h", "alarms_per_patient_day",
            "alert_hours_pct"]
    res = res[cols]
    res.to_csv(OUT / "E1_E2_results.csv", index=False)

    lgbm = res[res.method == "LightGBM"].set_index(["trained_at", "evaluated_at"])
    report += ["## Results (test patients only)", "", "```", res.round(3).to_string(index=False), "```", ""]
    report += ["## Key comparison: imported vs local LightGBM", "", "```",
               lgbm[["AUROC_hourly", "utility", "sensitivity_patient", "alarms_per_patient_day"]].round(3).to_string(),
               "```", ""]
    (OUT / "E1_E2_report.md").write_text("\n".join(report), encoding="utf-8")
    print("\n" + "\n".join(report))
    print(f"\nWrote {OUT / 'E1_E2_results.csv'} and {OUT / 'E1_E2_report.md'}")


if __name__ == "__main__":
    main()
