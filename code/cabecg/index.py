"""Build one record-level index across all six cohorts.

Columns: source, country, record_id, patient_id, age, sex, fs, n_samples, duration_s,
file (relative to data/), h5_row (CODE-15% only), strat_fold (PTB-XL only),
the six panel labels, the audit labels, and dx_raw (the original codes, for auditing).
"""

import ast
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

from .headers import parse_header
from .labels import AUDIT_LABELS, CODE15_COLUMNS, PANEL, labels_from_scp, labels_from_snomed
from .paths import (CHALLENGE_TRAINING, CODE15_ROOT, ECG_ARRHYTHMIA_ROOT, PTBXL_ROOT,
                    find_one, rel)

COLUMNS = (["source", "country", "record_id", "patient_id", "age", "sex", "fs", "n_samples",
            "duration_s", "file", "h5_row", "strat_fold"] + PANEL + AUDIT_LABELS + ["dx_raw"])

COUNTRY = {
    "ptbxl": "Germany", "georgia": "USA", "cpsc_2018": "China", "cpsc_2018_extra": "China",
    "chapman_shaoxing": "China", "ningbo": "China", "code15": "Brazil",
}

# ecg-arrhythmia record numbers JS00001-JS10646 come from Chapman/Shaoxing and JS10647 onward
# from Ningbo (10,646 + 34,905 originals; 399 Chapman records were removed, leaving 10,247,
# which matches the Challenge 2021 Chapman-Shaoxing count). The E0 audit verifies both counts.
CHAPMAN_LAST_ID = 10646


def build_ptbxl():
    db_csv = find_one(PTBXL_ROOT, "ptbxl_database.csv")
    root = db_csv.parent
    db = pd.read_csv(db_csv, index_col="ecg_id")
    rows = []
    for ecg_id, r in db.iterrows():
        scp = ast.literal_eval(r["scp_codes"])
        rows.append({
            "source": "ptbxl", "record_id": f"ptbxl_{ecg_id:05d}",
            "patient_id": f"ptbxl_p{int(r['patient_id'])}",
            "age": r["age"] if 0 <= r["age"] < 120 else np.nan,  # PTB-XL codes ages over 89 as 300
            "sex": "M" if r["sex"] == 0 else "F",
            "fs": 500.0, "n_samples": 5000, "file": rel(root / r["filename_hr"]),
            "strat_fold": int(r["strat_fold"]),
            "dx_raw": ";".join(sorted(scp)), **labels_from_scp(scp),
        })
    return pd.DataFrame(rows)


def _wfdb_rows(hea_files, source_of):
    rows = []
    for hea in tqdm(hea_files, desc="headers", unit="rec", mininterval=2):
        h = parse_header(hea)
        source = source_of(h["record"])
        rows.append({
            "source": source, "record_id": f"{source}_{h['record']}",
            "patient_id": f"{source}_{h['record']}",  # no patient IDs: record-level
            "age": h["age"], "sex": h["sex"], "fs": h["fs"], "n_samples": h["n_samples"],
            "file": rel(hea), "dx_raw": ";".join(h["dx"]), **labels_from_snomed(h["dx"]),
        })
    return rows


def build_challenge():
    rows = []
    for source in ["georgia", "cpsc_2018", "cpsc_2018_extra"]:
        files = sorted((CHALLENGE_TRAINING / source).rglob("*.hea"))
        print(f"  {source}: {len(files)} headers")
        rows += _wfdb_rows(files, lambda rec, s=source: s)
    return pd.DataFrame(rows)


def build_ecg_arrhythmia():
    files = sorted(ECG_ARRHYTHMIA_ROOT.rglob("JS*.hea"))
    print(f"  ecg_arrhythmia: {len(files)} headers")

    def source_of(record):
        return "chapman_shaoxing" if int(record[2:]) <= CHAPMAN_LAST_ID else "ningbo"

    return pd.DataFrame(_wfdb_rows(files, source_of))


def build_code15():
    import h5py
    exams = pd.read_csv(find_one(CODE15_ROOT, "exams.csv"))
    h5_files = {p.name: p for p in CODE15_ROOT.rglob("exams_part*.hdf5")}
    print(f"  code15: {len(h5_files)} HDF5 parts found: {sorted(h5_files)}")
    frames = []
    for name, path in sorted(h5_files.items()):
        with h5py.File(path, "r") as f:
            ids = np.asarray(f["exam_id"][:])
        pos = pd.Series(np.arange(len(ids)), index=ids)
        part = exams[exams["trace_file"] == name].copy()
        part = part[part["exam_id"].isin(pos.index)]
        part["h5_row"] = pos.loc[part["exam_id"]].to_numpy()
        part["file"] = rel(path)
        frames.append(part)
    if not frames:
        return pd.DataFrame(columns=COLUMNS)
    ex = pd.concat(frames, ignore_index=True)
    out = pd.DataFrame({
        "source": "code15",
        "record_id": "code15_" + ex["exam_id"].astype(str),
        "patient_id": "code15_p" + ex["patient_id"].astype(str),
        "age": ex["age"], "sex": np.where(ex["is_male"].astype(bool), "M", "F"),
        "fs": 400.0, "n_samples": 4096, "file": ex["file"], "h5_row": ex["h5_row"],
        "dx_raw": "",
    })
    for name, col in CODE15_COLUMNS.items():
        out[name] = ex[col].astype(bool).astype(int).to_numpy()
    for name in AUDIT_LABELS:
        out[name] = np.nan  # not labelled in CODE-15%
    return out


def build_index():
    parts = []
    for name, fn in [("PTB-XL", build_ptbxl), ("Challenge 2021", build_challenge),
                     ("ecg-arrhythmia", build_ecg_arrhythmia), ("CODE-15%", build_code15)]:
        print(f"Indexing {name} ...")
        try:
            parts.append(fn())
        except FileNotFoundError as e:
            print(f"  SKIPPED: {e}")
    df = pd.concat(parts, ignore_index=True)
    df["country"] = df["source"].map(COUNTRY)
    df["duration_s"] = df["n_samples"] / df["fs"]
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = np.nan
    return df[COLUMNS]
