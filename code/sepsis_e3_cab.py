"""E3: Calibrate, Adapt, or Block? Certified remedy selection for an imported sepsis model.

Setting: hospital S's model is imported by hospital T. T can label n of its own patients
(drawn at random from T's train+validation patients). Every policy below decides what to switch
on; each decision is then judged on T's patients that were NOT labelled (future patients).

Policies compared
  AS-IS        imported model, home threshold                          (no local data)
  LABEL-FREE   imported model, threshold re-set so the share of alert-hours on T's unlabelled
               data matches the home share                             (no labels)
  RECALIBRATE  imported model, threshold re-set to hit the target sensitivity on the n labels
  FINE-TUNE    imported model boosted further on half the labels, threshold set on the other half
  RETRAIN      new local model from half the labels, threshold set on the other half
  CAB          KEEP -> CALIBRATE -> ADAPT -> BLOCK, each step switched on only if exact tests on
               the labelled patients show both safety criteria are met (see cabsepsis/cab.py)
The first five always switch something on; only CAB can refuse (BLOCK -> unit falls back to
modified NEWS2 >= 5 for the utility numbers).

Safety criteria (pre-specified from the SOURCE hospital only):
  sensitivity  >= s_star                               (patient-level, onset-12h..onset+3h)
  false-alert  <= home false-alert rate + margin       (share of non-septic patients ever alerted)
Primary: s_star = 0.80, margin = 0.05. A 3 x 3 grid of criteria is also run.

Oracle ("correct") remedy for each criterion, from large samples of T:
  KEEP feasible       home threshold meets both criteria on all T patients
  CALIBRATE feasible  the best threshold reaching s_star on all T patients meets the false-alert bound
  ADAPT feasible      a model boosted on T's whole train split meets both on T's test split
  otherwise BLOCK.

Run from the repository root:
    python code\\sepsis_e3_cab.py --reps 2 --budgets 1000          (smoke test, a few minutes)
    python code\\sepsis_e3_cab.py                                   (full run, resumable)
    python code\\sepsis_e3_cab.py --summary-only                    (re-make the report)
Writes outputs/sepsis/E3_runs.csv, E3_oracle.csv, E3_summary.csv, E3_report.md.
"""

import argparse
import json
import time
import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import beta

from cabsepsis.cab import (SiteFrame, cab_select, feasible, largest_threshold_for, rates)
from cabsepsis.data import REPO, load_all
from cabsepsis.features import load_features
from cabsepsis.scores import compute_scores

warnings.filterwarnings("ignore", message=".*eval_set.*")

OUT = REPO / "outputs" / "sepsis"
RUNS = OUT / "E3_runs.csv"
S_STARS = [0.75, 0.80, 0.85]
MARGINS = [0.00, 0.05, 0.10]
PRIMARY = (0.80, 0.05)
POLICIES = ["AS-IS", "LABEL-FREE", "RECALIBRATE", "FINE-TUNE", "RETRAIN", "CAB"]

ADAPT_PARAMS = dict(objective="binary", learning_rate=0.03, num_leaves=15, min_data_in_leaf=100,
                    feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=5.0,
                    metric="auc", verbose=-1)
RETRAIN_PARAMS = dict(ADAPT_PARAMS, learning_rate=0.05, num_leaves=31)


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def fit_booster(Xn, y, patient_of_row, fit_patients, params, seed, init_model=None):
    """Train on rows of fit_patients; 20% of those patients are held out for early stopping."""
    rng = np.random.default_rng(seed)
    fp = np.array(sorted(fit_patients))
    rng.shuffle(fp)
    n_es = max(1, int(0.2 * len(fp)))
    es_set = np.zeros(patient_of_row.max() + 1, bool); es_set[fp[:n_es]] = True
    tr_set = np.zeros_like(es_set); tr_set[fp[n_es:]] = True
    tr, es = tr_set[patient_of_row], es_set[patient_of_row]
    p = dict(params, seed=int(seed))
    dtr = lgb.Dataset(Xn[tr], y[tr], free_raw_data=False)
    if y[es].min() != y[es].max():
        des = lgb.Dataset(Xn[es], y[es], reference=dtr, free_raw_data=False)
        return lgb.train(p, dtr, num_boost_round=1000, valid_sets=[des], init_model=init_model,
                         callbacks=[lgb.early_stopping(50, verbose=False)])
    return lgb.train(p, dtr, num_boost_round=150, init_model=init_model)


def new_trees_raw(booster, Xn, init_iters):
    """Raw score of only the trees added after init_iters (best iteration if early-stopped)."""
    end = booster.best_iteration if booster.best_iteration > 0 else booster.current_iteration()
    if end <= init_iters:
        return np.zeros(len(Xn))
    return booster.predict(Xn, start_iteration=init_iters, num_iteration=end - init_iters, raw_score=True)


