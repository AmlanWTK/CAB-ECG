"""E3 (v2): Calibrate, Adapt, or Block? Certified remedy selection for an imported sepsis model.

Setting: hospital S's model is used at hospital T. T labels n of its own patients (drawn at
random from T's eligible pool). Every policy decides what to switch on; each decision is then
judged on T's eligible patients that were NOT labelled (stand-ins for future patients).

Directions
  A->B, B->A   cross-hospital import (pool = target train+val patients; judged on the rest)
  A->A, B->B   positive control: the model's own hospital, new patients (pool and judging both
               within the home TEST split, which the model never saw). Nothing has shifted, so a
               good procedure should mostly KEEP here.

The vendor's threshold (what arrives with the model): the highest threshold whose 95% lower
confidence bound for patient sensitivity on the home validation set is >= s_star. v1 used the
plain point estimate, which makes KEEP borderline even at home (true sensitivity ~ s_star).

Safety criteria, fixed from the HOME hospital only:
  sensitivity  >= s_star                                  (septic patients alerted onset-12h..+3h)
  false-alert  <= home false-alert rate at the vendor threshold + margin
                                                          (non-septic patients ever alerted)
Primary: s_star = 0.80, margin = 0.05. A 3 x 3 grid of criteria is also reported.

Policies
  AS-IS        imported model, vendor threshold                             (no local data)
  LABEL-FREE   imported model, threshold matching the home share of alert-hours on T's
               unlabelled data                                              (no labels)
  RECALIBRATE  imported model, threshold hitting s_star on the n labels (point estimate)
  FINE-TUNE    adapted model (see ADAPT) with threshold hitting s_star on the other half
  RETRAIN      new local model from the fit half, threshold hitting s_star on the other half
  CAB          KEEP / CALIBRATE / ADAPT / BLOCK with exact certification (cabsepsis/cab.py)
ADAPT model: three candidates fitted on the fit half -- leaf values re-estimated on local data
(LightGBM refit, decay 0.9), extra boosting rounds on top of the imported model, or both -- and
the one with the best hourly AUROC on a held-out 20% of the fit half is kept. The certification
half is never touched while fitting or choosing, so the CAB guarantee holds.

"apparent" columns: what each policy's own data said about it when its threshold was set.
silent failure = it looked safe on its own data but failed on the unlabelled patients.

Run from the repository root:
    python code\\sepsis_e3_cab.py --reps 2 --budgets 1000          (smoke test)
    python code\\sepsis_e3_cab.py                                   (full run, resumable)
    python code\\sepsis_e3_cab.py --summary-only                    (re-make the report)
Writes outputs/sepsis/E3v2_runs.csv, E3v2_oracle.csv, E3v2_summary.csv, E3v2_report.md.
"""

import argparse
import time
import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import beta
from sklearn.metrics import roc_auc_score

from cabsepsis.cab import (SiteFrame, cab_select, certified_threshold, feasible,
                           largest_threshold_for, rates)
from cabsepsis.data import REPO, load_all
from cabsepsis.features import load_features
from cabsepsis.scores import compute_scores

warnings.filterwarnings("ignore", message=".*eval_set.*")

OUT = REPO / "outputs" / "sepsis"
TAG = "E3v2"
RUNS = OUT / f"{TAG}_runs.csv"
ORACLE = OUT / f"{TAG}_oracle.csv"
SAMPLING = {"septic_share": None, "septic_cap": 0.5}


def configure(septic_share=None, septic_cap=0.5):
    """Random labelling (default, the frozen E3v2 analysis) or enriched labelling (E4).

    Enriched: of the n labelled patients, septic_share are septic (capped at septic_cap of the
    septic patients in the pool, so enough remain to judge the result); the rest are non-septic.
    Sensitivity is estimated only from septic patients and false alerts only from non-septic
    patients, so the exact tests and the CAB guarantee are unchanged by the enrichment."""
    global TAG, RUNS, ORACLE
    SAMPLING.update(septic_share=septic_share, septic_cap=septic_cap)
    TAG = "E3v2" if septic_share is None else f"E4enr{int(round(100 * septic_share))}"
    RUNS = OUT / f"{TAG}_runs.csv"
    ORACLE = OUT / f"{TAG}_oracle.csv"
