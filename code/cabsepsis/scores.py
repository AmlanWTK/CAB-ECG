"""Bedside early-warning scores computed hourly from forward-filled values.

All four are MODIFIED versions because the Challenge 2019 data has no consciousness level,
no supplemental-oxygen flag (FiO2 > 0.21 is used as a proxy where recorded), no band forms
and no urine output. Report them as "modified qSOFA / SIRS / NEWS2 / MEWS".
"""

import numpy as np
import pandas as pd


def _bands(x, edges, points):
    """Assign points by value bands: edges are ascending upper limits, points has len(edges)+1."""
    out = np.select([x <= e for e in edges], points[:-1], default=points[-1]).astype(np.float32)
    return np.where(np.isnan(x), 0, out)


def compute_scores(ff):
    """ff: forward-filled hourly values with columns HR, O2Sat, Temp, SBP, Resp, PaCO2, WBC, FiO2."""
    hr, spo2, temp, sbp, rr = (ff[c].to_numpy(np.float64) for c in ["HR", "O2Sat", "Temp", "SBP", "Resp"])
    paco2, wbc, fio2 = (ff[c].to_numpy(np.float64) for c in ["PaCO2", "WBC", "FiO2"])

    qsofa = np.where(np.isnan(rr), 0, rr >= 22).astype(float) + np.where(np.isnan(sbp), 0, sbp <= 100).astype(float)

    sirs = (np.where(np.isnan(temp), 0, (temp > 38) | (temp < 36)).astype(float)
            + np.where(np.isnan(hr), 0, hr > 90).astype(float)
            + np.where(np.isnan(rr) & np.isnan(paco2), 0, (np.nan_to_num(rr) > 20) | (np.nan_to_num(paco2, nan=99) < 32)).astype(float)
            + np.where(np.isnan(wbc), 0, (wbc > 12) | (wbc < 4)).astype(float))

    news2 = (_bands(rr, [8, 11, 20, 24], [3, 1, 0, 2, 3])
             + _bands(spo2, [91, 93, 95], [3, 2, 1, 0])
             + np.where(np.nan_to_num(fio2) > 0.21, 2, 0)
             + _bands(temp, [35.0, 36.0, 38.0, 39.0], [3, 1, 0, 1, 2])
             + _bands(sbp, [90, 100, 110, 219], [3, 2, 1, 0, 3])
             + _bands(hr, [40, 50, 90, 110, 130], [3, 1, 0, 1, 2, 3]))

    mews = (_bands(sbp, [70, 80, 100, 199], [3, 2, 1, 0, 2])
            + _bands(hr, [40, 50, 100, 110, 129], [2, 1, 0, 1, 2, 3])
            + _bands(rr, [8, 14, 20, 29], [2, 0, 1, 2, 3])
            + _bands(temp, [35.0, 38.4], [2, 0, 2]))

    return pd.DataFrame({"qSOFA_mod": qsofa, "SIRS_mod": sirs, "NEWS2_mod": news2, "MEWS_mod": mews},
                        index=ff.index).astype(np.float32)


# Conventional alert cut-offs for each score.
STANDARD_CUTOFFS = {"qSOFA_mod": 2, "SIRS_mod": 2, "NEWS2_mod": 5, "MEWS_mod": 4}
