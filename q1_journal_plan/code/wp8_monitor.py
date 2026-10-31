"""WP8 (ECG): a monitor that re-opens the gate when a switched-on finding stops being safe.

After CAB switches a finding on at site A (the site's largest label budget in ecg_e3_cab.py), a random sample of the
ECGs it then reads is audited: each gets a cardiologist label, one at a time. After T_PRE audits
the population changes to B: another cohort, including the Brazilian cohort read with the signal
gain halved (code15_half; CAB switches nothing on at code15 itself, so it is never A). The monitor must stay quiet while the deployed model and
threshold are safe on the population being read, and raise an alarm (re-open the gate) once they
are not.

MONITOR. Two betting tests, one per criterion, each at delta/2:
    positives:  x = s* - hit         mean <= 0 while sensitivity >= s*
    negatives:  x = hit - f*         mean <= 0 while FPR <= f*
Capital K_t = prod (1 + lambda_i x_i), with lambda_i >= 0 chosen from the previous W
observations only (aGRAPA on a sliding window, clipped so each factor is at least 1 - c). While
every audit comes from a safe population K_t is a nonnegative supermartingale, so by Ville's
inequality the chance that it ever reaches 2/delta is at most delta/2: the probability of any
false alarm, over an unlimited number of audits, is at most delta. The window lets the bets grow
soon after a change instead of being held down by the safe history.

CUSUM-<ARL>. The same bets in a CUSUM e-detector (Shin, Ramdas and Rinaldo): per criterion,
log M_j = max(log M_{j-1}, 0) + log(1 + lambda_j x_j), which restarts the evidence whenever it
falls below 1; alarm when the average of the two statistics reaches ARL. While every audit comes
from a safe population, the expected number of audits before a false alarm is at least ARL. This
bounds the average time to a false alarm, not the probability of any false alarm.

Comparators (no guarantee over repeated looks):
    CHECK-POINT  every BATCH audits, the point estimates on the last BATCH audits against s*, f*
    CHECK-TEST   every BATCH audits, exact one-sided binomial tests on the last BATCH audits at
                 delta/2 each, not corrected for the repeated looks

Truth: the deployed model and threshold judged on the whole cohort being read (as the primary
judge in ecg_e3_cab.py). A scenario is a drift when the configuration is unsafe on B, a null when
it is safe on B (including B = A, no change).

Run from the repository root after ecg_e3_cab.py:
    python q1_journal_plan/code/wp8_monitor.py [--reps 200]
    python q1_journal_plan/code/wp8_monitor.py --window 250 --tag W8w250   (sensitivity analysis)
    python q1_journal_plan/code/wp8_monitor.py --t-post 16000 --tag W8long (longer horizon)
Writes outputs/ecg/<tag>_runs.csv and <tag>_report.md.
"""

import argparse
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binom
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ecg_e3_cab as e3  # noqa: E402
from ecg_e3_cab import PANEL, cab_select, home_operating_points, load_scores, logit  # noqa: E402

S_STAR, MARGIN = e3.PRIMARY
DELTA = 0.05          # monitor's error budget: chance of any false alarm while safe
WINDOW, C = 100, 0.5  # betting window (observations per criterion) and clipping
T_PRE, T_POST = 2000, 4000
BATCH = 250
MIN_POS = 50          # positives a cohort needs for its truth to be judged
ARLS = [5000, 20000]  # CUSUM monitors: guaranteed average audits to a false alarm
MONITORS = ["MONITOR"] + [f"CUSUM-{a // 1000}k" for a in ARLS] + ["CHECK-POINT", "CHECK-TEST"]
LARGE_SENS, LARGE_FPR = 0.05, 2.0   # reporting only: what counts as a large drift
BUDGETS = [250, 500, 1000, 2000, 4000, 8000, 16000]  # as ecg_e3_cab.py; the largest that fits is used


def fit_head(Z, y, fit):
    """ADAPT head as in ecg_e3_cab.fit_adapt, returned as a function so it can score other sites."""
    if y[fit].sum() < 2 or (~y[fit]).sum() < 2:
        return None
    sc = StandardScaler().fit(Z[fit])
    lr = LogisticRegression(C=0.1, max_iter=2000).fit(sc.transform(Z[fit]), y[fit])
    return lambda Zn: lr.predict_proba(sc.transform(Zn))[:, 1]


