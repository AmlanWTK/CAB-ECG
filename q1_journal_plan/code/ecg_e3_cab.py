"""E3 (ECG): certified Calibrate / Adapt / Block for each finding at each importing site.

The PTB-XL model (ecg_e1_source.py) is imported by each target cohort. For each finding, a
random sample of n target ECGs is labelled; every policy picks a model and threshold from it,
and is judged on the target's ECGs:
    unsafe  = sensitivity < s* or false-positive rate > f*        (if it switched anything on)
Primary judge: the whole cohort, less the records an ADAPT head was fitted on (columns *_cohort).
Sensitivity analysis: the unlabelled ECGs, or a fixed evaluation set with --holdout (columns
sens, fpr, unsafe).

Criteria (notes/ecg_design.md): s* = 0.90 (0.80 secondary); f* = max(2 x home FPR, home FPR +
0.01), with the absolute margin home FPR + 0.05 as a sensitivity analysis. The vendor's
threshold and home FPR come from PTB-XL fold 10.

Policies (as in the sepsis chapter):
    AS-IS        imported model, vendor threshold
    LABEL-FREE   imported model, threshold giving the vendor's home share of positive calls on
                 the target's unlabelled ECGs
    RECALIBRATE  imported model, highest threshold reaching s* on the n labels (point estimate)
    FINE-TUNE    adapted model, threshold set the same way on the certification half
    NAIVE-VAL    CAB's order, each remedy accepted on point estimates
    NAIVE-500    keep or recalibrate on point estimates from the first 500 labels
    LTT-DIRECT   Learn-then-Test over both models on the certification half
    CERT-RECAL   CAB without the adapt stage
    CRC          conformal risk control (Angelopoulos et al., ICLR 2024) on the imported model:
                 the highest threshold whose CRC bound on the miss rate is at most 1 - s*,
                 switched on only if the CRC bound on the false-positive rate is at most f*.
                 Controls both rates in expectation over the labelled sample, not with high
                 probability as CAB does.
    CAB          certified KEEP -> CALIBRATE -> ADAPT -> BLOCK (cabsepsis.cab.cab_select)
ADAPT is a logistic-regression head on the frozen network's embedding and the imported logit,
fitted on the half of the labels not used for certification.

The same labelled ECGs are used for all findings of a site (a hospital labels each ECG once);
the certification half is stratified by the finding's label.

Run from the repository root (resumable per target; rerun the same command after a stop):
    python q1_journal_plan/code/ecg_e3_cab.py [--targets chapman_shaoxing,ningbo,code15]
        [--reps 100] [--budgets 250,500,1000,2000,4000] [--tag E3]
    python q1_journal_plan/code/ecg_e3_cab.py --summary-only
Writes outputs/ecg/<tag>_runs_<target>.csv and <tag>_report.md.
"""

import argparse
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code"))
from cabecg.labels import PANEL  # noqa: E402
from cabecg.paths import INDEX_CSV, OUTPUTS  # noqa: E402
from cabsepsis.cab import cab_select, largest_threshold_for  # noqa: E402
from sepsis_e3_cab import ltt_direct, naive_select  # noqa: E402

OUT = OUTPUTS / "ecg"
SCORES = OUT / "scores"
S_STARS = [0.90, 0.80]
PRIMARY = (0.90, "relative")
MARGINS = {"relative": lambda f: max(2 * f, f + 0.01), "absolute": lambda f: f + 0.05}
ALPHA = 0.05
TARGETS = ["georgia", "cpsc_2018", "cpsc_2018_extra", "chapman_shaoxing", "ningbo", "code15"]
POLICIES = ["AS-IS", "LABEL-FREE", "RECALIBRATE", "FINE-TUNE", "NAIVE-VAL", "NAIVE-500",
            "LTT-DIRECT", "CERT-RECAL", "CRC", "CAB"]
# Secondary transfers, kept out of the primary tables: (name, panel finding scored, label column).
# Ningbo codes AF with the atrial-flutter code (E0 audit, notes/ecg_design.md).
SECONDARY = {"ningbo": [("AF_from_AFL", "AF", "AFL")]}
MIN_UNLABELLED_POS = 50   # judging rule (notes/ecg_design.md): expected unlabelled positives
                          # at the largest budget used for the target
