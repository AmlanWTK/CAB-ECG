"""Hour-level and patient-level evaluation of an hourly risk score (vectorised).

Patient-level definitions (same window as the Challenge 2019 utility):
  onset t_s   = first labelled hour + 6
  detected    = any alert in [t_s - 12, t_s + 3]
  lead time   = t_s - first alert hour in that window (hours of warning; >0 = before onset).
                It is capped at 12 h by the window, so also report detected_6h_early_pct:
                septic patients alerted at least 6 h before onset.
  alarms/day  = new alarms (0 -> 1 transitions) per 24 patient-hours, over all patients
"""

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

DT_EARLY, DT_OPTIMAL, DT_LATE = -12, -6, 3
U_FP, MAX_U_TP, MIN_U_FN = -0.05, 1.0, -2.0


def challenge_utility(labels, preds):
    """Reference (loop) version of the official Challenge 2019 utility for one patient."""
    labels = np.asarray(labels)
    preds = np.asarray(preds).astype(bool)
    septic = bool(labels.any())
    t_s = int(np.argmax(labels)) - DT_OPTIMAL if septic else np.inf
    m1 = MAX_U_TP / (DT_OPTIMAL - DT_EARLY); b1 = -m1 * DT_EARLY
    m2 = -MAX_U_TP / (DT_LATE - DT_OPTIMAL); b2 = -m2 * DT_LATE
    m3 = MIN_U_FN / (DT_LATE - DT_OPTIMAL); b3 = -m3 * DT_OPTIMAL
    u = np.zeros(len(labels))
    for t in range(len(labels)):
        if t > t_s + DT_LATE:
            continue
        if septic and preds[t]:
            u[t] = max(m1 * (t - t_s) + b1, U_FP) if t <= t_s + DT_OPTIMAL else m2 * (t - t_s) + b2
        elif not septic and preds[t]:
            u[t] = U_FP
        elif septic and not preds[t]:
            u[t] = 0.0 if t <= t_s + DT_OPTIMAL else m3 * (t - t_s) + b3
    return u.sum()


def _patient_frame(meta):
    """Row-aligned arrays: septic flag and onset hour t_s of each row's patient."""
    lab = meta["SepsisLabel"].to_numpy()
    pid = meta["pid"].to_numpy()
    first = meta.loc[lab == 1].groupby("pid")["hour"].min()
    t_s = pd.Series(pid).map(first + 6).to_numpy(dtype=float)  # NaN for non-septic
    return np.isfinite(t_s), t_s


def _row_utility(t, septic, t_s, preds):
    m1 = MAX_U_TP / (DT_OPTIMAL - DT_EARLY); b1 = -m1 * DT_EARLY
    m2 = -MAX_U_TP / (DT_LATE - DT_OPTIMAL); b2 = -m2 * DT_LATE
    m3 = MIN_U_FN / (DT_LATE - DT_OPTIMAL); b3 = -m3 * DT_OPTIMAL
    dt = np.where(septic, t - np.nan_to_num(t_s), 0.0)
    u = np.zeros(len(t))
    in_range = ~septic | (dt <= DT_LATE)
    early = dt <= DT_OPTIMAL
    tp = septic & preds & in_range
    u[tp & early] = np.maximum(m1 * dt[tp & early] + b1, U_FP)
    u[tp & ~early] = m2 * dt[tp & ~early] + b2
    u[~septic & preds] = U_FP
    fn = septic & ~preds & in_range & ~early
    u[fn] = m3 * dt[fn] + b3
    return u


def normalised_utility(meta, alerts):
    t = meta["hour"].to_numpy(dtype=float)
    septic, t_s = _patient_frame(meta)
    alerts = np.asarray(alerts, dtype=bool)
    dt = np.where(septic, t - np.nan_to_num(t_s), 0.0)
    best_pred = septic & (dt >= DT_EARLY) & (dt <= DT_LATE)
    obs = _row_utility(t, septic, t_s, alerts).sum()
    best = _row_utility(t, septic, t_s, best_pred).sum()
    worst = _row_utility(t, septic, t_s, np.zeros(len(t), dtype=bool)).sum()
    return (obs - worst) / (best - worst)


def patient_detection(meta, alerts):
    alerts = np.asarray(alerts, dtype=bool)
    t = meta["hour"].to_numpy(dtype=float)
    pid = meta["pid"].to_numpy()
    septic, t_s = _patient_frame(meta)
    prev = np.r_[False, alerts[:-1]] & np.r_[False, pid[1:] == pid[:-1]]
    rising = alerts & ~prev
    in_win = septic & (t >= t_s + DT_EARLY) & (t <= t_s + DT_LATE)
    hit = in_win & alerts
    d = pd.DataFrame({"pid": pid, "septic": septic, "rising": rising,
                      "hit_hour": np.where(hit, t, np.nan), "t_s": t_s})
    g = d.groupby("pid", sort=False)
    out = pd.DataFrame({
        "hours": g.size(), "alarms": g["rising"].sum(), "septic": g["septic"].first(),
        "first_hit": g["hit_hour"].min(), "t_s": g["t_s"].first(),
    })
    out["detected"] = out["first_hit"].notna()
    out["lead_h"] = out["t_s"] - out["first_hit"]
    return out


def window_max_score(meta, score):
    """For each septic patient, the highest score inside the detection window."""
    t = meta["hour"].to_numpy(dtype=float)
    septic, t_s = _patient_frame(meta)
    in_win = septic & (t >= t_s + DT_EARLY) & (t <= t_s + DT_LATE)
    s = pd.Series(np.where(in_win, np.nan_to_num(score, nan=-np.inf), np.nan))
    return s.groupby(meta["pid"].to_numpy(), sort=False).max().dropna()


def threshold_for_sensitivity(meta, score, target=0.80):
    """Highest threshold that still detects `target` of septic patients (exact, vectorised)."""
    m = window_max_score(meta, score).to_numpy()
    return float(np.quantile(m, 1.0 - target, method="lower"))


def evaluate(meta, score, threshold):
    y = meta["SepsisLabel"].to_numpy()
    score = np.asarray(score, dtype=float)
    ok = ~np.isnan(score)
    alerts = np.nan_to_num(score, nan=-np.inf) >= threshold
    det = patient_detection(meta, alerts)
    sep = det[det.septic]
    return {
        "AUROC_hourly": roc_auc_score(y[ok], score[ok]),
        "AUPRC_hourly": average_precision_score(y[ok], score[ok]),
        "utility": normalised_utility(meta, alerts),
        "sensitivity_patient": sep["detected"].mean(),
        "median_lead_h": sep["lead_h"].median(),
        "detected_6h_early_pct": 100.0 * (sep["lead_h"] >= 6).mean(),
        "alarms_per_patient_day": det["alarms"].sum() / (det["hours"].sum() / 24.0),
        "alert_hours_pct": 100.0 * alerts.mean(),
    }
