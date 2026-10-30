# Analysis plan: multi-hospital sepsis transfer study (WP3, WP9)

Draft 1, 2026-10-30 (draft 1: false-alert limit and recording thresholds decided; monitoring
added). To be fixed and dated before any model is run on the full eICU-CRD or
MIMIC-IV data. Items marked **[decide]** are open; items marked **[from counts]** may be set after
looking at cohort sizes and septic counts per hospital, which say nothing about model performance.
Any change after the first full run is listed in the paper as a deviation.

## 1. Question

When a sepsis early-warning model trained at one hospital (or system) is imported by another,
does the CAB gate keep the probability of switching on an unsafe alert below alpha, and how do the
usual alternatives compare, across many real hospital-to-hospital transfers?

## 2. Data

- eICU-CRD v2.0 (about 200,000 ICU stays, 208 US hospitals, 2014-2015) and MIMIC-IV (one US
  academic centre; years 2008-2019 in shifted time).
- Hourly tables in the PhysioNet/CinC 2019 Challenge format (`code/challenge_format.py`), built by
  `code/mimiciv_sepsis.py` and `code/eicu_sepsis.py`; the chapter's features (`cabsepsis.features`)
  unchanged.
- Known difference: MIMIC-IV has no troponin I (troponin T only), so that variable is missing there.

## 3. Labels (decided 2026-10-30, `notes/sepsis_labels.md`)

- Sepsis-3 with the Challenge's SOFA rise (2 points within 24 h), onset window (24 h before to
  12 h after suspicion), 6 h label lead and cohort rules (at least 8 h; onset < 4 h excluded;
  2-week truncation).
- Suspected infection, primary ("relaxed"): any non-screening culture and any systemic antibiotic
  order, paired 72 h / 24 h. Sensitivity analysis: the Challenge's own rule (blood culture, IV
  antibiotic course of at least 72 h) on MIMIC-IV.

## 4. Hospitals and transfers

- eICU hospitals are eligible if antibiotics are recorded in at least 20% of their stays and
  cultures in at least 10% (recording rates, not outcomes; decided 2026-10-30). Stricter cuts
  protect the labels against hospitals that record only partly. Sensitivity analysis: 10% and 5%.
  In the demo, 85 of 186 hospitals record no cultures at all, but with a median of 12 stays per
  hospital the demo cannot place the cut more finely.
- A target must have enough septic stays to judge safety: at least 50 septic stays in the cohort
  (the ECG study's judging rule). **[from counts]** With about 2-3% of cohort stays septic, few
  single eICU hospitals reach this; if fewer than about 20 do, targets are hospital groups
  (region x bed-size category, or region alone) **[decide]**.
- Sources: MIMIC-IV, and the eICU hospitals or groups with the most septic stays, each split
  into train / validation / home-test by patient as in the chapter.
- Transfers: every source to every eligible target outside its own system; plus home controls.
- MIMIC-IV temporal split for WP8: earlier anchor-year groups as source, later as target.

## 5. Imported model

- LightGBM as in the chapter (same features and parameters), trained on the source's train split
  with early stopping on its validation split. WP5 adds logistic regression and a small recurrent
  model.
- Vendor operating point: the highest threshold certified for s* on the source's home test split
  (as in the chapter); home false-alert rate measured there.

## 6. Safety criteria

- Patient-level, as in the chapter: sensitivity = share of septic patients alerted between 12 h
  before and 3 h after onset; false-alert rate = share of non-septic patients alerted at least once.
- Primary: s* = 0.80 and f* = home false-alert rate + 0.05 (the chapter's primary; decided
  2026-10-30). The ECG study's relative limit, max(2 x home, home + 0.01), is not used: with the
  chapter's home false-alert rates of 0.29-0.48 it would allow 0.6-1.0. ECG keeps the relative
  limit because its home FPRs are 1-3%.
- Secondary: s* in {0.75, 0.85}; margins {0, 0.10}.

## 7. Policies

CAB (alpha = 0.05) and the chapter's comparators: as supplied, label-free reset, prevalence
correction, recalibration, fine-tuning, local retraining, closed testing, point-estimate validation
(all labels; first 500), Learn-then-Test without order, CAB without adapt; plus conformal risk
control (as in the ECG study).

## 8. Experiment

- Label budgets: 50, 100, 200, 400, 800, 1,600 patients, capped at half of the target's eligible
  patients. **[from counts]**
- 100 random repeats per transfer and budget; seeds fixed in advance.
- Judge: the whole target cohort (the population the labels are drawn from), less records used to
  fit an adapted model; sensitivity analysis on the unlabelled patients only. Decided for the ECG
  study (`notes/ecg_design.md`); applies here.

## 9. Outcomes

- Primary: per transfer, the share of runs that switched on an unsafe alert; summarised as the
  mean over transfers, the worst transfer, and the number of transfers above alpha.
- Secondary: share of runs switched on; first budget with half of runs switched on; ward numbers
  (PPV, alerts per bed-day, lead time) in switched-on runs (WP4).

## 10. Sensitivity analyses

Labels under the Challenge rule (MIMIC-IV); the other criteria; judge on unlabelled patients; a
second training seed; eICU hospitals that fail the recording check, reported separately.

## 11. Monitoring after deployment (WP8; `notes/wp8_design.md`)

- Monitor: two betting tests on audited stays (missed septic stays; false alerts in non-septic
  stays), each at delta/2 = 0.025, with sliding-window aGRAPA bets (window 100, c = 0.5); the
  probability of any false alarm while the deployment is safe is at most 0.05 (Ville).
- Comparators: point-estimate checks and uncorrected binomial tests every 250 audited stays.
- Test: MIMIC-IV temporal split (deployment certified on earlier anchor-year groups, audits from
  later groups) and eICU transfers (deployment at one hospital or group, audits from another).
- Outcomes: false alarms in runs where the deployment stays safe; detection and audits to
  alarm where it becomes unsafe, by size of the drift.
- **[decide]** whether sensitivity audits are enriched for septic stays, and whether the guarantee
  is the probability of any false alarm or the average time to one, once the ECG comparison of
  the two is done.

## 12. Reporting

TRIPOD+AI checklist; code and this plan released with the paper; every deviation listed.

## To decide before the full run

1. Targets: single hospitals or groups, once septic counts per hospital are known.
2. Label budgets, once target sizes are known.
3. Monitoring: enriched sensitivity audits; type of false-alarm guarantee (section 11).

Decided 2026-10-30: recording thresholds 20% / 10% (section 4); false-alert limit home + 0.05
(section 6).
