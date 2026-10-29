"""Download the ECG datasets for the journal version (macOS, Linux or Windows; needs curl).

    PTB-XL v1.0.3            (Germany, source)    PhysioNet's Amazon S3 mirror, 1.84 GB zip
    ecg-arrhythmia v1.0.0    (China, targets)     PhysioNet's Amazon S3 mirror, 2.50 GB zip
    Challenge 2021 v1.0.3:   Georgia (USA), CPSC 2018 and CPSC-Extra (China)
                             physionet.org only (slow per connection, so 32 in parallel)
    CODE-15% exams.csv and the first --code15-parts parts (Brazil)   Zenodo, 2.7 GB per part
    Challenge 2021 label tables (GitHub)

All CC BY 4.0. Safe to re-run: complete files are skipped and partial zips are resumed.
Zips are unpacked into the layout in data/README.md and kept, so a rerun does not fetch them.

Usage, from the repository root:
    python scripts/download_ecg.py [--only ptbxl,arrhythmia,challenge,code15,tables] [--code15-parts 1]
"""

import argparse
import concurrent.futures
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
S3 = "https://physionet-open.s3.amazonaws.com"
ZIPS = {
    "ptbxl": (f"{S3}/ptb-xl/ptb-xl-1.0.3.zip", DATA / "ptbxl" / "ptb-xl-1.0.3.zip", 1839504686),
    "arrhythmia": (f"{S3}/ecg-arrhythmia/ecg-arrhythmia-1.0.0.zip",
                   DATA / "ecg_arrhythmia" / "ecg-arrhythmia-1.0.0.zip", 2498709074),
}
CHALLENGE = "https://physionet.org/files/challenge-2021/1.0.3/training"
CHALLENGE_SETS = {"georgia": (11, 10344), "cpsc_2018": (7, 6877), "cpsc_2018_extra": (4, 3453)}
TABLES = "https://raw.githubusercontent.com/physionetchallenges/evaluation-2021/main"
ZENODO = "https://zenodo.org/api/records/4916206"


def fetch(url, tries=8):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return r.read()
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(3 * (attempt + 1))


def curl(url, out, size):
    """Resumable download of one large file; returns True when it has the expected size."""
    out.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(20):
        if out.exists() and out.stat().st_size == size:
            return True
        subprocess.run(["curl", "-sSL", "-C", "-", "--retry", "10", "-o", str(out), url])
    return out.exists() and out.stat().st_size == size


def unzip_once(z, dest):
    flag = dest / f".{z.name}.unpacked"
    if not flag.exists():
        print(f"  unpacking {z.name} ...")
        with zipfile.ZipFile(z) as f:
            f.extractall(dest)
        flag.touch()


def get_zip(name):
    url, out, size = ZIPS[name]
    print(f"{name}: {url}")
    if not curl(url, out, size):
        sys.exit(f"{name}: download incomplete, run again")
    unzip_once(out, out.parent)
    print(f"{name}: done")


def mat_complete(hea, mat):
    """The .mat holds a 24-byte header then int16 samples: size = offset + 2 * leads * samples."""
    if not (hea.exists() and mat.exists()):
        return False
    first = hea.read_text().split()
    nsig, nsamp = int(first[1]), int(first[3])
    return mat.stat().st_size in (24 + 2 * nsig * nsamp, 2 * nsig * nsamp)


def get_record(item):
    """Fetch one record. Some RECORDS lists name a record that is stored in the next folder
    (e.g. georgia/g1 lists E01000, which is in g2), so the neighbouring folders are tried too."""
    folder, rec = item
    s, g = folder.rsplit("/g", 1)
    for cand in [folder, f"{s}/g{int(g) + 1}", f"{s}/g{int(g) - 1}"]:
        base = DATA / "challenge2021" / "training" / cand
        hea, mat = base / f"{rec}.hea", base / f"{rec}.mat"
        if mat_complete(hea, mat):
            return
        try:
            data = {f: fetch(f"{CHALLENGE}/{cand}/{f.name}", tries=3) for f in (hea, mat)}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
        base.mkdir(parents=True, exist_ok=True)
        for f, b in data.items():
            tmp = f.with_suffix(f.suffix + ".tmp")
            tmp.write_bytes(b)
            tmp.replace(f)
        return
    print(f"  not found on PhysioNet: {folder}/{rec}", flush=True)


def try_record(item):
    try:
        get_record(item)
    except Exception as e:
        return str(e)


def get_challenge():
    items = []
    for s, (n_groups, _) in CHALLENGE_SETS.items():
        for g in range(1, n_groups + 1):
            folder = f"{s}/g{g}"
            items += [(folder, r) for r in fetch(f"{CHALLENGE}/{folder}/RECORDS").decode().split()]
    print(f"challenge: {len(items)} records from physionet.org (32 in parallel)")
    for attempt in range(5):   # PhysioNet sometimes answers 502; failed records are retried in a later pass
        failed, done = [], 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
            for item, err in zip(items, pool.map(try_record, items)):
                done += 1
                if err:
                    failed.append(item)
                if done % 1000 == 0 or done == len(items):
                    print(f"  {done}/{len(items)} ({len(failed)} failed so far)", flush=True)
        if not failed:
            break
        print(f"challenge: pass {attempt + 1} left {len(failed)} records, retrying them")
        items = failed
    root = DATA / "challenge2021" / "training"
    for s, (_, n) in CHALLENGE_SETS.items():
        ok = sum(mat_complete(h, h.with_suffix(".mat")) for h in (root / s).rglob("*.hea"))
        print(f"challenge {s}: {ok} complete records (expected {n})")
        if ok != n:
            sys.exit("challenge: incomplete, run again")


def get_tables():
    for f in ["dx_mapping_scored.csv", "dx_mapping_unscored.csv", "weights.csv"]:
        out = DATA / "challenge2021" / f
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(fetch(f"{TABLES}/{f}"))
    print("tables: done")


def get_code15(parts):
    files = {f["key"]: f for f in json.loads(fetch(ZENODO))["files"]}
    wanted = ["exams.csv"] + [f"exams_part{i}.zip" for i in range(parts)]
    for key in wanted:
        f = files[key]
        out = DATA / "code15" / key
        print(f"code15: {key} ({f['size'] / 1e9:.2f} GB)")
        if not curl(f["links"]["self"], out, f["size"]):
            sys.exit(f"code15: {key} incomplete, run again")
        if key.endswith(".zip"):
            unzip_once(out, out.parent)
    print("code15: done")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="ptbxl,arrhythmia,tables,challenge,code15")
    ap.add_argument("--code15-parts", type=int, default=1)
    a = ap.parse_args()
    for step in a.only.split(","):
        if step in ZIPS:
            get_zip(step)
        elif step == "challenge":
            get_challenge()
        elif step == "tables":
            get_tables()
        elif step == "code15":
            get_code15(a.code15_parts)
    print("RESULT: requested ECG downloads are COMPLETE.")


if __name__ == "__main__":
    main()