S_STARS = [0.75, 0.80, 0.85]
MARGINS = [0.00, 0.05, 0.10]
PRIMARY = (0.80, 0.05)
VENDOR_DELTA = 0.05
REFIT_DECAY = 0.9

ADAPT_PARAMS = dict(objective="binary", learning_rate=0.03, num_leaves=15, min_data_in_leaf=100,
                    feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=5.0,
                    metric="auc", verbose=-1)
RETRAIN_PARAMS = dict(ADAPT_PARAMS, learning_rate=0.05, num_leaves=31)


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def split_patients(fit_patients, n_patients, seed):
    rng = np.random.default_rng(seed)
    fp = rng.permutation(np.asarray(fit_patients))
    n_es = max(1, int(0.2 * len(fp)))
    es = np.zeros(n_patients, bool); es[fp[:n_es]] = True
    tr = np.zeros(n_patients, bool); tr[fp[n_es:]] = True
    return tr, es


def boost(Xn, y, tr, es, params, seed, init_model=None, rounds=1000, patience=50):
    p = dict(params, seed=int(seed))
    dtr = lgb.Dataset(Xn[tr], y[tr], free_raw_data=False)
    if y[es].min() != y[es].max():
        des = lgb.Dataset(Xn[es], y[es], reference=dtr, free_raw_data=False)
        return lgb.train(p, dtr, num_boost_round=rounds, valid_sets=[des], init_model=init_model,
                         callbacks=[lgb.early_stopping(patience, verbose=False)])
    return lgb.train(p, dtr, num_boost_round=150, init_model=init_model)


def added_raw(booster, Xn, init_iters):
    """Raw score of only the trees added after init_iters (up to the best iteration)."""
    end = booster.best_iteration if booster.best_iteration > 0 else booster.current_iteration()
    if end <= init_iters:
        return np.zeros(len(Xn))
    return booster.predict(Xn, start_iteration=init_iters, num_iteration=end - init_iters, raw_score=True)


def fit_adapt(Xn, y, row_patient, tr_pt, es_pt, src_booster, src_raw, seed):
    """Fit the three ADAPT candidates on tr rows; keep the best by hourly AUROC on es rows."""
    tr, es = tr_pt[row_patient], es_pt[row_patient]
    init = src_booster.current_iteration()
    cands = {}
    b = boost(Xn, y, tr, es, ADAPT_PARAMS, seed, init_model=src_booster)
    cands["boost"] = src_raw + added_raw(b, Xn, init)
    rf = src_booster.refit(Xn[tr], y[tr], decay_rate=REFIT_DECAY)
    rf_raw = rf.predict(Xn, raw_score=True)
    cands["refit"] = rf_raw
    b2 = boost(Xn, y, tr, es, ADAPT_PARAMS, seed, init_model=rf)
    cands["refit+boost"] = rf_raw + added_raw(b2, Xn, init)
    if y[es].min() == y[es].max():
        best = "refit"
    else:
        best = max(cands, key=lambda k: roc_auc_score(y[es], cands[k][es]))
    return best, sigmoid(cands[best])


def model_dict(sf, score):
    w, s = sf.patient_max(score)
    return {"wmax": w, "smax": s, "septic": sf.septic, "score": score}


def cp_upper(k, n, conf=0.95):
    return 1.0 if k == n else float(beta.ppf(conf, k + 1, n - k))


