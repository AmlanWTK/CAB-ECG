"""eICU-CRD -> hourly Sepsis-3 labels per ICU stay (WP1), using the shared rules in sepsis3.py.

Inputs (eICU-CRD v2.0 layout; the open demo by default): patient, microLab, medication, lab,
respiratoryCare, respiratoryCharting, vitalPeriodic, vitalAperiodic, nurseCharting, infusiondrug,
intakeOutput. eICU times are minutes from unit admission; hour h covers [h, h+1). Each SOFA
component is scored from the worst value in the hour; events up to 24 h before admission count
towards hour 0. Large tables are read in chunks.

Choices (notes/sepsis_labels.md), matched to the MIMIC-IV extractor where the data allow:
  - cultures: from microLab or from culture orders in the treatment table (eICU fills microLab at
    few hospitals: 12 of 186 in the demo). --definition relaxed (default): any site; challenge: blood
    only. Time = culturetakenoffset or treatmentoffset
  - antibiotics: medication rows with a systemic antibacterial in the drug name (list shared with
    mimiciv_sepsis.py), not cancelled. relaxed: any route except topical, eye, ear, vaginal and
    inhaled, plus "antibacterials" in the treatment table; time = order start. challenge: IV routes
    only, courses as in MIMIC-IV (joined if less than 24 h apart, at least 72 h long)
  - hospital recording check: a hospital is "adequate" if antibiotics are recorded in at least
    MIN_ABX_SHARE of its stays and cultures in at least MIN_CULTURE_SHARE (provisional thresholds,
    to be fixed in the analysis plan before the full run; recording rates, not outcomes)
  - PaO2/FiO2: lab paO2 with the latest FiO2 (lab or respiratory charting) in the previous 4 h;
    ventilation from respiratoryCare vent start/end
  - GCS: nurseCharting "GCS Total" (text such as "Unable to score due to medication" not scored)
  - MAP: lowest of invasive (vitalPeriodic systemicmean) and non-invasive (vitalAperiodic) in the hour
  - vasopressors from infusiondrug: rates in mcg/kg/min, or mcg/min divided by the patient's weight;
    where the unit is not given (ml/hr or blank) the drug counts as given at an unknown low rate
    (SOFA 3 for norepinephrine or epinephrine, 2 for dopamine or dobutamine)
  - urine: intakeOutput output rows labelled as urine, 24 h sum from hour 23

Run from the repository root:
    python q1_journal_plan/code/eicu_sepsis.py [--definition relaxed|challenge]
        [--root data/eicu_demo/eicu-crd-demo-2.0.1] [--out outputs/sepsis_q1/eicu_demo]
Writes <out>_<definition>_stays.csv (one row per stay, with hospital, recording check and cohort
decision), <out>_<definition>_hospitals.csv, <out>_<definition>_hourly.csv.gz (one row per
stay-hour, Challenge cohort only) and <out>_<definition>_challenge.pkl (the same hours in the
Challenge format, challenge_format.py; site = eICU hospital id; all hospitals, filter with the
hospitals file).
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import challenge_format as CF  # noqa: E402
import sepsis3 as S3  # noqa: E402
from mimiciv_sepsis import ANTIBIOTICS, COURSE_GAP, COURSE_MIN, hour_of  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = REPO / "data/eicu_demo/eicu-crd-demo-2.0.1"
LABS = {"paO2": "pao2", "FiO2": "fio2", "platelets x 1000": "platelets", "total bilirubin": "bilirubin",
        "creatinine": "creatinine"}
PRESSORS = {"norepinephrine": "norepi", "epinephrine": "epi", "dopamine": "dopa", "dobutamine": "dobu"}
UNKNOWN_RATE = 0.01   # given, rate unknown: the lowest SOFA tier for the drug
EXCLUDED_ROUTE_WORDS = ["TOP", "OPHTH", "EYE", "OTIC", "EAR", "INHAL", "NEB", "VAG"]
MIN_ABX_SHARE, MIN_CULTURE_SHARE = 0.20, 0.10   # provisional


def read(root, name, usecols, filt=None):
    path = root / f"{name}.csv.gz"
    parts = []
    for c in pd.read_csv(path, usecols=usecols, chunksize=2_000_000, low_memory=False):
        parts.append(filt(c) if filt else c)
    return pd.concat(parts, ignore_index=True)


def export_challenge(root, stays, grid, hc, out):
    """The Challenge-format hourly table (challenge_format.py) for the Challenge cohort."""
    keep = set(stays.stay)
    parts = []
    for table, cols in [("vitalPeriodic", CF.EICU_PERIODIC), ("vitalAperiodic", CF.EICU_APERIODIC)]:
        v = read(root, table, ["patientunitstayid", "observationoffset"] + list(cols))
        v = v[v.patientunitstayid.isin(keep)].melt(id_vars=["patientunitstayid", "observationoffset"],
                                                   var_name="col", value_name="value")
        parts.append(pd.DataFrame({"stay": v.patientunitstayid, "t": v.observationoffset / 60,
                                   "var": v.col.map(cols), "value": v.value}))
    tc = read(root, "nurseCharting", ["patientunitstayid", "nursingchartoffset", "nursingchartcelltypevalname",
                                      "nursingchartvalue"], lambda c: c[c.nursingchartcelltypevalname == "Temperature (C)"])
    tv = pd.to_numeric(tc.nursingchartvalue, errors="coerce")
    tc = tc[tv.between(25, 45)]  # temperature is mostly charted by nurses in eICU; drop impossible values
    parts.append(pd.DataFrame({"stay": tc.patientunitstayid, "t": tc.nursingchartoffset / 60, "var": "Temp",
                               "value": pd.to_numeric(tc.nursingchartvalue, errors="coerce")}))
    lab = read(root, "lab", ["patientunitstayid", "labname", "labresultoffset", "labresult"],
               lambda c: c[c.labname.isin(list(CF.EICU_LAB))])
    parts.append(pd.DataFrame({"stay": lab.patientunitstayid, "t": lab.labresultoffset / 60,
                               "var": lab.labname.map(CF.EICU_LAB), "value": lab.labresult}))
    w = CF.wide(pd.concat(parts, ignore_index=True), grid)

    pt = read(root, "patient", ["patientunitstayid", "hospitalid", "age", "gender", "unittype", "hospitaladmitoffset"])
    demo = pd.DataFrame({"stay": pt.patientunitstayid, "site": pt.hospitalid.astype(str),
                         "unit": pt.unittype.map(CF.EICU_UNITS).fillna("other"),
                         "Age": pd.to_numeric(pt.age.replace("> 89", "90"), errors="coerce"),
                         "Gender": np.where(pt.gender == "Male", 1, np.where(pt.gender == "Female", 0, np.nan)),
                         "HospAdmTime": pt.hospitaladmitoffset / 60})
    df = CF.assemble(w, hc, demo, "eicu")
    df.to_pickle(f"{out}_challenge.pkl")
    cov = CF.coverage(df)
    print(f"Challenge format: {len(df)} rows, {df.pid.nunique()} stays, {df.site.nunique()} hospitals; present in rows: "
          + ", ".join(f"{v} {cov[v]:.0%}" for v in ["HR", "MAP", "Temp", "Resp", "Creatinine", "Lactate", "WBC"]))
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--out", default=str(REPO / "outputs/sepsis_q1/eicu_demo"))
    ap.add_argument("--definition", choices=["relaxed", "challenge"], default="relaxed")
    a = ap.parse_args()
    root, out = Path(a.root), Path(f"{a.out}_{a.definition}")
    relaxed = a.definition == "relaxed"
    out.parent.mkdir(parents=True, exist_ok=True)

    pt = read(root, "patient", ["patientunitstayid", "hospitalid", "unitdischargeoffset", "admissionweight"])
    stays = pt.rename(columns={"patientunitstayid": "stay"})
    stays["hours"] = np.ceil(stays.unitdischargeoffset / 60).clip(lower=1).astype(int)
    keep = set(stays.stay)
    print(f"{len(stays)} ICU stays, {stays.hospitalid.nunique()} hospitals")

    def in_window(df, t_col, lo=-24.0):
        df = df.rename(columns={"patientunitstayid": "stay"})
        df = df[df.stay.isin(keep)].copy()
        df["t"] = df[t_col] / 60
        df = df.merge(stays[["stay", "hours"]], on="stay")
        return df[(df.t >= lo) & (df.t <= df.hours)].drop(columns="hours")

    # --- suspected infection ---
    mb = read(root, "microLab", ["patientunitstayid", "culturetakenoffset", "culturesite"])
    if not relaxed:
        mb = mb[mb.culturesite.fillna("").str.contains("Blood")]
    mb = mb.rename(columns={"culturetakenoffset": "offset"})
    tr_all = read(root, "treatment", ["patientunitstayid", "treatmentoffset", "treatmentstring"])
    ts = tr_all.treatmentstring.fillna("").str.lower()
    tr = tr_all[ts.str.contains("cultures") & (ts.str.contains("blood") | relaxed)]
    tr = tr.rename(columns={"treatmentoffset": "offset"})
    cultures = in_window(pd.concat([mb[["patientunitstayid", "offset"]], tr[["patientunitstayid", "offset"]]]),
                         "offset", lo=-S3.ABX_AFTER_CULTURE)
    md = read(root, "medication", ["patientunitstayid", "drugname", "routeadmin", "drugordercancelled",
                                   "drugstartoffset", "drugstopoffset"])
    route = md.routeadmin.fillna("").str.strip().str.upper()
    is_abx = (md.drugname.fillna("").str.lower().str.contains("|".join(ANTIBIOTICS))
              & (md.drugordercancelled.fillna("No") != "Yes"))
    if relaxed:
        md = md[is_abx & ~route.str.contains("|".join(EXCLUDED_ROUTE_WORDS))]
        abx_tr = tr_all[ts.str.contains("antibacterials")]
        ab = pd.concat([pd.DataFrame({"stay": md.patientunitstayid, "t": md.drugstartoffset / 60}),
                        pd.DataFrame({"stay": abx_tr.patientunitstayid, "t": abx_tr.treatmentoffset / 60})])
    else:
        md = md[is_abx & (route.str.startswith("IV") | route.str.startswith("INTRAVEN"))
                & (md.drugstopoffset > md.drugstartoffset)].rename(columns={"patientunitstayid": "stay"})
        md["a"], md["b"] = md.drugstartoffset / 60, md.drugstopoffset / 60
        ab = S3.courses(md, "stay", "a", "b", COURSE_GAP, COURSE_MIN)
    ab = ab.merge(stays[["stay", "hours"]], on="stay")
    abx = ab[(ab.t >= -S3.ABX_AFTER_CULTURE) & (ab.t <= ab.hours)]
    t_susp = S3.suspicion_times(cultures, abx)

    # --- hourly features ---
    grid = pd.DataFrame([(s, h) for s, n in zip(stays.stay, stays.hours) for h in range(n)],
                        columns=["stay", "hour"])

    def hourly(ev, col, how):
        ev = ev.assign(hour=hour_of(ev.t))
        return ev.groupby(["stay", "hour"])[col].agg(how).rename(col)

    lab = read(root, "lab", ["patientunitstayid", "labname", "labresultoffset", "labresult"],
               lambda c: c[c.labname.isin(list(LABS))])
    lab = in_window(lab.dropna(subset=["labresult"]), "labresultoffset")
    lab["name"] = lab.labname.map(LABS)
    feats = {}
    for name, how in [("platelets", "min"), ("bilirubin", "max"), ("creatinine", "max")]:
        feats[name] = hourly(lab[lab.name == name].rename(columns={"labresult": name}), name, how)

    rch = read(root, "respiratoryCharting", ["patientunitstayid", "respchartoffset", "respchartvaluelabel",
                                             "respchartvalue"], lambda c: c[c.respchartvaluelabel == "FiO2"])
    rch["fio2"] = pd.to_numeric(rch.respchartvalue, errors="coerce")
    rch = in_window(rch.dropna(subset=["fio2"]), "respchartoffset")
    fio2 = pd.concat([lab[lab.name == "fio2"][["stay", "t", "labresult"]].rename(columns={"labresult": "fio2"}),
                      rch[["stay", "t", "fio2"]]])
    fio2["fio2"] = np.where(fio2.fio2 > 1, fio2.fio2 / 100, fio2.fio2)
    fio2 = fio2[(fio2.fio2 >= 0.21) & (fio2.fio2 <= 1)].sort_values("t")
    pao2 = lab[lab.name == "pao2"][["stay", "t", "labresult"]].rename(columns={"labresult": "pao2"}).sort_values("t")
    pf = pd.merge_asof(pao2, fio2, on="t", by="stay", direction="backward", tolerance=4.0).dropna(subset=["fio2"])
    pf["pf"] = pf.pao2 / pf.fio2
    feats["pf"] = hourly(pf, "pf", "min")

    rc = read(root, "respiratoryCare", ["patientunitstayid", "ventstartoffset", "ventendoffset"])
    rc = rc[(rc.ventendoffset > rc.ventstartoffset)].rename(columns={"patientunitstayid": "stay"})
    rc = rc[rc.stay.isin(keep)].merge(stays[["stay", "hours"]], on="stay")
    vent = [(s, h) for s, a_, b_, n in zip(rc.stay, hour_of(rc.ventstartoffset / 60), hour_of(rc.ventendoffset / 60),
                                          rc.hours) for h in range(a_, min(b_, n - 1) + 1)]
    feats["ventilated"] = pd.Series(True, index=pd.MultiIndex.from_tuples(sorted(set(vent)), names=["stay", "hour"]),
                                    name="ventilated") if vent else pd.Series(dtype=bool, name="ventilated")

    vp = read(root, "vitalPeriodic", ["patientunitstayid", "observationoffset", "systemicmean"])
    va = read(root, "vitalAperiodic", ["patientunitstayid", "observationoffset", "noninvasivemean"])
    mp = pd.concat([vp.rename(columns={"systemicmean": "map"}), va.rename(columns={"noninvasivemean": "map"})])
    mp = in_window(mp.dropna(subset=["map"]), "observationoffset")
    feats["map"] = hourly(mp[(mp["map"] > 10) & (mp["map"] < 250)], "map", "min")

    nc = read(root, "nurseCharting", ["patientunitstayid", "nursingchartoffset", "nursingchartcelltypevalname",
                                      "nursingchartvalue"], lambda c: c[c.nursingchartcelltypevalname == "GCS Total"])
    nc["gcs"] = pd.to_numeric(nc.nursingchartvalue, errors="coerce")
    nc = in_window(nc[(nc.gcs >= 3) & (nc.gcs <= 15)], "nursingchartoffset")
    feats["gcs"] = hourly(nc, "gcs", "min")

    inf = read(root, "infusiondrug", ["patientunitstayid", "infusionoffset", "drugname", "drugrate", "patientweight"])
    inf = in_window(inf, "infusionoffset").merge(stays[["stay", "admissionweight"]], on="stay", how="left")
    name = inf.drugname.fillna("").str.lower()
    rate = pd.to_numeric(inf.drugrate, errors="coerce")
    weight = pd.to_numeric(inf.patientweight, errors="coerce").fillna(inf.admissionweight)
    per_kg = np.where(name.str.contains(r"mcg/kg/min"), rate,
                      np.where(name.str.contains(r"mcg/min"), rate / weight, np.nan))
    per_kg = np.where(np.isnan(per_kg) & (rate > 0), UNKNOWN_RATE, per_kg)
    inf["rate_kg"] = per_kg
    for drug, col in PRESSORS.items():
        x = inf[name.str.startswith(drug) | name.str.contains(drug + r"\b") & ~(
            (drug == "epinephrine") & name.str.contains("norepinephrine"))]
        x = x[x.rate_kg > 0]
        feats[col] = hourly(x.rename(columns={"rate_kg": col}), col, "max")

    io = read(root, "intakeOutput", ["patientunitstayid", "intakeoutputoffset", "cellpath", "celllabel",
                                     "cellvaluenumeric"],
              lambda c: c[c.cellpath.fillna("").str.contains("Output") & c.celllabel.fillna("").str.contains("Urine|URINE")
                          & ~c.celllabel.fillna("").str.contains("Stool|Count")])
    io = in_window(io, "intakeoutputoffset", lo=0)
    feats["urine"] = hourly(io[(io.cellvaluenumeric >= 0)].rename(columns={"cellvaluenumeric": "urine"}), "urine", "sum")

    h = grid.set_index(["stay", "hour"]).join(pd.DataFrame(feats)).reset_index().sort_values(["stay", "hour"])
    for col in S3.FEATURES:
        if col not in h:
            h[col] = np.nan
    h["ventilated"] = h.ventilated.eq(True)
    h["urine"] = h.urine.fillna(0)
    h["urine_24h"] = (h.groupby("stay").urine.rolling(24, min_periods=24).sum()
                      .reset_index(level=0, drop=True).reindex(h.index))
    h = h.reset_index(drop=True)
    h, onset = S3.score_and_label(h, t_susp)

    st = stays[["stay", "hospitalid", "hours"]].set_index("stay")
    st["has_abx"] = st.index.isin(abx.stay)
    st["has_culture"] = st.index.isin(cultures.stay)
    hosp = st.groupby("hospitalid").agg(stays=("hours", "size"), abx_share=("has_abx", "mean"),
                                        culture_share=("has_culture", "mean"))
    hosp["adequate"] = (hosp.abx_share >= MIN_ABX_SHARE) & (hosp.culture_share >= MIN_CULTURE_SHARE)
    hosp.to_csv(f"{out}_hospitals.csv")
    st["hospital_adequate"] = st.hospitalid.map(hosp.adequate)
    st["t_suspicion"] = t_susp
    st["onset"] = onset
    st["max_sofa"] = h.groupby("stay").sofa.max()
    hc, reasons = S3.challenge_cohort(h, onset)
    st["excluded"] = pd.Series(reasons)
    st["septic"] = st.onset.notna() & st.excluded.isna()
    st.to_csv(f"{out}_stays.csv")
    hc.to_csv(f"{out}_hourly.csv.gz", index=False)
    print(f"all hospitals:")
    S3.summary(st, hc)
    ok = st[st.hospital_adequate]
    print(f"hospitals with adequate recording: {int(hosp.adequate.sum())} of {len(hosp)} ({len(ok)} stays)")
    S3.summary(ok, hc[hc.stay.isin(ok.index)])
    export_challenge(root, stays, grid, hc, out)
    inc = ok[ok.excluded.isna()]
    by_h = inc.groupby("hospitalid").agg(stays=("septic", "size"), septic=("septic", "sum"))
    print(f"hospitals with >= 20 stays: {(by_h.stays >= 20).sum()}; with >= 5 septic stays: {(by_h.septic >= 5).sum()}")
    print(f"stays with a culture ({a.definition}): {cultures.stay.nunique()}; with antibiotics ({a.definition}): "
          f"{abx.stay.nunique()}")


if __name__ == "__main__":
    main()
