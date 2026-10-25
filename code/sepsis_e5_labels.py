"""E5: how many local labels does certification need? A calculator, checked against the data.

Every CAB decision is a pair of exact binomial tests (cabsepsis/cab.py), each at level alpha/4:
  sensitivity  detections among k labelled SEPTIC patients      (H0: sensitivity < s*)
  false alerts alerts among m labelled NON-SEPTIC patients      (H0: false-alert rate > f*)
so the labels needed depend on (a) how far the model's true rates are from the targets and
(b) the septic share of the labelled patients. Septic patients are the scarce resource.

Part A, analytic (no data needed):
  septic patients needed for the sensitivity test, non-septic patients for the false-alert test,
  and total patients under random labelling, for a grid of targets, gaps and prevalences.
  Each test is given power sqrt(0.9), so both pass together with probability >= 0.9.
  ADAPT needs twice as many: half the labels fit the model, the other half certify it.

Part B, on the data (compute desktop; needs the E1 models and data caches):
  1. planning estimate: the Part A calculator applied to each model's real operating curve on
     the target's test patients (best threshold), i.e. what a hospital could compute in advance
     from an expected sensitivity / false-alert trade-off;
  2. simulation: CAB's exact decision rule on patients resampled from the target's test patients
     at budgets up to 32,000, with the imported and the oracle-adapted model held fixed. This is
     the certification cost alone (no refitting noise), so it is a lower bound on what the full
     E3 procedure needs;
  3. E3v2's labels needed, restated as septic patients labelled.

Run from the repository root:
    python code\\sepsis_e5_labels.py --analytic-only     (anywhere; seconds)
    python code\\sepsis_e5_labels.py                     (compute desktop; minutes)
Writes outputs/sepsis/E5_analytic.csv, E5_sim.csv, E5_needed.csv and E5_report.md.
"""

import argparse
import time
import zlib
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy.stats import binom

from cabsepsis.cab import cab_select
from cabsepsis.data import REPO

OUT = REPO / "outputs" / "sepsis"
ALPHA = 0.05
POWER = 0.9
KMAX = 100_000
S_STARS = [0.75, 0.80, 0.85]
F_STARS = [0.30, 0.40, 0.50]
GAPS = [0.02, 0.03, 0.05, 0.075, 0.10]
PREVALENCES = [0.03, 0.057, 0.088, 0.15]
BUDGETS = [250, 500, 1000, 2000, 3000, 4000, 6000, 8000, 12000, 16000, 24000, 32000]


# ---------------------------------------------------------------------------------- Part A
def pass_cutoff(k, p0, delta):
    """Smallest count c with P(Binom(k, p0) >= c) <= delta, for each k (the exact one-sided test
    of 'rate >= p0' in cab.py passes iff the count is >= c; c > k means it can never pass)."""
    k = np.asarray(k, dtype=np.int64)
    c = binom.ppf(1 - delta, k, p0).astype(np.int64) + 1
    for _ in range(3):   # guard against floating-point edge cases in ppf
        up = binom.sf(c - 1, k, p0) > delta
        down = (c >= 1) & (binom.sf(c - 2, k, p0) <= delta)
        c = c + up - down
    return c


@lru_cache(maxsize=None)
def _needed(p_true, p0, delta, power):
    if p_true <= p0:
        return None
    k = np.arange(1, KMAX + 1)
    pw = binom.sf(pass_cutoff(k, p0, delta) - 1, k, p_true)
    hit = np.flatnonzero(pw >= power)
    return int(k[hit[0]]) if len(hit) else None


def septic_needed(sens, s_star, delta=ALPHA / 4, power=POWER ** 0.5):
    """Labelled septic patients for the sensitivity test to pass with the given power."""
    return _needed(round(float(sens), 4), float(s_star), float(delta), float(power))


def nonseptic_needed(fa, f_star, delta=ALPHA / 4, power=POWER ** 0.5):
    """Labelled non-septic patients for the false-alert test (the same test on 1 - rate)."""
    return _needed(round(1 - float(fa), 4), 1 - float(f_star), float(delta), float(power))


def total_needed(k, m, prevalence, adapt=False):
    """Patients to label at random so that, on average, k septic and m non-septic are included."""
    if k is None or m is None:
        return None
    n = max(k / prevalence, m / (1 - prevalence))
    return int(np.ceil(n * (2 if adapt else 1)))


def analytic():
    rows = []
    for g in GAPS:
        for s in S_STARS:
            rows.append({"table": "septic", "target": s, "gap": g,
                         "needed": septic_needed(s + g, s)})
        for f in F_STARS:
            rows.append({"table": "non-septic", "target": f, "gap": g,
                         "needed": nonseptic_needed(f - g, f)})
        k, m = septic_needed(0.80 + g, 0.80), nonseptic_needed(0.40 - g, 0.40)
        for pi in PREVALENCES:
            rows.append({"table": "total (s*=0.80, f*=0.40)", "target": pi, "gap": g,
                         "needed": total_needed(k, m, pi)})
            rows.append({"table": "total ADAPT (s*=0.80, f*=0.40)", "target": pi, "gap": g,
                         "needed": total_needed(k, m, pi, adapt=True)})
    return pd.DataFrame(rows)


