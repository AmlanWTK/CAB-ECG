"""Copy the small, final result files from outputs/ (git-ignored) into results/ (tracked),
so they can be pushed to GitHub and pulled on another computer.

Only reports, summary CSVs, figures and tables are copied (a few MB). Large files (feature
cache, per-run CSVs, models) stay in outputs/ and are never committed.

Run from the repository root, after the experiments and sepsis_figures.py:
    python scripts\\publish_results.py
then:
    git add results
    git commit -m "Results"
    git push
"""

import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "outputs" / "sepsis"
DST = REPO / "results" / "sepsis"

FILES = [
    "E1_E2_report.md", "E1_E2_results.csv",
    "E2_ci.md", "E2_ci.csv", "E2_calibration.csv",
    "E3_report.md", "E3_summary.csv", "E3_oracle.csv",            # v1, kept for the record
    "E3v2_report.md", "E3v2_summary.csv", "E3v2_oracle.csv",      # primary analysis
    "splits.csv", "lgbm_siteA.json", "lgbm_siteB.json",           # reproducibility
]
MAX_MB = 20


def main():
    DST.mkdir(parents=True, exist_ok=True)
    copied, missing = [], []
    for name in FILES:
        f = SRC / name
        if f.exists():
            shutil.copy2(f, DST / name)
            copied.append(name)
        else:
            missing.append(name)
    fig_src = SRC / "figures"
    if fig_src.exists():
        (DST / "figures").mkdir(exist_ok=True)
        for f in sorted(fig_src.iterdir()):
            if f.suffix.lower() in {".png", ".pdf", ".md"}:
                shutil.copy2(f, DST / "figures" / f.name)
                copied.append(f"figures/{f.name}")
    total = sum(p.stat().st_size for p in DST.rglob("*") if p.is_file()) / 1e6
    print(f"Copied {len(copied)} files into results/sepsis ({total:.1f} MB):")
    for c in copied:
        print(f"  {c}")
    if missing:
        print("Not found (skipped): " + ", ".join(missing))
    if total > MAX_MB:
        print(f"WARNING: results/sepsis is {total:.0f} MB; check before committing.")
    print("\nNext: git add results ; git commit -m \"Results\" ; git push")


if __name__ == "__main__":
    main()
