# Sepsis-3 labels from MIMIC-IV and eICU (WP1)

Draft, 2026-10-30. Shared rules in `code/sepsis3.py` (Challenge 2019 style); extractors in
`code/mimiciv_sepsis.py` (done for MIMIC-IV) and an eICU extractor (to do).

## Rules (Challenge 2019, checked against Reyna et al., Crit Care Med 2020;48:210-217, Methods)

- Suspected infection: blood culture and IV antibiotics given for at least 72 consecutive hours.
  Culture first: antibiotic within 72 h. Antibiotic first: culture within 24 h. Time = the earlier.
- SOFA rise: 2 or more within a 24-hour period (above the lowest SOFA in the previous 24 h).
- Onset: earlier of suspicion and SOFA rise, with the rise no more than 24 h before or 12 h after
  suspicion. SepsisLabel = 1 from 6 h before onset.
- Cohort: at least 8 hourly windows; onset less than 4 h after ICU admission excluded; truncated
  at 2 weeks.

Fixed on 2026-10-30. The first version of `sepsis3.py` had the pairing windows reversed (culture
first: antibiotic within 24 h), used Seymour et al.'s 48/24 h window and a rise against the lowest
SOFA in the whole stay, and had no cohort rules. The first demo run used that version: 31% septic,
median onset 1.6 h, 50% of hours labelled.

## MIMIC-IV extraction choices

- Cultures: specimens with "BLOOD CULTURE" in the type; charttime, else chartdate.
- Antibiotics: IV prescriptions (route starting "IV") with a systemic antibacterial in the drug
  name (list in the code). Overlapping prescriptions, or ones less than 24 h apart, form one course;
  only courses of at least 72 h count; time = course start. The 24 h gap allowance is our choice
  (the Challenge does not say how "consecutive" was judged).
- PaO2/FiO2: arterial pO2 with the latest FiO2 in the previous 4 h; ventilation from
  procedureevents 225792.
- GCS: eye + verbal + motor charted together; not scored when verbal is "No Response-ETT".
- MAP: lowest of 220052, 220181, 225312 in the hour. Vasopressors in mcg/kg/min.
- Urine: 24 h sum from hour 23. Events up to 24 h before ICU admission count towards hour 0.

## Check on the open demo (MIMIC-IV demo v2.2: 100 patients, 140 ICU stays)

- Suspected infection in 25 stays (18%); Sepsis-3 before cohort rules in 12.
- Excluded: 7 with onset under 4 h, 4 with under 8 h of data. Cohort: 129 stays.
- Septic: 5 of 129 (4%); median onset 21 h after admission (IQR 4-118). SepsisLabel = 1 in 5.8% of
  hours. The same order as the Challenge data, but five septic stays are too few to judge more
  closely; the full database will.
- Hours with each SOFA component measured: cardio 94%, renal 76%, CNS 16%, coag 7%, resp 4%,
  liver 3% (labs are daily; the 24 h rolling worst fills the gaps).

## Open questions before the full databases

1. How "72 consecutive hours" of antibiotics was judged in the Challenge (gap allowance).
2. GCS under sedation and intubation: not scored here (counts as normal in SOFA). Compare with
   mimic-code's SOFA concept once full access is available.
3. Check the septic share on full MIMIC-IV against the Challenge's per-system shares
   (Supplemental Table 1 of Reyna et al.).

## eICU (demo v2.0.1: 2,520 stays, 186 hospitals), 2026-10-30

`code/eicu_sepsis.py`; same shared rules and scoring as MIMIC-IV (`sepsis3.score_and_label`).

- Under the Challenge rules, only 9 of 2,520 stays have suspected infection (0.4%) and none is
  septic after the cohort rules. Cultures and antibiotics are recorded unevenly: microLab is filled
  at 12 of 186 hospitals; adding culture orders from the treatment table gives blood cultures in 130
  stays; IV antibiotic courses of at least 72 h are found in 141 stays, and the two rarely coincide.
  Only 107 hospitals record any antibiotic in medication, 101 any culture.
- Relaxing the rules (suspected infection in stays):

  | Rules | Stays |
  |---|---|
  | Challenge (blood culture, IV antibiotic >= 72 h) | 9 (0.4%) |
  | any culture site | 20 (0.8%) |
  | no 72 h antibiotic rule | 24 (1.0%) |
  | both | 49 (1.9%) |
  | both, plus antibiotics from the treatment table | 209 (8.3%) |

  MIMIC-IV demo under the Challenge rules: 25 of 140 (18%).
- Decision needed for WP3: in eICU, labels under any rule depend on how well each hospital records
  cultures and antibiotics. Options: one relaxed definition for both databases with a
  data-completeness filter on eICU hospitals (Challenge rules as a sensitivity analysis on
  MIMIC-IV), or Challenge rules on MIMIC-IV only with eICU on a separate definition.

## Decision (2026-10-30): one relaxed definition for both databases

Primary labels for the transfer study use the "relaxed" suspected-infection rule in both
databases: any non-screening culture and any systemic antibiotic order (in eICU also culture and
antibacterial entries in the treatment table), with no minimum antibiotic duration. The SOFA rise,
onset window, 6 h label lead and cohort rules stay exactly as in the Challenge. The Challenge's own
rule (blood culture, IV antibiotic course >= 72 h) is run on MIMIC-IV as a sensitivity analysis.
Reason: in eICU, recording of cultures and antibiotics differs by hospital, so labels must not
depend on the strictest recording, and the same rule must hold at every hospital.

eICU hospital recording check (provisional, to be fixed in the analysis plan before the full run):
a hospital is kept if antibiotics are recorded in at least 20% of its stays and cultures in at
least 10%. These are recording rates, not outcomes.

Demo results (`--definition relaxed` / `challenge`):

| | MIMIC-IV relaxed | MIMIC-IV challenge | eICU relaxed, adequate hospitals | eICU challenge, all |
|---|---|---|---|---|
| Suspected infection | 72 of 140 (51%) | 25 of 140 (18%) | 170 of 736 (23%) | 9 of 2,520 (0.4%) |
| Excluded (onset < 4 h / < 8 h of data) | 22 / 4 | 7 / 4 | 33 / 38 | 3 / 238 |
| Cohort, septic | 114, 8 (7.0%) | 129, 5 (3.9%) | 665, 16 (2.4%) | 2,279, 0 |
| Onset, median (IQR) h | 6.7 (5.0-14.8) | 21 (4-118) | 13.2 (10.0-23.5) | - |
| Hours with SepsisLabel = 1 | 16.7% | 5.8% | 5.1% | 0% |

- 60 of 186 eICU demo hospitals pass the recording check (736 stays). In the demo each hospital has
  only about 14 stays, so the check is noisy there; on the full database it will rest on hundreds
  of stays per hospital.
- eICU's septic share is lower than MIMIC-IV's under the same rule (2.4% vs 7.0%). Possible reasons:
  sparser SOFA inputs in eICU (PaO2 2%, bilirubin 3%, GCS 15% of hours) or case mix. To check on the
  full data: SOFA component coverage by hospital, and whether a coverage requirement belongs in the
  recording check.
- The onset-under-4-h rule excludes many septic stays (22 of 30 in MIMIC-IV, 33 of 51 in eICU),
  as in the Challenge: early-warning models are for sepsis that develops in the ICU.
