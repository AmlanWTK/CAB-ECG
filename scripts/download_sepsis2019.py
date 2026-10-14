"""Download the PhysioNet/CinC Challenge 2019 sepsis training data (sets A and B).

Source: PhysioNet's official open-data mirror on Amazon S3 (licence CC BY 4.0).
  set A = Beth Israel Deaconess Medical Center, 20,336 patients
  set B = Emory University Hospital, 20,000 patients
Each patient is one pipe-separated file of hourly rows (about 42 MB in total).

Safe to re-run: files already present with the right size are skipped, and every file
is checked against the size listed by the server at the end.

Usage, from the repository root:
    python scripts\\download_sepsis2019.py
"""

import concurrent.futures
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BUCKET = "https://physionet-open.s3.amazonaws.com"
PREFIX = "challenge-2019/1.0.0/training/"
NS = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
REPO = Path(__file__).resolve().parents[1]
DEST = REPO / "data" / "sepsis2019" / "training"
EXPECTED = {"training_setA": 20336, "training_setB": 20000}


def fetch(url, tries=6):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except Exception as e:  # network hiccup: wait and retry
            if attempt == tries - 1:
                raise
            time.sleep(2 * (attempt + 1))


def list_keys():
    keys, token = [], None
    while True:
        q = {"list-type": "2", "prefix": PREFIX, "max-keys": "1000"}
        if token:
            q["continuation-token"] = token
        root = ET.fromstring(fetch(BUCKET + "/?" + urllib.parse.urlencode(q)))
        for c in root.findall("s:Contents", NS):
            key = c.find("s:Key", NS).text
            if key.endswith(".psv"):
                keys.append((key, int(c.find("s:Size", NS).text)))
        if root.find("s:IsTruncated", NS).text == "true":
            token = root.find("s:NextContinuationToken", NS).text
        else:
            return keys


def local_path(key):
    return DEST / key[len(PREFIX):]


def download(item):
    key, size = item
    out = local_path(key)
    if out.exists() and out.stat().st_size == size:
        return "skipped"
    out.parent.mkdir(parents=True, exist_ok=True)
    data = fetch(BUCKET + "/" + urllib.parse.quote(key))
    tmp = out.with_suffix(".tmp")
    tmp.write_bytes(data)
    tmp.replace(out)
    return "downloaded"


def main():
    print("Listing files on the PhysioNet S3 mirror ...")
    keys = list_keys()
    print(f"{len(keys)} patient files listed. Downloading to {DEST}")
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
        for _ in pool.map(download, keys):
            done += 1
            if done % 2000 == 0 or done == len(keys):
                print(f"  {done}/{len(keys)}")

    bad = [k for k, s in keys if not local_path(k).exists() or local_path(k).stat().st_size != s]
    print()
    for folder, n in EXPECTED.items():
        have = len(list((DEST / folder).glob("*.psv")))
        print(f"{folder}: {have} files (expected {n})")
    if bad or any(len(list((DEST / f).glob('*.psv'))) != n for f, n in EXPECTED.items()):
        print(f"RESULT: NOT complete ({len(bad)} files missing or wrong size). Run this script again.")
        sys.exit(1)
    print("RESULT: Challenge 2019 sepsis data is COMPLETE and intact.")


if __name__ == "__main__":
    main()
