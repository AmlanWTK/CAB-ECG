# ECG domain: study design (WP10)

Draft, 2026-10-28. Settled before any target results are seen.

## Question

An ECG classifier trained in one country is imported by hospitals in other countries. For each
finding, can CAB decide whether to keep it, recalibrate it, adapt it or block it, while keeping
the probability of switching on an unsafe finding below alpha?

## Data

| Role | Cohort | Country | Records |
|---|---|---|---|
| Source | PTB-XL v1.0.3 | Germany | 21,799 |
| Target | Georgia (Challenge 2021) | USA | 10,344 |
| Target | CPSC 2018 | China | 6,877 |
| Target | CPSC-Extra | China | 3,453 |
| Target | Chapman-Shaoxing (ecg-arrhythmia) | China | 10,247 |
| Target | Ningbo (ecg-arrhythmia) | China | 34,905 |
| Target | CODE-15%, part 0 | Brazil | about 20,000 |

Findings: the six-label panel in `code/cabecg/labels.py` (AF, IAVB, RBBB, LBBB, SB, STach).
A transfer is one finding at one target: up to 6 x 6 = 36, fewer where a finding is too rare
at a target to judge safety (rule below).

## Source model

- Signals: 12 leads, 10 s, resampled to 100 Hz, in mV (`code/cabecg/signals.py`).
- Network: a small 1-D ResNet with six sigmoid outputs, trained on PTB-XL folds 1-8, early
  stopping on fold 9. Fold 10 is the vendor's home test set.
- The vendor's threshold for each finding is the highest one reaching sensitivity s* on fold 10.

## Safety criteria (per finding)

- Sensitivity at least s* = 0.90 (the primary criterion; 0.80 as a sensitivity analysis).
- False-positive rate at most f* = max(2 x home FPR, home FPR + 0.01): the false-positive rate
  may at most double, with at least one percentage point allowed. Decided 2026-10-28, before any
  CAB result, because four findings have home FPRs of 0.5-1%, where the sepsis study's absolute
  margin of +0.05 would allow a tenfold rise. The absolute margin is a sensitivity analysis.

## Remedies

- KEEP / CALIBRATE: the imported network and its score; threshold certified on all labels.
- ADAPT: a new logistic-regression head per finding on the frozen network's embedding, fitted
  on half of the labelled records and certified on the other half.
- BLOCK: the finding is not shown at that site.

The gate is `cab_select` in `code/cabsepsis/cab.py`, unchanged: with one score per record, its
`wmax` and `smax` are both the record's score and `septic` is the finding's label.

## Experiment

- Label budgets: 250, 500, 1,000, 2,000, 4,000 labelled records per target (capped by cohort size).
- 100 random repeats per transfer and budget; seeds fixed as in the sepsis study.
- Safety judged on the target's unlabelled records.
- Comparators: the same as the sepsis chapter (AS-IS, LABEL-FREE, LABEL-SHIFT, RECALIBRATE,
  FINE-TUNE, CLOSED-TEST, NAIVE-VAL, NAIVE-500, LTT-DIRECT, CERT-RECAL), plus conformal risk
  control (WP7).
- Judging rule: a transfer is judged only when the target has at least 50 unlabelled positives
  at the largest budget used for it.

## Known issues to handle

- Label conventions differ by site (the E0 audit checks AF vs atrial flutter, incomplete vs
  complete RBBB). These are real shifts the gate must cope with, but they are reported.
- Only PTB-XL and CODE-15% have patient IDs; elsewhere records are treated as independent.
- CODE-15% labels come from automatic reports checked by cardiologists, not a full review.
- Ningbo and Chapman share a source database; treated as two targets but noted.

## Findings so far (E1, 2026-10-28)

- Source model (seed 0): best validation mean AUROC 0.986; results in `outputs/ecg/E1_source.md`.
- Discrimination transfers well to Chapman and Ningbo (AUROC 0.88-0.996), but sensitivity at
  the vendor threshold falls for RBBB (0.67, 0.74), LBBB at Chapman (0.43) and sinus
  bradycardia (0.73, 0.71); AF false positives rise at Chapman (0.8% to 5.8%).