def window_bets(x, lower):
    """Predictable aGRAPA bets from the previous WINDOW values of x (pseudo-observation 0, weight 1)."""
    cs = np.concatenate([[0.0], np.cumsum(x)])
    cs2 = np.concatenate([[0.0], np.cumsum(x * x)])
    t = np.arange(len(x))
    lo = np.maximum(t - WINDOW, 0)
    k = t - lo + 1.0
    mu = (cs[t] - cs[lo]) / k
    var = np.maximum((cs2[t] - cs2[lo]) / k - mu * mu, 1e-12)
    return np.clip(mu / (var + mu * mu), 0.0, C / abs(lower))


def first_crossing(x, lower, times):
    """Audit index at which the capital on x first reaches 2/delta, or -1."""
    if len(x) == 0:
        return -1
    logk = np.cumsum(np.log1p(window_bets(x, lower) * x))
    hit = np.flatnonzero(logk >= np.log(2 / DELTA))
    return int(times[hit[0]]) if len(hit) else -1


def monitor_alarm(y, h, f_star):
    pos, neg = np.flatnonzero(y), np.flatnonzero(~y)
    a = [first_crossing(S_STAR - h[pos].astype(float), S_STAR - 1, pos),
         first_crossing(h[neg].astype(float) - f_star, -f_star, neg)]
    a = [t for t in a if t >= 0]
    return min(a) if a else -1


def cusum_path(x, lower, times, T):
    """log CUSUM statistic on the audit clock (0 before the stream's first observation)."""
    out = np.zeros(T)
    if len(x) == 0:
        return out
    S = np.concatenate([[0.0], np.cumsum(np.log1p(window_bets(x, lower) * x))])
    W = S[1:] - np.minimum.accumulate(S[:-1])       # W_j = max(W_{j-1}, 0) + z_j, W_0 = 0
    last = np.searchsorted(times, np.arange(T), side="right") - 1
    out[last >= 0] = W[last[last >= 0]]
    return out


def cusum_alarm(y, h, f_star, arl):
    T = len(y)
    pos, neg = np.flatnonzero(y), np.flatnonzero(~y)
    ws = cusum_path(S_STAR - h[pos].astype(float), S_STAR - 1, pos, T)
    wf = cusum_path(h[neg].astype(float) - f_star, -f_star, neg, T)
    hit = np.flatnonzero(np.logaddexp(ws, wf) - np.log(2) >= np.log(arl))
    return int(hit[0]) if len(hit) else -1


def batch_alarm(y, h, f_star, test):
    for end in range(BATCH, len(y) + 1, BATCH):
        yb, hb = y[end - BATCH:end], h[end - BATCH:end]
        n, m = int(yb.sum()), int((~yb).sum())
        miss, fp = int((yb & ~hb).sum()), int((~yb & hb).sum())
        if test:
            bad = (n and binom.sf(miss - 1, n, 1 - S_STAR) <= DELTA / 2) or \
                  (m and binom.sf(fp - 1, m, f_star) <= DELTA / 2)
        else:
            bad = (n and miss / n > 1 - S_STAR) or (m and fp / m > f_star)
        if bad:
            return end - 1
    return -1


def cohort(name, idx):
    p, emb, meta = load_scores(name, idx)
    return {"p": p, "emb": emb, "meta": meta, "n": len(meta)}


