"""Load the Challenge 2019 hourly patient files into one table.

Columns: pid, site (A = Beth Israel Deaconess, B = Emory), hour (0-based row within the
patient), unit (MICU / SICU / unknown), the 40 Challenge variables, SepsisLabel.

SepsisLabel is 1 from 6 hours before sepsis onset (Sepsis-3) onward, so for a septic
patient: onset hour = first labelled hour + 6.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

REPO = Path(__file__).resolve().parents[2]
TRAINING = REPO / "data" / "sepsis2019" / "training"
CACHE = REPO / "outputs" / "sepsis" / "rows.pkl"

VITALS = ["HR", "O2Sat", "Temp", "SBP", "MAP", "DBP", "Resp", "EtCO2"]
LABS = ["BaseExcess", "HCO3", "FiO2", "pH", "PaCO2", "SaO2", "AST", "BUN", "Alkalinephos",
        "Calcium", "Chloride", "Creatinine", "Bilirubin_direct", "Glucose", "Lactate",
        "Magnesium", "Phosphate", "Potassium", "Bilirubin_total", "TroponinI", "Hct", "Hgb",
        "PTT", "WBC", "Fibrinogen", "Platelets"]
DEMOGRAPHICS = ["Age", "Gender", "Unit1", "Unit2", "HospAdmTime", "ICULOS"]
SITES = {"A": "training_setA", "B": "training_setB"}


def _read(path, site):
    d = pd.read_csv(path, sep="|")
    d.insert(0, "hour", np.arange(len(d), dtype=np.int32))
    d.insert(0, "site", site)
    d.insert(0, "pid", f"{site}_{path.stem}")
    return d


def load_all(use_cache=True):
    if use_cache and CACHE.exists():
        return pd.read_pickle(CACHE)
    frames = []
    for site, folder in SITES.items():
        files = sorted((TRAINING / folder).glob("*.psv"))
        if not files:
            raise FileNotFoundError(f"No .psv files in {TRAINING / folder}. Run scripts\\download_sepsis2019.py")
        for p in tqdm(files, desc=f"set {site}", unit="pt", mininterval=2):
            frames.append(_read(p, site))
    df = pd.concat(frames, ignore_index=True)
    df["unit"] = np.where(df["Unit1"] == 1, "MICU", np.where(df["Unit2"] == 1, "SICU", "unknown"))
    float_cols = VITALS + LABS + ["Age", "HospAdmTime"]
    df[float_cols] = df[float_cols].astype(np.float32)
    df["SepsisLabel"] = df["SepsisLabel"].astype(np.int8)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    df.to_pickle(CACHE)
    return df


def patient_table(df):
    """One row per patient: site, unit (most frequent), n_hours, septic, label_start, onset."""
    g = df.groupby("pid", sort=False)
    first_label = df[df["SepsisLabel"] == 1].groupby("pid")["hour"].min()
    pt = pd.DataFrame({
        "site": g["site"].first(),
        "unit": g["unit"].agg(lambda u: u.value_counts().index[0]),
        "n_hours": g.size(),
        "age": g["Age"].first(),
        "male": g["Gender"].first(),
    })
    pt["label_start"] = first_label.reindex(pt.index)
    pt["septic"] = pt["label_start"].notna()
    pt["onset"] = pt["label_start"] + 6
    return pt
