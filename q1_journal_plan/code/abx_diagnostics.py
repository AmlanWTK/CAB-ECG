"""Antibiotic courses from orders versus administrations, MIMIC-IV (WP1 label check).

The Challenge counts suspected infection only when IV antibiotics were *administered* for at least
72 consecutive hours (Reyna et al. 2020). mimiciv_sepsis.py --definition challenge builds those
courses from prescription orders (hosp/prescriptions: start and stop of each order). This script
builds them a second way, from the recorded administrations (hosp/emar), and compares the two, so
we can see whether the order-based courses miss real courses.

Output is aggregate only (PhysioNet data use agreement): counts and percentages, counts from 1 to 9
shown as "<10", no identifiers.

    python q1_journal_plan/code/abx_diagnostics.py --root <MIMIC-IV folder>

Administration courses: doses of a systemic antibacterial (same list as the extractor) recorded as
given ("Administered", "Delayed Administered", "Administered in Other Location", "Started"), by the
IV route (route from the linked prescription; doses with no linked route are reported separately).
Doses less than 24 h apart form one course, and a course counts if its first and last doses are at
least 72 h apart: the same joining rule as the order-based courses, applied to dose times.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mimiciv_sepsis as M   # noqa: E402
import sepsis3 as S3          # noqa: E402

GIVEN = {"Administered", "Delayed Administered", "Administered in Other Location", "Started"}
ABX = "|".join(M.ANTIBIOTICS)


def n(x):
    x = int(x)
    return "<10" if 0 < x < 10 else f"{x:,}"


def pct(a, b):
    return "-" if b == 0 or 0 < a < 10 else f"{a / b:.1%}"


def longest(df, key, start, stop):
    """Longest joined course per key (hours), with the extractor's 24-h joining rule."""
    df = df.dropna(subset=[start, stop]).sort_values([key, start])
    out = {}
    for k, g in df.groupby(key):
        best, cs, ce = 0.0, None, None
        for st, sp in zip(g[start], g[stop]):
            if cs is not None and st - ce <= M.COURSE_GAP:
                ce = max(ce, sp)
                continue
            if cs is not None:
                best = max(best, ce - cs)
            cs, ce = st, sp
        out[k] = max(best, ce - cs)
    return pd.Series(out)


