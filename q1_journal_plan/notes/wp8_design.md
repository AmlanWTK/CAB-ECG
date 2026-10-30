# WP8: monitoring after deployment

2026-10-30. First build and test on the ECG domain; the sepsis test (MIMIC-IV temporal split,
eICU) waits for PhysioNet access. Code: `code/wp8_monitor.py`. Results:
`outputs/ecg/W8_report.md` (window 100, primary) and `W8w50`, `W8w250`, `W8w500` (window
sensitivity analysis).

## Question

Once the gate has switched a model on, the population it reads can change (a new site, a new
device, a new case mix). Can a monitor re-open the gate when the switched-on configuration stops
meeting the criteria, with its own error guarantee, without false alarms while it still meets
them?

## Design

- **Audits.** After deployment a random sample of the cases the model reads is labelled, one at a
  time (for ECG: a cardiologist reads the ECG; for sepsis: chart review or the Sepsis-3 label once
  it is known).
- **Monitor.** Two betting tests on the audits, each at delta/2:
  - positives: x = s* - hit, mean <= 0 while sensitivity >= s*;
  - negatives: x = hit - f*, mean <= 0 while FPR <= f*.
  - Capital K_t = prod(1 + lambda_i x_i). The bets lambda_i >= 0 use only earlier audits:
    aGRAPA on a sliding window of the last W observations, clipped so each factor is at least
    1 - c (c = 0.5). An alarm is raised when either capital reaches 2/delta.
- **Guarantee.** While every audit comes from a population on which the configuration is safe,
  each capital is a nonnegative supermartingale. By Ville's inequality the probability of any
  false alarm, over an unlimited number of audits, is at most delta. This holds whatever the
  bets, as long as they are chosen before each audit is seen; the window only affects power.
- **Why a window.** With bets estimated from all past audits, a long safe history holds the bets
  at zero for a long time after a change. The window lets them respond to recent audits.
- **Comparators** (no guarantee over repeated looks):
  - CHECK-POINT: every 250 audits, the point estimates on the last 250 audits against s* and f*.
  - CHECK-TEST: every 250 audits, exact one-sided binomial tests on the last 250 audits at
    delta/2 each, uncorrected for the repeated looks.

## ECG experiment

- **Deployments.** Each target cohort as site A, each judged finding, 200 repeats. CAB runs at
  the site's largest label budget (as in E3); runs it blocks are not monitored. 1,533 of 6,200
  deployments were switched on. Three were unsafe at A (CAB's own errors) and are excluded.
- **Streams.** 2,000 audits drawn from A's population, then 4,000 from B. B is every cohort with
  at least 50 positives for the finding, including A itself (no change) and the Brazilian cohort
  with the signal gain halved (`code15_half`, a device change). CAB switches nothing on at
  `code15`, so the gain change is only seen as a move from another site.
- **Truth.** The deployed model and threshold judged on the whole cohort being read (the primary
  judge of E3).
- delta = 0.05; s* = 0.90; f* = relative margin (as in the ECG primary analysis).

## Results (window 100; `outputs/ecg/W8_report.md`)

False alarms, as the share of runs with any alarm while every audit came from a safe population,
over 6,000 audits:

| scenario | runs | MONITOR | CHECK-POINT | CHECK-TEST |
|---|---|---|---|---|
| no change | 1,530 | 0.0% | 99.7% | 9.3% |
| change to a population where it is still safe | 1,715 | 0.0% | 98.9% | 11.7% |

Drift to a population where the configuration is unsafe (5,802 runs, 58 scenarios):

| monitor | alarm before the change | detected within 4,000 audits | median audits to alarm |
|---|---|---|---|
| MONITOR | 0.0% | 65.2% | 538 |
| CHECK-POINT | 93.2% | 6.8% | 250 |
| CHECK-TEST | 2.8% | 82.6% | 250 |

Detection depends on how far past the criteria the configuration falls. Runs that fail
sensitivity only (2,053):

| sensitivity below s* by | runs | MONITOR | CHECK-TEST |
|---|---|---|---|
| up to 0.02 | 280 | 1% | 24% |
| 0.02-0.05 | 471 | 19% | 52% |
| 0.05-0.10 | 496 | 48% | 72% |
| 0.10-0.20 | 250 | 53% | 80% |
| more than 0.20 | 556 | 84% | 94% |

Runs that fail FPR only (485):

| FPR / f* | runs | MONITOR | CHECK-TEST |
|---|---|---|---|
| 1.0-1.1 | 176 | 2% | 37% |
| 1.1-1.25 | 170 | 25% | 54% |
| 1.25-1.5 | 64 | 78% | 86% |
| 1.5-2.0 | 69 | 100% | 99% |

Runs that fail both criteria (3,264): MONITOR 82%, CHECK-TEST 95%.

Window sensitivity analysis: detection 65.6%, 64.1% and 62.8% for windows 50, 250 and 500, and
false alarms at most 0.2% throughout. The window is not what limits power.

## Reading

- The monitor is the only one of the three that keeps its error promise. Point-estimate checks
  alarm in almost every safe run. Uncorrected repeated tests alarm in about 10% of safe runs
  over 6,000 audits, and their false-alarm rate keeps growing with the number of looks.
- The cost of the guarantee is power against drifts just past the criteria. Large drifts are
  found, typically within a few hundred to two thousand audits. Part of CHECK-TEST's extra
  detection of small drifts comes from the same tendency to alarm that gives it false alarms
  when nothing is wrong.
- Detection of sensitivity drift is limited by the number of audited positives. At 2-4%
  prevalence, 4,000 audits contain 80-160 positives, too few to show that sensitivity is
  0.88 rather than 0.90. For sepsis, monitoring sensitivity will need positive-enriched audits
  (for example, auditing every confirmed septic case for whether it was alerted), which keeps the
  guarantee if the enrichment rule is fixed in advance.
- The monitor uses less than its error budget: no false alarms in 3,245 safe runs, against an
  allowed 5%. Possible gains, to test on ECG before fixing for sepsis:
  - a CUSUM-type e-detector (Shin, Ramdas and Rinaldo), which controls the average time to a
    false alarm instead of the probability of any false alarm;
  - bets mixed over a grid of fractions instead of a single estimated bet.

## Open

- Choose the guarantee for the paper: the probability of any false alarm (as here) or the
  average run length to a false alarm (CUSUM-type). Clinically, the first is simpler to state.
- Sepsis: patient-level criteria mean an audit is a whole stay. The MIMIC-IV temporal split
  (earlier anchor-year groups as A, later as B) is the planned test.
- References to check before writing: Ville (1939); Waudby-Smith and Ramdas (JRSS-B 2024) for
  betting confidence sequences and aGRAPA; Shin, Ramdas and Rinaldo (e-detectors).
