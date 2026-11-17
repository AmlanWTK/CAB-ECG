"""Where Sepsis-3 cases are gained and lost in an extraction (WP1 label check, notes/label_check.md).

Reads the per-stay table written by mimiciv_sepsis.py or eicu_sepsis.py (<out>_<definition>_stays.csv)
and prints aggregate counts only, so the output can be shared under the PhysioNet data use
agreement: no stay identifiers, no row-level values, and any count from 1 to 9 is shown as "<10".

    python q1_journal_plan/code/label_diagnostics.py outputs/sepsis_q1/mimiciv_full_challenge_stays.csv
        [outputs/sepsis_q1/mimiciv_full_relaxed_stays.csv]

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


def main():
    a = [report(p) for p in sys.argv[1:]]
    if len(a) == 2:
        c, r = (x.set_index("stay").septic for x in a)
        both = (c & r.reindex(c.index, fill_value=False)).sum()
        print(f"\n== overlap: {n(both)} of {n(c.sum())} stays septic under the first definition are "
              f"septic under the second ({pct(both, c.sum())})")


if __name__ == "__main__":
    main()