# ----------------------------------------------------------------------------------------------
def prepare_direction(src, tgt, X, meta, df, boosters):
    t0 = time.time()
    booster = boosters[src]
    home_dir = src == tgt

    # Vendor side: threshold certified on home validation data, home false-alert rate.
    mv = (df["site"].eq(src) & df["split"].eq("val")).to_numpy()
    sfv = SiteFrame(meta[mv])
    pv = booster.predict(X[mv].to_numpy(np.float32))
    wv, sv = sfv.patient_max(pv)
    home = {}
    for s_star in S_STARS:
        tau = certified_threshold(wv[sfv.septic], s_star, VENDOR_DELTA)
        if tau is None:
            tau = largest_threshold_for(wv[sfv.septic], s_star)
        sens, fa = rates(wv, sv, sfv.septic, np.ones(sfv.n_patients, bool), tau)
        home[s_star] = {"tau": tau, "sens": sens, "fa": fa, "alert_frac": float((pv >= tau).mean())}

    # Target hospital.
    mt = df["site"].eq(tgt).to_numpy()
    sf = SiteFrame(meta[mt])
    Xn = X[mt].to_numpy(np.float32)
    y = sf.meta["SepsisLabel"].to_numpy()
    split_pt = df.loc[mt, "split"].to_numpy()[sf.offsets]
    if home_dir:
        eligible = split_pt == "test"
        pool = np.flatnonzero(eligible)
    else:
        eligible = np.ones(sf.n_patients, bool)
        pool = np.flatnonzero(split_pt != "test")
    src_raw = booster.predict(Xn, raw_score=True)
    srcd = model_dict(sf, sigmoid(src_raw))
    news2 = compute_scores(X[mt])["NEWS2_mod"].to_numpy()
    pool_rows = np.isin(sf.row_patient, pool)
    tau_lf = {s: float(np.quantile(srcd["score"][pool_rows], 1 - home[s]["alert_frac"])) for s in S_STARS}

    # Oracle ADAPT / local models (cross-hospital only): target train split, early stop on val.
    ora_ad = ora_loc = None
    if not home_dir:
        tr_pt = split_pt == "train"
        va_pt = split_pt == "val"
        _, p_ad = fit_adapt(Xn, y, sf.row_patient, tr_pt, va_pt, booster, src_raw, 0)
        ora_ad = model_dict(sf, p_ad)
        b_loc = boost(Xn, y, tr_pt[sf.row_patient], va_pt[sf.row_patient], RETRAIN_PARAMS, 0,
                      rounds=3000, patience=100)
        ora_loc = model_dict(sf, b_loc.predict(Xn, num_iteration=b_loc.best_iteration or None))
    test_mask = split_pt == "test"

    oracle, orows = {}, []
    for s_star in S_STARS:
        for margin in MARGINS:
            f_star = home[s_star]["fa"] + margin
            k = feasible(srcd["wmax"], srcd["smax"], sf.septic, eligible, s_star, f_star, tau=home[s_star]["tau"])
            c = feasible(srcd["wmax"], srcd["smax"], sf.septic, eligible, s_star, f_star)
            if ora_ad is not None:
                a = feasible(ora_ad["wmax"], ora_ad["smax"], sf.septic, test_mask, s_star, f_star)
                l = feasible(ora_loc["wmax"], ora_loc["smax"], sf.septic, test_mask, s_star, f_star)
                remedy = "KEEP" if k[0] else "CALIBRATE" if c[0] else "ADAPT" if a[0] else "BLOCK"
                a_fa, l_fa = a[3], l[3]
            else:
                remedy = "KEEP" if k[0] else "CALIBRATE" if c[0] else "ADAPT|BLOCK"
                a_fa = l_fa = np.nan
            oracle[(s_star, margin)] = remedy
            orows.append({"direction": f"{src}->{tgt}", "s_star": s_star, "margin": margin,
                          "vendor_threshold": home[s_star]["tau"], "home_sens": home[s_star]["sens"],
                          "home_fa": home[s_star]["fa"], "f_star": f_star, "oracle_remedy": remedy,
                          "keep_sens": k[2], "keep_fa": k[3], "calibrate_fa_at_s_star": c[3],
                          "adapt_fa_at_s_star": a_fa, "local_model_fa_at_s_star": l_fa})
    print(f"  prepared {src}->{tgt} in {time.time() - t0:.0f}s; oracle (primary) = {oracle[PRIMARY]}")
    return dict(src=src, tgt=tgt, booster=booster, home=home, sf=sf, Xn=Xn, y=y, pool=pool,
                eligible=eligible, src_raw=src_raw, srcd=srcd, news2=news2, tau_lf=tau_lf,
                oracle=oracle, orows=orows)


