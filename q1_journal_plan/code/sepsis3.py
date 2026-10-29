"""Sepsis-3 onset from hourly ICU data, shared by the MIMIC-IV and eICU extractors.

Follows the rules used to label the PhysioNet/CinC 2019 Challenge (Reyna et al. 2020), so labels
from the new databases mean the same thing as the chapter's:

- Suspected infection: a body-fluid culture and an antibiotic, the antibiotic within 24 h after
  the culture or the culture within 72 h after the antibiotic. Its time is the earlier of the two.
  The first such pair in the stay is used.
- Organ dysfunction: SOFA rises by 2 or more within 48 h before to 24 h after suspicion. SOFA is
  computed hourly as the worst score of each component over the previous 24 h; the rise is
  measured against the lowest SOFA earlier in the stay.
- Onset: the earlier of the suspicion time and the first hour of the SOFA rise.
- SepsisLabel: 1 from 6 h before onset onward, as in the Challenge.

All times are hours from ICU admission (floats; may be negative for events before admission).
The extractors supply long tables with columns: stay, t (hours) and, for measurements, value.
"""

import numpy as np
import pandas as pd

ABX_AFTER_CULTURE = 24
CULTURE_AFTER_ABX = 72
SOFA_BEFORE, SOFA_AFTER = 48, 24
LABEL_LEAD = 6


def suspicion_times(cultures, antibiotics):
    """First time of suspected infection per stay (Series indexed by stay)."""
    m = cultures[["stay", "t"]].merge(antibiotics[["stay", "t"]], on="stay", suffixes=("_c", "_a"))
    d = m.t_a - m.t_c
    ok = ((d >= 0) & (d <= ABX_AFTER_CULTURE)) | ((d < 0) & (-d <= CULTURE_AFTER_ABX))
    m = m[ok]
    return np.minimum(m.t_c, m.t_a).groupby(m.stay).min().rename("t_suspicion")


# ---- SOFA component scores (Vincent et al. 1996) ----

def score_resp(pf, ventilated):
    s = np.select([pf < 100, pf < 200, pf < 300, pf < 400], [4, 3, 2, 1], 0).astype(float)
    s = np.where((pf < 200) & ~ventilated, 2, s)      # 3 and 4 need respiratory support
    return np.where(np.isnan(pf), np.nan, s)


def score_coag(platelets):
    s = np.select([platelets < 20, platelets < 50, platelets < 100, platelets < 150], [4, 3, 2, 1], 0)
    return np.where(np.isnan(platelets), np.nan, s)


def score_liver(bilirubin):
    s = np.select([bilirubin >= 12, bilirubin >= 6, bilirubin >= 2, bilirubin >= 1.2], [4, 3, 2, 1], 0)
    return np.where(np.isnan(bilirubin), np.nan, s)


def score_cardio(map_, dopa, dobu, epi, norepi):
    """Vasopressor rates in mcg/kg/min (NaN or 0 when not given)."""
    dopa, dobu, epi, norepi = (np.nan_to_num(x) for x in (dopa, dobu, epi, norepi))
    s = np.select([(dopa > 15) | (epi > 0.1) | (norepi > 0.1),
                   (dopa > 5) | (epi > 0) | (norepi > 0),
                   (dopa > 0) | (dobu > 0),
                   map_ < 70], [4, 3, 2, 1], 0).astype(float)
    no_info = np.isnan(map_) & (s == 0)
    return np.where(no_info, np.nan, s)


def score_cns(gcs):
    s = np.select([gcs < 6, gcs < 10, gcs < 13, gcs < 15], [4, 3, 2, 1], 0)
    return np.where(np.isnan(gcs), np.nan, s)


def score_renal(creatinine, urine_24h):
    sc = np.select([creatinine >= 5, creatinine >= 3.5, creatinine >= 2, creatinine >= 1.2], [4, 3, 2, 1], 0)
    sc = np.where(np.isnan(creatinine), np.nan, sc)
    su = np.select([urine_24h < 200, urine_24h < 500], [4, 3], 0)
    su = np.where(np.isnan(urine_24h), np.nan, su)
    return np.fmax(sc, su)


COMPONENTS = ["sofa_resp", "sofa_coag", "sofa_liver", "sofa_cardio", "sofa_cns", "sofa_renal"]


def hourly_sofa(h):
    """h: one row per stay-hour (sorted by stay, hour) with hourly component scores (NaN = not
    measured). Returns total SOFA per row: worst of each component over the last 24 h, missing
    components counted as 0 (normal), as is usual for SOFA in retrospective data."""
    worst = (h.groupby("stay", sort=False)[COMPONENTS]
             .rolling(24, min_periods=1).max().reset_index(level=0, drop=True))
    return worst.fillna(0).sum(axis=1).reindex(h.index)


def onset_times(h, t_susp):
    """h: stay, hour, sofa. Onset per stay (Series), NaN when not septic."""
    h = h[["stay", "hour", "sofa"]].copy()
    h["base"] = h.groupby("stay", sort=False)["sofa"].cummin()
    h["t_susp"] = h["stay"].map(t_susp)
    rise = h[(h.sofa - h.base >= 2) & (h.hour >= h.t_susp - SOFA_BEFORE) & (h.hour <= h.t_susp + SOFA_AFTER)]
    t_sofa = rise.groupby("stay")["hour"].min()
    onset = np.fmin(t_susp.reindex(t_sofa.index), t_sofa)
    return onset.reindex(h["stay"].unique()).rename("onset")


def sepsis_label(h, onset):
    """1 from LABEL_LEAD hours before onset onward."""
    return (h["hour"] >= h["stay"].map(onset) - LABEL_LEAD).astype(np.int8)
