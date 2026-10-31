"""WP7 (ECG): stronger comparators for the gate, on the same label samples as ecg_e3_cab.py.

Each policy picks a model and threshold from the n labelled target ECGs (or from none) and is
judged on the whole target cohort, as the primary judge of E3. Primary criterion only
(s* = 0.90, relative false-positive margin).

    BAYES-FLAT    Bayesian updating of the imported model from a flat Beta(1, 1) prior: the
                  highest threshold with posterior P(sensitivity >= s*) >= 0.95, switched on if
                  posterior P(FPR <= f*) >= 0.95 there.
    BAYES-MATCHED BAYES-FLAT at the strictness of CAB's tests: posterior probability 1 - alpha/4
                  for each criterion instead of 0.95.
    BAYES-HOME    the same as BAYES-FLAT with the vendor's home validation (PTB-XL fold 10) as the prior: at
                  each threshold, Beta(1 + home hits, 1 + home misses) for sensitivity and
                  Beta(1 + home false positives, 1 + home true negatives) for FPR.
    RILEY-SIZE    precision-based minimum sample size, then point estimates: switched on only
                  when the labels hold enough positives to estimate sensitivity at s* to within
                  +/- 0.05, and enough negatives to estimate FPR at f* to within +/- f*/2 (95%
                  intervals), then KEEP / CALIBRATE / ADAPT accepted on point estimates as in
                  NAIVE-VAL. After Riley et al.'s sample-size approach for external validation.
    CORAL         unsupervised domain adaptation: target embeddings aligned to the source's mean
                  and covariance (CORAL, Sun et al. 2016) and scored by the network's own output
                  layer; vendor threshold; no labels.
    CORAL-VAL     CORAL scores with the threshold recalibrated on the labels (highest threshold
                  reaching s*), switched on if the point estimates meet both criteria.

Run from the repository root after ecg_e3_cab.py:
    python q1_journal_plan/code/wp7_comparators.py [--reps 100]
Writes outputs/ecg/W7_runs_<target>.csv and W7_report.md (with CAB, NAIVE-VAL and CRC from E3).
"""

import argparse
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import beta
from scipy.linalg import sqrtm

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ecg_e3_cab as e3  # noqa: E402
from ecg_e3_cab import PANEL, fit_adapt, judge, largest_threshold_for, load_scores, logit  # noqa: E402
from sepsis_e3_cab import naive_select  # noqa: E402

S_STAR, MARGIN = e3.PRIMARY
POST = 0.95                        # posterior probability required by the Bayesian policies
SENS_HALF, Z = 0.05, 1.96          # RILEY-SIZE precision targets
POLICIES = ["BAYES-FLAT", "BAYES-MATCHED", "BAYES-HOME", "RILEY-SIZE", "CORAL", "CORAL-VAL"]
FROM_E3 = ["NAIVE-VAL", "CRC", "CAB"]
BUDGETS = [250, 500, 1000, 2000, 4000, 8000, 16000]


def output_layer(idx):
    """The network's output layer, recovered from PTB-XL scores and embeddings (score =
    sigmoid(emb @ W + b) exactly), and the source embedding mean and covariance (folds 1-8)."""
    p, emb, meta = load_scores("ptbxl", idx)
    X = np.column_stack([emb.astype(np.float64), np.ones(len(emb))])
    coef, err = np.zeros((X.shape[1], p.shape[1])), 0.0
    for k in range(p.shape[1]):
        ok = (p[:, k] > 1e-5) & (p[:, k] < 1 - 1e-5)  # saturated scores lost precision when stored
        coef[:, k], *_ = np.linalg.lstsq(X[ok], logit(p[ok, k]), rcond=None)
        err = max(err, float(np.abs(X[ok] @ coef[:, k] - logit(p[ok, k])).max()))
    tr = meta["strat_fold"].to_numpy() <= 8
    return coef[:-1], coef[-1], emb[tr].mean(0), np.cov(emb[tr], rowvar=False), err


def coral_scores(emb, W, b, mu_s, cov_s, eps=1.0):
    """CORAL: whiten the target embeddings, re-colour with the source covariance, shift to the
    source mean; then the network's output layer."""
    d = emb.shape[1]
    cov_t = np.cov(emb, rowvar=False) + eps * np.eye(d)
    A = np.real(np.linalg.solve(sqrtm(cov_t), np.eye(d)) @ sqrtm(cov_s + eps * np.eye(d)))
    z = (emb - emb.mean(0)) @ A + mu_s
    return 1 / (1 + np.exp(-(z @ W + b)))


def home_counts(idx):
    """Per finding: PTB-XL fold-10 scores of positives and negatives (the BAYES-HOME prior)."""
    p, _, meta = load_scores("ptbxl", idx)
    te = meta["strat_fold"].to_numpy() == 10
    out = {}
    for k, f in enumerate(PANEL):
        y = meta[f].to_numpy()[te].astype(bool)
        out[f] = (p[te, k][y], p[te, k][~y])
    return out


