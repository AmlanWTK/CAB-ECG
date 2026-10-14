"""Step 2 of E0: label-semantics and data audit. Reads outputs/index/index.csv.

Checks:
  A. the SNOMED codes we map carry the expected abbreviations in the Challenge 2021 tables
  B. record counts per cohort, including the Chapman/Ningbo split
  C. prevalence of each panel label (and audit labels) per cohort
  D. labelling-convention flags (AF vs flutter, RBBB vs incomplete RBBB, ...)
  E. durations, age/sex availability
  F. signal sanity on a random sample per cohort: shape, NaNs, flat leads, amplitude in mV

Run from the repository root (after build_index.py):
    python code\\audit_e0.py
Writes outputs/audit/E0_audit.md and outputs/audit/prevalence.csv.
"""

import sys

import numpy as np
import pandas as pd

from cabecg.labels import AUDIT_LABELS, EXPECTED_ABBREVIATION, PANEL
from cabecg.paths import AUDIT_DIR, CHALLENGE_ROOT, DATA, INDEX_CSV
from cabecg.signals import load_standardised

SOURCE_ORDER = ["ptbxl", "georgia", "chapman_shaoxing", "ningbo", "cpsc_2018", "cpsc_2018_extra", "code15"]
EXPECTED_COUNTS = {"ptbxl": 21799, "georgia": 10344, "chapman_shaoxing": 10247, "ningbo": 34905,
                   "cpsc_2018": 6877, "cpsc_2018_extra": 3453}
SAMPLE_PER_SOURCE = 60

out_lines = []


def say(text=""):
    print(text)
    out_lines.append(text)


def table(df):
    say("```")
    say(df.to_string())
    say("```")
    say()


def check_codes():
    say("## A. SNOMED codes vs Challenge 2021 dx_mapping tables")
    frames = []
    for name in ["dx_mapping_scored.csv", "dx_mapping_unscored.csv"]:
        p = CHALLENGE_ROOT / name
        if p.exists():
            frames.append(pd.read_csv(p, dtype=str))
    if not frames:
        say("dx_mapping tables not found in data/challenge2021 - skipped")
        return
    m = pd.concat(frames)
    code_col = [c for c in m.columns if "snomed" in c.lower()][0]
    ab_col = [c for c in m.columns if "abbrev" in c.lower()][0]
    found = dict(zip(m[code_col].str.strip(), m[ab_col].str.strip()))
    rows = []
    for code, expected in EXPECTED_ABBREVIATION.items():
        got = found.get(code, "NOT FOUND")
        rows.append({"code": code, "expected": expected, "in_table": got, "ok": got == expected})
    t = pd.DataFrame(rows).set_index("code")
    table(t)
    say(f"All codes match: {bool(t['ok'].all())}")
    say()


def counts(df):
    say("## B. Records per cohort")
    n = df.groupby("source").size().reindex(SOURCE_ORDER)
    t = pd.DataFrame({"records": n, "expected": pd.Series(EXPECTED_COUNTS).reindex(SOURCE_ORDER)})
    t["ok"] = (t["records"] == t["expected"]) | t["expected"].isna()
    table(t)
    say("Chapman/Ningbo split rule (JS<=10646 -> Chapman) is confirmed if both counts match.")
    say()


def prevalence(df):
    say("## C. Prevalence per cohort: count (percent)")
    cols = PANEL + AUDIT_LABELS
    g = df.groupby("source")
    n = g.size().reindex(SOURCE_ORDER)
    cnt = g[cols].sum(min_count=1).reindex(SOURCE_ORDER)
    pct = (cnt.div(n, axis=0) * 100).round(1)
    shown = cnt.astype("Int64").astype(str) + " (" + pct.astype(str) + ")"
    shown = shown.where(cnt.notna(), "n/a")
    shown.insert(0, "records", n)
    table(shown)
    prev = cnt.copy()
    prev.insert(0, "records", n)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    prev.to_csv(AUDIT_DIR / "prevalence.csv")
    say("Cells with fewer than 30 positives (too rare for label-budget experiments):")
    rare = [(s, c, int(cnt.loc[s, c])) for s in SOURCE_ORDER for c in PANEL
            if s in cnt.index and pd.notna(cnt.loc[s, c]) and cnt.loc[s, c] < 30]
    for s, c, k in rare:
        say(f"  {s:18s} {c:6s} {k}")
    if not rare:
        say("  none")
    say()