HOLDOUT = 0.0   # --holdout: share of each cohort set aside as a fixed evaluation set, never labelled


def judged_findings(meta, budgets):
    """Findings judged at a target: at least MIN_UNLABELLED_POS positives expected to remain
    unlabelled at the largest budget that fits (budgets above half the cohort are not used)."""
    n_rec = len(meta)
    largest = max([b for b in budgets if b <= n_rec // 2], default=0)
    judged_share = HOLDOUT if HOLDOUT else (n_rec - largest) / n_rec  # holdout: positives in the evaluation set
    return [f for f in PANEL if np.nansum(meta[f].to_numpy()) * judged_share >= MIN_UNLABELLED_POS]


def load_scores(source, idx):
    z = np.load(SCORES / f"{source}.npz", allow_pickle=True)
    ids = pd.read_csv(OUT / "signals" / f"{source.removesuffix('_half')}_ids.csv").set_index("record_id")
    ok = ids.loc[z["record_id"], "n_valid"].to_numpy() > 0  # unreadable records were cached as zeros
    meta = idx.loc[z["record_id"][ok]]
    return z["score"][ok].astype(np.float64), z["emb"][ok], meta


def home_operating_points(idx):
    """Vendor threshold, home FPR and home positive-call share per finding and s*, on fold 10."""
    p, _, meta = load_scores("ptbxl", idx)
    te = meta["strat_fold"].to_numpy() == 10
    home = {}
    for k, f in enumerate(PANEL):
        y = meta[f].to_numpy()[te].astype(bool)
        s = p[te, k]
        for s_star in S_STARS:
            tau = largest_threshold_for(s[y], s_star)
            home[(f, s_star)] = {"tau": tau, "fpr": float((s[~y] >= tau).mean()),
                                 "share": float((s >= tau).mean())}
    return home


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def fit_adapt(Z, y, fit):
    """Logistic head on [embedding, imported logit], fitted on the fit records; scores for all."""
    if y[fit].sum() < 2 or (~y[fit]).sum() < 2:
        return None
    sc = StandardScaler().fit(Z[fit])
    lr = LogisticRegression(C=0.1, max_iter=2000).fit(sc.transform(Z[fit]), y[fit])
    return lr.predict_proba(sc.transform(Z))[:, 1]


def crc_threshold(s_pos, s_neg, s_star, f_star):
    """Conformal risk control with a 0/1 loss bounded by 1: a threshold tau is accepted when
    (n / (n + 1)) * risk_hat(tau) + 1 / (n + 1) <= epsilon. Miss rate (epsilon = 1 - s*) sets the
    highest tau; the false-positive bound (epsilon = f*) is then checked at that tau."""
    n, m = len(s_pos), len(s_neg)
    k_max = int(np.floor((1 - s_star) * (n + 1) - 1))  # most misses allowed: (k + 1) / (n + 1) <= 1 - s*
    if n == 0 or m == 0 or k_max < 0:
        return np.nan
    tau = float(np.sort(s_pos)[k_max])  # k_max positives score below tau (ties aside)
    fp = int((s_neg >= tau).sum())
    return tau if (fp + 1) / (m + 1) <= f_star else np.nan


def judge(m, tau, y, mask, f_star, s_star):
    if m is None or not np.isfinite(tau):
        return False, np.nan, np.nan, False
    s = m["wmax"]
    sens = float((s[mask & y] >= tau).mean())
    fpr = float((s[mask & ~y] >= tau).mean())
    return True, sens, fpr, bool(sens < s_star or fpr > f_star)


def run_target(target, idx, home, budgets, reps, out_csv):
    p_all, emb, meta = load_scores(target, idx)
    n_rec = len(meta)
    base = 100 + zlib.crc32(target.removesuffix("_half").encode()) % 900  # code15_half: same draws as code15
    findings = judged_findings(meta, budgets)
    transfers = [(f, PANEL.index(f), f) for f in findings]
    transfers += [(name, PANEL.index(f), col) for name, f, col in SECONDARY.get(target, [])]
    print(f"{target}: {n_rec} ECGs; transfers {[t[0] for t in transfers]}", flush=True)
    hold = np.zeros(n_rec, bool)  # fixed evaluation set: the same for every finding, budget and repeat
    hold[np.random.default_rng(base + 1).permutation(n_rec)[: int(round(HOLDOUT * n_rec))]] = True
    pool = np.flatnonzero(~hold)
    rows = []
    t0 = time.time()
    for n in [b for b in budgets if b <= n_rec // 2]:
        for rep in range(reps):
            seed = base * 10_000_000 + n * 1000 + rep
            rng = np.random.default_rng(seed)
            lab = np.zeros(n_rec, bool)
            lab_idx = rng.choice(pool, size=n, replace=False)
            lab[lab_idx] = True
            lab500 = np.zeros(n_rec, bool)
            lab500[lab_idx[:500]] = True
            unl = ~lab
            ev = hold if HOLDOUT else unl  # where safety is judged
            for f, k, ycol in transfers:
                y = np.nan_to_num(meta[ycol].to_numpy(dtype=float)).astype(bool)
                frng = np.random.default_rng(seed + 7919 * (k + 1))
                cert = np.zeros(n_rec, bool)
                for grp in (lab_idx[y[lab_idx]], lab_idx[~y[lab_idx]]):
                    g = frng.permutation(grp)
                    cert[g[: len(g) // 2]] = True
                fit = lab & ~cert
                src = {"wmax": p_all[:, k], "smax": p_all[:, k], "septic": y}
                Z = np.column_stack([emb, logit(p_all[:, k])])
                p_ad = fit_adapt(Z, y, fit)
                ada = None if p_ad is None else {"wmax": p_ad, "smax": p_ad, "septic": y}
                n_pos_unl = int((ev & y).sum())
                for s_star in S_STARS:
                    h = home[(PANEL[k], s_star)]
                    tau_lf = float(np.quantile(p_all[unl, k], 1 - h["share"]))
                    for mname, mfun in MARGINS.items():
                        f_star = mfun(h["fpr"])
                        remedy, tau_cab = cab_select(lab, cert, src, ada, h["tau"], s_star, f_star, ALPHA)
                        cr, tau_cr = cab_select(lab, cert, src, None, h["tau"], s_star, f_star, ALPHA)
                        pick = {"KEEP": src, "CALIBRATE": src, "ADAPT": ada}
                        rn, tn = naive_select(src, ada, y, lab, cert, h["tau"], s_star, f_star)
                        r5, t5 = naive_select(src, None, y, lab500, cert, h["tau"], s_star, f_star, adapt=False)
                        if ada is not None:
                            rl, tl = ltt_direct(src, ada, y, cert, s_star, f_star, ALPHA)
                            tau_ft = largest_threshold_for(p_ad[cert & y], s_star)
                        else:
                            rl, tl, tau_ft = "BLOCK", np.nan, np.nan
                        choices = {
                            "AS-IS": (src, h["tau"], "KEEP"),
                            "LABEL-FREE": (src, tau_lf, "CALIBRATE"),
                            "RECALIBRATE": (src, largest_threshold_for(p_all[lab & y, k], s_star), "CALIBRATE"),
                            "FINE-TUNE": (ada, tau_ft, "ADAPT"),
                            "NAIVE-VAL": (pick.get(rn), tn, rn),
                            "NAIVE-500": (pick.get(r5), t5, r5),
                            "LTT-DIRECT": (pick.get(rl), tl, rl),
                            "CERT-RECAL": (pick.get(cr), tau_cr, cr),
                            "CRC": (src, crc_threshold(p_all[lab & y, k], p_all[lab & ~y, k],
                                                       s_star, f_star), "CALIBRATE"),
                            "CAB": (pick.get(remedy), tau_cab, remedy),
                        }
                        for pol, (m, tau, rem) in choices.items():
                            on, sens, fpr, unsafe = judge(m, tau, y, ev, f_star, s_star)
                            # secondary judge: the whole cohort (the population the labels were
                            # drawn from), less the records an ADAPT head was fitted on
                            cohort = ~fit if rem == "ADAPT" else np.ones(n_rec, bool)
                            _, sens_c, fpr_c, unsafe_c = judge(m, tau, y, cohort, f_star, s_star)
                            rows.append({"target": target, "finding": f, "n_labelled": n, "rep": rep,
                                         "s_star": s_star, "margin": mname, "f_star": f_star,
                                         "policy": pol, "remedy": rem if on else "BLOCK",
                                         "activated": on, "sens": sens, "fpr": fpr, "unsafe": unsafe,
                                         "sens_cohort": sens_c, "fpr_cohort": fpr_c,
                                         "unsafe_cohort": unsafe_c,
                                         "n_pos_unlabelled": n_pos_unl})
            if (rep + 1) % 25 == 0:
                print(f"  {target} n={n} rep {rep + 1}/{reps} ({time.time() - t0:.0f}s)", flush=True)
    res = pd.DataFrame(rows)
    res.to_csv(out_csv, index=False)
    return res


# Judges (decided 2026-10-30, notes/ecg_design.md): the whole cohort, the population the labels are
# drawn from, is primary; the sample judge (unlabelled remainder, or the fixed evaluation set with
# --holdout) is a sensitivity analysis showing how much a judge measured on a sample adds by chance.
PRIMARY_JUDGE = "unsafe_cohort"
SAMPLE_JUDGE = "unsafe"


def sample_judge_name():
    return (f"a fixed evaluation set of {HOLDOUT:.0%} of each cohort, never labelled (budgets drawn "
            "from the rest)" if HOLDOUT else "the unlabelled ECGs only")


def policy_table(prim, col):
    by_t = prim.groupby(["policy", "target", "finding"])[col].mean().rename("u").reset_index()
    return by_t.groupby("policy").agg(transfers=("u", "size"), mean_unsafe=("u", "mean"),
                                      worst_unsafe=("u", "max"),
                                      transfers_over_alpha=("u", lambda u: int((u > ALPHA).sum())))


def secondary_section(sec):
    """Report lines for the secondary transfers (primary criterion, both judges)."""
    if sec.empty:
        return []
    lines = ["## Secondary transfers", "",
             "Not in the tables above. " + "; ".join(
                 f"{t} {name}: score of {f}, label column {col}"
                 for t, v in SECONDARY.items() for name, f, col in v) + ".", ""]
    prim = sec[(sec.s_star == PRIMARY[0]) & (sec.margin == PRIMARY[1])]
    for (t, f), g in prim.groupby(["target", "finding"]):
        mix = g[g.policy == "CAB"].groupby("n_labelled").remedy.value_counts(normalize=True).unstack(fill_value=0)
        for col, name in [(PRIMARY_JUDGE, "whole cohort"), (SAMPLE_JUDGE, sample_judge_name())]:
            tab = g.pivot_table(index="policy", columns="n_labelled", values=col, aggfunc="mean")
            lines += [f"{t} {f}, unsafe rate by budget, judged on {name}:", "", "```",
                      tab.reindex(POLICIES).round(3).to_string(), "```", ""]
        lines += [f"{t} {f}, CAB decisions by budget:", "", "```", mix.round(2).to_string(), "```", ""]
    return lines


def summarise(res, tag):
    secondary = {name for v in SECONDARY.values() for name, _, _ in v}
    sec = res[res.finding.isin(secondary)]
    res = res[~res.finding.isin(secondary)]
    prim = res[(res.s_star == PRIMARY[0]) & (res.margin == PRIMARY[1])]
    over = policy_table(prim, PRIMARY_JUDGE).join(prim.groupby("policy")["activated"].mean()
                                                  .rename("switched_on")).reindex(POLICIES)
    bud = prim.pivot_table(index="policy", columns="n_labelled", values=PRIMARY_JUDGE,
                           aggfunc="mean").reindex(POLICIES)
    cab = prim[prim.policy == "CAB"]
    mix = cab.groupby(["target", "finding"]).remedy.value_counts(normalize=True).unstack(fill_value=0)
    largest = cab[cab.n_labelled == cab.groupby("target").n_labelled.transform("max")]
    mix_l = largest.groupby(["target", "finding"]).remedy.value_counts(normalize=True).unstack(fill_value=0)
    over_s = policy_table(prim, SAMPLE_JUDGE).reindex(POLICIES)
    bud_s = prim.pivot_table(index="policy", columns="n_labelled", values=SAMPLE_JUDGE,
                             aggfunc="mean").reindex(POLICIES)
    cell = cab.groupby(["target", "finding", "n_labelled"])
    cells_over = pd.DataFrame({"whole_cohort": cell[PRIMARY_JUDGE].mean(), "sample": cell[SAMPLE_JUDGE].mean()})
    cells_over = cells_over[(cells_over > ALPHA).any(axis=1)]
    sens_rows = []
    for (s_star, m), g in res.groupby(["s_star", "margin"]):
        t = g.groupby(["policy", "target", "finding"])[PRIMARY_JUDGE].mean().groupby("policy").agg(["mean", "max"])
        for pol in POLICIES:
            if pol in t.index:
                sens_rows.append({"s_star": s_star, "margin": m, "policy": pol,
                                  "mean_unsafe": t.loc[pol, "mean"], "worst_unsafe": t.loc[pol, "max"]})
    sens = pd.DataFrame(sens_rows).pivot_table(index="policy", columns=["s_star", "margin"],
                                               values=["mean_unsafe", "worst_unsafe"]).reindex(POLICIES)
    lines = [f"# {tag} (ECG): certified Calibrate / Adapt / Block across imported sites", "",
             f"Primary criterion: s* = {PRIMARY[0]}, relative false-positive margin; alpha = {ALPHA}. "
             f"Targets: {', '.join(sorted(res.target.unique()))}. Unsafe = switched on and failing a "
             "criterion on the whole cohort (less the records an ADAPT head was fitted on), the population "
             "the labelled ECGs are drawn from.", "",
             "Per policy, over transfers (target x finding) and budgets:", "",
             "```", over.round(3).to_string(), "```", "",
             "Unsafe rate by label budget:", "", "```", bud.round(3).to_string(), "```", "",
             "CAB decisions at each target's largest budget:", "", "```", mix_l.round(2).to_string(), "```", "",
             "CAB decisions, all budgets:", "", "```", mix.round(2).to_string(), "```", "",
             "Sensitivity analysis (s* and margin):", "", "```", sens.round(3).to_string(), "```", "",
             f"## Sensitivity analysis: judged on {sample_judge_name()}", "",
             "A judge measured on a sample has its own sampling error, so it counts some thresholds that "
             "meet the criteria on the cohort as unsafe; at large budgets CAB's thresholds sit close to s*, "
             "where this happens most.", "",
             "Per policy, over transfers and budgets:", "", "```", over_s.round(3).to_string(), "```", "",
             "Unsafe rate by label budget:", "", "```", bud_s.round(3).to_string(), "```", "",
             "CAB at a single transfer and budget above alpha under either judge:", "", "```",
             cells_over.round(3).to_string() if len(cells_over) else "(none)", "```", ""]
    lines += secondary_section(sec)
    (OUT / f"{tag}_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:14]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", default=",".join(TARGETS))
    ap.add_argument("--reps", type=int, default=100)
    ap.add_argument("--budgets", default="250,500,1000,2000,4000,8000,16000")
    ap.add_argument("--tag", default="E3")
    ap.add_argument("--scores", default="scores", help="folder under outputs/ecg, e.g. scores_seed1")
    ap.add_argument("--holdout", type=float, default=0.0,
                    help="share of each cohort kept as a fixed evaluation set (e.g. 0.3); 0 = judge on the unlabelled rest")
    ap.add_argument("--summary-only", action="store_true")
    a = ap.parse_args()
    global SCORES, HOLDOUT
    SCORES = OUT / a.scores
    HOLDOUT = a.holdout
    idx = pd.read_csv(INDEX_CSV, low_memory=False).set_index("record_id")
    home = home_operating_points(idx)
    budgets = [int(b) for b in a.budgets.split(",")]
    parts = []
    for t in a.targets.split(","):
        out_csv = OUT / f"{a.tag}_runs_{t}.csv"
        if out_csv.exists():
            runs = pd.read_csv(out_csv)
            keep = judged_findings(idx[idx["source"] == t.removesuffix("_half")], budgets)
            keep += [name for name, _, _ in SECONDARY.get(t, [])]
            parts.append(runs[runs["finding"].isin(keep)])  # runs made under the older 20-positive rule
        elif not a.summary_only and (SCORES / f"{t}.npz").exists():
            parts.append(run_target(t, idx, home, budgets, a.reps, out_csv))
        elif not a.summary_only:
            print(f"{t}: not scored yet, skipped")
    if parts:
        summarise(pd.concat(parts, ignore_index=True), a.tag)


if __name__ == "__main__":
    main()
