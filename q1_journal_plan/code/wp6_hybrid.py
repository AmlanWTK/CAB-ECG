"""WP6: hybrid recalibration gate, compared with CAB's recalibration gate on random labels.

The labelling design is chosen per transfer before any label, from the scores alone:
  - if the vendor threshold flags at least FLAG_CUT of the target's ECGs (a common finding),
    label at random and use CAB's exact binomial tests: identical to CERT-RECAL in E3;
  - otherwise draw records with replacement, half uniformly and half from those scored above the
    label-free threshold tau0 or in the band of 2x as many just below it, until n distinct records
    are labelled, and use the anytime-valid betting tests (wp6_betting.py).
FLAG_CUT = 0.25 was set from the WP6 feasibility study on 9 ECG transfers (post hoc; to be checked
on the sepsis data).

Weighted branch, as CAB's stage 1 at delta = alpha/4 per test: thresholds on a label-free grid are
tested for sensitivity in fixed sequence from the lowest upwards; the highest passing one is
tested for FPR; KEEP if the vendor threshold is no lower and also passes the FPR test. Judged on the
whole cohort (primary judge). ADAPT is not part of this comparison.

Run from the repository root after E3 (seed 0):
    python q1_journal_plan/code/wp6_hybrid.py
Writes outputs/ecg/WP6_hybrid_runs.csv and WP6_hybrid.md.
"""

import sys
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ecg_e3_cab as E  # noqa: E402
import wp6_betting as B  # noqa: E402

S_STAR, MARGIN, DELTA, REPS = 0.90, "relative", E.ALPHA / 4, 100
FLAG_CUT = 0.25
BUDGETS = [250, 500, 1000, 2000, 4000, 8000, 16000]


def band_design(s, tau0):
    n = len(s)
    above = s >= tau0
    below = np.flatnonzero(~above)
    band = np.zeros(n, bool)
    band[below[np.argsort(-s[below])][: 2 * above.sum()]] = True
    focus = above | band
    return 0.5 / n + 0.5 * focus / focus.sum()


def draws_until(rng, q, n, reps):
    """Draw with replacement until n distinct records per repeat (capped at 8n draws).
    Returns draws (reps x T) and, per repeat, how many draws were used."""
    T = 8 * n
    idx = rng.choice(len(q), size=(reps, T), replace=True, p=q)
    used = np.empty(reps, int)
    for r in range(reps):
        _, first = np.unique(idx[r], return_index=True)
        first = np.sort(first)
        used[r] = first[n - 1] + 1 if len(first) >= n else T
    return idx, used


def passes(x, lower, used):
    """Anytime-valid test passed by draw `used` (capital crossed 1/delta at or before it)."""
    t = B.certify_times(x, lower, DELTA)
    return (t > 0) & (t <= used)


def weighted_gate(rng, s, y, q, tau_home, f_star, n, grid):
    idx, used = draws_until(rng, q, n, REPS)
    sel = np.full(REPS, np.nan)
    alive = np.ones(REPS, bool)
    for tau in grid:  # ascending: most sensitive first
        x, lo = B.sens_increments(idx, y, s >= tau, q, S_STAR)
        ok = passes(x, lo, used) & alive
        sel = np.where(ok, tau, sel)
        alive &= ok
        if not alive.any():
            break
    remedy = np.full(REPS, "BLOCK", dtype=object)
    tau_out = np.full(REPS, np.nan)
    for r in np.flatnonzero(np.isfinite(sel)):
        def fpr_ok(t):
            x, lo = B.fpr_increments(idx[r:r + 1], y, s >= t, q, f_star)
            return bool(passes(x, lo, used[r:r + 1])[0])
        if fpr_ok(sel[r]):
            if tau_home <= sel[r] and fpr_ok(tau_home):
                remedy[r], tau_out[r] = "KEEP", tau_home
            else:
                remedy[r], tau_out[r] = "CALIBRATE", sel[r]
    return remedy, tau_out


