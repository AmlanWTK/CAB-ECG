"""Hourly features computed only from data available up to that hour (no look-ahead).

For each vital sign: last value (forward-filled), measured-this-hour flag, hours since last
measurement, 6-hour rolling mean/min/max/std, change over 1 h and 6 h.
For each lab: last value and hours since last measurement.
Plus age, sex, hours since hospital admission, ICU length of stay, shock index.
Unit1/Unit2 (ICU type) are deliberately left out so the model cannot learn site identity.
"""

import numpy as np
import pandas as pd

from .data import CACHE, LABS, VITALS

FEATURE_CACHE = CACHE.parent / "features.pkl"


def build_features(df):
    df = df.sort_values(["pid", "hour"])
    g = df.groupby("pid", sort=False)
    feats = {}
    cols = VITALS + LABS
    ff = g[cols].ffill()
    hour = df["hour"].astype(np.float32)
    for c in cols:
        last_seen = hour.where(df[c].notna())
        last_seen = last_seen.groupby(df["pid"], sort=False).ffill()
        feats[f"{c}_since"] = np.minimum((hour - last_seen).fillna(99), 99).astype(np.float32)
        feats[f"{c}"] = ff[c].astype(np.float32)
    for c in VITALS:
        feats[f"{c}_meas"] = df[c].notna().astype(np.int8)
        series = ff[c]
        roll = series.groupby(df["pid"], sort=False).rolling(6, min_periods=1)
        feats[f"{c}_mean6"] = roll.mean().reset_index(level=0, drop=True).astype(np.float32)
        feats[f"{c}_min6"] = roll.min().reset_index(level=0, drop=True).astype(np.float32)
        feats[f"{c}_max6"] = roll.max().reset_index(level=0, drop=True).astype(np.float32)
        feats[f"{c}_std6"] = roll.std().reset_index(level=0, drop=True).astype(np.float32)
        feats[f"{c}_d1"] = (series - series.groupby(df["pid"], sort=False).shift(1)).astype(np.float32)
        feats[f"{c}_d6"] = (series - series.groupby(df["pid"], sort=False).shift(6)).astype(np.float32)
    feats["age"] = df["Age"].astype(np.float32)
    feats["male"] = df["Gender"].astype(np.float32)
    feats["hosp_adm_time"] = df["HospAdmTime"].astype(np.float32)
    feats["iculos"] = df["ICULOS"].astype(np.float32)
    feats["shock_index"] = (ff["HR"] / ff["SBP"]).replace([np.inf, -np.inf], np.nan).astype(np.float32)
    X = pd.DataFrame(feats, index=df.index)
    meta = df[["pid", "site", "unit", "hour", "SepsisLabel"]]
    return X, meta


def load_features(df, use_cache=True):
    """build_features with an on-disk cache. df must be sorted by pid, hour (as load_all + sort)."""
    meta = df[["pid", "site", "unit", "hour", "SepsisLabel"]]
    if use_cache and FEATURE_CACHE.exists():
        X = pd.read_pickle(FEATURE_CACHE)
        if len(X) == len(df) and X.index.equals(df.index):
            return X, meta
    X, meta = build_features(df)
    X.to_pickle(FEATURE_CACHE)
    return X, meta