def run_site(a_name, sites, home, reps):
    A = sites[a_name]
    base = 100 + zlib.crc32(a_name.encode()) % 900
    n_lab = max(b for b in BUDGETS if b <= A["n"] // 2)
    findings = e3.judged_findings(A["meta"], BUDGETS)
    rows = []
    for f in findings:
        k = PANEL.index(f)
        h0 = home[(f, S_STAR)]
        f_star = e3.MARGINS[MARGIN](h0["fpr"])
        yA = np.nan_to_num(A["meta"][f].to_numpy(dtype=float)).astype(bool)
        targets = [b for b in sites if np.nansum(sites[b]["meta"][f].to_numpy()) >= MIN_POS]
        for rep in range(reps):
            rng = np.random.default_rng(base * 1_000_000 + k * 10_000 + rep)
            lab = np.zeros(A["n"], bool)
            lab_idx = rng.choice(A["n"], size=n_lab, replace=False)
            lab[lab_idx] = True
            cert = np.zeros(A["n"], bool)
            for grp in (lab_idx[yA[lab_idx]], lab_idx[~yA[lab_idx]]):
                g = rng.permutation(grp)
                cert[g[: len(g) // 2]] = True
            fit = lab & ~cert
            src = {"wmax": A["p"][:, k], "smax": A["p"][:, k], "septic": yA}
            head = fit_head(np.column_stack([A["emb"], logit(A["p"][:, k])]), yA, fit)
            ada = None
            if head is not None:
                pa = head(np.column_stack([A["emb"], logit(A["p"][:, k])]))
                ada = {"wmax": pa, "smax": pa, "septic": yA}
            remedy, tau = cab_select(lab, cert, src, ada, h0["tau"], S_STAR, f_star, e3.ALPHA)
            if remedy == "BLOCK":
                rows.append({"site_a": a_name, "finding": f, "rep": rep, "remedy": remedy})
                continue

            def scores(S):
                if remedy == "ADAPT":
                    return head(np.column_stack([S["emb"], logit(S["p"][:, k])]))
                return S["p"][:, k]

            popA = ~fit if remedy == "ADAPT" else np.ones(A["n"], bool)
            hA = scores(A) >= tau
            sensA, fprA = hA[popA & yA].mean(), hA[popA & ~yA].mean()
            pre = rng.choice(np.flatnonzero(popA), size=T_PRE)
            for b in targets:
                B = sites[b]
                yB = np.nan_to_num(B["meta"][f].to_numpy(dtype=float)).astype(bool)
                hB = hA if b == a_name else scores(B) >= tau
                popB = popA if b == a_name else np.ones(B["n"], bool)
                sensB, fprB = hB[popB & yB].mean(), hB[popB & ~yB].mean()
                post = rng.choice(np.flatnonzero(popB), size=T_POST)
                y = np.concatenate([yA[pre], yB[post]])
                h = np.concatenate([hA[pre], hB[post]])
                row = {"site_a": a_name, "finding": f, "rep": rep, "remedy": remedy, "site_b": b,
                       "f_star": f_star, "sens_a": sensA, "fpr_a": fprA, "sens_b": sensB, "fpr_b": fprB,
                       "unsafe_a": bool(sensA < S_STAR or fprA > f_star),
                       "unsafe_b": bool(sensB < S_STAR or fprB > f_star)}
                row["MONITOR"] = monitor_alarm(y, h, f_star)
                for arl in ARLS:
                    row[f"CUSUM-{arl // 1000}k"] = cusum_alarm(y, h, f_star, arl)
                row["CHECK-POINT"] = batch_alarm(y, h, f_star, test=False)
                row["CHECK-TEST"] = batch_alarm(y, h, f_star, test=True)
                rows.append(row)
    return rows


def summarise(res, tag):
    on = res[res.remedy != "BLOCK"].copy()
    on = on[~on.unsafe_a.astype(bool)]  # deployments that were safe at A (CAB's own failures reported apart)
    on["kind"] = np.where(on.site_b == on.site_a, "no change",
                          np.where(on.unsafe_b, "drift to unsafe", "change, still safe"))
    lines = [f"# {tag}: monitoring after deployment (ECG)", "",
             f"s* = {S_STAR}, f* = {MARGIN} margin; delta = {DELTA}; window {WINDOW}; "
             f"{T_PRE} audits at A, then {T_POST} from B; checks every {BATCH} audits.", "",
             f"Deployments: {res.drop_duplicates(['site_a', 'finding', 'rep']).shape[0]} "
             f"(site, finding, repeat); switched on by CAB: "
             f"{res[res.remedy != 'BLOCK'].drop_duplicates(['site_a', 'finding', 'rep']).shape[0]}; "
             f"unsafe at A (CAB error, excluded below): "
             f"{res[(res.remedy != 'BLOCK') & res.unsafe_a.astype(bool)].drop_duplicates(['site_a', 'finding', 'rep']).shape[0]}.", ""]
    lines += ["## False alarms (any alarm while every audit came from a safe population)", "",
              "| scenario | runs | " + " | ".join(MONITORS) + " |", "|---|---|" + "---|" * len(MONITORS)]
    for kind in ["no change", "change, still safe"]:
        g = on[on.kind == kind]
        cells = [f"{(g[m] >= 0).mean():.1%}" for m in MONITORS]
        lines.append(f"| {kind} | {len(g)} | " + " | ".join(cells) + " |")
    g = on[on.kind == "drift to unsafe"]
    lines += ["", "## Drift to an unsafe population", "",
              f"{len(g)} runs, {g.drop_duplicates(['site_a', 'finding', 'site_b']).shape[0]} scenarios.", "",
              f"| monitor | alarm before change | detected within {T_POST} audits | median audits to alarm after change |",
              "|---|---|---|---|"]
    for m in MONITORS:
        early = (g[m] >= 0) & (g[m] < T_PRE)
        det = g[m] >= T_PRE
        delay = (g.loc[det, m] - T_PRE + 1).median()
        lines.append(f"| {m} | {early.mean():.1%} | {det.mean():.1%} | {delay:.0f} |")
    large = (g.sens_b < S_STAR - LARGE_SENS) | (g.fpr_b > LARGE_FPR * g.f_star)
    lines += ["", f"By size of the drift: large = sensitivity below s* - {LARGE_SENS} or FPR above "
              f"{LARGE_FPR} x f*; small = the rest.", "",
              "| monitor | large: runs | detected | median delay | small: runs | detected | median delay |",
              "|---|---|---|---|---|---|---|"]
    for m in MONITORS:
        cells = []
        for sel in (large, ~large):
            s = g[sel]
            det = s[m] >= T_PRE
            d = (s.loc[det, m] - T_PRE + 1).median()
            cells += [str(len(s)), f"{det.mean():.1%}", "-" if np.isnan(d) else f"{d:.0f}"]
        lines.append(f"| {m} | " + " | ".join(cells) + " |")
    lines += ["", "## Per drift scenario (MONITOR)", "",
              "| A | finding | B | sens at B | FPR at B (f*) | detected | median delay |", "|---|---|---|---|---|---|---|"]
    for (a, f, b), s in g.groupby(["site_a", "finding", "site_b"]):
        det = s.MONITOR >= T_PRE
        d = (s.loc[det, "MONITOR"] - T_PRE + 1).median()
        lines.append(f"| {a} | {f} | {b} | {s.sens_b.mean():.3f} | {s.fpr_b.mean():.3f} ({s.f_star.iloc[0]:.3f}) | "
                     f"{det.mean():.0%} | {'-' if np.isnan(d) else f'{d:.0f}'} |")
    (e3.OUT / f"{tag}_report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    global WINDOW, T_POST
    ap = argparse.ArgumentParser()
    ap.add_argument("--t-post", type=int, default=T_POST)
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--window", type=int, default=WINDOW)
    ap.add_argument("--tag", default="W8")
    ap.add_argument("--summary-only", action="store_true")
    a = ap.parse_args()
    WINDOW = a.window
    T_POST = a.t_post
    out_csv = e3.OUT / f"{a.tag}_runs.csv"
    if not a.summary_only:
        idx = pd.read_csv(e3.INDEX_CSV, low_memory=False).set_index("record_id")
        home = home_operating_points(idx)
        sites = {s: cohort(s, idx) for s in e3.TARGETS + ["code15_half"]}
        rows, t0 = [], time.time()
        for s in e3.TARGETS:
            rows += run_site(s, sites, home, a.reps)
            print(f"{s} done ({time.time() - t0:.0f}s)", flush=True)
        pd.DataFrame(rows).to_csv(out_csv, index=False)
    summarise(pd.read_csv(out_csv), a.tag)


if __name__ == "__main__":
    main()