def convention_flags(df):
    say("## D. Labelling-convention flags")
    rows = []
    for s in SOURCE_ORDER:
        d = df[df.source == s]
        if d.empty or s == "code15":
            continue
        rows.append({
            "source": s,
            "AF": int(d.AF.sum()), "AFL": int(d.AFL.sum()), "AF&AFL": int((d.AF.eq(1) & d.AFL.eq(1)).sum()),
            "RBBB": int(d.RBBB.sum()), "IRBBB": int(d.IRBBB.sum()),
            "SB&NSR": int((d.SB.eq(1) & d.NSR.eq(1)).sum()),
            "STach&NSR": int((d.STach.eq(1) & d.NSR.eq(1)).sum()),
            "no_dx": int((d.dx_raw.fillna("") == "").sum()),
        })
    table(pd.DataFrame(rows).set_index("source"))
    say("Read: AFL >> AF at a site suggests AF is coded as flutter there; RBBB high with")
    say("IRBBB=0 suggests complete/incomplete RBBB are lumped; SB&NSR counts show whether")
    say("sinus brady/tachy are coded alongside 'normal sinus rhythm'.")
    say()


def durations(df):
    say("## E. Duration and demographics")
    g = df.groupby("source")
    t = pd.DataFrame({
        "fs_Hz": g.fs.agg(lambda x: ",".join(str(int(v)) for v in sorted(set(x.dropna())))),
        "dur_median_s": g.duration_s.median().round(1),
        "dur_min_s": g.duration_s.min().round(1),
        "dur_max_s": g.duration_s.max().round(1),
        "pct_under_10s": g.duration_s.apply(lambda x: round(100 * (x < 9.99).mean(), 1)),
        "age_known_pct": g.age.apply(lambda x: round(100 * x.notna().mean(), 1)),
        "age_median": g.age.median(),
        "male_pct": g.sex.apply(lambda x: round(100 * (x == "M").mean(), 1)),
        "patients": g.patient_id.nunique(),
    }).reindex(SOURCE_ORDER)
    table(t)


def signal_sanity(df):
    say(f"## F. Signal sanity ({SAMPLE_PER_SOURCE} random records per cohort, standardised to 100 Hz x 10 s)")
    rows = []
    for s in SOURCE_ORDER:
        d = df[df.source == s]
        if d.empty:
            continue
        sample = d.sample(min(SAMPLE_PER_SOURCE, len(d)), random_state=0)
        amps, flat, nans, errors, valid = [], 0, 0, 0, []
        first_error = ""
        for _, r in sample.iterrows():
            try:
                x, k = load_standardised(r)
            except Exception as e:  # report, do not stop the audit
                errors += 1
                first_error = first_error or f"{type(e).__name__}: {e}"
                continue
            valid.append(k)
            nans += int(np.isnan(x).any())
            seg = x[:, :k]
            flat += int((seg.std(axis=1) < 1e-3).sum())
            amps.append(np.percentile(np.abs(seg[1] - np.median(seg[1])), 99))  # lead II, mV
        rows.append({
            "source": s, "read_ok": len(valid), "errors": errors,
            "lead_II_p99_amp_mV": round(float(np.median(amps)), 3) if amps else np.nan,
            "flat_leads": flat, "with_nan": nans,
            "valid_samples_median": int(np.median(valid)) if valid else 0,
            "first_error": first_error[:60],
        })
    table(pd.DataFrame(rows).set_index("source"))
    say("Expected lead II amplitude is roughly 0.5-2 mV. A cohort far outside that range")
    say("(e.g. ~1000x or ~0.001x) has a unit/scale problem to fix in signals.SOURCE_SCALE.")
    say()


def main():
    if not INDEX_CSV.exists():
        sys.exit("outputs/index/index.csv not found - run python code\\build_index.py first")
    df = pd.read_csv(INDEX_CSV, low_memory=False)
    say("# E0 audit")
    say()
    check_codes()
    counts(df)
    prevalence(df)
    convention_flags(df)
    durations(df)
    signal_sanity(df)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    (AUDIT_DIR / "E0_audit.md").write_text("\n".join(out_lines), encoding="utf-8")
    print(f"Wrote {AUDIT_DIR / 'E0_audit.md'}")


if __name__ == "__main__":
    main()