def model_dict(sf, score):
    w, s = sf.patient_max(score)
    return {"wmax": w, "smax": s, "septic": sf.septic, "score": score}


def cp_upper(k, n, conf=0.95):
    return 1.0 if k == n else float(beta.ppf(conf, k + 1, n - k))


# ----------------------------------------------------------------------------------------------
def prepare_direction(src, tgt, X, meta, df, boosters):
    t0 = time.time()
    booster = boosters[src]
    init_iters = booster.current_iteration()

    # Source validation set: home thresholds, home false-alert rate, home alert-hour share.
    mv = (df["site"].eq(src) & df["split"].eq("val")).to_numpy()
    sfv = SiteFrame(meta[mv])
    pv = booster.predict(X[mv].to_numpy(np.float32))
    wv, sv = sfv.patient_max(pv)
    home = {}
    for s_star in S_STARS:
        tau = largest_threshold_for(wv[sfv.septic], s_star)
        _, fa = rates(wv, sv, sfv.septic, np.ones(sfv.n_patients, bool), tau)
        home[s_star] = {"tau": tau, "fa": fa, "alert_frac": float((pv >= tau).mean())}

    # Target hospital.
    mt = (df["site"].eq(tgt)).to_numpy()
    sf = SiteFrame(meta[mt])
    Xn = X[mt].to_numpy(np.float32)
    y = sf.meta["SepsisLabel"].to_numpy()
    split_pt = df.loc[mt, "split"].to_numpy()[sf.offsets]
    pool = np.flatnonzero(split_pt != "test")
    test_mask = split_pt == "test"
    src_raw = booster.predict(Xn, raw_score=True)
    srcd = model_dict(sf, sigmoid(src_raw))
    news2 = compute_scores(X[mt])["NEWS2_mod"].to_numpy()
    pool_rows = (split_pt != "test")[sf.row_patient]
    tau_lf = {s: float(np.quantile(srcd["score"][pool_rows], 1 - home[s]["alert_frac"])) for s in S_STARS}

    # Oracle models on the full target train split (early stopping on target val split).
    tr_pt = np.flatnonzero(split_pt == "train")
    va_pt = np.flatnonzero(split_pt == "val")
    tr_rows = np.isin(sf.row_patient, tr_pt)
    va_rows = np.isin(sf.row_patient, va_pt)

    def oracle_fit(params, init):
        p = dict(params, seed=0)
        dtr = lgb.Dataset(Xn[tr_rows], y[tr_rows], free_raw_data=False)
        dva = lgb.Dataset(Xn[va_rows], y[va_rows], reference=dtr, free_raw_data=False)
        return lgb.train(p, dtr, num_boost_round=3000, valid_sets=[dva], init_model=init,
                         callbacks=[lgb.early_stopping(100, verbose=False)])

    b_ad = oracle_fit(ADAPT_PARAMS, booster)
    ora_ad = model_dict(sf, sigmoid(src_raw + new_trees_raw(b_ad, Xn, init_iters)))
    b_loc = oracle_fit(RETRAIN_PARAMS, None)
    ora_loc = model_dict(sf, b_loc.predict(Xn, num_iteration=b_loc.best_iteration))

    all_pt = np.ones(sf.n_patients, bool)
    oracle, orows = {}, []
    for s_star in S_STARS:
        for margin in MARGINS:
            f_star = home[s_star]["fa"] + margin
            k = feasible(srcd["wmax"], srcd["smax"], sf.septic, all_pt, s_star, f_star, tau=home[s_star]["tau"])
            c = feasible(srcd["wmax"], srcd["smax"], sf.septic, all_pt, s_star, f_star)
            a = feasible(ora_ad["wmax"], ora_ad["smax"], sf.septic, test_mask, s_star, f_star)
            l = feasible(ora_loc["wmax"], ora_loc["smax"], sf.septic, test_mask, s_star, f_star)
            remedy = "KEEP" if k[0] else "CALIBRATE" if c[0] else "ADAPT" if a[0] else "BLOCK"
            oracle[(s_star, margin)] = remedy
            orows.append({"direction": f"{src}->{tgt}", "s_star": s_star, "margin": margin,
                          "f_star": round(f_star, 4), "oracle_remedy": remedy,
                          "keep_sens": k[2], "keep_fa": k[3],
                          "calibrate_fa_at_s_star": c[3], "adapt_fa_at_s_star": a[3],
                          "local_model_fa_at_s_star": l[3]})
    print(f"  prepared {src}->{tgt} in {time.time() - t0:.0f}s; oracle (primary) = {oracle[PRIMARY]}")
    return dict(src=src, tgt=tgt, booster=booster, init_iters=init_iters, home=home, sf=sf, Xn=Xn,
                y=y, pool=pool, src_raw=src_raw, srcd=srcd, news2=news2, tau_lf=tau_lf,
                oracle=oracle, orows=orows)


