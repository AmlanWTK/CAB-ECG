"""Calibrate / Adapt / Block: fast per-patient tools and the certified selection rule.

Safety criteria for a deployed sepsis alert at the target hospital (both patient-level):
  sensitivity  share of septic patients alerted in [onset - 12 h, onset + 3 h]   must be >= s_star
  false-alert  share of non-septic patients alerted at least once during the stay must be <= f_star

Selection (cheapest first, stop at the first remedy that passes):
  KEEP       the imported model with its home threshold                 (tested on all n labels)
  CALIBRATE  the imported model with a new local threshold              (chosen and tested on all n)
  ADAPT      the imported model boosted further on local data (fit half), threshold chosen and
             tested on the other half
  BLOCK      nothing passed

Each remedy is tested at level alpha/3, split equally between its two criteria. Thresholds are
picked by fixed-sequence testing over the ordered thresholds (Learn-then-Test, Angelopoulos et al.),
using exact binomial (Clopper-Pearson) tests. By the union bound, the probability of switching on
a remedy that fails either criterion at the target is at most alpha.
"""

import numpy as np
import pandas as pd
from scipy.stats import binom

from .metrics import DT_EARLY, DT_LATE, _patient_frame, _row_utility

REMEDIES = ["KEEP", "CALIBRATE", "ADAPT"]


class SiteFrame:
    """Row and patient arrays for one hospital's rows (meta sorted by pid, hour)."""

    def __init__(self, meta):
        meta = meta.reset_index(drop=True)
        self.meta = meta
        codes, self.pids = pd.factorize(meta["pid"], sort=False)
        self.row_patient = codes
        self.offsets = np.flatnonzero(np.r_[True, codes[1:] != codes[:-1]])
        self.n_patients = len(self.offsets)
        t = meta["hour"].to_numpy(dtype=float)
        septic_row, t_s = _patient_frame(meta)
        self.in_win = septic_row & (t >= t_s + DT_EARLY) & (t <= t_s + DT_LATE)
        self.septic = septic_row[self.offsets]
        self.hours = np.diff(np.r_[self.offsets, len(meta)])
        self.u1 = _row_utility(t, septic_row, t_s, np.ones(len(t), bool))
        self.u0 = _row_utility(t, septic_row, t_s, np.zeros(len(t), bool))
        self.ubest = _row_utility(t, septic_row, t_s, self.in_win)
        self.first_row = np.r_[True, codes[1:] != codes[:-1]]

    def patient_max(self, score):
        """(window max for septic patients / -inf otherwise, whole-stay max) per patient."""
        s = np.nan_to_num(np.asarray(score, dtype=np.float64), nan=-np.inf)
        wmax = np.maximum.reduceat(np.where(self.in_win, s, -np.inf), self.offsets)
        smax = np.maximum.reduceat(s, self.offsets)
        return wmax, smax

    def rows_of(self, patient_mask):
        return patient_mask[self.row_patient]

    def utility(self, score, tau, patient_mask):
        r = self.rows_of(patient_mask)
        a = np.nan_to_num(score, nan=-np.inf)[r] >= tau
        obs = np.where(a, self.u1[r], self.u0[r]).sum()
        best, worst = self.ubest[r].sum(), self.u0[r].sum()
        return (obs - worst) / (best - worst)

    def alarms_per_day(self, score, tau, patient_mask):
        r = self.rows_of(patient_mask)
        a = np.nan_to_num(score, nan=-np.inf) >= tau
        prev = np.r_[False, a[:-1]] & ~self.first_row
        rising = a & ~prev
        return rising[r].sum() / (r.sum() / 24.0)


def rates(wmax, smax, septic, mask, tau):
    """Patient-level sensitivity and false-alert rate of threshold tau on patients in mask."""
    sep, non = mask & septic, mask & ~septic
    sens = (wmax[sep] >= tau).mean() if sep.any() else np.nan
    fa = (smax[non] >= tau).mean() if non.any() else np.nan
    return sens, fa


def largest_threshold_for(wmax_sep, s_star):
    """Largest threshold whose observed sensitivity is >= s_star (point estimate, no guarantee)."""
    m = np.sort(np.asarray(wmax_sep))[::-1]
    k = len(m)
    if k == 0:
        return np.nan
    d = int(np.ceil(s_star * k - 1e-9))
    return float(m[max(d, 1) - 1])


def certified_threshold(wmax_sep, s_star, delta):
    """Largest threshold with an exact one-sided test of sens >= s_star passing at level delta.

    Thresholds are tested from the most sensitive end; because detections can only fall as the
    threshold rises, the passing thresholds form a prefix and the last one is returned (None if
    even detecting every septic patient would not pass)."""
    m = np.sort(np.asarray(wmax_sep))[::-1]
    k = len(m)
    if k == 0:
        return None
    d = np.arange(1, k + 1)
    ok = binom.sf(d - 1, k, s_star) <= delta
    if not ok.any():
        return None
    d_min = int(d[ok][0])
    return float(m[d_min - 1])


def sens_test(wmax_sep, tau, s_star, delta):
    k = len(wmax_sep)
    if k == 0:
        return False
    d = int((np.asarray(wmax_sep) >= tau).sum())
    return bool(binom.sf(d - 1, k, s_star) <= delta)


def fa_test(smax_non, tau, f_star, delta):
    k = len(smax_non)
    if k == 0:
        return False
    f = int((np.asarray(smax_non) >= tau).sum())
    return bool(binom.cdf(f, k, f_star) <= delta)


def cab_select(lab_all, lab_cert, src, ada, tau_home, s_star, f_star, alpha):
    """Run the certified selection.

    lab_all / lab_cert: boolean patient masks (all labelled; certification half).
    src / ada: dicts with 'wmax', 'smax', 'septic' arrays for the imported and adapted models.
    Returns (remedy, threshold)."""
    d = alpha / len(REMEDIES) / 2
    sep, non = lab_all & src["septic"], lab_all & ~src["septic"]
    if sens_test(src["wmax"][sep], tau_home, s_star, d) and fa_test(src["smax"][non], tau_home, f_star, d):
        return "KEEP", tau_home
    tau = certified_threshold(src["wmax"][sep], s_star, d)
    if tau is not None and fa_test(src["smax"][non], tau, f_star, d):
        return "CALIBRATE", tau
    if ada is not None:
        sep, non = lab_cert & ada["septic"], lab_cert & ~ada["septic"]
        tau = certified_threshold(ada["wmax"][sep], s_star, d)
        if tau is not None and fa_test(ada["smax"][non], tau, f_star, d):
            return "ADAPT", tau
    return "BLOCK", np.nan


def feasible(wmax, smax, septic, mask, s_star, f_star, tau=None):
    """Large-sample check on patients in mask. tau=None: best threshold reaching s_star."""
    if tau is None:
        tau = largest_threshold_for(wmax[mask & septic], s_star)
    sens, fa = rates(wmax, smax, septic, mask, tau)
    return bool(sens >= s_star and fa <= f_star), tau, sens, fa
