# WP6: fewer labels (design)

Draft, 2026-10-30.

## Problem

CAB certifies sensitivity with an exact binomial test on randomly labelled records. The
binding resource is positives: at delta = alpha/4, at least 42 positives are needed even with
no misses, so a finding with prevalence p needs at least 42 / p random labels. In the ECG study
this is why 8-11 of 31 transfers were blocked although a safe remedy existed (E5).

Labelling more of the records the model scores high finds positives faster, but the labelled
set is then no longer random, and the binomial test is no longer valid. WP6 needs a test that
stays exact under a known, non-uniform labelling design.

## Reformulation

For threshold tau and a cohort of N records with labels y_i and scores s_i:

    sensitivity >= s*   <=>   mean_i z_i >= 0,   z_i = y_i * (1[s_i >= tau] - s*)
    FPR <= f*           <=>   mean_i w_i <= 0,   w_i = (1 - y_i) * (1[s_i >= tau] - f*)

Both are means of bounded quantities over the cohort, which is the primary judge's estimand.

## Design

Draw records one at a time, with replacement, from the cohort with known probabilities q_i
set from the imported scores before any label is seen:

    q_i = eps / N + (1 - eps) * g(s_i) / sum_j g(s_j)

g favours records likely to be positive (e.g. g = score or sqrt(score)); the floor eps keeps
every record reachable and bounds the weights. Then x = z_i / (N q_i) is an unbiased draw of the
cohort mean of z, bounded in [-s* / (N q_min), (1 - s*) / (N q_min)], and the same holds for w.

Test with a betting confidence sequence for the mean of bounded i.i.d. variables [to verify:
Waudby-Smith and Ramdas, JRSS-B 2024]. The capital K_t = prod (1 + lambda_t (x_t - 0)), with
predictable lambda_t >= 0 small enough to keep each factor positive, is a nonnegative
supermartingale when the mean is <= 0. Reject (certify) when K_t >= 1/delta (Ville's
inequality). This is exact at every sample size, and anytime-valid: labelling can stop as soon
as the evidence suffices, which is the "sequential labelling" part of WP6.

Choices to make by simulation: g, eps, the betting rule for lambda_t.

## Feasibility study (this step)

To isolate the label question, certify one pre-chosen threshold per transfer (the cohort's
highest threshold with sensitivity >= s* + 0.02 and FPR <= f*; an oracle choice) and compare
labels needed until certification, over 100 repeats:

1. CAB's test: random labels, exact binomial on sensitivity and FPR at fixed n (smallest n on a
   grid with power >= 50%).
2. Betting test, uniform sampling (shows the effect of the test alone).
3. Betting test, score-weighted sampling, several g and eps.

Validity check: thresholds where the cohort's sensitivity is exactly at or just below s*, with
the betting test run to the label cap; the rate of certification must stay <= delta.

## Open questions for after the feasibility study

- Threshold choice with weighted labels (fixed sequence over a threshold grid, as now).
- ADAPT with weighted labels: the head must be fitted on records whose labels are not used for
  certification; weighting the fit is optional, the test half must use the design above.
- Labelling with replacement counts repeated records once in cost; or a without-replacement
  version of the betting test.
- Comparison with prediction-powered inference [to verify: Angelopoulos et al., Science 2023]
  and active inference [to verify: Zrnic and Candes, 2024], which give asymptotic, not exact,
  guarantees.

## Feasibility results (2026-10-30)

`wp6_betting.py` (test), `wp6_feasibility.py` -> `outputs/ecg/WP6_feasibility.md`.

- Validity: on a synthetic cohort with sensitivity exactly 0.90, the betting test certified in
  0-1 of 1,000 repeats (limit delta = 0.0125) under uniform, score-weighted and band designs.
- Labels to certify one oracle threshold (sensitivity >= 0.92 and FPR <= f* on the cohort;
  9 transfers have one), by which half of 100 repeats certified. Binomial = CAB's test on random
  labels, on a grid in steps of sqrt(2).

  | Transfer | Prevalence | Binomial | Betting, uniform | Best weighted |
  |---|---|---|---|---|
  | Georgia IAVB | 7.4% | > 10,344 | > cap | 8,070 (band) |
  | Georgia SB | 16.2% | 8,000 | 8,722 | 4,966 (band) |
  | Chapman SB | 38.0% | 2,828 | 4,929 | 5,228 (band) |
  | Chapman STach | 15.3% | 8,000 | 8,164 | 4,460 (score) |
  | Ningbo RBBB | 3.7% | 32,000 | > cap | 15,241 (band) |
  | Ningbo SB | 36.3% | 4,000 | 6,512 | 7,023 (band) |
  | Ningbo IAVB, LBBB; CPSC-Extra RBBB | 0.7-3.3% | none | none | none |

- Reading:
  1. Weighted designs save labels for findings of middling prevalence: about 1.6-2x against
     the binomial (Georgia SB, Chapman STach, Ningbo RBBB), and they make Georgia IAVB
     certifiable at all. Sampling the band just below the threshold, where misses would be,
     was the best design in three of four.
  2. For common findings (SB at 36-38%), the exact binomial on random labels beats every betting
     design; the betting rule (aGRAPA) is less efficient than the exact test when positives are
     plentiful.
  3. The rarest transfers stay out of reach under every design. Proving sensitivity means ruling
     out misses, and misses are positives the model scores low: no design based on this model's
     scores can seek them out, so most of the cost of bounding them remains. My first statement
     that score weighting cannot help at all was too strong; it helps where misses sit just below
     the threshold.
