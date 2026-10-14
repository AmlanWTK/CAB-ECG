"""Read one record from any source and standardise it to 12 x (seconds * target_fs) in mV.

Standard form: canonical lead order I, II, III, aVR, aVL, aVF, V1-V6; resampled to target_fs
(default 100 Hz); the first `seconds` (default 10 s) kept; shorter records zero-padded at the end.
"""

from fractions import Fraction
from functools import lru_cache
from pathlib import Path

import numpy as np
import scipy.io
from scipy.signal import resample_poly

from .headers import parse_header
from .paths import DATA

LEADS = ["I", "II", "III", "AVR", "AVL", "AVF", "V1", "V2", "V3", "V4", "V5", "V6"]

# Multiply raw values by this to get mV. CODE-15% units are confirmed by the E0 audit
# (amplitude check against PTB-XL) before any training uses them.
SOURCE_SCALE = {"code15": 1.0}


_ALIASES = {"DI": "I", "DII": "II", "DIII": "III"}


def _canonical(name):
    n = name.strip().upper()
    return _ALIASES.get(n, n)


def _reorder(sig, leads):
    order = {_canonical(l): i for i, l in enumerate(leads)}
    missing = [l for l in LEADS if l not in order]
    if missing:
        raise ValueError(f"missing leads {missing}; found {leads}")
    return sig[[order[l] for l in LEADS]]


def read_wfdb_mat(hea_path):
    """Challenge 2021 / ecg-arrhythmia record: .hea + MATLAB .mat holding 'val' (n_sig x n)."""
    h = parse_header(hea_path)
    mat_path = Path(hea_path).with_name(h["signals"][0]["file"])
    val = np.asarray(scipy.io.loadmat(mat_path)["val"], dtype=np.float64)
    if val.shape[0] != h["n_sig"] and val.shape[1] == h["n_sig"]:
        val = val.T
    gain = np.array([s["gain"] for s in h["signals"]])[:, None]
    base = np.array([s["baseline"] for s in h["signals"]])[:, None]
    sig = (val - base) / gain
    unit_scale = np.array([1e-3 if s["units"].lower() in {"uv", "microvolt"} else 1.0 for s in h["signals"]])[:, None]
    sig = sig * unit_scale
    return _reorder(sig, [s["lead"] for s in h["signals"]]), h["fs"]


def read_ptbxl(rel_base):
    """PTB-XL record via wfdb (rel_base like 'ptbxl/<folder>/records500/00000/00001_hr')."""
    import wfdb
    sig, fields = wfdb.rdsamp(str(DATA / rel_base))
    return _reorder(sig.T, fields["sig_name"]), float(fields["fs"])


@lru_cache(maxsize=4)
def _h5(path):
    import h5py
    return h5py.File(path, "r")


def read_code15(rel_h5, row):
    """CODE-15% exam: tracings[row] is 4096 x 12 at 400 Hz, zero-padded at both ends."""
    f = _h5(str(DATA / rel_h5))
    x = np.asarray(f["tracings"][int(row)], dtype=np.float64).T  # 12 x 4096
    nonzero = np.flatnonzero(np.any(x != 0, axis=0))
    if nonzero.size:
        x = x[:, nonzero[0]:nonzero[-1] + 1]
    return x * SOURCE_SCALE["code15"], 400.0


def read_record(row):
    """Read a raw record (12 x n in mV, fs) from an index row."""
    if row["source"] == "ptbxl":
        return read_ptbxl(row["file"])
    if row["source"] == "code15":
        return read_code15(row["file"], row["h5_row"])
    return read_wfdb_mat(DATA / row["file"])


def standardise(sig, fs, target_fs=100, seconds=10):
    """Resample and fix length. Returns (12 x target_fs*seconds float32, n_valid_samples)."""
    sig = np.nan_to_num(np.asarray(sig, dtype=np.float64))
    ratio = Fraction(int(round(target_fs)), int(round(fs))).limit_denominator(1000)
    if ratio != 1:
        sig = resample_poly(sig, ratio.numerator, ratio.denominator, axis=1)
    n = int(target_fs * seconds)
    out = np.zeros((sig.shape[0], n), dtype=np.float32)
    k = min(n, sig.shape[1])
    out[:, :k] = sig[:, :k]
    return out, k


def load_standardised(row, target_fs=100, seconds=10):
    sig, fs = read_record(row)
    return standardise(sig, fs, target_fs, seconds)
