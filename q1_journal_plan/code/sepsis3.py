"""Sepsis-3 onset from hourly ICU data, shared by the MIMIC-IV and eICU extractors.

Follows the rules used to label the PhysioNet/CinC 2019 Challenge (Reyna et al., Crit Care Med
2020;48:210-217, Methods), so labels from the new databases mean the same thing as the chapter's:

- Suspected infection: a blood culture and an IV antibiotic given for at least 72 consecutive
  hours (the extractors keep only such courses). If the culture came first, the antibiotic must be
  ordered within 72 h; if the antibiotic came first, the culture must be drawn within 24 h. Its
  time is the earlier of the two; the first such pair in the stay is used.
- Organ dysfunction: a rise in SOFA of 2 or more within a 24-hour period, i.e. above the lowest
  SOFA in the previous 24 h. SOFA is computed hourly as the worst score of each component over the
  previous 24 h.
- Onset: the earlier of the suspicion time and the first hour of the SOFA rise, provided the rise
  falls no more than 24 h before or 12 h after suspicion.
- SepsisLabel: 1 from 6 h before onset onward, as in the Challenge.
- Cohort: stays with at least 8 hours of data; stays with onset less than 4 h after ICU admission
  excluded; stays truncated at 2 weeks (`challenge_cohort`).

Two definitions of suspected infection (decided 2026-10-30, notes/sepsis_labels.md); everything
else above is shared:
- "relaxed" (primary, both databases): any non-screening culture and any systemic antibiotic order,
  with no minimum duration, because eICU hospitals record cultures and antibiotics unevenly;
- "challenge" (sensitivity analysis): blood cultures and IV antibiotic courses of at least 72 h,
  exactly as in the Challenge.

All times are hours from ICU admission (floats; may be negative for events before admission).
The extractors supply long tables with columns: stay, t (hours) and, for measurements, value.
"""

import numpy as np
import pandas as pd

ABX_AFTER_CULTURE = 72       # culture first: antibiotic within 72 h
CULTURE_AFTER_ABX = 24       # antibiotic first: culture within 24 h
SOFA_BEFORE, SOFA_AFTER = 24, 12
SOFA_RISE_WINDOW = 24
LABEL_LEAD = 6
MIN_HOURS, MIN_ONSET_HOUR, MAX_HOURS = 8, 4, 14 * 24


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
    h["base"] = (h.groupby("stay", sort=False)["sofa"].rolling(SOFA_RISE_WINDOW + 1, min_periods=1).min()
                 .reset_index(level=0, drop=True).reindex(h.index))  # lowest SOFA in the previous 24 h
    h["t_susp"] = h["stay"].map(t_susp)
    rise = h[(h.sofa - h.base >= 2) & (h.hour >= h.t_susp - SOFA_BEFORE) & (h.hour <= h.t_susp + SOFA_AFTER)]
    t_sofa = rise.groupby("stay")["hour"].min()
    onset = np.fmin(t_susp.reindex(t_sofa.index), t_sofa)
    return onset.reindex(h["stay"].unique()).rename("onset")


def sepsis_label(h, onset):
    """1 from LABEL_LEAD hours before onset onward."""
    return (h["hour"] >= h["stay"].map(onset) - LABEL_LEAD).astype(np.int8)


def challenge_cohort(h, onset):
    """Apply the Challenge's cohort rules to the hourly table h (stay, hour, ...): drop stays with
    fewer than MIN_HOURS hours or onset before MIN_ONSET_HOUR, and truncate at MAX_HOURS.
    Returns (hourly table, set of excluded stays with the reason)."""
    n_hours = h.groupby("stay").hour.max() + 1
    short = set(n_hours[n_hours < MIN_HOURS].index)
    early = set(onset[onset < MIN_ONSET_HOUR].index)
    keep = ~h.stay.isin(short | early) & (h.hour < MAX_HOURS)
    reasons = {**{s: "under 8 h" for s in short}, **{s: "onset under 4 h" for s in early - short}}
    return h[keep], reasons


FEATURES = ["pf", "ventilated", "platelets", "bilirubin", "map", "dopa", "dobu", "epi", "norepi",
            "gcs", "creatinine", "urine_24h"]


def score_and_label(h, t_susp):
    """h: one row per stay-hour (sorted by stay, hour) with FEATURES (worst value in the hour;
    NaN = not measured). Adds the component scores, sofa and SepsisLabel; returns (h, onset)."""
    h = h.copy()
    h["sofa_resp"] = score_resp(h.pf.to_numpy(), h.ventilated.to_numpy())
    h["sofa_coag"] = score_coag(h.platelets.to_numpy())
    h["sofa_liver"] = score_liver(h.bilirubin.to_numpy())
    h["sofa_cardio"] = score_cardio(h["map"].to_numpy(), h.dopa.to_numpy(), h.dobu.to_numpy(),
                                    h.epi.to_numpy(), h.norepi.to_numpy())
    h["sofa_cns"] = score_cns(h.gcs.to_numpy())
    h["sofa_renal"] = score_renal(h.creatinine.to_numpy(), h.urine_24h.to_numpy())
    h["sofa"] = hourly_sofa(h)
    onset = onset_times(h, t_susp)
    h["SepsisLabel"] = sepsis_label(h, onset)
    return h, onset


def courses(df, key, start, stop, gap, min_len):
    """Treatment courses from intervals (numeric hours): intervals overlapping or less than `gap`
    apart are joined; returns (key, start) of courses lasting at least `min_len`."""
    df = df.dropna(subset=[start, stop]).sort_values([key, start])
    out = []
    for k, g in df.groupby(key):
        cs = ce = None
        for st, sp in zip(g[start], g[stop]):
            if cs is not None and st - ce <= gap:
                ce = max(ce, sp)
                continue
            if cs is not None and ce - cs >= min_len:
                out.append((k, cs))
            cs, ce = st, sp
        if cs is not None and ce - cs >= min_len:
            out.append((k, cs))
    return pd.DataFrame(out, columns=[key, "t"])


def summary(st, hc):
    """Print the label summary used for both databases (st: stays with t_suspicion, onset,
    excluded, septic; hc: hourly table of the Challenge cohort)."""
    n = len(st)
    inc = st[st.excluded.isna()]
    print(f"suspected infection: {st.t_suspicion.notna().sum()} of {n} stays ({st.t_suspicion.notna().mean():.0%})")
    print(f"Sepsis-3 before cohort rules: {st.onset.notna().sum()} of {n}; onset hour median {st.onset.median():.1f}")
    print("excluded:", st.excluded.value_counts().to_dict())
    print(f"Challenge cohort: {len(inc)} stays, septic {inc.septic.sum()} ({inc.septic.mean():.1%}); onset hour "
          f"median {inc.onset.median():.1f} (IQR {inc.onset.quantile(.25):.1f} to {inc.onset.quantile(.75):.1f})")
    cover = hc[COMPONENTS].notna().mean()
    print("hours with each SOFA component measured:", ", ".join(f"{c[5:]} {v:.0%}" for c, v in cover.items()))
    print(f"hourly rows {len(hc)}, SepsisLabel = 1 in {hc.SepsisLabel.mean():.1%}")
