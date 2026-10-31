# Label check for the full data (WP1)

2026-10-31. Written before the full eICU-CRD and MIMIC-IV data are available, so that the first
labels are compared with figures chosen in advance, not with figures found afterwards. This is a
check that the labelling code is working, not a result.

## Published figures to compare against

| Source | Data and rules | Septic | Suspected infection |
|---|---|---|---|
| Reyna et al. 2020 (Challenge 2019) [1]; counts from our copy of the public data | Hospital A (Beth Israel Deaconess, the MIMIC hospital), Challenge rules: 20,336 patients | 8.8% | not reported |
| same | Hospital B (Emory), Challenge rules: 20,000 patients | 5.7% | not reported |
| Moor et al. 2021 [2] | eICU, 56,765 stays, after removing hospitals with Sepsis-3 prevalence below 15% and other quality exclusions; suspected infection from repeated antibiotics only (eICU's culture recording judged inadequate) | 8% | 17% |
| same | MIMIC-III, 36,591 stays; suspected infection 48 h before to 24 h after; onset 4-168 h | 26% | 45% |

How comparable each figure is:

- **Closest match.** Hospital A uses the Challenge's rules, which our code follows (SOFA window, 6 h
  lead, at least 8 h of data, onset at 4 h or later, 2-week truncation), at the hospital MIMIC-IV
  comes from, for earlier years. Our MIMIC-IV labels under the Challenge definition should come
  close to its 8.8%.
- **Our relaxed definition** (any non-screening culture, any systemic antibiotic order) should give
  a higher rate than the Challenge definition on the same stays.
- **eICU figures are not directly comparable.** Moor et al. used a different definition of
  suspected infection and removed hospitals by their sepsis prevalence, an outcome-based
  exclusion we do not use. They show the order of magnitude only.
- **MIMIC-III 26% (Moor et al.)** uses wider windows and no Challenge cohort rules, so it is an
  upper reference, not a target.

On the demos (too small to judge; for orientation only): MIMIC-IV demo, Challenge definition 3.9%
(5 of 129), relaxed 7.0% (8 of 114); eICU demo, hospitals passing the recording check, relaxed
2.4% (16 of 665).

## Checks, fixed in advance

Ranges confirmed 2026-10-31. Run on the first full extraction, before any model is trained.

1. **MIMIC-IV, Challenge definition.** The share of cohort stays labelled septic should be within
   5-13%, around hospital A's 8.8%.
2. **MIMIC-IV, relaxed definition.** Its septic share should be at least that of the Challenge
   definition, and the stays labelled septic under the Challenge definition should mostly also be
   septic under the relaxed one (at least 80%).
3. **eICU, hospitals passing the recording check, relaxed definition.** The septic share should be
   within 3-15%.
4. **Coverage.** The share of stay-hours with each SOFA component measured should be close to the
   demo's (eICU: cardiovascular about 85%, renal about 70%; respiration, coagulation and liver
   2-5%), and onset hours should not be concentrated at the earliest allowed hour.

If a check fails, the extraction is investigated (definitions, item lists, units, time windows)
and the cause and fix are recorded in `notes/sepsis_labels.md` before anything else is run. The
thresholds are not tuned to the data afterwards. If a failure turns out to have no extraction
cause, it is reported as it stands.

## Running the full extraction

The extractors now read each large table once, in chunks, and reduce it to hourly values as they
go (`code/bigtable.py`), keeping finished passes in `<out>_cache/` so a stopped run restarts
where it stopped. Tested on the demos (labels identical to the earlier code; hourly Challenge
values equal to within float32 rounding, 2e-7 relative). Full-scale synthetic tests on this 16 GB
machine:

- the hourly aggregation of 144 M vital-sign rows over 12 M stay-hours took 112 s, with a peak of
  1.1 GB;
- SOFA scoring, onset and cohort rules on 12 M stay-hours took 16 s, with a peak of 4.8 GB.

Reading the compressed tables will take most of the time: likely tens of minutes for eICU
nurseCharting and MIMIC-IV chartevents. Commands:

    python q1_journal_plan/code/eicu_sepsis.py --root data/eicu/eicu-collaborative-research-database-2.0 --out outputs/sepsis_q1/eicu
    python q1_journal_plan/code/eicu_sepsis.py --root ... --out outputs/sepsis_q1/eicu --definition challenge
    python q1_journal_plan/code/mimiciv_sepsis.py --root data/mimiciv/<version> --out outputs/sepsis_q1/mimiciv
    python q1_journal_plan/code/mimiciv_sepsis.py --root ... --out outputs/sepsis_q1/mimiciv --definition challenge

The second run of each database reuses the first run's cache. The root folders are placeholders:
use wherever the downloads are unpacked.

## References

1. Reyna MA, Josef CS, Jeter R, et al. Early prediction of sepsis from clinical data: the
   PhysioNet/Computing in Cardiology Challenge 2019. Crit Care Med. 2020;48(2):210-217.
   doi:10.1097/CCM.0000000000004145
2. Moor M, Bennet N, Plecko D, et al. Predicting sepsis in multi-site, multi-national intensive
   care cohorts using deep learning. arXiv:2107.05230; 2021.