def bins(title, s, base):
    c = pd.cut(s, [-np.inf, 24, 48, 72, 120, np.inf], right=False,
               labels=["under 24 h", "24-48 h", "48-72 h", "72-120 h", "120 h or more"]).value_counts(sort=False)
    print(f"  {title} (n = {n(len(s))})")
    for k, v in c.items():
        print(f"    {k:>14}: {n(v):>8}  {pct(v, base):>6}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    root = Path(ap.parse_args().root)
    t0 = pd.Timestamp("2000-01-01")
    hours = lambda s: (pd.to_datetime(s) - t0).dt.total_seconds() / 3600   # noqa: E731

    stays = M.read(root, "icu/icustays", ["subject_id", "hadm_id", "stay_id", "intime", "outtime"])
    stays = stays.rename(columns={"stay_id": "stay"})
    stays["intime"], stays["outtime"] = pd.to_datetime(stays.intime), pd.to_datetime(stays.outtime)
    stays = stays[stays.intime.notna() & stays.outtime.notna() & (stays.outtime > stays.intime)]
    icu_hadm = set(stays.hadm_id)

    mb = M.read(root, "hosp/microbiologyevents", ["hadm_id", "chartdate", "charttime", "spec_type_desc"],
                lambda c: c[c.spec_type_desc.fillna("").str.upper().str.contains("BLOOD CULTURE")
                            & c.hadm_id.isin(icu_hadm)])
    mb["time"] = mb.charttime.fillna(mb.chartdate)
    bc_hadm = set(mb.hadm_id)

    rx = M.read(root, "hosp/prescriptions", ["hadm_id", "pharmacy_id", "starttime", "stoptime", "drug", "route"],
                lambda c: c[c.drug.fillna("").str.lower().str.contains(ABX) & c.hadm_id.isin(icu_hadm)])
    route = rx.drop_duplicates("pharmacy_id").set_index("pharmacy_id").route
    iv = rx[rx.route.fillna("").str.upper().str.startswith("IV")].copy()
    iv["a"], iv["b"] = hours(iv.starttime), hours(iv.stoptime)

    seen = set()   # admissions with any administration record: emar does not cover every admission

    def emar_filter(c):
        seen.update(c.hadm_id.dropna().unique())
        return c[c.medication.fillna("").str.lower().str.contains(ABX) & c.hadm_id.isin(icu_hadm)]

    em = M.read(root, "hosp/emar", ["hadm_id", "pharmacy_id", "charttime", "medication", "event_txt"], emar_filter)
    print("\n== antibiotic administration records (emar), ICU admissions, by event")
    for k, v in em.event_txt.fillna("(blank)").str.strip().value_counts().head(12).items():
        print(f"    {k[:34]:>34}: {n(v):>10}")
    em = em[em.event_txt.fillna("").str.strip().isin(GIVEN)].copy()
    em["route"] = em.pharmacy_id.map(route).fillna("").str.upper()
    print(f"  doses given {n(len(em))}: IV {pct(em.route.str.startswith('IV').sum(), len(em))}, "
          f"no linked route {pct((em.route == '').sum(), len(em))}")
    em["t"] = hours(em.charttime)

    print(f"\n== ICU admissions with a blood culture: {n(len(bc_hadm))}; with any emar record "
          f"{n(len(bc_hadm & seen))} ({pct(len(bc_hadm & seen), len(bc_hadm))})")
    print("  (comparisons below use only these, so both sources could record a course)")
    bc_hadm = bc_hadm & seen
    base = len(bc_hadm)
    sets = {}
    sets["orders"] = longest(iv[iv.hadm_id.isin(bc_hadm)], "hadm_id", "a", "b")
    for label, mask in [("emar_iv", em.route.str.startswith("IV")),
                        ("emar_iv_or_unknown", em.route.str.startswith("IV") | (em.route == ""))]:
        d = em[mask & em.hadm_id.isin(bc_hadm)]
        sets[label] = longest(d.assign(t2=d.t), "hadm_id", "t", "t2")
    for label, s in sets.items():
        print(f"  {label}: any IV antibiotic {n(len(s))} ({pct(len(s), base)}); course of 72 h or more "
              f"{n((s >= M.COURSE_MIN).sum())} ({pct((s >= M.COURSE_MIN).sum(), base)})")
        bins(f"longest course, {label}", s, base)
    o = set(sets["orders"][sets["orders"] >= M.COURSE_MIN].index)
    e = set(sets["emar_iv"][sets["emar_iv"] >= M.COURSE_MIN].index)
    print(f"  72-h course by orders and by administrations: {n(len(o & e))}; orders only {n(len(o - e))}; "
          f"administrations only {n(len(e - o))}")

    # suspected infection per ICU stay with each source, as the extractor computes it
    cultures = M.to_stays(mb.dropna(subset=["hadm_id"]), stays, "hadm_id", "time", lo=-S3.ABX_AFTER_CULTURE)
    out = {}
    crs = S3.courses(iv, "hadm_id", "a", "b", M.COURSE_GAP, M.COURSE_MIN)
    crs["starttime"] = t0 + pd.to_timedelta(crs.t, unit="h")
    out["orders"] = S3.suspicion_times(cultures, M.to_stays(crs.drop(columns="t"), stays, "hadm_id", "starttime",
                                                            lo=-S3.ABX_AFTER_CULTURE))
    d = em[em.route.str.startswith("IV")].assign(t2=lambda x: x.t)
    crs = S3.courses(d, "hadm_id", "t", "t2", M.COURSE_GAP, M.COURSE_MIN)
    crs["starttime"] = t0 + pd.to_timedelta(crs.t, unit="h")
    out["emar_iv"] = S3.suspicion_times(cultures, M.to_stays(crs.drop(columns="t"), stays, "hadm_id", "starttime",
                                                             lo=-S3.ABX_AFTER_CULTURE))
    cov = set(stays[stays.hadm_id.isin(seen)].stay)
    out = {k: s[s.index.isin(cov)] for k, s in out.items()}
    N = len(cov)
    print(f"\n== suspected infection (Challenge definition), {n(N)} ICU stays in admissions with emar records")
    for k, s in out.items():
        print(f"  from {k}: {n(len(s))} ({pct(len(s), N)})")
    a, b = set(out["orders"].index), set(out["emar_iv"].index)
    print(f"  both {n(len(a & b))}; orders only {n(len(a - b))}; administrations only {n(len(b - a))}")
    both = sorted(a & b)
    dt = out["emar_iv"].reindex(both) - out["orders"].reindex(both)
    if len(both) >= 10:
        print(f"  where both: administration-based suspicion minus order-based, median {dt.median():.1f} h "
              f"(IQR {dt.quantile(.25):.1f} to {dt.quantile(.75):.1f})")


if __name__ == "__main__":
    main()