- Directions, not yet chosen:
  a. Without-replacement betting (labels here are 15-45% of a cohort, where sampling without
     replacement narrows the bounds a lot) and a better betting rule. Pure method work; helps every
     design, including uniform.
  b. A hybrid gate: binomial on random labels for common findings, band-weighted betting
     otherwise, with the choice fixed in advance from the scores alone.
  c. A second, independent signal to find misses (e.g. the ECG machine's own automatic
     interpretation, which exists for nearly every ECG). The only route past the floor, but
     needs data we don't have in these cohorts.

## Without-replacement test (2026-10-30)

Added to `wp6_betting.py`: strata fixed from the scores (above tau, the band of 2x as many
records just below it, the rest), each labelled in random order without replacement on a
schedule fixed in advance; an anytime-valid lower bound per stratum from without-replacement
betting, combined with the union bound. No record is labelled twice; a fully labelled stratum
is known exactly.

- Validity: synthetic cohort with sensitivity 0.8967, labelling allowed up to the whole cohort:
  0 of 400 repeats certified, unstratified and stratified.
- Labels by which half of 100 repeats certified both criteria (oracle threshold, as before):

  | Transfer | N | Binomial | Best with replacement | WoR uniform | WoR strata 25/25/50 | WoR strata 10/40/50 |
  |---|---|---|---|---|---|---|
  | Georgia IAVB | 10,344 | none | 8,070 | 7,923 | 9,962 | 9,539 |
  | Georgia SB | 10,344 | 8,000 | 4,966 | 6,625 | 9,394 | 9,407 |
  | CPSC-Extra RBBB | 3,453 | none | none | 3,433 | 3,439 | 3,440 |
  | Chapman SB | 10,246 | 4,000 | 4,770 | 4,281 | 7,523 | 8,049 |
  | Chapman STach | 10,246 | 8,000 | 4,858 | 6,676 | 9,286 | 7,797 |
  | Ningbo IAVB | 34,904 | none | none | 30,724 | 34,904 | 34,904 |
  | Ningbo RBBB | 34,904 | 32,000 | 15,295 | 22,268 | 15,420 | 16,604 |
  | Ningbo LBBB | 34,904 | none | none | 32,422 | 31,312 | 30,990 |
  | Ningbo SB | 34,904 | 4,000 | 6,549 | 6,319 | 25,797 | 21,001 |

- Reading:
  1. Without replacement, every transfer can be certified eventually, but for the rare ones
     (Ningbo IAVB and LBBB, CPSC-Extra RBBB) only after labelling 88-99% of the cohort. That is
     no saving: it amounts to labelling everything.
  2. Stratifying without replacement was worse than not stratifying in most transfers: the error
     budget is split three ways, and the large "rest" stratum still has to be bounded.
  3. Nothing beat the exact binomial on random labels for common findings, and nothing beat
     band-weighted sampling with replacement for middling ones.
- Conclusion for WP6. With only the imported model's scores to steer labelling, the savings are
  about 1.6-2x for findings of middling prevalence, from band-weighted sampling, and none for
  rare findings. The rare-finding cost comes from having to rule out misses the model scores low,
  and no score-based design can find those efficiently. Routes past it need either a second,
  independent signal to find misses (direction c), or a weaker guarantee (asymptotic methods such
  as prediction-powered inference), which would give up CAB's exactness.

## Hybrid gate (2026-10-30) and conclusion

`wp6_hybrid.py` -> `outputs/ecg/WP6_hybrid.md`. Design chosen per transfer from the scores alone:
random labels with CAB's binomial tests where the vendor threshold flags at least 25% of the
target (SB at Chapman and Ningbo), otherwise band-weighted draws around the label-free threshold
with the betting tests. Recalibration only (KEEP / CALIBRATE / BLOCK); thresholds on a label-free
grid in fixed sequence; whole-cohort judge; 31 transfers, all budgets, 100 repeats.

| Gate | Mean unsafe | Worst transfer | Cells over alpha | Runs switched on | Transfers half on |
|---|---|---|---|---|---|
| CAB recalibration, random labels | 0.1% | 0.8% | 0 | 12.3% | 5 |
| Hybrid recalibration | 0.0% | 0.8% | 0 | 10.2% | 4 |

The hybrid is as safe and less useful. It loses Chapman STach (half on at 4,000 labels with CAB,
never with the hybrid) and delays Georgia SB (500 to 2,000 labels). The feasibility gains came from
an oracle threshold with the band placed around it. In a real gate the threshold must be searched
over a grid of candidates, each tested in turn, and the band is placed around a label-free guess.
Under those conditions the exact binomial on random labels is the better test.

Conclusion for WP6 (2026-10-30):
- Keep CAB's design: random labels and exact binomial tests.
- Result for the paper: with labelling steered only by the imported model's scores, no design we
  tried saves labels in a working gate. Weighted with-replacement betting, without-replacement
  stratified betting and a hybrid all fail to. The reason: proving sensitivity means ruling out
  missed positives, which the model scores low, so a score-based design cannot seek them out.
  The rare-finding label cost (about 42 / prevalence random labels at least) is the price of an
  exact guarantee with no other information.
- Routes left, not pursued now: a second, independent signal that finds misses (e.g. the ECG
  machine's own interpretation); or an asymptotic guarantee (prediction-powered inference), which
  gives up exactness. Either could be revisited for the sepsis data, where other signals (orders,
  cultures) exist.
- Code kept for reproducibility: `wp6_betting.py`, `wp6_feasibility.py`, `wp6_hybrid.py`.
