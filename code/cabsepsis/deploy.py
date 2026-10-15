"""Deployment layer for the monitoring application.

Wraps the CAB procedure (cabsepsis/cab.py, sepsis_e3_cab.py) so an application can:
  1. read the vendor package that ships with an imported model (home threshold, home rates),
  2. run the certified gate on a hospital's labelled patients and explain every step,
  3. return the configuration to deploy (model scores + threshold), or BLOCK.

The decision rule is exactly cab_select(); gate_explained() also reports the exact
Clopper-Pearson bounds behind each pass/fail. A test (tests/test_deploy.py) checks that both
functions always agree.
"""

import numpy as np
from scipy.stats import beta

from .cab import SiteFrame, certified_threshold, largest_threshold_for, rates

VENDOR_DELTA = 0.05


def cp_lower(x, k, delta):
    """One-sided lower confidence bound (level 1 - delta) for a binomial proportion x/k."""
    return 0.0 if x == 0 else float(beta.ppf(delta, x, k - x + 1))


def cp_upper(x, k, delta):
    """One-sided upper confidence bound (level 1 - delta) for a binomial proportion x/k."""
    return 1.0 if x == k else float(beta.ppf(1 - delta, x + 1, k - x))


def model_dict(sf, score):
    w, s = sf.patient_max(score)
    return {"wmax": w, "smax": s, "septic": sf.septic, "score": score}


def vendor_package(sf_home_val, p_home_val, s_star, margin):
    """What ships with the model: a threshold certified at home (95% lower bound for sensitivity
    >= s_star on home validation patients), the home false-alert rate there, and the false-alert
    limit the importing hospital asks for (home rate + margin)."""
    w, s = sf_home_val.patient_max(p_home_val)
    tau = certified_threshold(w[sf_home_val.septic], s_star, VENDOR_DELTA)
    if tau is None:
        tau = largest_threshold_for(w[sf_home_val.septic], s_star)
    sens, fa = rates(w, s, sf_home_val.septic, np.ones(sf_home_val.n_patients, bool), tau)
    return {"tau": tau, "home_sens": sens, "home_fa": fa, "f_star": fa + margin,
            "home_patients": int(sf_home_val.n_patients), "home_septic": int(sf_home_val.septic.sum())}


def _check(model, mask, tau, s_star, f_star, delta):
    sep = model["wmax"][mask & model["septic"]]
    non = model["smax"][mask & ~model["septic"]]
    d, k = int((sep >= tau).sum()), len(sep)
    f, k0 = int((non >= tau).sum()), len(non)
    lo, up = cp_lower(d, k, delta), cp_upper(f, k0, delta)
    return {"threshold": tau, "septic_n": k, "detected": d, "sens_observed": d / k if k else np.nan,
            "sens_lower_bound": lo, "nonseptic_n": k0, "alerted": f,
            "fa_observed": f / k0 if k0 else np.nan, "fa_upper_bound": up,
            "sens_ok": bool(k > 0 and lo >= s_star), "fa_ok": bool(k0 > 0 and up <= f_star)}


def gate_explained(lab_all, lab_cert, src, get_ada, tau_home, s_star, f_star, alpha=0.05):
    """Same decisions as cab_select(), with the evidence for each step.

    get_ada: callable returning the adapted model dict (only called if stage 1 fails, because
    fitting it takes time). Returns (remedy, threshold, steps, ada_or_None)."""
    d = alpha / 4
    steps = []
    sep = src["wmax"][lab_all & src["septic"]]
    tau_cal = certified_threshold(sep, s_star, d)
    keep = _check(src, lab_all, tau_home, s_star, f_star, d)
    keep.update(step="Keep as is", data="all labelled patients", passed=keep["sens_ok"] and keep["fa_ok"])
    steps.append(keep)
    if tau_cal is not None:
        cal = _check(src, lab_all, tau_cal, s_star, f_star, d)
        cal.update(step="Calibrate (new threshold)", data="all labelled patients", passed=cal["fa_ok"])
    else:
        cal = {"step": "Calibrate (new threshold)", "data": "all labelled patients", "passed": False,
               "note": "too few septic patients to prove the sensitivity target at any threshold"}
    steps.append(cal)
    if keep["passed"]:
        return "KEEP", tau_home, steps, None
    if cal["passed"]:
        return "CALIBRATE", tau_cal, steps, None
    ada = get_ada() if get_ada is not None else None
    if ada is not None:
        sep = ada["wmax"][lab_cert & ada["septic"]]
        tau_ad = certified_threshold(sep, s_star, d)
        if tau_ad is not None:
            ad = _check(ada, lab_cert, tau_ad, s_star, f_star, d)
            ad.update(step="Adapt (model updated on local data)", data="certification half", passed=ad["fa_ok"])
        else:
            ad = {"step": "Adapt (model updated on local data)", "data": "certification half", "passed": False,
                  "note": "too few septic patients to prove the sensitivity target at any threshold"}
        steps.append(ad)
        if ad["passed"]:
            return "ADAPT", tau_ad, steps, ada
    return "BLOCK", np.nan, steps, ada


def draw_labels(sf, pool, n, seed, septic_share=None, septic_cap=0.5):
    """Labelled sample (random, or enriched with septic patients) and its 50/50 split into a fit
    half and a certification half, stratified by sepsis -- as in sepsis_e3_cab.one_run."""
    rng = np.random.default_rng(seed)
    if septic_share is None:
        lab_idx = rng.choice(pool, size=n, replace=False)
    else:
        sep_pool, non_pool = pool[sf.septic[pool]], pool[~sf.septic[pool]]
        n_sep = min(int(round(septic_share * n)), int(septic_cap * len(sep_pool)))
        lab_idx = np.concatenate([rng.choice(sep_pool, size=n_sep, replace=False),
                                  rng.choice(non_pool, size=n - n_sep, replace=False)])
    lab = np.zeros(sf.n_patients, bool); lab[lab_idx] = True
    cert = np.zeros_like(lab)
    for grp in (lab_idx[sf.septic[lab_idx]], lab_idx[~sf.septic[lab_idx]]):
        g = rng.permutation(grp)
        cert[g[: len(g) // 2]] = True
    return lab, cert, lab & ~cert


__all__ = ["SiteFrame", "vendor_package", "gate_explained", "draw_labels", "model_dict",
           "cp_lower", "cp_upper"]
