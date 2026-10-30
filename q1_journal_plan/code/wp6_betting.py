"""WP6: exact, anytime-valid certification of sensitivity and FPR from score-weighted labels.

Records are drawn with replacement from the cohort with known probabilities q (set from the
imported scores before any label is seen). For threshold tau,

    sensitivity >= s*  <=>  mean_i y_i (1[s_i >= tau] - s*)      >= 0
    FPR <= f*          <=>  mean_i (1 - y_i) (f* - 1[s_i >= tau]) >= 0

and z / (N q) is an unbiased draw of each cohort mean. A betting capital process on these draws
is a nonnegative supermartingale when the mean is <= 0, so crossing 1/delta certifies the
criterion with error at most delta at any stopping time (Ville's inequality). See
notes/wp6_design.md.
"""

import numpy as np


def design_q(score, eps, power=1.0):
    """Sampling probabilities: a floor eps spread uniformly, the rest proportional to score**power."""
    n = len(score)
    g = np.clip(score, 1e-12, None) ** power
    return eps / n + (1 - eps) * g / g.sum()


def certify_times(x, lower, delta, c=0.5, prior_n=1.0):
    """For draws x (reps x T) with known lower bound `lower` < 0, the first draw (1-based) at which
    the capital for H0: mean <= 0 reaches 1/delta, or 0 if it never does.

    Bets are aGRAPA, lambda_t = mu_hat / (var_hat + mu_hat^2) from draws before t, clipped to
    [0, c / |lower|] so every factor 1 + lambda x is at least 1 - c. Estimates start from a
    pseudo-draw at 0 with weight prior_n.
    """
    reps, T = x.shape
    cs = np.cumsum(x, axis=1)
    cs2 = np.cumsum(x * x, axis=1)
    k = np.arange(1, T + 1)
    s_prev = np.concatenate([np.zeros((reps, 1)), cs[:, :-1]], axis=1)
    s2_prev = np.concatenate([np.zeros((reps, 1)), cs2[:, :-1]], axis=1)
    n_prev = (k - 1) + prior_n
    mu = s_prev / n_prev
    var = np.maximum(s2_prev / n_prev - mu * mu, 1e-12)
    lam = np.clip(mu / (var + mu * mu), 0.0, c / abs(lower))
    logk = np.cumsum(np.log1p(lam * x), axis=1)
    hit = logk >= np.log(1 / delta)
    first = np.where(hit.any(axis=1), hit.argmax(axis=1) + 1, 0)
    return first


def draws(rng, q, reps, T):
    """Record indices drawn with replacement, reps x T."""
    return rng.choice(len(q), size=(reps, T), replace=True, p=q)


def unique_until(idx, t):
    """Number of distinct records among the first t draws of each row (t = 0: none)."""
    return np.array([len(np.unique(row[:k])) if k else 0 for row, k in zip(idx, t)])


def sens_increments(idx, y, above, q, s_star):
    n = len(y)
    z = y * (above.astype(float) - s_star)
    return z[idx] / (n * q[idx]), -s_star / (n * q.min())


def fpr_increments(idx, y, above, q, f_star):
    n = len(y)
    w = (1 - y) * (f_star - above.astype(float))
    return w[idx] / (n * q[idx]), -(1 - f_star) / (n * q.min())


# --- Without replacement, stratified (labels are never repeated) -------------------------------
#
# The cohort is split into strata fixed from the scores before any label is seen. Each stratum is
# labelled in a uniformly random order without replacement, and draws go to the strata on a
# schedule that is also fixed in advance. For a stratum of N_h records with values in [a, b], the
# capital for H0: stratum mean <= m bets on x_t - m_t, where m_t = (N_h m - S_{t-1}) / (N_h - t + 1)
# is the largest mean the unlabelled rest can have under H0; it is a nonnegative supermartingale
# under H0 (Waudby-Smith and Ramdas, without-replacement betting [to verify]). A stratum's
# anytime-valid lower bound L_h is the largest grid value m such that every grid value up to m has
# been rejected at level delta_h. The criterion is certified once sum_h N_h L_h >= 0; with
# sum_h delta_h = delta, the error is at most delta by the union bound.