def bayes_threshold(pos, neg, f_star, prior=None, post=POST):
    """Highest threshold with P(sens >= s*) >= POST; then P(FPR <= f*) >= POST, else nan."""
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    cand = np.sort(pos)[::-1]                    # thresholds at positive scores, highest first
    hits = np.arange(1, len(cand) + 1)
    a, b = 1 + hits, 1 + len(cand) - hits
    if prior is not None:
        hp = np.sort(prior[0])
        h_hits = len(hp) - np.searchsorted(hp, cand, side="left")   # home positives >= tau
        a, b = a + h_hits, b + len(hp) - h_hits
    ok = beta.sf(S_STAR, a, b) >= post
    if not ok.any():
        return np.nan
    tau = float(cand[np.flatnonzero(ok)[0]])     # the first (highest) threshold that passes
    fp = int((neg >= tau).sum())
    a, b = 1 + fp, 1 + len(neg) - fp
    if prior is not None:
        h_fp = int((prior[1] >= tau).sum())
        a, b = a + h_fp, b + len(prior[1]) - h_fp
    return tau if beta.cdf(f_star, a, b) >= post else np.nan


def riley_needed(f_star):
    """Positives and negatives needed for 95% half-widths SENS_HALF at s* and f*/2 at f*."""
    n_pos = int(np.ceil(Z ** 2 * S_STAR * (1 - S_STAR) / SENS_HALF ** 2))
    n_neg = int(np.ceil(Z ** 2 * f_star * (1 - f_star) / (f_star / 2) ** 2))
    return n_pos, n_neg