def analytic_lines(an):
    lines = ["## Part A: labels needed for certification (exact tests, alpha = 0.05)", "",
             f"Each test at level alpha/4 = {ALPHA / 4}, power sqrt({POWER}) so that both pass with "
             f"probability >= {POWER}. gap = how far the model's true rate is on the safe side of "
             "the target.", ""]
    titles = {"septic": "Septic patients needed (sensitivity test); columns = target s*",
              "non-septic": "Non-septic patients needed (false-alert test); columns = target f*",
              "total (s*=0.80, f*=0.40)": "Total patients, random labelling, KEEP/CALIBRATE "
                                          "(same gap on both rates); columns = septic prevalence",
              "total ADAPT (s*=0.80, f*=0.40)": "Total patients, random labelling, ADAPT "
                                                "(half fit, half certify); columns = prevalence"}
    for t, title in titles.items():
        piv = an[an.table == t].pivot(index="gap", columns="target", values="needed")
        lines += [f"### {title}", "", "```", piv.to_string(), "```", ""]
    return lines


# ---------------------------------------------------------------------------------- Part B
def planning_estimate(m, septic, s_star, f_star, prevalence, adapt, tau=None, n_grid=300):
    """Smallest random-labelling budget over thresholds on the model's operating curve."""
    w, s = m["wmax"], m["smax"]
    sep_w, non_s = w[septic], s[~septic]
    taus = [tau] if tau is not None else np.unique(np.quantile(sep_w[np.isfinite(sep_w)],
                                                               np.linspace(0.0, 0.5, n_grid)))
    best = None
    for t in taus:
        sens, fa = (sep_w >= t).mean(), (non_s >= t).mean()
        if sens <= s_star or fa >= f_star:
            continue
        n = total_needed(septic_needed(sens, s_star), nonseptic_needed(fa, f_star), prevalence, adapt)
        if n is not None and (best is None or n < best[0]):
            best = (n, t, sens, fa)
    return best


