"""MIMIC-IV -> hourly Sepsis-3 labels per ICU stay (WP1), using the shared rules in sepsis3.py.

Inputs (MIMIC-IV v2.2 layout; the open demo by default):
    icu/icustays, icu/chartevents, icu/inputevents, icu/outputevents, icu/procedureevents,
    hosp/labevents, hosp/microbiologyevents, hosp/prescriptions
Hours are counted from ICU admission (hour h covers [h, h+1)). Each SOFA component is scored from
the worst value in the hour; events up to 24 h before admission count towards hour 0, so the first
hours have a baseline. Large tables are read in chunks and filtered by item, so the same code runs
on the full database.

Choices (documented in notes/sepsis_labels.md):
  - cultures: --definition relaxed (default): every specimen except screening tests ("SCREEN" in
    the type); challenge: blood cultures only. Time = charttime, or chartdate when only a date
  - antibiotics: prescriptions of a systemic antibacterial (list below). relaxed: any route except
    topical, eye, ear and inhaled, time = order start; challenge: IV routes only, overlapping orders
    or ones less than COURSE_GAP h apart form one course, only courses of at least 72 h count
    (the Challenge's "72 consecutive hours"), time = course start
  - PaO2/FiO2: arterial pO2 (lab 50821) with the latest FiO2 (chart 223835 or lab 50816) in the
    previous 4 h; ventilation from procedureevents 225792 (invasive ventilation)
  - GCS: eye + verbal + motor charted together; not scored when the verbal score is "No Response-ETT"
  - MAP: lowest of 220052, 220181, 225312 in the hour
  - vasopressors: norepinephrine, epinephrine, dopamine, dobutamine rates in mcg/kg/min (mcg/min
    divided by the recorded weight)
  - urine: sum of urine outputs over the previous 24 h, from hour 23 onwards

Run from the repository root:
    python q1_journal_plan/code/mimiciv_sepsis.py [--definition relaxed|challenge]
        [--root data/mimiciv_demo/mimic-iv-clinical-database-demo-2.2] [--out outputs/sepsis_q1/mimiciv_demo]
Writes <out>_<definition>_stays.csv (one row per stay, with the cohort decision) and
<out>_<definition>_hourly.csv.gz (one row per stay-hour, Challenge cohort only).
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sepsis3 as S3  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = REPO / "data/mimiciv_demo/mimic-iv-clinical-database-demo-2.2"

ANTIBIOTICS = [
    "amikacin", "amoxicillin", "ampicillin", "azithromycin", "aztreonam", "cefazolin", "cefepime",
    "cefotaxime", "cefotetan", "cefoxitin", "cefpodoxime", "ceftaroline", "ceftazidime",
    "ceftriaxone", "cefuroxime", "cephalexin", "ciprofloxacin", "clarithromycin", "clindamycin",
    "colistin", "daptomycin", "doxycycline", "ertapenem", "erythromycin", "gentamicin", "imipenem",
    "levofloxacin", "linezolid", "meropenem", "metronidazole", "minocycline", "moxifloxacin",
    "nafcillin", "nitrofurantoin", "oxacillin", "penicillin", "piperacillin", "polymyxin",
    "rifampin", "sulfamethoxazole", "tetracycline", "tigecycline", "tobramycin", "vancomycin",
]
COURSE_GAP, COURSE_MIN = 24, 72   # hours
EXCLUDED_ROUTES = {"TP", "OU", "OS", "OD", "AU", "AS", "AD", "IH", "NEB", "EX-VIVO", "DIALYS", "BU"}
MAP_ITEMS = [220052, 220181, 225312]
GCS_ITEMS = {220739: "eye", 223900: "verbal", 223901: "motor"}
FIO2_CHART = 223835
PRESSORS = {221906: "norepi", 221289: "epi", 221662: "dopa", 221653: "dobu"}
URINE_ITEMS = [226559, 226560, 226561, 226584, 226563, 226564, 226565, 226567, 226557, 226558]
VENT_ITEM = 225792
LABS = {50821: "pao2", 50816: "fio2_lab", 51265: "platelets", 50885: "bilirubin", 50912: "creatinine"}


def read(root, name, usecols, chunks=False, keep=None):
    """Read a table; with chunks, keep only rows whose itemid is in `keep`."""
    path = root / f"{name}.csv.gz"
    if not chunks:
        return pd.read_csv(path, usecols=usecols)
    parts = [c[c.itemid.isin(keep)] for c in pd.read_csv(path, usecols=usecols, chunksize=2_000_000)]
    return pd.concat(parts, ignore_index=True)


def to_stays(df, stays, key, time_col, lo=-24.0):
    """Attach events to stays through `key` (hadm_id or subject_id); t in hours from intime.
    Keeps events from `lo` hours before admission to discharge."""
    m = df.merge(stays[[key, "stay", "intime", "outtime"]], on=key)
    t = pd.to_datetime(m[time_col])
    m["t"] = (t - m.intime).dt.total_seconds() / 3600
    m = m[(m.t >= lo) & (t <= m.outtime)]
    return m.drop(columns=["intime", "outtime"])


def hour_of(t):
    return np.maximum(np.floor(t), 0).astype(int)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--out", default=str(REPO / "outputs/sepsis_q1/mimiciv_demo"))
    ap.add_argument("--definition", choices=["relaxed", "challenge"], default="relaxed")
    a = ap.parse_args()
    root = Path(a.root)
    out = Path(f"{a.out}_{a.definition}")
    relaxed = a.definition == "relaxed"
    out.parent.mkdir(parents=True, exist_ok=True)

    stays = read(root, "icu/icustays", ["subject_id", "hadm_id", "stay_id", "intime", "outtime"])
    stays = stays.rename(columns={"stay_id": "stay"})
    stays["intime"] = pd.to_datetime(stays.intime)
    stays["outtime"] = pd.to_datetime(stays.outtime)
    stays["hours"] = np.ceil((stays.outtime - stays.intime).dt.total_seconds() / 3600).astype(int)
    print(f"{len(stays)} ICU stays")

    # --- suspected infection ---
    mb = read(root, "hosp/microbiologyevents", ["hadm_id", "charttime", "chartdate", "spec_type_desc"])
    spec = mb.spec_type_desc.fillna("").str.upper()
    mb = mb[~spec.str.contains("SCREEN")] if relaxed else mb[spec.str.contains("BLOOD CULTURE")]
    mb["time"] = mb.charttime.fillna(mb.chartdate)
    cultures = to_stays(mb.dropna(subset=["hadm_id"]), stays, "hadm_id", "time", lo=-S3.ABX_AFTER_CULTURE)
    rx = read(root, "hosp/prescriptions", ["hadm_id", "starttime", "stoptime", "drug", "route"])
    drug = rx.drug.fillna("").str.lower()
    route = rx.route.fillna("").str.upper()
    is_abx = drug.str.contains("|".join(ANTIBIOTICS)) & (~route.isin(EXCLUDED_ROUTES) if relaxed else route.str.startswith("IV"))
    rx = rx[is_abx].dropna(subset=["hadm_id"]).copy()
    t0 = pd.Timestamp("2000-01-01")
    rx["a"] = (pd.to_datetime(rx.starttime) - t0).dt.total_seconds() / 3600
    rx["b"] = (pd.to_datetime(rx.stoptime) - t0).dt.total_seconds() / 3600
    crs = S3.courses(rx, "hadm_id", "a", "b", COURSE_GAP, COURSE_MIN)
    crs["starttime"] = t0 + pd.to_timedelta(crs.t, unit="h")
    orders = rx.dropna(subset=["starttime"])[["hadm_id", "starttime"]]
    abx = to_stays(orders if relaxed else crs.drop(columns="t"), stays, "hadm_id", "starttime",
                   lo=-S3.ABX_AFTER_CULTURE)
    t_susp = S3.suspicion_times(cultures, abx)

    # --- hourly grid ---
    grid = pd.DataFrame([(s, h) for s, n in zip(stays.stay, stays.hours) for h in range(max(n, 1))],
                        columns=["stay", "hour"])

    def hourly(ev, col, how):
        ev = ev.assign(hour=hour_of(ev.t))
        return ev.groupby(["stay", "hour"])[col].agg(how).rename(col)

    labs = read(root, "hosp/labevents", ["subject_id", "charttime", "itemid", "valuenum"], chunks=True, keep=list(LABS))
    labs = to_stays(labs.dropna(subset=["valuenum"]), stays, "subject_id", "charttime")
    labs["name"] = labs.itemid.map(LABS)
    ch_items = MAP_ITEMS + list(GCS_ITEMS) + [FIO2_CHART]
    ch = read(root, "icu/chartevents", ["stay_id", "charttime", "itemid", "value", "valuenum"], chunks=True, keep=ch_items)
    ch = ch.rename(columns={"stay_id": "stay"}).merge(stays[["stay", "intime"]], on="stay")
    ch["t"] = (pd.to_datetime(ch.charttime) - ch.intime).dt.total_seconds() / 3600
    ch = ch[ch.t >= -24]

    feats = {}
    for name, how in [("platelets", "min"), ("bilirubin", "max"), ("creatinine", "max")]:
        feats[name] = hourly(labs[labs.name == name].rename(columns={"valuenum": name}), name, how)
    feats["map"] = hourly(ch[ch.itemid.isin(MAP_ITEMS)].rename(columns={"valuenum": "map"}), "map", "min")

    # GCS: the three parts charted at the same time
    g = ch[ch.itemid.isin(list(GCS_ITEMS))].copy()
    g["part"] = g.itemid.map(GCS_ITEMS)
    ett = g[(g.part == "verbal") & g.value.fillna("").str.contains("ETT")][["stay", "charttime"]].drop_duplicates()
    g = g.pivot_table(index=["stay", "charttime", "t"], columns="part", values="valuenum", aggfunc="min").reset_index()
    g["gcs"] = g[["eye", "verbal", "motor"]].sum(axis=1, min_count=3)
    g = g.merge(ett.assign(ett=True), on=["stay", "charttime"], how="left")
    g.loc[g.ett.notna(), "gcs"] = np.nan
    feats["gcs"] = hourly(g.dropna(subset=["gcs"]), "gcs", "min")

    # PaO2 / FiO2: latest FiO2 within the previous 4 h
    fio2 = pd.concat([ch[ch.itemid == FIO2_CHART][["stay", "t", "valuenum"]],
                      labs[labs.name == "fio2_lab"][["stay", "t", "valuenum"]]]).rename(columns={"valuenum": "fio2"})
    fio2["fio2"] = np.where(fio2.fio2 > 1, fio2.fio2 / 100, fio2.fio2)
    fio2 = fio2[(fio2.fio2 >= 0.21) & (fio2.fio2 <= 1)].sort_values("t")
    pao2 = labs[labs.name == "pao2"][["stay", "t", "valuenum"]].rename(columns={"valuenum": "pao2"}).sort_values("t")
    pf = pd.merge_asof(pao2, fio2, on="t", by="stay", direction="backward", tolerance=4.0).dropna(subset=["fio2"])
    pf["pf"] = pf.pao2 / pf.fio2
    feats["pf"] = hourly(pf, "pf", "min")

    # ventilation and vasopressors: expand intervals to the hours they cover
    def interval_hours(df, value=None):
        df = df.merge(stays[["stay", "intime", "hours"]], on="stay")
        h0 = hour_of((pd.to_datetime(df.starttime) - df.intime).dt.total_seconds() / 3600)
        h1 = hour_of((pd.to_datetime(df.endtime) - df.intime).dt.total_seconds() / 3600)
        rows = [(s, h, v) for s, a_, b_, n, v in zip(df.stay, h0, h1, df.hours,
                                                     df[value] if value else np.ones(len(df)))
                for h in range(a_, min(b_, n - 1) + 1)]
        return pd.DataFrame(rows, columns=["stay", "hour", "v"])

    pe = read(root, "icu/procedureevents", ["stay_id", "starttime", "endtime", "itemid"])
    vent = interval_hours(pe[pe.itemid == VENT_ITEM].rename(columns={"stay_id": "stay"}))
    feats["ventilated"] = vent.groupby(["stay", "hour"]).v.max().astype(bool).rename("ventilated")

    ie = read(root, "icu/inputevents", ["stay_id", "starttime", "endtime", "itemid", "rate", "rateuom", "patientweight"],
              chunks=True, keep=list(PRESSORS)).rename(columns={"stay_id": "stay"})
    ie["rate_kg"] = np.where(ie.rateuom == "mcg/kg/min", ie.rate,
                             np.where(ie.rateuom == "mcg/min", ie.rate / ie.patientweight, np.nan))
    for item, name in PRESSORS.items():
        x = interval_hours(ie[ie.itemid == item].dropna(subset=["rate_kg"]), "rate_kg")
        feats[name] = x.groupby(["stay", "hour"]).v.max().rename(name)

    oe = read(root, "icu/outputevents", ["stay_id", "charttime", "itemid", "value"], chunks=True, keep=URINE_ITEMS)
    oe = oe.rename(columns={"stay_id": "stay"}).merge(stays[["stay", "intime"]], on="stay")
    oe["t"] = (pd.to_datetime(oe.charttime) - oe.intime).dt.total_seconds() / 3600
    feats["urine"] = hourly(oe[oe.t >= 0].rename(columns={"value": "urine"}), "urine", "sum")

    h = grid.set_index(["stay", "hour"]).join(pd.DataFrame(feats)).reset_index().sort_values(["stay", "hour"])
    h["ventilated"] = h.ventilated.eq(True)
    h["urine"] = h.urine.fillna(0)
    urine24 = h.groupby("stay").urine.rolling(24, min_periods=24).sum().reset_index(level=0, drop=True)
    h["urine_24h"] = urine24.reindex(h.index)
    h = h.reset_index(drop=True)

    h, onset = S3.score_and_label(h, t_susp)

    st = stays[["stay", "subject_id", "hadm_id", "hours"]].set_index("stay")
    st["t_suspicion"] = t_susp
    st["onset"] = onset
    st["max_sofa"] = h.groupby("stay").sofa.max()
    hc, reasons = S3.challenge_cohort(h, onset)
    st["excluded"] = pd.Series(reasons)
    st["septic"] = st.onset.notna() & st.excluded.isna()
    st.to_csv(f"{out}_stays.csv")
    hc.to_csv(f"{out}_hourly.csv.gz", index=False)

    S3.summary(st, hc)

if __name__ == "__main__":
    main()
