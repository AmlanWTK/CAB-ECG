# Response to the review of Section 4

2026-11-02. Every point checked against the code and result files in `code/` and
`outputs/sepsis/`. "Changed" means Section 4 now says this.

## P1

1. **63% (Table 5) versus 68% (Table 9) for the imported A→B model.** Not an error: the two
   evaluate different patients. Table 5 (`sepsis_e2_ci.py`) uses hospital B's 4,000 test patients
   (sensitivity 0.632, 95% interval 0.572–0.693). Table 9 (`sepsis_e13_leadtime.py`) averages 20
   runs, each judged on the about 8,000 patients of hospital B not labelled in that run
   (`comp = eligible & ~lab`), drawn from all splits. Over all of hospital B's patients the
   imported model's sensitivity is 0.672 (`E11_headroom.md`, A→B, headroom 0). Both use the same
   vendor threshold and the same detection window. The reviewer's check also exposed a second
   difference: Table 9's "local model" is the receiving hospital's own model trained on its
   training set with a threshold set to 80% sensitivity on its test patients, whereas Table 5's
   local model is that hospital's source model at its vendor threshold. Changed: Table 9's note
   and a paragraph after it explain both differences.
2. **Pooled exact bounds in Table 8.** The reviewer is right, for a further reason. Besides
   heterogeneity across settings, the nine requirement pairs of each run share the same labelled
   sample (the seed depends on scenario, budget and repetition only), so runs pooled across
   settings are not independent, and a pooled Clopper–Pearson bound is not justified. Changed: the
   pooled-bound column is removed; group means and worst settings are presented as descriptive;
   inference rests on each setting's own exact interval, whose 100 runs use independent samples.
   The count "settings whose exact 95% interval lies wholly above α" is unchanged (0 everywhere),
   and the statement that about 48 settings would exceed 5% by chance if every true rate were 5%
   is an expectation, which does not need independence.
3. **Title of 4.4.** Changed to "Empirical Unsafe-Deployment Rates Were Consistent with the
   Guarantee", and the opening now says the simulations cannot prove the guarantee, which follows
   from the proof in Section 3.5.

## P2

4. **Aggregation scope.** Changed: Fig. 4 is described as the primary requirements by budget;
   Table 6 and the 0.7% figure as averages over the whole-hospital transfers and the same-hospital
   control, all requirement pairs and all budgets; Table 7 as group averages over all requirement
   pairs and budgets.
5. **Budgets up to 32,000 in 4.7.** A separate simulation (`sepsis_e11_headroom.py`): same-hospital
   control, models fixed, no adaptation, CAB's rule applied to labelled samples drawn with
   replacement from the hospital's test patients, 200 samples per cell. Sampling with replacement
   is what allows budgets beyond the 4,068 test patients. Changed: 4.7 describes this. The
   calculator check in 4.5 (`sepsis_e5_labels.py`, part B) is described the same way: models
   fixed, samples with replacement, 400 per budget, smallest budget at which CAB chose the
   correct remedy in at least 90% of samples.
6. **Label noise.** Changed to the reviewer's framing: a limited robustness check under one-sided
   noise, 20 runs per condition (at most 1 unsafe run of 20 in any condition). The mechanism is
   now described as what the labels do to each test, with "the net effect was fewer deployments
   in these runs, although it need not be in every case".

## P3 and others

7. **72 bedside combinations.** Changed: eight scenarios (including the two controls) × nine
   requirement pairs, each of the four scores at every cut-off on all eligible patients
   (`E7_fallback.md`).
8. **Bootstrap.** Changed in Table 5's caption: paired percentile intervals from resampling
   patients with replacement, 2,000 resamples (200 for AUROC), both models on the same resampled
   patients (`sepsis_e2_ci.py`).
9. **Shorter window.** Checked: the window is set in `cabsepsis.cab` and so applies to the vendor's
   threshold, CAB's tests and the judging. Changed: 4.8 says so, with 30 runs per setting.
10. **Blocking costs.** All three measures are per 100 admissions (missed and falsely alerted
    patients) or per patient-day (alarms), from `E3mac100_impact.md`; the fallback figures are
    given for each hospital separately.
11. **Lead time conditional on detection.** Table 9's note says lead times are among detected
    patients and the last column is the share of all septic patients.