- Ningbo has no AF positives under the AF code; checked in the E0 audit before AF is used there.
- One ecg-arrhythmia header (JS01052) is malformed and is skipped; one Chapman record carries
  the name S23074.
- CODE-15% amplitudes are about 2.1 times those of every other cohort (lead II robust range
  2.0 mV vs 0.93-0.95 mV), with the values used as distributed (the authors give them as mV for
  their model). AUROC there is lower (0.81-0.93); halving the signals raises it (0.86-0.95) but
  not to the other targets' level. Main analysis: data as distributed, because that is what an
  importing hospital would feed the model; the halved version is a sensitivity analysis.
- Margin: settled as the relative margin (see Safety criteria).
- Georgia, CPSC 2018 and CPSC-Extra (all 20,674 records, size-checked): AUROC 0.92-0.99 at
  Georgia. CPSC 2018 has no SB or STach labels, so those two are not judged there. RBBB at
  CPSC 2018 is lower (0.86), probably because its RBBB code includes incomplete RBBB (E0 audit).
  LBBB at CPSC-Extra is 0.60 on only 38 positives, too few to judge under the 50-positive rule.
  CPSC records run 6-144 s; the first 10 s are used, and records under 10 s are zero-padded.
- Judging rule, implementation fix: the first E3 runs selected findings with at least 20
  positives in total, not the rule above. Fixed to the rule as written, taking the expected
  number of unlabelled positives at the largest budget used. This drops LBBB and SB at
  CPSC-Extra (about 27 and 32), leaving 31 transfers; CAB had blocked both in every run.
- E3, all six targets, 31 transfers: CAB unsafe in 0.3% of runs on average, worst transfer 2.2%,
  none above alpha; NAIVE-VAL 34% (worst 71%), AS-IS 94%. CAB switched on 12% of runs. Mostly
  CALIBRATE for SB (Chapman, Ningbo, Georgia) and some ADAPT for IAVB at CPSC 2018 (44% of runs
  at 2,000 labels). Rare findings are blocked: certifying s* = 0.90 at delta = alpha/4 needs at
  least 42 positives even with perfect detection.
- Budgets 8,000 and 16,000 added on 2026-10-29, after the first E3 results, to test whether
  blocking of rare findings is a label-count limit. Under the half-cohort rule they fit only
  Ningbo (both) and CODE-15% (8,000). Ningbo: at 16,000 labels CAB switches on RBBB (95% of
  runs), STach (97%), IAVB (61%) and LBBB (49%); at 4,000 labels it was 10% or less. So the
  blocking was a label-count limit. CODE-15%: still all BLOCK at 8,000, as the oracle predicted.
- Open issue, judge noise at large budgets: at 16,000 labels CAB's unsafe rate at Ningbo is
  LBBB 0.07, STach 0.06, SB 0.05 (alpha 0.05). All failures are borderline (sensitivity
  0.876-0.899 vs 0.90, or FPR within 0.001 of f*). Rerunning the same 100 seeds and judging on
  the whole cohort instead of the unlabelled remainder gives 0.00 for all three
  (scratch check). With 46% of the cohort labelled, the remainder (about 134 LBBB positives) is
  small and negatively correlated with the labelled half, so the remainder judge flags thresholds
  that meet the criterion on the hospital's population. The primary E3 analysis is unchanged
  (remainder judge).
- Decided 2026-10-29: report both judges. Primary = unlabelled remainder (as pre-specified);
  secondary = whole cohort, less the records an ADAPT head was fitted on (columns
  `*_cohort` in the run files, section "Secondary judge" in E3_report.md). Full rerun with the
  same seeds reproduced every earlier decision and primary verdict.
- Result, 31 transfers, budgets 250-16,000. CAB, primary judge: mean unsafe 0.3%, worst
  transfer (all budgets pooled) 2.2%, none over alpha. Three single transfer-and-budget cells
  exceed alpha: Georgia IAVB at 4,000 (0.07), Ningbo LBBB and STach at 16,000 (0.07, 0.06).
  The secondary judge gives 0.01, 0.00, 0.00 for these, mean unsafe 0.1%, worst 0.8%.
  NAIVE-VAL: 33-34% mean under either judge.
