"""WP6 feasibility: labels needed to certify one threshold per ECG transfer, by labelling design.

For each primary transfer with a safe CALIBRATE threshold (seed 0 scores): tau = the cohort's
highest threshold with sensitivity >= s* + 0.02 and FPR <= f* (an oracle choice, so that only
the labelling question differs). Over 100 repeats:

    binomial      CAB's exact binomial tests on random labels at fixed n; reported: the smallest n
                  on a grid with power >= 50%
    bet-uniform   betting test, records drawn uniformly (sequential: stops when both certify)
    bet-score     betting test, records drawn in proportion to the imported score (floor eps)
    bet-band      betting test, records drawn mostly from those scored at or just below tau,
                  where misses would be (the K records just below tau, K = 2 x those above)
    wor-*         without-replacement betting, stratified by score (above tau, the band below,
                  the rest), labels shared out by fixed proportions; no record labelled twice

Labels = distinct records labelled until both sensitivity and FPR are certified (each at
delta = alpha/4); reported is the median over all repeats, counting a repeat that never
certified within the cap as infinite, so it is the label count by which half of the repeats have
certified (blank: fewer than half did). This matches the binomial's power >= 50%.

Run from the repository root:
    python q1_journal_plan/code/wp6_feasibility.py
Writes outputs/ecg/WP6_feasibility.csv and .md.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ecg_e3_cab as E  # noqa: E402
import wp6_betting as B  # noqa: E402
from cabsepsis.cab import fa_test, sens_test  # noqa: E402

S_STAR, MARGIN, DELTA, REPS = 0.90, "relative", E.ALPHA / 4, 100


def oracle_tau(s, y, f_star):
    order = np.sort(np.unique(s[y]))[::-1]
    for tau in order:  # highest first
        if (s[y] >= tau).mean() >= S_STAR + 0.02:
            return tau if (s[~y] >= tau).mean() <= f_star else np.nan
    return np.nan


def binomial_n(rng, s, y, tau, f_star, cap):
    grid = [int(250 * 2 ** (j / 2)) for j in range(30)]
    for n in [g for g in grid if g <= cap]:
        ok = 0
        for _ in range(REPS):
            lab = rng.choice(len(y), size=n, replace=False)
            yl, sl = y[lab], s[lab]
            ok += sens_test(sl[yl], tau, S_STAR, DELTA) and fa_test(sl[~yl], tau, f_star, DELTA)
        if ok >= REPS / 2:
            return n
    return np.nan


def betting(rng, q, s, y, tau, f_star, T):
    idx = B.draws(rng, q, REPS, T)
    above = s >= tau
    xs, lo_s = B.sens_increments(idx, y, above, q, S_STAR)
    xf, lo_f = B.fpr_increments(idx, y, above, q, f_star)
    ts, tf = B.certify_times(xs, lo_s, DELTA), B.certify_times(xf, lo_f, DELTA)
    done = (ts > 0) & (tf > 0)
    t = np.maximum(ts, tf)
    labels = np.full(REPS, np.inf)  # repeats that never certified count as needing more than the cap
    labels[done] = B.unique_until(idx[done], t[done])
    med = float(np.median(labels))  # the label count by which half of all repeats have certified
    return done.mean(), med if np.isfinite(med) else np.nan


def wor(seed, s, y, tau, f_star, strata, props):
    """Without-replacement stratified test; sensitivity and FPR use the same labelled records
    (the same seed gives the same random orders in both calls)."""
    above = (s >= tau).astype(float)
    z = y * (above - S_STAR)
    w = (1 - y) * (f_star - above)
    n = len(y)
    ts = B.stratified_certify(np.random.default_rng(seed), z, strata, props, -S_STAR, 1 - S_STAR, DELTA, REPS, n)
    tf = B.stratified_certify(np.random.default_rng(seed), w, strata, props, -(1 - f_star), f_star, DELTA, REPS, n)
    done = (ts > 0) & (tf > 0)
    labels = np.where(done, np.maximum(ts, tf), np.inf)
    med = float(np.median(labels))
    return done.mean(), med if np.isfinite(med) else np.nan


def main():
    idx = pd.read_csv(E.INDEX_CSV, low_memory=False).set_index("record_id")
    home = E.home_operating_points(idx)
    budgets = [250, 500, 1000, 2000, 4000, 8000, 16000]
    rng = np.random.default_rng(2026)
    rows = []
    for t in E.TARGETS:
        p_all, _, meta = E.load_scores(t, idx)
        n_rec = len(meta)
        for f in E.judged_findings(meta, budgets):
            k = E.PANEL.index(f)
            s, y = p_all[:, k], meta[f].to_numpy().astype(bool)
            f_star = E.MARGINS[MARGIN](home[(f, S_STAR)]["fpr"])
            tau = oracle_tau(s, y, f_star)
            if not np.isfinite(tau):
                continue
            T = min(2 * n_rec, 40000)
            row = {"target": t, "finding": f, "N": n_rec, "positives": int(y.sum()),
                   "prevalence": y.mean(), "sens": (s[y] >= tau).mean(), "fpr": (s[~y] >= tau).mean(),
                   "f_star": f_star, "floor_42": int(np.ceil(42 / y.mean())),
                   "binomial": binomial_n(rng, s, y, tau, f_star, n_rec)}
            above = s >= tau
            below_rank = np.argsort(-np.where(above, -np.inf, s))[: 2 * above.sum()]
            band = np.zeros(n_rec, bool)
            band[below_rank] = True
            designs = {"bet-uniform": np.full(n_rec, 1 / n_rec),
                       "bet-score .5": B.design_q(s, 0.5),
                       "bet-band .5": 0.5 / n_rec + 0.5 * (above | band) / (above | band).sum(),
                       "bet-band .8": 0.8 / n_rec + 0.2 * (above | band) / (above | band).sum()}
            for name, q in designs.items():
                share, lab = betting(rng, q, s, y, tau, f_star, T)
                row[name] = lab
                row[name + " done"] = share
            strata = np.where(above, 0, np.where(band, 1, 2))
            for name, st, props in [("wor-uniform", np.zeros(n_rec, int), [1.0]),
                                    ("wor-strata 25/25/50", strata, [.25, .25, .5]),
                                    ("wor-strata 10/40/50", strata, [.10, .40, .50])]:
                share, lab = wor(int(rng.integers(1 << 31)), s, y, tau, f_star, st, props)
                row[name] = lab
                row[name + " done"] = share
            rows.append(row)
            print(f"{t} {f}: binomial {row['binomial']}, best with replacement "
                  f"{np.nanmin([row[k] for k in designs] + [np.inf])}, without: {row['wor-uniform']}, "
                  f"{row['wor-strata 25/25/50']}, {row['wor-strata 10/40/50']}", flush=True)
    res = pd.DataFrame(rows)
    res.to_csv(E.OUT / "WP6_feasibility.csv", index=False)
    cols = ["target", "finding", "prevalence", "floor_42", "binomial", "bet-uniform",
            "bet-score .5", "bet-band .5", "wor-uniform", "wor-strata 25/25/50", "wor-strata 10/40/50"]
    done = [c for c in res.columns if c.endswith(" done")]
    lines = ["# WP6 feasibility: labels to certify one oracle threshold", "",
             f"s* = {S_STAR}, {MARGIN} FPR limit, delta = {DELTA} per test, {REPS} repeats. Binomial: smallest "
             "n on the grid with power >= 50%. Betting designs: distinct labels by which half of all repeats "
             "had certified both tests (NaN: fewer than half within the cap).", "",
             "```", res[cols].round(3).to_string(index=False), "```", "",
             "Share of repeats certified within the cap:", "", "```",
             res[["target", "finding"] + done].round(2).to_string(index=False), "```", ""]
    (E.OUT / "WP6_feasibility.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