def run_target(target, idx, home, prior, layer, reps, out_csv):
    p_all, emb, meta = load_scores(target, idx)
    n_rec = len(meta)
    base = 100 + zlib.crc32(target.removesuffix("_half").encode()) % 900  # as ecg_e3_cab.py
    findings = e3.judged_findings(meta, BUDGETS)
    W, b, mu_s, cov_s, _ = layer
    p_coral = coral_scores(emb, W, b, mu_s, cov_s)
    print(f"{target}: {n_rec} ECGs; findings {findings}", flush=True)
    rows, t0 = [], time.time()
    pool = np.arange(n_rec)
    for n in [x for x in BUDGETS if x <= n_rec // 2]:
        for rep in range(reps):
            seed = base * 10_000_000 + n * 1000 + rep
            rng = np.random.default_rng(seed)
            lab = np.zeros(n_rec, bool)
            lab_idx = rng.choice(pool, size=n, replace=False)   # the same draw as E3
            lab[lab_idx] = True
            for f in findings:
                k = PANEL.index(f)
                y = np.nan_to_num(meta[f].to_numpy(dtype=float)).astype(bool)
                frng = np.random.default_rng(seed + 7919 * (k + 1))
                cert = np.zeros(n_rec, bool)
                for grp in (lab_idx[y[lab_idx]], lab_idx[~y[lab_idx]]):
                    g = frng.permutation(grp)
                    cert[g[: len(g) // 2]] = True
                fit = lab & ~cert
                h = home[(f, S_STAR)]
                f_star = e3.MARGINS[MARGIN](h["fpr"])
                src = {"wmax": p_all[:, k], "smax": p_all[:, k], "septic": y}
                cor = {"wmax": p_coral[:, k], "smax": p_coral[:, k], "septic": y}
                pos, neg = p_all[lab & y, k], p_all[lab & ~y, k]
                n_pos, n_neg = riley_needed(f_star)
                if (lab & y).sum() >= n_pos and (lab & ~y).sum() >= n_neg:
                    p_ad = fit_adapt(np.column_stack([emb, logit(p_all[:, k])]), y, fit)
                    ada = None if p_ad is None else {"wmax": p_ad, "smax": p_ad, "septic": y}
                    rr, tr = naive_select(src, ada, y, lab, cert, h["tau"], S_STAR, f_star)
                    riley = ({"KEEP": src, "CALIBRATE": src, "ADAPT": ada}.get(rr), tr, rr)
                else:
                    riley = (None, np.nan, "BLOCK")
                tc = largest_threshold_for(p_coral[lab & y, k], S_STAR)
                cv_ok = np.isfinite(tc) and (p_coral[lab & ~y, k] >= tc).mean() <= f_star
                choices = {
                    "BAYES-FLAT": (src, bayes_threshold(pos, neg, f_star), "CALIBRATE"),
                    "BAYES-MATCHED": (src, bayes_threshold(pos, neg, f_star, post=1 - e3.ALPHA / 4), "CALIBRATE"),
                    "BAYES-HOME": (src, bayes_threshold(pos, neg, f_star, prior[f]), "CALIBRATE"),
                    "RILEY-SIZE": riley,
                    "CORAL": (cor, h["tau"], "KEEP"),
                    "CORAL-VAL": (cor, tc if cv_ok else np.nan, "CALIBRATE"),
                }
                for pol, (m, tau, rem) in choices.items():
                    cohort = ~fit if rem == "ADAPT" else np.ones(n_rec, bool)
                    on, sens, fpr, unsafe = judge(m, tau, y, cohort, f_star, S_STAR)
                    rows.append({"target": target, "finding": f, "n_labelled": n, "rep": rep,
                                 "policy": pol, "remedy": rem if on else "BLOCK", "activated": on,
                                 "sens_cohort": sens, "fpr_cohort": fpr, "unsafe_cohort": unsafe,
                                 "f_star": f_star})
            if (rep + 1) % 50 == 0:
                print(f"  {target} n={n} rep {rep + 1}/{reps} ({time.time() - t0:.0f}s)", flush=True)
    res = pd.DataFrame(rows)
    res.to_csv(out_csv, index=False)
    return res


def summarise(w7, err):
    e3_runs = pd.concat([pd.read_csv(e3.OUT / f"E3_runs_{t}.csv") for t in e3.TARGETS], ignore_index=True)
    e3_runs = e3_runs[(e3_runs.s_star == S_STAR) & (e3_runs.margin == MARGIN) & e3_runs.policy.isin(FROM_E3)]
    keys = w7[["target", "finding"]].drop_duplicates()
    e3_runs = e3_runs.merge(keys, on=["target", "finding"])
    cols = ["target", "finding", "n_labelled", "rep", "policy", "activated", "unsafe_cohort"]
    res = pd.concat([w7[cols], e3_runs[cols]], ignore_index=True)
    res["unsafe_cohort"] = res.unsafe_cohort.astype(bool)
    pol = POLICIES + FROM_E3
    per = res.groupby(["policy", "target", "finding", "n_labelled"]).agg(
        unsafe=("unsafe_cohort", "mean"), on=("activated", "mean")).reset_index()
    lines = ["# W7: stronger comparators (ECG)", "",
             f"Primary criterion (s* = {S_STAR}, {MARGIN} margin); judged on the whole target cohort; "
             f"same label samples as E3; {per[['target', 'finding']].drop_duplicates().shape[0]} transfers. "
             f"Output layer recovered from PTB-XL embeddings to within {err:.1e} on the logit scale (unsaturated scores).", "",
             "Unsafe rate per transfer and budget (share of runs switching on an unsafe configuration), "
             "summarised over all transfer-budget cells:", "",
             "| policy | mean unsafe | worst cell | cells above 5% | mean switched on |", "|---|---|---|---|---|"]
    for p in pol:
        g = per[per.policy == p]
        lines.append(f"| {p} | {g.unsafe.mean():.1%} | {g.unsafe.max():.0%} | "
                     f"{(g.unsafe > 0.05).sum()} of {len(g)} | {g.on.mean():.1%} |")
    lines += ["", "By budget (mean unsafe over transfers; switched on in brackets):", "",
              "| n | " + " | ".join(pol) + " |", "|---|" + "---|" * len(pol)]
    for n, g in per.groupby("n_labelled"):
        cells = []
        for p in pol:
            s = g[g.policy == p]
            cells.append(f"{s.unsafe.mean():.1%} ({s.on.mean():.0%})" if len(s) else "-")
        lines.append(f"| {n} | " + " | ".join(cells) + " |")
    lines += ["", "CORAL (no labels) per transfer: unsafe (U), safe (S) or blocked (-), the same in every run:", ""]
    c = per[(per.policy == "CORAL")].drop_duplicates(["target", "finding"])
    lines.append(", ".join(f"{r.target}/{r.finding}: {'-' if r.on == 0 else ('U' if r.unsafe > 0 else 'S')}"
                           for r in c.itertuples()))
    (e3.OUT / "W7_report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=100)
    ap.add_argument("--targets", default=",".join(e3.TARGETS))
    ap.add_argument("--summary-only", action="store_true")
    a = ap.parse_args()
    idx = pd.read_csv(e3.INDEX_CSV, low_memory=False).set_index("record_id")
    layer = output_layer(idx)
    print(f"output layer recovered; max logit error {layer[4]:.2e}", flush=True)
    parts = []
    if not a.summary_only:
        home = e3.home_operating_points(idx)
        prior = home_counts(idx)
    for t in a.targets.split(","):
        out_csv = e3.OUT / f"W7_runs_{t}.csv"
        if out_csv.exists():
            parts.append(pd.read_csv(out_csv))
        elif not a.summary_only:
            parts.append(run_target(t, idx, home, prior, layer, a.reps, out_csv))
    summarise(pd.concat(parts, ignore_index=True), layer[4])


if __name__ == "__main__":
    main()
