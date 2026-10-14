"""Step 1 of E0: index every record of all six cohorts into outputs/index/index.csv.

Run from the repository root:
    python code\\build_index.py
"""

from cabecg.index import build_index
from cabecg.paths import INDEX_CSV, INDEX_DIR


def main():
    df = build_index()
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(INDEX_CSV, index=False)
    print()
    print(df.groupby("source", sort=False).size().rename("records").to_string())
    print(f"\nTotal {len(df)} records. Wrote {INDEX_CSV}")


if __name__ == "__main__":
    main()