def simulate(src, ada, septic, tau_home, s_star, f_star, n, reps, rng, alpha):
    """CAB's decision rule on n patients resampled (with replacement) from the base set."""
    N = len(septic)
    counts = {"KEEP": 0, "CALIBRATE": 0, "ADAPT": 0, "BLOCK": 0}
    n_sep = 0
    for _ in range(reps):
        idx = rng.integers(0, N, n)
        sp = septic[idx]
        sub_src = {"wmax": src["wmax"][idx], "smax": src["smax"][idx], "septic": sp}
        sub_ada = None if ada is None else {"wmax": ada["wmax"][idx], "smax": ada["smax"][idx],
                                            "septic": sp}
        lab = np.ones(n, bool)
        cert = np.zeros(n, bool)
        for grp in (np.flatnonzero(sp), np.flatnonzero(~sp)):
            g = rng.permutation(grp)
            cert[g[: len(g) // 2]] = True
        remedy, _ = cab_select(lab, cert, sub_src, sub_ada, tau_home, s_star, f_star, alpha)
        counts[remedy] += 1
        n_sep += int(sp.sum())
    out = {f"P_{k}": v / reps for k, v in counts.items()}
    out["septic_labelled"] = n_sep / reps
    return out


def subset(m, mask):
    return {"wmax": m["wmax"][mask], "smax": m["smax"][mask]}


def part_b(reps, alpha, directions):
    import lightgbm as lgb
    from cabsepsis.data import load_all
    from cabsepsis.features import load_features
    from sepsis_e3_cab import MARGINS, prepare_direction

    print("Loading data and features ...")
    df = load_all().sort_values(["pid", "hour"]).reset_index(drop=True)
    df["split"] = df["pid"].map(pd.read_csv(OUT / "splits.csv", index_col=0)["split"])
    X, meta = load_features(df)
    boosters = {s: lgb.Booster(model_file=str(OUT / f"lgbm_site{s}.txt")) for s in ["A", "B"]}

    sims, needs = [], []
    for d in directions:
        src, tgt = d.split("->")
        P = prepare_direction(src, tgt, X, meta, df, boosters)
        sf = P["sf"]
        base = P["test_mask"] if src != tgt else P["eligible"]
        septic = sf.septic[base]
        pool_prev = float(sf.septic[P["pool"]].mean())
        srcm = subset(P["srcd"], base)
        adam = None if P["ora_ad"] is None else subset(P["ora_ad"], base)
        t0 = time.time()
        for s_star in S_STARS:
            for margin in MARGINS:
                f_star = P["home"][s_star]["fa"] + margin
                tau_home = P["home"][s_star]["tau"]
                oracle = P["oracle"][(s_star, margin)]
                rng = np.random.default_rng(zlib.crc32(f"{d}|{s_star}|{margin}".encode()))
                first_ok = None
                for n in BUDGETS:
                    r = simulate(srcm, adam, septic, tau_home, s_star, f_star, n, reps, rng, alpha)
                    r["P_correct"] = sum(r[f"P_{o}"] for o in oracle.split("|") if f"P_{o}" in r)
                    sims.append({"direction": d, "s_star": s_star, "margin": margin, "f_star": f_star,
                                 "oracle": oracle, "n_labelled": n, **r})
                    if first_ok is None and r["P_correct"] >= POWER:
                        first_ok = (n, r["septic_labelled"])
                plan = None
                first = oracle.split("|")[0]
                if first == "KEEP":
                    plan = planning_estimate(srcm, septic, s_star, f_star, pool_prev, False, tau=tau_home)
                elif first == "CALIBRATE":
                    plan = planning_estimate(srcm, septic, s_star, f_star, pool_prev, False)
                elif first == "ADAPT" and adam is not None:
                    plan = planning_estimate(adam, septic, s_star, f_star, pool_prev, True)
                needs.append({"direction": d, "s_star": s_star, "margin": margin, "oracle": oracle,
                              "pool_prevalence": pool_prev,
                              "plan_patients": plan[0] if plan else None,
                              "plan_septic": int(round(plan[0] * pool_prev / (2 if first == "ADAPT" else 1)))
                              if plan else None,
                              "plan_sens": plan[2] if plan else None, "plan_fa": plan[3] if plan else None,
                              "sim_patients": first_ok[0] if first_ok else None,
                              "sim_septic": round(first_ok[1]) if first_ok else None})
        print(f"  {d}: simulated in {time.time() - t0:.0f}s")
    return pd.DataFrame(sims), pd.DataFrame(needs)


def e3_in_septic(needs):
    """E3v2 labels needed (full procedure, with refitting), restated as septic patients."""
    f = OUT / "E3v2_summary.csv"
    if not f.exists():
        return None
    summ = pd.read_csv(f)
    prev = needs.drop_duplicates("direction").set_index("direction")["pool_prevalence"]
    rows = []
    for (d, s, m), q in summ[summ.policy == "CAB"].groupby(["direction", "s_star", "margin"]):
        ok = q[(q.correct_rate >= 0.9) & (q.unsafe_rate <= 0.05)]
        n = int(ok.n_labelled.min()) if len(ok) else None
        rows.append({"direction": d, "s_star": s, "margin": m, "e3_patients": n,
                     "e3_septic": round(n * prev[d]) if n and d in prev else None})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--analytic-only", action="store_true")
    ap.add_argument("--reps", type=int, default=400)
    ap.add_argument("--alpha", type=float, default=ALPHA)
    ap.add_argument("--directions", default="A->B,B->A,A->A,B->B")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    an = analytic()
    an.to_csv(OUT / "E5_analytic.csv", index=False)
    lines = ["# E5: labels needed for certified deployment", ""] + analytic_lines(an)

    if not a.analytic_only:
        sims, needs = part_b(a.reps, a.alpha, a.directions.split(","))
        e3 = e3_in_septic(needs)
        if e3 is not None:
            needs = needs.merge(e3, on=["direction", "s_star", "margin"], how="left")
        sims.to_csv(OUT / "E5_sim.csv", index=False)
        needs.to_csv(OUT / "E5_needed.csv", index=False)
        lines += ["## Part B: labels needed per direction and criterion", "",
                  "plan_*: calculator on the model's real operating curve (best threshold).",
                  "sim_*: smallest budget where CAB's exact rule picks the oracle remedy in >= 90% "
                  f"of {a.reps} resamples, models held fixed (certification cost only).",
                  "e3_*: the full E3v2 procedure, ADAPT refitted on each sample (30 reps).",
                  "*_septic: septic patients among those labelled.", "",
                  "```", needs.round(3).to_string(index=False), "```", ""]
        s0, m0 = 0.80, 0.05
        prim = sims[np.isclose(sims.s_star, s0) & np.isclose(sims.margin, m0)]
        cols = ["direction", "n_labelled", "septic_labelled", "P_KEEP", "P_CALIBRATE", "P_ADAPT",
                "P_BLOCK", "P_correct"]
        lines += [f"## Simulated CAB decisions, primary criterion (s* = {s0}, margin = {m0})", "",
                  "```", prim[cols].round(3).to_string(index=False), "```", ""]
    (OUT / "E5_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"Wrote {OUT / 'E5_report.md'}")


if __name__ == "__main__":
    main()