def one_run(P, n, rep, alpha):
    sf, Xn, y = P["sf"], P["Xn"], P["y"]
    seed = (0 if P["src"] == "A" else 1) * 10_000_000 + n * 1000 + rep
    rng = np.random.default_rng(seed)
    lab_idx = rng.choice(P["pool"], size=n, replace=False)
    lab = np.zeros(sf.n_patients, bool); lab[lab_idx] = True
    cert = np.zeros_like(lab)
    for grp in (lab_idx[sf.septic[lab_idx]], lab_idx[~sf.septic[lab_idx]]):
        g = rng.permutation(grp)
        cert[g[: len(g) // 2]] = True
    fit = lab & ~cert
    comp = ~lab

    b_ad = fit_booster(Xn, y, sf.row_patient, np.flatnonzero(fit), ADAPT_PARAMS, seed, init_model=P["booster"])
    ada = model_dict(sf, sigmoid(P["src_raw"] + new_trees_raw(b_ad, Xn, P["init_iters"])))
    b_rt = fit_booster(Xn, y, sf.row_patient, np.flatnonzero(fit), RETRAIN_PARAMS, seed)
    rt = model_dict(sf, b_rt.predict(Xn, num_iteration=b_rt.best_iteration if b_rt.best_iteration > 0 else None))
    srcd = P["srcd"]

    rows = []
    for s_star in S_STARS:
        for margin in MARGINS:
            f_star = P["home"][s_star]["fa"] + margin
            tau_home = P["home"][s_star]["tau"]
            remedy, tau_cab = cab_select(lab, cert, srcd, ada, tau_home, s_star, f_star, alpha)
            cab_model = {"KEEP": srcd, "CALIBRATE": srcd, "ADAPT": ada}.get(remedy)
            choices = {
                "AS-IS": (srcd, tau_home),
                "LABEL-FREE": (srcd, P["tau_lf"][s_star]),
                "RECALIBRATE": (srcd, largest_threshold_for(srcd["wmax"][lab & sf.septic], s_star)),
                "FINE-TUNE": (ada, largest_threshold_for(ada["wmax"][cert & sf.septic], s_star)),
                "RETRAIN": (rt, largest_threshold_for(rt["wmax"][cert & sf.septic], s_star)),
                "CAB": (cab_model, tau_cab),
            }
            oracle = P["oracle"][(s_star, margin)]
            primary = (s_star, margin) == PRIMARY
            for pol, (mdl, tau) in choices.items():
                active = mdl is not None
                if active:
                    sens, fa = rates(mdl["wmax"], mdl["smax"], sf.septic, comp, tau)
                    unsafe = bool(sens < s_star or fa > f_star)
                else:
                    sens = fa = np.nan
                    unsafe = False
                r = {"direction": f"{P['src']}->{P['tgt']}", "n_labelled": n, "rep": rep,
                     "s_star": s_star, "margin": margin, "f_star": f_star, "policy": pol,
                     "remedy": remedy if pol == "CAB" else pol, "oracle": oracle,
                     "correct": (remedy == oracle) if pol == "CAB" else np.nan,
                     "activated": active, "threshold": tau, "sens": sens, "false_alert": fa,
                     "unsafe": unsafe, "utility": np.nan, "alarms_per_day": np.nan,
                     "fallback_sens": np.nan, "fallback_false_alert": np.nan}
                if primary:
                    score, thr = (mdl["score"], tau) if active else (P["news2"], 5.0)
                    r["utility"] = sf.utility(score, thr, comp)
                    r["alarms_per_day"] = sf.alarms_per_day(score, thr, comp)
                    if not active:
                        s2, f2 = rates(*sf.patient_max(P["news2"]), sf.septic, comp, 5.0)
                        r["fallback_sens"], r["fallback_false_alert"] = s2, f2
                rows.append(r)
    return rows


# ----------------------------------------------------------------------------------------------
def summarise():
    runs = pd.read_csv(RUNS)
    g = runs.groupby(["direction", "s_star", "margin", "n_labelled", "policy"], sort=True)
    summ = g.agg(reps=("rep", "size"), unsafe_rate=("unsafe", "mean"), unsafe_k=("unsafe", "sum"),
                 activated_rate=("activated", "mean"), correct_rate=("correct", "mean"),
                 sens_mean=("sens", "mean"), false_alert_mean=("false_alert", "mean"),
                 utility_mean=("utility", "mean"), alarms_per_day_mean=("alarms_per_day", "mean")).reset_index()
    summ["unsafe_upper95"] = [cp_upper(int(k), int(n)) for k, n in zip(summ.unsafe_k, summ.reps)]
    cab = runs[runs.policy == "CAB"]
    mix = (cab.groupby(["direction", "s_star", "margin", "n_labelled"])["remedy"]
           .value_counts(normalize=True).unstack(fill_value=0).reset_index())
    summ.to_csv(OUT / "E3_summary.csv", index=False)
    oracle = pd.read_csv(OUT / "E3_oracle.csv")

    lines = ["# E3: Calibrate, Adapt, or Block?", "",
             "Each row: one source->target direction, one label budget n (patients labelled at the target),",
             "one policy; averaged over repeated random label samples. Judged on the target's unlabelled patients.",
             "unsafe = switched on something that fails sensitivity >= s* or false-alert <= f* on those patients.", "",
             "## Oracle remedy for each criterion", "", "```", oracle.round(3).to_string(index=False), "```", ""]
    s0, m0 = PRIMARY
    for d in sorted(summ.direction.unique()):
        p = summ[(summ.direction == d) & (summ.s_star == s0) & (summ.margin == m0)]
        lines += [f"## Primary criterion, {d} (s* = {s0}, margin = {m0})", "", "```",
                  p[["n_labelled", "policy", "reps", "activated_rate", "unsafe_rate", "unsafe_upper95",
                     "correct_rate", "sens_mean", "false_alert_mean", "utility_mean", "alarms_per_day_mean"]]
                  .round(3).to_string(index=False), "```", ""]
        mx = mix[(mix.direction == d) & (mix.s_star == s0) & (mix.margin == m0)]
        lines += ["CAB decisions (share of runs):", "", "```", mx.round(3).to_string(index=False), "```", ""]

    # Labels needed: smallest n with P(correct) >= 0.9 and unsafe <= 0.05 for CAB.
    need = []
    for (d, s, m), q in summ[summ.policy == "CAB"].groupby(["direction", "s_star", "margin"]):
        ok = q[(q.correct_rate >= 0.9) & (q.unsafe_rate <= 0.05)]
        need.append({"direction": d, "s_star": s, "margin": m,
                     "oracle": oracle[(oracle.direction == d) & (oracle.s_star == s) & (oracle.margin == m)].oracle_remedy.iloc[0],
                     "labels_needed": int(ok.n_labelled.min()) if len(ok) else "> max budget"})
    lines += ["## Labels needed by CAB (P(correct remedy) >= 0.9 and P(unsafe) <= 0.05)", "", "```",
              pd.DataFrame(need).to_string(index=False), "```", ""]

    worst = (summ.groupby(["policy"]).agg(max_unsafe_rate=("unsafe_rate", "max"),
                                          mean_unsafe_rate=("unsafe_rate", "mean")).reset_index())
    lines += ["## Unsafe activation across ALL criteria, budgets and directions", "", "```",
              worst.round(3).to_string(index=False), "```", ""]
    (OUT / "E3_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"Wrote {OUT / 'E3_report.md'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=30)
    ap.add_argument("--budgets", default="250,500,1000,2000,4000,8000")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--directions", default="A->B,B->A")
    ap.add_argument("--summary-only", action="store_true")
    a = ap.parse_args()
    if a.summary_only:
        return summarise()

    budgets = [int(b) for b in a.budgets.split(",")]
    print("Loading data and features ...")
    df = load_all().sort_values(["pid", "hour"]).reset_index(drop=True)
    split = pd.read_csv(OUT / "splits.csv", index_col=0)["split"]
    df["split"] = df["pid"].map(split)
    X, meta = load_features(df)
    boosters = {s: lgb.Booster(model_file=str(OUT / f"lgbm_site{s}.txt")) for s in ["A", "B"]}

    done = set()
    if RUNS.exists():
        prev = pd.read_csv(RUNS, usecols=["direction", "n_labelled", "rep"]).drop_duplicates()
        done = set(map(tuple, prev.to_numpy()))
    oracle_file = OUT / "E3_oracle.csv"
    for d in a.directions.split(","):
        src, tgt = d.split("->")
        print(f"Direction {src} -> {tgt}: preparing (oracle models take a few minutes) ...")
        P = prepare_direction(src, tgt, X, meta, df, boosters)
        orc = pd.DataFrame(P["orows"])
        if oracle_file.exists():
            old = pd.read_csv(oracle_file)
            orc = pd.concat([old[old.direction != d], orc], ignore_index=True)
        orc.to_csv(oracle_file, index=False)
        for n in budgets:
            if n > 0.9 * len(P["pool"]):
                print(f"  skip n={n}: pool has {len(P['pool'])} patients")
                continue
            t0 = time.time()
            for rep in range(a.reps):
                if (d, n, rep) in done:
                    continue
                rows = one_run(P, n, rep, a.alpha)
                pd.DataFrame(rows).to_csv(RUNS, mode="a", header=not RUNS.exists(), index=False)
            print(f"  {d} n={n}: {a.reps} reps in {time.time() - t0:.0f}s")
    summarise()


if __name__ == "__main__":
    main()
