# WP7: stronger comparators

2026-10-31. Built and run on the ECG domain. Code: `code/wp7_comparators.py`. Results:
`outputs/ecg/W7_report.md`. The sepsis runs reuse the same policies once the data arrive.

## Policies

All use the same label samples as E3 (same seeds) and are judged on the whole target cohort (the
primary judge). Primary criterion only: s* = 0.90, relative false-positive margin.

- **BAYES-FLAT.** Bayesian updating of the imported model from a flat Beta(1, 1) prior. It takes
  the highest threshold with posterior P(sensitivity >= s*) >= 0.95, and switches on if
  posterior P(FPR <= f*) >= 0.95 at that threshold.
- **BAYES-MATCHED.** BAYES-FLAT at the strictness of CAB's tests: posterior probability
  1 - alpha/4 = 0.9875 for each criterion instead of 0.95.
- **BAYES-HOME.** The same as BAYES-FLAT, with the vendor's home validation (PTB-XL fold 10) as the prior: at
  each threshold, the home hits and misses are added to the target counts. This borrows the
  vendor's evidence, as a hospital might when it treats the vendor's validation as prior
  knowledge.
- **RILEY-SIZE.** Precision-based minimum sample size, then point estimates. The policy switches
  on only when the labels hold enough positives to estimate sensitivity at s* to within ±0.05,
  and enough negatives to estimate FPR at f* to within ±f*/2 (95% intervals; 139 positives, and
  for example 1,010 negatives at f* = 0.015). It then accepts KEEP / CALIBRATE / ADAPT on point
  estimates, as NAIVE-VAL does. This adapts the precision-based approach of Riley et al. (Stat
  Med 2021; BMJ 2024), which sets sample sizes for calibration and discrimination, to the two
  criteria used here.
- **CORAL.** Unsupervised domain adaptation (Sun, Feng and Saenko, AAAI 2016). The target
  embeddings are aligned to the source's mean and covariance (PTB-XL folds 1-8) and scored by the
  network's own output layer at the vendor threshold. No labels are used.
  - The output layer was recovered from the stored PTB-XL scores and embeddings by least squares
    on the logit scale. It reproduces the scores to within 0.003 on the logit scale (unsaturated
    scores; saturated ones lost precision when stored as 32-bit floats) and to within 0.00002 on
    the probability scale at the targets.
- **CORAL-VAL.** CORAL scores, threshold recalibrated on the labels (highest threshold reaching
  s*), switched on if the point estimates meet both criteria.

## Results (31 transfers, 159 transfer-budget cells, 100 repeats)

| policy | mean unsafe | worst cell | cells above 5% | mean switched on |
|---|---|---|---|---|
| CAB | 0.1% | 2% | 0 | 14.4% |
| BAYES-FLAT | 0.6% | 7% | 1 | 15.6% |
| BAYES-MATCHED | 0.1% | 2% | 0 | 12.4% |
| BAYES-HOME | 11.3% | 68% | 65 | 33.1% |
| RILEY-SIZE | 9.6% | 64% | 31 | 19.7% |
| CORAL | 95.6% | 100% | 152 | 100.0% |
| CORAL-VAL | 28.6% | 70% | 107 | 43.1% |
| NAIVE-VAL (E3) | 32.4% | 80% | 115 | 52.7% |
| CRC (E3) | 16.3% | 54% | 82 | 31.9% |

The 16,000 budget is reached only at Ningbo, so that row of the by-budget table in the report
describes Ningbo alone.

## Reading

- **Label-free domain adaptation does not make an imported model safe.** CORAL left 30 of 31
  transfers unsafe at the vendor threshold. Matching the feature distribution does not restore
  the operating point.
- **Borrowing the vendor's evidence is unsafe.** BAYES-HOME's prior is the home validation, which
  is exactly what no longer holds after the transfer. With few target labels the prior dominates
  and the policy switches on configurations that fail at the target. Its unsafe rate falls as
  labels outweigh the prior (15% at 250 labels, 3% at 16,000).
- **A sample-size rule does not fix point-estimate validation.** Once RILEY-SIZE has enough
  labels it behaves like NAIVE-VAL. Its unsafe rate rises with the budget (0% at 250, where it
  rarely switches on; 17-38% at 4,000-16,000), because precise estimates of a configuration
  that sits just past a criterion still pass half the time.
- **Flat-prior Bayesian updating comes close to CAB on ECG.** BAYES-FLAT was 0.6% unsafe on
  average, with one cell above 5% (7%), and switched on slightly more often than CAB (15.6% vs
  14.4%). Requiring 95% posterior probability for each criterion acts much like a one-sided 5%
  test for each, so it is a less strict form of what CAB does.
  - The difference is the guarantee. CAB's error is bounded at alpha for every transfer.
    BAYES-FLAT's is not: with two criteria at 5% each and a threshold chosen from the same data,
    its error can exceed 5%, as it did in one cell here.
  - On ECG most transfers are far from the criteria, which hides the difference. Transfers near
    the boundary (expected in sepsis, where home and target rates are closer) are where it
    shows.
  - This should be reported plainly, not hidden: on these data a careful Bayesian analysis would
    usually have been safe too. CAB's added value is a guarantee that holds without relying on
    the transfers being far from the boundary, plus the ADAPT stage.
- **At equal strictness, CAB's gain is the ADAPT stage.** BAYES-MATCHED was as safe as CAB
  (0.1% mean, worst cell 2%) but switched on less often: 12.4% vs 14.4% overall, and 49% vs 80%
  at Ningbo's 16,000 labels.
  - The difference comes from transfers that only an adapted model can make safe, which a policy
    on the imported model alone has to block.
  - So, against a careful Bayesian analysis, CAB offers two things: a frequentist guarantee
    stated in advance, and a certified way to adapt the model when recalibration is not enough.
- **Not done.** No Bayesian hierarchical model across sites was tried. That would need several
  labelled target sites at once, which is not the import setting.

## References checked (2026-10-31)

- Riley RD, Debray TPA, Collins GS, et al. Minimum sample size for external validation of a
  clinical prediction model with a binary outcome. Stat Med. 2021;40:4230-4251.
  doi:10.1002/sim.9025
- Riley RD, Snell KIE, Archer L, et al. Evaluation of clinical prediction models (part 3):
  calculating the sample size required for an external validation study. BMJ. 2024;384:e074821.
  doi:10.1136/bmj-2023-074821
- Sun B, Feng J, Saenko K. Return of frustratingly easy domain adaptation. AAAI 2016:2058-2065.
  doi:10.1609/aaai.v30i1.10306
