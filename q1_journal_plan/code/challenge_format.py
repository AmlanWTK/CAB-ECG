"""Hourly tables in the PhysioNet/CinC 2019 Challenge format, from MIMIC-IV or eICU (WP2).

The output has the columns of the chapter's loader (code/cabsepsis/data.py): pid, site, hour, unit,
the 40 Challenge variables and SepsisLabel, so the chapter's features, models and gate run on it
unchanged. One row per stay-hour of the Challenge cohort (sepsis3.challenge_cohort).

Values: the mean of the measurements in the hour, in the Challenge's units (temperature in degrees
C, FiO2 as a fraction, labs in US units). Demographics as in the Challenge: Gender 1 = male;
Unit1 = medical ICU, Unit2 = surgical ICU, both missing for other units; HospAdmTime = hours from
hospital admission to ICU admission (negative); ICULOS = hour + 1.

Known gap: MIMIC-IV records troponin T, not troponin I, so TroponinI is missing there.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "code"))
from cabsepsis.data import DEMOGRAPHICS, LABS, VITALS  # noqa: E402

VARS = VITALS + LABS

# MIMIC-IV: chartevents itemids (vitals, FiO2) and labevents itemids
MIMIC_CHART = {220045: "HR", 220277: "O2Sat", 223761: "Temp_F", 223762: "Temp", 220050: "SBP", 220179: "SBP",
               220052: "MAP", 220181: "MAP", 225312: "MAP", 220051: "DBP", 220180: "DBP", 220210: "Resp",
               224690: "Resp", 228640: "EtCO2", 223835: "FiO2"}
MIMIC_LAB = {50802: "BaseExcess", 50882: "HCO3", 50803: "HCO3", 50816: "FiO2", 50820: "pH", 50818: "PaCO2",
             50817: "SaO2", 50878: "AST", 51006: "BUN", 50863: "Alkalinephos", 50893: "Calcium",
             50902: "Chloride", 50912: "Creatinine", 50883: "Bilirubin_direct", 50931: "Glucose",
             50809: "Glucose", 50813: "Lactate", 50960: "Magnesium", 50970: "Phosphate", 50971: "Potassium",
             50822: "Potassium", 50885: "Bilirubin_total", 51221: "Hct", 51222: "Hgb", 51275: "PTT",
             51301: "WBC", 51300: "WBC", 51214: "Fibrinogen", 51265: "Platelets"}
MIMIC_UNITS = {"Medical Intensive Care Unit (MICU)": "MICU", "Surgical Intensive Care Unit (SICU)": "SICU"}

# eICU: vitalPeriodic / vitalAperiodic columns and lab names
EICU_PERIODIC = {"heartrate": "HR", "sao2": "O2Sat", "temperature": "Temp", "systemicsystolic": "SBP",
                 "systemicmean": "MAP", "systemicdiastolic": "DBP", "respiration": "Resp", "etco2": "EtCO2"}
EICU_APERIODIC = {"noninvasivesystolic": "SBP", "noninvasivemean": "MAP", "noninvasivediastolic": "DBP"}
EICU_LAB = {"Base Excess": "BaseExcess", "HCO3": "HCO3", "bicarbonate": "HCO3", "FiO2": "FiO2", "pH": "pH",
            "paCO2": "PaCO2", "O2 Sat (%)": "SaO2", "AST (SGOT)": "AST", "BUN": "BUN",
            "alkaline phos.": "Alkalinephos", "calcium": "Calcium", "chloride": "Chloride",
            "creatinine": "Creatinine", "direct bilirubin": "Bilirubin_direct", "glucose": "Glucose",
            "bedside glucose": "Glucose", "lactate": "Lactate", "magnesium": "Magnesium",
            "phosphate": "Phosphate", "potassium": "Potassium", "total bilirubin": "Bilirubin_total",
            "troponin - I": "TroponinI", "Hct": "Hct", "Hgb": "Hgb", "PTT": "PTT", "WBC x 1000": "WBC",
            "fibrinogen": "Fibrinogen", "platelets x 1000": "Platelets"}
EICU_UNITS = {"MICU": "MICU", "SICU": "SICU"}


def clean(ev):
    """Unit conversions on a long table (stay, t, var, value)."""
    ev = ev.dropna(subset=["value"]).copy()
    f = ev["var"] == "Temp_F"
    ev.loc[f, "value"] = (ev.loc[f, "value"] - 32) * 5 / 9
    ev.loc[f, "var"] = "Temp"
    fio2 = ev["var"] == "FiO2"
    ev.loc[fio2 & (ev.value > 1), "value"] /= 100
    ev = ev[~fio2 | ev.value.between(0.21, 1.0)]
    return ev


def wide(ev, grid):
    """Mean per stay-hour and variable, on the hourly grid (stay, hour)."""
    ev = clean(ev[(ev.t >= 0)])
    ev["hour"] = np.floor(ev.t).astype(int)
    w = ev.groupby(["stay", "hour", "var"]).value.mean().unstack("var")
    w = grid.set_index(["stay", "hour"]).join(w)
    for v in VARS:
        if v not in w:
            w[v] = np.nan
    return w[VARS].reset_index()


def long_events(stay, t, var, value):
    """Measurements at t >= 0 in the Challenge's units, with their hour: the input to a
    bigtable.HourlyAgg("mean") built chunk by chunk (the same values as wide() gives)."""
    ev = pd.DataFrame({"stay": np.asarray(stay), "t": np.asarray(t, dtype=float), "var": np.asarray(var),
                       "value": pd.to_numeric(pd.Series(np.asarray(value)), errors="coerce").to_numpy()})
    ev = clean(ev[ev.t >= 0])
    ev["hour"] = np.floor(ev.t).astype(int)
    return ev


def wide_from_hourly(hourly, grid):
    """wide() from hourly means already computed (bigtable.HourlyAgg("mean").result())."""
    w = grid.set_index(["stay", "hour"]).join(hourly)
    for v in VARS:
        if v not in w:
            w[v] = np.nan
    return w[VARS].reset_index()


def assemble(w, hc, demo, db):
    """w: wide hourly variables; hc: Challenge-cohort hourly table with SepsisLabel; demo: per stay
    (stay, site, unit in {MICU, SICU, other}, Age, Gender, HospAdmTime). Returns the chapter's table."""
    out = hc[["stay", "hour", "SepsisLabel"]].merge(w, on=["stay", "hour"], how="left")
    out = out.merge(demo, on="stay", how="left")
    out["Unit1"] = np.where(out.unit == "MICU", 1.0, np.where(out.unit == "SICU", 0.0, np.nan))
    out["Unit2"] = np.where(out.unit == "SICU", 1.0, np.where(out.unit == "MICU", 0.0, np.nan))
    out["unit"] = np.where(out.unit.isin(["MICU", "SICU"]), out.unit, "unknown")
    out["ICULOS"] = out.hour + 1
    out["pid"] = db + "_" + out.stay.astype(str)
    out["site"] = out.site.astype(str)
    cols = ["pid", "site", "hour", "unit"] + VARS + DEMOGRAPHICS + ["SepsisLabel"]
    out = out.sort_values(["pid", "hour"])[cols].reset_index(drop=True)
    out[VARS + ["Age", "HospAdmTime"]] = out[VARS + ["Age", "HospAdmTime"]].astype(np.float32)
    out["SepsisLabel"] = out.SepsisLabel.astype(np.int8)
    return out


def coverage(df):
    """Share of rows with each variable present (for comparison with the Challenge)."""
    return df[VARS].notna().mean()