def mean_grid(a, b, k=150, tiny=1e-7):
    """Grid over [a, b] that is dense near 0, where stratum means of rare findings sit."""
    neg = -np.geomspace(tiny, -a, k)[::-1] if a < 0 else np.array([])
    pos = np.geomspace(tiny, b, k) if b > 0 else np.array([])
    return np.concatenate([[a], neg, [0.0], pos, [b]])


def wor_lcb_paths(x, n_total, a, b, delta, c=0.5, prior_n=1.0):
    """x: reps x n draws (values in [a, b]) in their drawn order from a stratum of n_total records.
    Returns reps x n lower bounds on the stratum mean after 1..n draws (exact once n = n_total)."""
    reps, n = x.shape
    t = np.arange(1, n + 1)
    s_prev = np.concatenate([np.zeros((reps, 1)), np.cumsum(x, axis=1)[:, :-1]], axis=1)
    s2_prev = np.concatenate([np.zeros((reps, 1)), np.cumsum(x * x, axis=1)[:, :-1]], axis=1)
    mu = s_prev / ((t - 1) + prior_n)
    var = np.maximum(s2_prev / ((t - 1) + prior_n) - mu * mu, 1e-12)
    remaining = n_total - t + 1
    lcb = np.full((reps, n), a, dtype=float)
    all_rej = np.ones((reps, n), bool)
    for m in mean_grid(a, b):
        m_t = (n_total * m - s_prev) / remaining
        impossible = m_t < a                      # data already exceed what H0 allows
        gap = np.maximum(m_t - a, 1e-12)
        d = mu - m_t
        lam = np.clip(d / (var + d * d), 0.0, c / gap)
        logk = np.cumsum(np.log1p(np.where(impossible, 0.0, lam * (x - m_t))), axis=1)
        rej = (np.maximum.accumulate(logk, axis=1) >= np.log(1 / delta)) | np.maximum.accumulate(impossible, axis=1)
        all_rej &= rej
        lcb = np.where(all_rej, m, lcb)
    if n == n_total:                               # fully labelled: the mean is known exactly
        lcb[:, -1] = x.sum(axis=1) / n_total
    return lcb


def schedule(sizes, props, T):
    """Stratum of each of the first T draws: largest shortfall against props, skipping strata that
    are used up. Depends only on stratum sizes and props, never on labels."""
    sizes, props = np.asarray(sizes), np.asarray(props, float)
    taken = np.zeros(len(sizes), int)
    out = np.empty(min(T, sizes.sum()), int)
    for i in range(len(out)):
        open_ = taken < sizes
        short = np.where(open_, props * (i + 1) - taken, -np.inf)
        h = int(np.argmax(short))
        out[i] = h
        taken[h] += 1
    return out


def stratified_certify(rng, values, strata, props, a, b, delta, reps, T):
    """values: per-record quantity whose cohort mean must be shown >= 0; strata: stratum id per
    record. Returns, per repeat, the number of labels at which sum_h N_h L_h first reaches 0
    (0 if never within T labels)."""
    ids = np.unique(strata)                       # props[h] belongs to stratum id h; empty strata drop out
    sizes = np.array([(strata == h).sum() for h in ids])
    props = np.asarray(props, float)[ids]
    sched = schedule(sizes, props / props.sum(), T)
    T = len(sched)
    count = np.zeros((len(ids), T), int)          # labels taken from each stratum after t draws
    for j in range(len(ids)):
        count[j] = np.cumsum(sched == j)
    total = np.zeros((reps, T))
    for j, h in enumerate(ids):
        members = np.flatnonzero(strata == h)
        n_h = int(count[j, -1])
        if n_h == 0:
            total += sizes[j] * a
            continue
        order = np.array([rng.permutation(members)[:n_h] for _ in range(reps)])
        lcb = wor_lcb_paths(values[order], sizes[j], a, b, delta / len(ids))
        k = count[j]                               # draws from this stratum after each total draw
        path = np.where(k > 0, lcb[:, np.maximum(k - 1, 0)], a)
        total += sizes[j] * path
    hit = total >= 0
    return np.where(hit.any(axis=1), hit.argmax(axis=1) + 1, 0)
