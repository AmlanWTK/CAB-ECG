"""Where Sepsis-3 cases are gained and lost in an extraction (WP1 label check, notes/label_check.md).

Reads the per-stay table written by mimiciv_sepsis.py or eicu_sepsis.py (<out>_<definition>_stays.csv)
and prints aggregate counts only, so the output can be shared under the PhysioNet data use
agreement: no stay identifiers, no row-level values, and any count from 1 to 9 is shown as "<10".

    python q1_journal_plan/code/label_diagnostics.py outputs/sepsis_q1/mimiciv_full_challenge_stays.csv
        [outputs/sepsis_q1/mimiciv_full_relaxed_stays.csv] [--root <MIMIC-IV folder>]

With two files (Challenge and relaxed definitions of the same database), it also reports how far
the two sets of septic stays overlap (check 2).
"""

import sys

import numpy as np
import pandas as pd

S3_MIN_ONSET_HOUR = 4


def n(x):
    """A count, with small cells suppressed."""
    x = int(x)
    return "<10" if 0 < x < 10 else f"{x:,}"


def pct(a, b):
    return "-" if b == 0 or 0 < a < 10 else f"{a / b:.1%}"


def table(title, s, bins, labels):
    """Counts of the values in s, binned."""
    c = pd.cut(s, bins, labels=labels, right=False).value_counts().reindex(labels)
    tot = len(s)
    print(f"  {title} (n = {n(tot)})")
    for lab, k in c.items():
        print(f"    {lab:>18}: {n(k):>8}  {pct(k, tot):>6}")


def report(path):
    st = pd.read_csv(path)
    N = len(st)
    print(f"\n== {path}: {n(N)} stays")
    susp = st[st.t_suspicion.notna()]
    sep = st[st.onset.notna()]
    print(f"  suspected infection {n(len(susp))} ({pct(len(susp), N)}); Sepsis-3 before cohort rules "
          f"{n(len(sep))} ({pct(len(sep), N)})")

    hb = [-np.inf, -24, 0, 4, 24, 72, np.inf]
    hl = ["before -24 h", "-24 to 0 h", "0 to 4 h", "4 to 24 h", "24 to 72 h", "72 h or later"]
    table("time of suspected infection, from ICU admission", susp.t_suspicion, hb, hl)

    no_rise = susp[susp.onset.isna()]
    print(f"  suspected infection without a qualifying SOFA rise: {n(len(no_rise))} ({pct(len(no_rise), len(susp))})")
    table("  their highest SOFA during the stay", no_rise.max_sofa.fillna(0), [0, 2, 4, 6, 10, np.inf],
          ["0-1", "2-3", "4-5", "6-9", "10+"])

    table("Sepsis-3 onset, from ICU admission", sep.onset, hb, hl)
    early = sep[sep.onset < S3_MIN_ONSET_HOUR]
    by_susp = (early.onset == early.t_suspicion).sum()
    print(f"  onset under 4 h: {n(len(early))}; onset set by the suspicion time {n(by_susp)} "
          f"({pct(by_susp, len(early))}), by the SOFA rise {n(len(early) - by_susp)}")

    short = st.excluded.eq("under 8 h")
    inc = st[st.excluded.isna()]
    print(f"  Challenge cohort {n(len(inc))}, septic {n(inc.septic.sum())} ({pct(inc.septic.sum(), len(inc))})")
    kept = st[~short]
    print(f"  for comparison, keeping onsets under 4 h: {n(kept.onset.notna().sum())} of {n(len(kept))} "
          f"stays of 8 h or more ({pct(kept.onset.notna().sum(), len(kept))})")
    table("length of stay, cohort", inc.hours, [0, 24, 48, 96, 168, 336, np.inf],
          ["under 24 h", "24-48 h", "48-96 h", "4-7 days", "7-14 days", "over 14 days"])
    return st


def by_group(st, root):
    """MIMIC-IV only: septic share of the Challenge cohort by first ICU unit and by anchor year group
    (the 3-year period in which each patient's stays fall, MIMIC-IV's only date information)."""
    from pathlib import Path
    root = Path(root)
    icu = pd.read_csv(root / "icu/icustays.csv.gz", usecols=["stay_id", "subject_id", "first_careunit"])
    pts = pd.read_csv(root / "hosp/patients.csv.gz", usecols=["subject_id", "anchor_year_group"])
    inc = st[st.excluded.isna()].merge(icu.rename(columns={"stay_id": "stay"})[["stay", "first_careunit"]],
                                       on="stay", how="left").merge(pts, on="subject_id", how="left")
    early = st[st.excluded.eq("onset under 4 h")].merge(icu.rename(columns={"stay_id": "stay"})[["stay", "first_careunit"]],
                                                        on="stay", how="left").merge(pts, on="subject_id", how="left")
    for col, title in [("first_careunit", "first ICU unit"), ("anchor_year_group", "anchor year group")]:
        g = inc.groupby(col).septic.agg(["size", "sum"])
        e = early.groupby(col).size()
        print(f"  septic share of the cohort by {title} (and stays excluded for onset under 4 h)")
        for k, r in g.sort_values("size", ascending=False).iterrows():
            print(f"    {str(k)[:40]:>40}: {n(r['sum']):>7} of {n(r['size']):>7}  {pct(r['sum'], r['size']):>6}"
                  f"   excluded early {n(e.get(k, 0)):>6}")


def main():
    args = sys.argv[1:]
    root = None
    if "--root" in args:
        i = args.index("--root")
        root = args[i + 1]
        args = args[:i] + args[i + 2:]
    a = [report(p) for p in args]
    if root:
        by_group(a[0], root)
    if len(a) == 2:
        c, r = (x.set_index("stay").septic for x in a)
        both = (c & r.reindex(c.index, fill_value=False)).sum()
        print(f"\n== overlap: {n(both)} of {n(c.sum())} stays septic under the first definition are "
              f"septic under the second ({pct(both, c.sum())})")
        # the stays septic under the first definition but not the second: what the second says
        s1, s2 = (x.set_index("stay") for x in a)
        lost = s2.reindex(c[c].index)
        lost = lost[~lost.septic.fillna(False).astype(bool)]
        status = np.select([lost.excluded.eq("onset under 4 h"), lost.excluded.eq("under 8 h"),
                            lost.t_suspicion.isna(), lost.onset.isna()],
                           ["excluded, onset under 4 h", "excluded, under 8 h", "no suspected infection",
                            "suspected infection, no SOFA rise"], "other")
        print(f"  the {n(len(lost))} not septic under the second definition, by their status there:")
        for k, v in pd.Series(status).value_counts().items():
            print(f"    {k:>36}: {n(v):>7}  {pct(v, len(lost)):>6}")
        d = lost.t_suspicion - s1.t_suspicion.reindex(lost.index)
        print(f"  suspicion earlier under the second definition: {n((d < 0).sum())}; same time: "
              f"{n((d == 0).sum())}; later: {n((d > 0).sum())}; median shift {d[d < 0].median():.1f} h"
              if (d < 0).sum() >= 10 else "  suspicion shift: fewer than 10 stays")


if __name__ == "__main__":
    main()
