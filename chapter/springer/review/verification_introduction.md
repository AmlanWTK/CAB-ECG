# Verification of the Introduction's claims

2026-11-01. Two checks requested on the Introduction: (1) that the safety guarantee holds when CAB
chooses among several configurations, including an adapted model; (2) that contribution 4 matches
the results.

## 1. The safety guarantee

Claim: the probability that CAB deploys a configuration violating either requirement is at most
α, for any shift and any number of labels, if the labelled patients are a random sample of the
receiving hospital's patients and their labels are correct.

Checked against the proof (Section 3.5; full version in `chapter/guarantee.md`) and the code
(`code/cabsepsis/cab.py: cab_select`, `code/sepsis_e3_cab.py: one_run, fit_adapt`).

- **Several configurations.** CAB can deploy one of three: KEEP (imported model, vendor
  threshold), CALIBRATE (imported model, certified threshold) or ADAPT (adapted model, its own
  certified threshold). Each test runs at δ = α/4.
  - Stage 1, imported model, all labels. A sensitivity error is possible only if the certified
    threshold has true sensitivity below s*, because KEEP's threshold is no higher (probability
    at most δ). A false-alert error needs a false-alert test to pass at a threshold whose true
    rate exceeds f*. Which threshold that can be is decided by the septic patients alone, so only
    one test can err (probability at most δ). Stage 1 costs 2δ.
  - Stage 2, adapted model, certification half: the same two arguments, 2δ.
  - At most one configuration is deployed, so the union bound gives 4δ = α.
- **The adapted model does not reuse its certification data.** In the code, the labelled
  patients are split into a fit half and a certification half, separately within septic and
  non-septic patients, before any model is fitted (`one_run`). The adapted model, its three
  candidates and the early-stopping subset that chooses between them use only the fit half
  (`split_patients(fit)`, `fit_adapt`). Its threshold and both tests use only the certification
  half (`cab_select(..., lab_cert, ...)`). Conditional on the fit half the adapted model is a fixed
  function, and the certification half is an independent sample, so the exact tests are valid.
- **Reaching Stage 2 depends on all labels, including the certification half.** This does not
  break the bound: the proof bounds the joint event "Stage 2 deploys an unsafe adapted model"
  by the unconditional probability that its certification tests pass when the model is unsafe,
  which is at most 2δ. The adapted model is fitted in every run, whatever Stage 1 decides.
- **Threshold chosen and tested on the same labels.** The certified threshold is chosen from the
  septic patients only; the false-alert test uses the non-septic patients only. Given each
  patient's class, the two groups are independent, so the threshold can be treated as fixed in
  the false-alert test.
- **Random number of septic patients.** The tests are conditional on the numbers of septic and
  non-septic patients labelled, so the bound holds for any such numbers and hence overall.

Not covered by the guarantee, and stated as such in the Introduction: labels that are wrong, a
labelled sample that is not random, and drift after deployment.

Conclusion: the bound is supported for selection among the three configurations, with the adapted
model fitted and certified on separate patients. No change to the method is needed.

## 2. Contribution 4 against the results

### "Samples of a few hundred patients rarely allowed any configuration to be certified"

The earlier wording, "too small to certify any configuration", was too strong; corrected.

CAB deployed a configuration (KEEP, CALIBRATE or ADAPT), share of runs, all nine criteria
(`outputs/sepsis/E10baselines_runs.csv`, `E10units_runs.csv`; 100 runs per setting):

| scenario | 250 labels | 500 labels | 1,000 labels |
|---|---|---|---|
| A→B (safe configuration exists for every criterion) | 0.0% | 0.0% | 0.7% |
| B→A | 0.0% | 0.0% | 0.0% |
| A→A, home control (KEEP correct) | 0.3% | 0.4% | 4.7% |
| B→B, home control (KEEP correct) | 0.1% | 2.1% | 10.3% |
| ICU-type imports (4 scenarios) | 0.0% | 0.0% | 0.0–0.4% |

Median septic patients labelled: 18 at 250 labels, 35 at 500, 71 at 1,000. At the primary
criterion: home control 0–2% at 500 labels; A→B 0% at 500 and 1,000 (correct remedy ADAPT).

New wording: "samples of a few hundred labelled patients rarely allowed any configuration to be
certified, even where a safe one existed."

### "The false-alert tolerance, not the vendor's threshold headroom, determined the labels needed"

Supported, for approving an unchanged model (KEEP or CALIBRATE) at the home control; the wording now
says so. `outputs/sepsis/E11_headroom.md`: models held fixed, s* = 0.80, 200 resamples per cell.

Mean share of runs approved over budgets of 1,000-32,000 labels:

| | headroom 0 | 2 | 4 | 6 | 10 points |
|---|---|---|---|---|---|
| A→A, tolerance 0 | 6% | 5% | 7% | 7% | 7% |
| A→A, tolerance 5 points | 47% | 45% | 46% | 47% | 47% |
| A→A, tolerance 10 points | 68% | 68% | 68% | 69% | 69% |
| B→B, tolerance 0 | 48% | 50% | 49% | 49% | 50% |
| B→B, tolerance 5 points | 67% | 64% | 67% | 65% | 66% |
| B→B, tolerance 10 points | 78% | 79% | 79% | 78% | 78% |

Headroom changes approval by at most 3 points; tolerance changes it by 20-62 points. At 8,000
labels, A→A approval was 4%, 54% and 98% for tolerances of 0, 5 and 10 points. To reach 90%
approval at A→A took about 16,000 labels at a tolerance of 5 points and 4,000-8,000 at 10
points; at a tolerance of 0 it was 22% even at 32,000.

Scope: this is shown at the home control with the models held fixed. Headroom does change how
many labels the KEEP route alone would need (A→A: about 109,000 patients at no headroom, 24,000
at 5 points), but CALIBRATE then approves the same configurations, so overall approval does not
change.

### Also checked (primary criterion, s* = 0.80, tolerance 5 points)

- B→A: blocked in 100% of runs at every budget from 250 to 12,000 (correct remedy BLOCK).
- A→B: ADAPT certified in 10%, 70% and 97% of runs at 4,000, 8,000 and 12,000 labels.
- Home control at 2,000 labels: B→B deployed in 25% of runs (KEEP 9%, CALIBRATE 14%, ADAPT 2%),
  A→A in 5%.