def main():
    idx = pd.read_csv(E.INDEX_CSV, low_memory=False).set_index("record_id")
    home = E.home_operating_points(idx)
    rows = []
    for t in E.TARGETS:
        p_all, _, meta = E.load_scores(t, idx)
        n_rec = len(meta)
        e3 = pd.read_csv(E.OUT / f"E3_runs_{t}.csv")
        e3 = e3[(e3.s_star == S_STAR) & (e3.margin == MARGIN) & (e3.policy == "CERT-RECAL")]
        for f in E.judged_findings(meta, BUDGETS):
            k = E.PANEL.index(f)
            s, y = p_all[:, k], meta[f].to_numpy().astype(bool)
            h = home[(f, S_STAR)]
            f_star = E.MARGINS[MARGIN](h["fpr"])
            flagged = float((s >= h["tau"]).mean())
            base = e3[e3.finding == f]
            for n in [b for b in BUDGETS if b <= n_rec // 2]:
                b = base[base.n_labelled == n]
                rec = {"target": t, "finding": f, "n_labelled": n, "flagged": flagged,
                       "cab_on": b.activated.mean(), "cab_unsafe": b.unsafe_cohort.mean()}
                if flagged >= FLAG_CUT:
                    rec.update(design="random", hyb_on=rec["cab_on"], hyb_unsafe=rec["cab_unsafe"])
                else:
                    tau0 = float(np.quantile(s, 1 - h["share"]))
                    q = band_design(s, tau0)
                    ranks = np.unique(np.geomspace(5, n_rec // 2, 60).astype(int))
                    grid = np.sort(np.unique(np.sort(s)[::-1][ranks - 1]))
                    rng = np.random.default_rng(zlib.crc32(f"{t}{f}{n}".encode()))
                    remedy, tau = weighted_gate(rng, s, y, q, h["tau"], f_star, n, grid)
                    on = remedy != "BLOCK"
                    unsafe = np.zeros(REPS, bool)
                    for r in np.flatnonzero(on):
                        sens = (s[y] >= tau[r]).mean()
                        fpr = (s[~y] >= tau[r]).mean()
                        unsafe[r] = sens < S_STAR or fpr > f_star
                    rec.update(design="weighted", hyb_on=on.mean(), hyb_unsafe=unsafe.mean())
                rows.append(rec)
                print(f"{t} {f} n={n} {rec['design']}: on {rec['cab_on']:.2f} -> {rec['hyb_on']:.2f}, "
                      f"unsafe {rec['cab_unsafe']:.3f} -> {rec['hyb_unsafe']:.3f}", flush=True)
    res = pd.DataFrame(rows)
    res.to_csv(E.OUT / "WP6_hybrid_runs.csv", index=False)
    per_t = res.groupby(["target", "finding", "design"]).agg(
        cab_unsafe=("cab_unsafe", "mean"), hyb_unsafe=("hyb_unsafe", "mean"),
        cab_on=("cab_on", "mean"), hyb_on=("hyb_on", "mean")).reset_index()
    first_on = lambda col: res[res[col] >= 0.5].groupby(["target", "finding"]).n_labelled.min()  # noqa: E731
    per_t = per_t.join(first_on("cab_on").rename("cab_first_half_on"), on=["target", "finding"])
    per_t = per_t.join(first_on("hyb_on").rename("hyb_first_half_on"), on=["target", "finding"])
    summary = pd.DataFrame({
        "mean_unsafe": [per_t.cab_unsafe.mean(), per_t.hyb_unsafe.mean()],
        "worst_unsafe": [per_t.cab_unsafe.max(), per_t.hyb_unsafe.max()],
        "cells_over_alpha": [int((res.cab_unsafe > E.ALPHA).sum()), int((res.hyb_unsafe > E.ALPHA).sum())],
        "switched_on": [res.cab_on.mean(), res.hyb_on.mean()],
        "transfers_half_on": [int(per_t.cab_first_half_on.notna().sum()), int(per_t.hyb_first_half_on.notna().sum())],
    }, index=["CAB recalibration (random labels)", "Hybrid recalibration"])
    lines = ["# WP6: hybrid recalibration gate vs CAB recalibration", "",
             f"s* = {S_STAR}, {MARGIN} FPR limit, alpha = {E.ALPHA}, {REPS} repeats, judged on the whole "
             f"cohort. Weighted design where the vendor threshold flags < {FLAG_CUT:.0%} of the target.", "",
             "```", summary.round(3).to_string(), "```", "",
             "Per transfer (first budget with at least half of runs switched on):", "", "```",
             per_t.round(3).to_string(index=False), "```", ""]
    (E.OUT / "WP6_hybrid.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
