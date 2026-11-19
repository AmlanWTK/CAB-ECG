# Analysis plan: multi-hospital sepsis transfer study (WP3, WP9)

Draft 2, **fixed 2026-11-19**, before any model was run on the full eICU-CRD or MIMIC-IV data
(draft 1: 2026-10-30, updated 2026-10-31). No item is left open. Items marked **[rule]** are
decided as rules applied mechanically to cohort sizes and septic counts per hospital, which say
nothing about model performance. Any change after this date is listed in the paper as a deviation.

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
- Label check before any model is run (`notes/label_check.md`, ranges confirmed 2026-10-31): MIMIC-IV
  under the Challenge rule within 5-13% septic (Challenge hospital A, the same hospital in
  earlier years: 8.8%); the relaxed rule at least as high and mostly containing the Challenge
  rule's cases; eICU hospitals passing the recording check within 3-15%; SOFA coverage close to
  the demos. A failure is investigated and documented, not tuned away.
- Changes to the labels before this plan was fixed (all on MIMIC-IV, before any model was run;
  `notes/sepsis_labels.md`). (a) Onset is set by the earliest suspicion episode that has a
  qualifying SOFA rise, not only by the first episode. This was adopted on 2026-11-17 after
  checks 1 and 2 had failed, because an earlier, unrelated suspicion hid later episodes. The
  paper reports both rules. (b) Septic stays end at onset + 3 h, as in the Challenge files.
  (c) SaO2 comes from arterial blood gases and charted arterial saturation only.
- Label check results on full MIMIC-IV (2026-11-18): check 1 fails (Challenge rule 3.8% of
  stays, 3.6% with a labelled hour, against 5-13%) and is reported as found; check 2 passes
  (relaxed 13.6%; overlap 84.2%); check 4 passes; check 5 passes (3 of 36 inputs flagged, each
  explained or fixed). Check 3 (eICU) is still to run.

## 4. Hospitals and transfers

- eICU hospitals are eligible if antibiotics are recorded in at least 20% of their stays and
  cultures in at least 10% (recording rates, not outcomes; decided 2026-10-30). Stricter cuts
  protect the labels against hospitals that record only partly. Sensitivity analysis: 10% and 5%.
  In the demo, 85 of 186 hospitals record no cultures at all, but with a median of 12 stays per
  hospital the demo cannot place the cut more finely.
- A target must have enough septic stays to judge safety: at least 50 septic stays in the cohort
  under the primary (relaxed) labels (the ECG study's judging rule).
- Targets **[rule]**, applied in this order to the hospitals that pass the recording check:
  1. If at least 20 single hospitals have 50 or more septic stays, those hospitals are the
     targets. Hospitals below 50 are not pooled.
  2. Otherwise, targets are groups of the passing hospitals by region x bed-size category (eICU
     `hospital` table: `region`, `numbedscategory`). Groups with 50 or more septic stays are
     targets.
  3. If fewer than 20 groups qualify under step 2, the groups are by region alone.
  Hospitals with region or bed size missing are left out of groups. The step reached and the
  counts at each step are reported.
- Sources **[rule]**: MIMIC-IV, and the five targets with the most septic stays (ties broken by
  more cohort stays). Each is split into train / validation / home-test by patient as in the
  chapter, and each remains a target for the other sources.
- Transfers: every source to every eligible target outside its own system; plus home controls.
- MIMIC-IV temporal split for WP8: earlier anchor-year groups as source, later as target.
- Open external target (added 2026-10-31): PhysioNet/CinC 2019 Challenge hospital B (Emory;
  `data/sepsis2019/training/training_setB`, open access): 20,000 patients, 1,142 septic (5.7%),
  761,995 hours. It is outside both MIMIC-IV and eICU, and its 34 measured variables match ours.
  - Its labels follow the Challenge rule, and the raw records are not released, so they cannot
    be relabelled. Transfers to B therefore use source models trained and certified on
    Challenge-rule labels (MIMIC-IV and eICU, `--definition challenge`), and are judged on B's
    own labels. They are reported with the Challenge-rule sensitivity analysis, not the primary.
  - The eICU recording check does not apply to B (the Challenge organisers built its labels).
  - Harmonisation (`code/challenge_b.py`, `notes/label_check.md` check 5): our MIMIC-IV inputs
    are compared with hospital A's, so that a transfer to B measures B's patients rather than
    differences between our extraction and the Challenge's processing. Demo dry run: the
    target side of the pipeline runs on B.
  - Hospital A (Beth Israel, the MIMIC-IV hospital in earlier years) is not an external target;
    it may serve as a check of MIMIC-IV labels over time. Hospital C was never released.

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
control (as in the ECG study); and from WP7 (`notes/wp7_design.md`): Bayesian updating from a flat
prior (at 0.95 and at CAB's strictness, 1 - alpha/4), Bayesian updating with the source's home
validation as prior, a precision-based minimum sample size followed by point estimates, and CORAL
domain adaptation (label-free, and recalibrated).

## 8. Experiment

- Label budgets **[rule]**: 50, 100, 200, 400, 800, 1,600 patients. A budget is used for a target
  only if it is at most half of the target's cohort stays. Every target has at least 50 septic
  stays and so at least a few hundred stays, so every target gets the smallest budgets.
- 100 random repeats per transfer and budget. Repeat r draws its labelled patients with seed r
  (0 to 99). Each source model is trained once, with seed 0 for its train / validation /
  home-test split and for LightGBM. The second-training-seed sensitivity analysis (section 10)
  uses seed 1.
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
- Audits: every stay, with the Sepsis-3 label computed from the record (no chart review), so no
  enrichment is needed. CUSUM e-detector (average time to a false alarm at least 5,000 and 20,000
  stays) as a secondary analysis.
- Guarantee (decided 2026-10-31): the probability of any false alarm, at most 0.05, is primary;
  CUSUM is secondary. On ECG the primary monitor found more drifts, sooner, than the CUSUM
  detector (87% vs 79-81% within 16,000 audits; `notes/wp8_design.md`), and its promise is the
  simpler one to state clinically.

## 12. Reporting

TRIPOD+AI checklist; code and this plan released with the paper; every deviation listed.

## Decisions

Fixed 2026-11-19: targets, sources and label budgets as rules (sections 4 and 8); seeds 0-99
(section 8); label changes and check results recorded (section 3). Challenge hospital B is a
target in any case (section 4).

Decided 2026-10-30: recording thresholds 20% / 10% (section 4); false-alert limit home + 0.05
(section 6). Decided 2026-10-31: label-check ranges as written (section 3); monitoring guarantee,
probability of any false alarm at most 0.05, with CUSUM secondary (section 11).