def one_run(P, n, rep, alpha):
    sf, Xn, y = P["sf"], P["Xn"], P["y"]
    seed = {"A->B": 0, "B->A": 1, "A->A": 2, "B->B": 3}[f"{P['src']}->{P['tgt']}"] * 10_000_000 + n * 1000 + rep
    share = SAMPLING["septic_share"]
    if share is not None:
        seed += 1_000_000_000
    rng = np.random.default_rng(seed)
    if share is None:
        lab_idx = rng.choice(P["pool"], size=n, replace=False)
    else:
        sep_pool = P["pool"][sf.septic[P["pool"]]]
        non_pool = P["pool"][~sf.septic[P["pool"]]]
        n_sep = min(int(round(share * n)), int(SAMPLING["septic_cap"] * len(sep_pool)))
        lab_idx = np.concatenate([rng.choice(sep_pool, size=n_sep, replace=False),
                                  rng.choice(non_pool, size=n - n_sep, replace=False)])
    lab = np.zeros(sf.n_patients, bool); lab[lab_idx] = True
    cert = np.zeros_like(lab)
    for grp in (lab_idx[sf.septic[lab_idx]], lab_idx[~sf.septic[lab_idx]]):
        g = rng.permutation(grp)
        cert[g[: len(g) // 2]] = True
    fit = lab & ~cert
    comp = P["eligible"] & ~lab
    tr_pt, es_pt = split_patients(np.flatnonzero(fit), sf.n_patients, seed)

    variant, p_ad = fit_adapt(Xn, y, sf.row_patient, tr_pt, es_pt, P["booster"], P["src_raw"], seed)
    ada = model_dict(sf, p_ad)
    b_rt = boost(Xn, y, tr_pt[sf.row_patient], es_pt[sf.row_patient], RETRAIN_PARAMS, seed)
    rt = model_dict(sf, b_rt.predict(Xn, num_iteration=b_rt.best_iteration or None))
    srcd = P["srcd"]

    rows = []
    for s_star in S_STARS:
        for margin in MARGINS:
            f_star = P["home"][s_star]["fa"] + margin
            tau_home = P["home"][s_star]["tau"]
            remedy, tau_cab = cab_select(lab, cert, srcd, ada, tau_home, s_star, f_star, alpha)
            cab_model = {"KEEP": srcd, "CALIBRATE": srcd, "ADAPT": ada}.get(remedy)
            cab_data = cert if remedy == "ADAPT" else lab
            choices = {   # policy: (model, threshold, data its threshold was judged on)
                "AS-IS": (srcd, tau_home, None),
                "LABEL-FREE": (srcd, P["tau_lf"][s_star], None),
                "RECALIBRATE": (srcd, largest_threshold_for(srcd["wmax"][lab & sf.septic], s_star), lab),
                "FINE-TUNE": (ada, largest_threshold_for(ada["wmax"][cert & sf.septic], s_star), cert),
                "RETRAIN": (rt, largest_threshold_for(rt["wmax"][cert & sf.septic], s_star), cert),
                "CAB": (cab_model, tau_cab, cab_data),
            }
            oracle = P["oracle"][(s_star, margin)]
            primary = (s_star, margin) == PRIMARY
            for pol, (mdl, tau, own) in choices.items():
                active = mdl is not None
                r = {"direction": f"{P['src']}->{P['tgt']}", "n_labelled": n, "rep": rep,
                     "s_star": s_star, "margin": margin, "f_star": f_star, "policy": pol,
                     "remedy": remedy if pol == "CAB" else pol, "oracle": oracle,
                     "correct": (remedy in oracle.split("|")) if pol == "CAB" else np.nan,
                     "adapt_variant": variant, "activated": active, "threshold": tau,
                     "sens": np.nan, "false_alert": np.nan, "unsafe": False,
                     "apparent_sens": np.nan, "apparent_false_alert": np.nan, "silent_failure": False,
                     "utility": np.nan, "alarms_per_day": np.nan,
                     "fallback_sens": np.nan, "fallback_false_alert": np.nan,
                     "n_septic_labelled": int(sf.septic[lab].sum())}
                if active:
                    sens, fa = rates(mdl["wmax"], mdl["smax"], sf.septic, comp, tau)
                    unsafe = bool(sens < s_star or fa > f_star)
                    if own is None and pol == "AS-IS":
                        a_s, a_f = P["home"][s_star]["sens"], P["home"][s_star]["fa"]
                    elif own is None:
                        a_s = a_f = np.nan
                    else:
                        a_s, a_f = rates(mdl["wmax"], mdl["smax"], sf.septic, own, tau)
                    looked_safe = bool(a_s >= s_star and a_f <= f_star)
                    r.update(sens=sens, false_alert=fa, unsafe=unsafe, apparent_sens=a_s,
                             apparent_false_alert=a_f, silent_failure=unsafe and looked_safe)
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
    summ = (g.agg(reps=("rep", "size"), activated_rate=("activated", "mean"),
                 unsafe_rate=("unsafe", "mean"), unsafe_k=("unsafe", "sum"),
                 silent_failure_rate=("silent_failure", "mean"), correct_rate=("correct", "mean"),
                 sens_mean=("sens", "mean"), false_alert_mean=("false_alert", "mean"),
                 utility_mean=("utility", "mean"), alarms_per_day_mean=("alarms_per_day", "mean"),
                 septic_labelled=("n_septic_labelled", "mean") if "n_septic_labelled" in runs else ("rep", "size"))
            .reset_index())
    if "n_septic_labelled" not in runs:
        summ = summ.drop(columns="septic_labelled")
    summ["unsafe_upper95"] = [cp_upper(int(k), int(n)) for k, n in zip(summ.unsafe_k, summ.reps)]
    summ.to_csv(OUT / f"{TAG}_summary.csv", index=False)
    cab = runs[runs.policy == "CAB"]
    mix = (cab.groupby(["direction", "s_star", "margin", "n_labelled"])["remedy"]
           .value_counts(normalize=True).unstack(fill_value=0).reset_index())
    oracle = pd.read_csv(ORACLE)
    cols = ["n_labelled"] + (["septic_labelled"] if "septic_labelled" in summ else []) + ["policy", "reps", "activated_rate", "unsafe_rate", "unsafe_upper95",
            "silent_failure_rate", "correct_rate", "sens_mean", "false_alert_mean", "utility_mean",
            "alarms_per_day_mean"]

    lines = [f"# {TAG}: Calibrate, Adapt, or Block?", "",
             "Each row: one direction, one label budget n (patients labelled at the target), one policy,",
             "averaged over repeated random label samples; judged on the target's unlabelled eligible patients.",
             "unsafe = switched on something that fails sensitivity >= s* or false-alert <= f* on those patients.",
             "silent failure = unsafe although its own data said it met both criteria.", "",
             "## Oracle remedy for each criterion", "", "```", oracle.round(3).to_string(index=False), "```", ""]
    s0, m0 = PRIMARY
    for d in sorted(summ.direction.unique()):
        p = summ[(summ.direction == d) & (summ.s_star == s0) & (summ.margin == m0)]
        lines += [f"## Primary criterion, {d} (s* = {s0}, margin = {m0})", "", "```",
                  p[cols].round(3).to_string(index=False), "```", ""]
        mx = mix[(mix.direction == d) & (mix.s_star == s0) & (mix.margin == m0)]
        lines += ["CAB decisions (share of runs):", "", "```", mx.round(3).to_string(index=False), "```", ""]

    piv = (summ[summ.policy == "CAB"].pivot_table(index=["direction", "s_star", "margin"],
                                                  columns="n_labelled", values="correct_rate"))
    lines += ["## CAB: share of runs choosing the oracle remedy, all criteria", "", "```",
              piv.round(2).to_string(), "```", ""]

    need = []
    for (d, s, m), q in summ[summ.policy == "CAB"].groupby(["direction", "s_star", "margin"]):
        ok = q[(q.correct_rate >= 0.9) & (q.unsafe_rate <= 0.05)]
        o = oracle[(oracle.direction == d) & (oracle.s_star == s) & (oracle.margin == m)].oracle_remedy.iloc[0]
        need.append({"direction": d, "s_star": s, "margin": m, "oracle": o,
                     "labels_needed": int(ok.n_labelled.min()) if len(ok) else "> max budget"})
    lines += ["## Labels needed by CAB (P(correct remedy) >= 0.9 and P(unsafe) <= 0.05)", "", "```",
              pd.DataFrame(need).to_string(index=False), "```", ""]
    base = OUT / "E3v2_summary.csv"
    if TAG != "E3v2" and base.exists():
        def first_ok(df):
            out = {}
            for (d, s, m), q in df[df.policy == "CAB"].groupby(["direction", "s_star", "margin"]):
                ok = q[(q.correct_rate >= 0.9) & (q.unsafe_rate <= 0.05)]
                out[(d, s, m)] = int(ok.n_labelled.min()) if len(ok) else None
            return out
        rnd, enr = first_ok(pd.read_csv(base)), first_ok(summ)
        comp = pd.DataFrame([{"direction": k[0], "s_star": k[1], "margin": k[2],
                              "random_labelling": rnd.get(k) or "> max", f"enriched ({TAG})": v or "> max"}
                             for k, v in enr.items()])
        lines += ["## Labels needed: random vs enriched labelling (CAB)", "", "```",
                  comp.to_string(index=False), "```", ""]

    worst = (summ.groupby("policy").agg(max_unsafe_rate=("unsafe_rate", "max"),
                                        mean_unsafe_rate=("unsafe_rate", "mean"),
                                        mean_silent_failure_rate=("silent_failure_rate", "mean"))
             .reset_index())
    lines += ["## Unsafe activation across ALL criteria, budgets and directions", "", "```",
              worst.round(3).to_string(index=False), "```", ""]
    av = cab[cab.remedy == "ADAPT"]["adapt_variant"].value_counts(normalize=True)
    lines += ["ADAPT model chosen when CAB switched on ADAPT:", "", "```", av.round(3).to_string(), "```", ""]
    (OUT / f"{TAG}_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"Wrote {OUT / f'{TAG}_report.md'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=30)
    ap.add_argument("--budgets", default="250,500,1000,2000,4000,8000,12000")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--directions", default="A->B,B->A,A->A,B->B")
    ap.add_argument("--summary-only", action="store_true")
    ap.add_argument("--septic-share", type=float, default=None,
                    help="enriched labelling: share of labelled patients who are septic (e.g. 0.5); "
                         "omit for random labelling (the frozen E3v2 analysis)")
    ap.add_argument("--septic-cap", type=float, default=0.5,
                    help="label at most this share of the pool's septic patients")
    a = ap.parse_args()
    configure(a.septic_share, a.septic_cap)
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
    for d in a.directions.split(","):
        src, tgt = d.split("->")
        print(f"Direction {src} -> {tgt}: preparing ...")
        P = prepare_direction(src, tgt, X, meta, df, boosters)
        orc = pd.DataFrame(P["orows"])
        if ORACLE.exists():
            old = pd.read_csv(ORACLE)
            orc = pd.concat([old[old.direction != d], orc], ignore_index=True)
        orc.to_csv(ORACLE, index=False)
        for n in budgets:
            n_non_pool = int((~P["sf"].septic[P["pool"]]).sum())
            if n > 0.9 * len(P["pool"]) or (SAMPLING["septic_share"] is not None and n > 0.9 * n_non_pool):
                print(f"  skip n={n}: pool has {len(P['pool'])} patients")
                continue
            t0, k = time.time(), 0
            for rep in range(a.reps):
                if (d, n, rep) in done:
                    continue
                rows = pd.DataFrame(one_run(P, n, rep, a.alpha))
                if RUNS.exists():
                    rows = rows.reindex(columns=pd.read_csv(RUNS, nrows=0).columns)
                rows.to_csv(RUNS, mode="a", header=not RUNS.exists(), index=False)
                k += 1
            print(f"  {d} n={n}: {k} new reps in {time.time() - t0:.0f}s")
    summarise()


if __name__ == "__main__":
    main()
