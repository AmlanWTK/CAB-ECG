"""MIMIC-IV -> hourly Sepsis-3 labels per ICU stay (WP1), using the shared rules in sepsis3.py.

Inputs (MIMIC-IV v2.2 layout; the open demo by default):
    icu/icustays, icu/chartevents, icu/inputevents, icu/outputevents, icu/procedureevents,
    hosp/labevents, hosp/microbiologyevents, hosp/prescriptions
Hours are counted from ICU admission (hour h covers [h, h+1)). Each SOFA component is scored from
the worst value in the hour; events up to 24 h before admission count towards hour 0, so the first
hours have a baseline. Large tables are read once each, in chunks, filtered by item and reduced to
hourly values chunk by chunk (bigtable.py), so the same code runs on the full database in 16 GB;
finished passes are kept in <out>_cache/ and reused (delete it after changing the extraction).

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
Writes <out>_<definition>_stays.csv (one row per stay, with the cohort decision),
<out>_<definition>_hourly.csv.gz (one row per stay-hour, Challenge cohort only) and
<out>_<definition>_challenge.pkl (the same hours in the Challenge format, challenge_format.py).
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bigtable as BT  # noqa: E402
import challenge_format as CF  # noqa: E402
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
CHAL_DTYPE = np.float32   # hourly sums for the Challenge table: half the memory of float64


def read(root, name, usecols, filt=None):
    """A table, filtered chunk by chunk (bigtable.read)."""
    return BT.read(root / f"{name}.csv.gz", usecols, filt)


def items(keep):
    return lambda c: c[c.itemid.isin(keep)]


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


def chal_vars(mapping):
    """Variable names after challenge_format.clean (Temp_F becomes Temp)."""
    return list(dict.fromkeys("Temp" if v == "Temp_F" else v for v in mapping.values()))


def pass_chart(root, stays, grid):
    """One pass over chartevents: hourly lowest MAP (SOFA); GCS parts and chart FiO2 with their
    times; hourly means of the Challenge vitals."""
    intime = stays.set_index("stay").intime
    keep = set(MAP_ITEMS) | set(GCS_ITEMS) | {FIO2_CHART} | set(CF.MIMIC_CHART)
    sofa = BT.HourlyAgg("min", grid, ["map"])
    chal = BT.HourlyAgg("mean", grid, chal_vars(CF.MIMIC_CHART), CHAL_DTYPE)
    gcs, fio2 = [], []
    for c in BT.chunks(root / "icu/chartevents.csv.gz", ["stay_id", "charttime", "itemid", "value", "valuenum"],
                       items(keep)):
        c = c[c.stay_id.isin(intime.index)]
        t = (pd.to_datetime(c.charttime) - c.stay_id.map(intime)).dt.total_seconds() / 3600
        w = t >= -24
        m = w & c.itemid.isin(MAP_ITEMS)
        sofa.add(pd.DataFrame({"stay": c.stay_id[m], "hour": hour_of(t[m]), "var": "map", "value": c.valuenum[m]}))
        g = w & c.itemid.isin(list(GCS_ITEMS))
        gcs.append(pd.DataFrame({"stay": c.stay_id[g], "t": t[g], "part": c.itemid[g].map(GCS_ITEMS),
                                 "value": c.valuenum[g].astype(np.float32),
                                 "ett": (c.itemid[g] == 223900) & c.value[g].astype(str).str.contains("ETT")}))
        f = w & (c.itemid == FIO2_CHART)
        fio2.append(pd.DataFrame({"stay": c.stay_id[f], "t": t[f], "fio2": c.valuenum[f]}))
        v = c.itemid.isin(list(CF.MIMIC_CHART))
        chal.add(CF.long_events(c.stay_id[v], t[v], c.itemid[v].map(CF.MIMIC_CHART), c.valuenum[v]))
    return sofa, chal, pd.concat(gcs, ignore_index=True), pd.concat(fio2, ignore_index=True)


def pass_lab(root, stays, grid):
    """One pass over labevents: hourly SOFA labs, PaO2 and lab FiO2 with their times, and hourly
    means of the Challenge labs."""
    lo, hi = BT.HourlyAgg("min", grid, ["platelets"]), BT.HourlyAgg("max", grid, ["bilirubin", "creatinine"])
    chal, raw = BT.HourlyAgg("mean", grid, chal_vars(CF.MIMIC_LAB), CHAL_DTYPE), []
    for c in BT.chunks(root / "hosp/labevents.csv.gz", ["subject_id", "charttime", "itemid", "valuenum"],
                       items(set(LABS) | set(CF.MIMIC_LAB))):
        s = to_stays(c[c.itemid.isin(list(LABS))].dropna(subset=["valuenum"]), stays, "subject_id", "charttime")
        ev = pd.DataFrame({"stay": s.stay, "t": s.t, "hour": hour_of(s.t), "var": s.itemid.map(LABS),
                           "value": s.valuenum})
        lo.add(ev[ev["var"] == "platelets"])
        hi.add(ev[ev["var"].isin(["bilirubin", "creatinine"])])
        raw.append(ev[ev["var"].isin(["pao2", "fio2_lab"])][["stay", "t", "var", "value"]])
        x = to_stays(c[c.itemid.isin(list(CF.MIMIC_LAB))], stays, "subject_id", "charttime", lo=0)
        chal.add(CF.long_events(x.stay, x.t, x.itemid.map(CF.MIMIC_LAB), x.valuenum))
    return lo, hi, chal, pd.concat(raw, ignore_index=True)


def pass_urine(root, stays, grid):
    intime = stays.set_index("stay").intime
    urine = BT.HourlyAgg("sum", grid, ["urine"])
    for c in BT.chunks(root / "icu/outputevents.csv.gz", ["stay_id", "charttime", "itemid", "value"],
                       items(URINE_ITEMS)):
        c = c[c.stay_id.isin(intime.index)]
        t = (pd.to_datetime(c.charttime) - c.stay_id.map(intime)).dt.total_seconds() / 3600
        k = t >= 0
        urine.add(pd.DataFrame({"stay": c.stay_id[k], "hour": hour_of(t[k]), "var": "urine", "value": c.value[k]}))
    return urine


def pass_small(root):
    abx = "|".join(ANTIBIOTICS)
    return {
        "microbiologyevents": read(root, "hosp/microbiologyevents", ["hadm_id", "charttime", "chartdate",
                                                                     "spec_type_desc"]),
        "prescriptions": read(root, "hosp/prescriptions", ["hadm_id", "starttime", "stoptime", "drug", "route"],
                              lambda c: c[c.drug.fillna("").str.lower().str.contains(abx)]),
        "procedureevents": read(root, "icu/procedureevents", ["stay_id", "starttime", "endtime", "itemid"],
                                items([VENT_ITEM])),
        "inputevents": read(root, "icu/inputevents", ["stay_id", "starttime", "endtime", "itemid", "rate",
                                                      "rateuom", "patientweight"], items(list(PRESSORS))),
    }


def export_challenge(root, stays, grid, hc, out, chal):
    """The Challenge-format hourly table (challenge_format.py) for the Challenge cohort."""
    w = CF.wide_from_hourly(chal.result(), grid)
    icu = read(root, "icu/icustays", ["stay_id", "first_careunit"]).rename(columns={"stay_id": "stay"})
    pts = read(root, "hosp/patients", ["subject_id", "gender", "anchor_age", "anchor_year"])
    adm = read(root, "hosp/admissions", ["hadm_id", "admittime"])
    demo = stays.merge(icu, on="stay").merge(pts, on="subject_id").merge(adm, on="hadm_id")
    demo["Age"] = demo.anchor_age + (demo.intime.dt.year - demo.anchor_year)
    demo["Gender"] = (demo.gender == "M").astype(int)
    demo["HospAdmTime"] = (pd.to_datetime(demo.admittime) - demo.intime).dt.total_seconds() / 3600
    demo["unit"] = demo.first_careunit.map(CF.MIMIC_UNITS).fillna("other")
    demo["site"] = "MIMIC-IV"
    df = CF.assemble(w, hc, demo[["stay", "site", "unit", "Age", "Gender", "HospAdmTime"]], "mimic")
    df.to_pickle(f"{out}_challenge.pkl")
    cov = CF.coverage(df)
    print(f"Challenge format: {len(df)} rows, {df.pid.nunique()} stays; present in rows: "
          + ", ".join(f"{v} {cov[v]:.0%}" for v in ["HR", "MAP", "Temp", "Resp", "Creatinine", "Lactate", "WBC"]))
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--out", default=str(REPO / "outputs/sepsis_q1/mimiciv_demo"))
    ap.add_argument("--definition", choices=["relaxed", "challenge"], default="relaxed")
    a = ap.parse_args()
    root = Path(a.root)
    out = Path(f"{a.out}_{a.definition}")
    cache = Path(f"{a.out}_cache")   # shared by both definitions
    relaxed = a.definition == "relaxed"
    out.parent.mkdir(parents=True, exist_ok=True)

    stays = read(root, "icu/icustays", ["subject_id", "hadm_id", "stay_id", "intime", "outtime"])
    stays = stays.rename(columns={"stay_id": "stay"})
    stays["intime"] = pd.to_datetime(stays.intime)
    stays["outtime"] = pd.to_datetime(stays.outtime)
    stays["hours"] = np.ceil((stays.outtime - stays.intime).dt.total_seconds() / 3600).astype(int)
    print(f"{len(stays)} ICU stays")
    G = BT.Grid(stays.stay, stays.hours)
    small = BT.cached(cache, "small_tables", lambda: pass_small(root))

    # --- suspected infection ---
    mb = small["microbiologyevents"]
    spec = mb.spec_type_desc.fillna("").str.upper()
    mb = mb[~spec.str.contains("SCREEN")] if relaxed else mb[spec.str.contains("BLOOD CULTURE")]
    mb["time"] = mb.charttime.fillna(mb.chartdate)
    cultures = to_stays(mb.dropna(subset=["hadm_id"]), stays, "hadm_id", "time", lo=-S3.ABX_AFTER_CULTURE)
    rx = small["prescriptions"]
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
    grid = G.frame()

    def hourly(ev, col, how):
        ev = ev.assign(hour=hour_of(ev.t))
        return ev.groupby(["stay", "hour"])[col].agg(how).rename(col)

    lab_lo, lab_hi, lab_chal, lab_raw = BT.cached(cache, "labevents", lambda: pass_lab(root, stays, G))
    feats = {"platelets": lab_lo.series("platelets"), "bilirubin": lab_hi.series("bilirubin"),
             "creatinine": lab_hi.series("creatinine")}
    ch_map, ch_chal, gcs_raw, fio2_chart = BT.cached(cache, "chartevents", lambda: pass_chart(root, stays, G))
    feats["map"] = ch_map.series("map")

    # GCS: the three parts charted at the same time (same stay and time)
    g = gcs_raw.pivot_table(index=["stay", "t"], columns="part", values="value", aggfunc="min").reset_index()
    for part in GCS_ITEMS.values():
        if part not in g:
            g[part] = np.nan
    g["gcs"] = g[["eye", "verbal", "motor"]].sum(axis=1, min_count=3)
    ett = gcs_raw[gcs_raw.ett][["stay", "t"]].drop_duplicates()
    g = g.merge(ett.assign(ett=True), on=["stay", "t"], how="left")
    g.loc[g.ett.notna(), "gcs"] = np.nan
    feats["gcs"] = hourly(g.dropna(subset=["gcs"]), "gcs", "min")

    # PaO2 / FiO2: latest FiO2 within the previous 4 h
    fio2 = pd.concat([fio2_chart, lab_raw[lab_raw["var"] == "fio2_lab"][["stay", "t", "value"]]
                      .rename(columns={"value": "fio2"})])
    fio2["fio2"] = np.where(fio2.fio2 > 1, fio2.fio2 / 100, fio2.fio2)
    fio2 = fio2[(fio2.fio2 >= 0.21) & (fio2.fio2 <= 1)].sort_values("t")
    pao2 = lab_raw[lab_raw["var"] == "pao2"][["stay", "t", "value"]].rename(columns={"value": "pao2"}).sort_values("t")
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

    pe = small["procedureevents"]
    vent = interval_hours(pe[pe.itemid == VENT_ITEM].rename(columns={"stay_id": "stay"}))
    feats["ventilated"] = vent.groupby(["stay", "hour"]).v.max().astype(bool).rename("ventilated")

    ie = small["inputevents"].rename(columns={"stay_id": "stay"})
    ie["rate_kg"] = np.where(ie.rateuom == "mcg/kg/min", ie.rate,
                             np.where(ie.rateuom == "mcg/min", ie.rate / ie.patientweight, np.nan))
    for item, name in PRESSORS.items():
        x = interval_hours(ie[ie.itemid == item].dropna(subset=["rate_kg"]), "rate_kg")
        feats[name] = x.groupby(["stay", "hour"]).v.max().rename(name)

    feats["urine"] = BT.cached(cache, "outputevents", lambda: pass_urine(root, stays, G)).series("urine")

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
    export_challenge(root, stays, grid, hc, out, BT.HourlyAgg.merged([ch_chal, lab_chal]))

if __name__ == "__main__":
    main()
