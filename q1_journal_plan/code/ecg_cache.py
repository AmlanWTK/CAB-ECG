"""Read every indexed ECG once and store it standardised (12 leads x 10 s at 100 Hz, mV, float16).

Needs outputs/index/index.csv (python code/build_index.py). Writes, per source,
outputs/ecg/signals/<source>.npy (n x 12 x 1000) and <source>_ids.csv (record_id, n_valid,
in the same order). Sources already cached are skipped; delete a file to rebuild it.

Run from the repository root (about 20-40 minutes in total, 8 processes):
    python q1_journal_plan/code/ecg_cache.py [--sources ptbxl,georgia,...]
"""

import argparse
import concurrent.futures
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code"))
from cabecg.paths import INDEX_CSV, OUTPUTS  # noqa: E402
from cabecg.signals import load_standardised  # noqa: E402

CACHE = OUTPUTS / "ecg" / "signals"


def _load(row):
    try:
        x, k = load_standardised(row)
        return np.clip(x, -10, 10).astype(np.float16), k
    except Exception as e:  # unreadable record: kept as zeros and flagged
        print(f"  unreadable {row['record_id']}: {e}", flush=True)
        return np.zeros((12, 1000), np.float16), 0


def cache_source(rows, source):
    out = CACHE / f"{source}.npy"
    if out.exists():
        print(f"{source}: cached")
        return
    recs = rows.to_dict("records")
    X = np.zeros((len(recs), 12, 1000), np.float16)
    valid = np.zeros(len(recs), np.int32)
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as pool:
        for i, (x, k) in enumerate(pool.map(_load, recs, chunksize=64)):
            X[i], valid[i] = x, k
            if (i + 1) % 5000 == 0:
                print(f"  {source}: {i + 1}/{len(recs)}", flush=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(out.with_suffix(".tmp.npy"), X)
    out.with_suffix(".tmp.npy").replace(out)
    pd.DataFrame({"record_id": rows["record_id"].to_numpy(), "n_valid": valid}).to_csv(
        CACHE / f"{source}_ids.csv", index=False)
    print(f"{source}: {len(recs)} records, {int((valid == 0).sum())} unreadable")


def load_cache(source):
    """Signals (memory-mapped) and ids for one source."""
    return np.load(CACHE / f"{source}.npy", mmap_mode="r"), pd.read_csv(CACHE / f"{source}_ids.csv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default="")
    a = ap.parse_args()
    idx = pd.read_csv(INDEX_CSV, low_memory=False)
    sources = a.sources.split(",") if a.sources else list(idx["source"].unique())
    for s in sources:
        cache_source(idx[idx["source"] == s].reset_index(drop=True), s)


if __name__ == "__main__":
    main()
