# Response to the review of Section 3

2026-11-02. Each point checked against the code that produced the results
(`code/sepsis_e1_baselines.py`, `code/sepsis_e3_cab.py`, `code/cabsepsis/cab.py`,
`code/cabsepsis/features.py`, `code/sepsis_e5_labels.py`). "Changed" means the text of Section 3
now says this.

## Fix before moving on

1. **Definition of F_home and the home-control claim.** Checked in `prepare_direction`: F_home is
   the observed false-alert rate on the vendor's validation patients at τ_home, a fixed number
   known before any local label. Changed: 3.2 and 3.3 say so, and that f* = F_home + m is
   benchmarked against that report. The reviewer was right that KEEP is then not always correct
   at home. The correct remedy, computed on the test patients (`*_oracle.csv`), was KEEP in 13 of
   the 18 home settings, including both at the primary requirements. With m = 0 it was CALIBRATE
   in 4 settings and "ADAPT or BLOCK" in 1. Changed: 3.7 no longer says KEEP is correct by
   construction; it gives these counts.
2. **Lemma 1.** Rewritten without the continuity phrase. With U = {t : S(t) < s*} and
   u = inf U, two cases: S(u) < s*, where the count at u is used; or S(u) ≥ s*, where the count
   of scores strictly above u is used, whose success probability Pr[W > u] is at most s*. In both
   cases the event S(τ̂) < s* implies that a count at a fixed, population-defined threshold
   reaches d_min, and that count is stochastically no larger than Bin(K, s*). Ties are handled
   explicitly (they only increase D(τ̂)). The only limit used is Pr[W > u] = lim S(t) as t
   decreases to u, which is the monotone limit of the events {W ≥ t}.
3. **d_min when no d ≤ K exists.** Changed: the text after (3) defines d_min as undefined and no
   threshold certified. The code does the same (`certified_threshold` returns `None`).
4. **Label calculator's joint 90%.** The reviewer is right. `septic_needed` and
   `nonseptic_needed` compute power at fixed true rates with √0.9 each. Changed: 3.8 says the
   calculation is at a fixed operating point, that the 90% holds exactly at a fixed threshold
   (the KEEP route) because the two tests use independent patients, and that for CALIBRATE and
   ADAPT it is a planning approximation, checked against simulation in Section 4.5.
5. **Prediction target and post-onset hours.** Checked in `sepsis_e1_baselines.py`: the models
   are trained on every hour of the training patients with the Challenge's hourly label, which is
   positive from 6 h before onset onwards, including after onset. Changed: 3.2 says this. 3.1
   says the onset is the Challenge's retrospective Sepsis-3 onset, not an adjudicated one.
6. **Stage 1 prose.** Changed to the reviewer's wording: if τ is certified and its false-alert
   test passes, KEEP if τ_home ≤ τ and its own false-alert test passes, otherwise CALIBRATE.

## Other points

- **Feature timing.** Checked in `features.py`: the last value is carried forward; rolling
  statistics use the current and five preceding hours; change over 1 h and 6 h. Changed: 3.2
  says so. Also corrected: the administrative feature is the time from hospital admission to
  ICU admission (the Challenge's HospAdmTime), not "hours since hospital admission"; the ICU
  length-of-stay feature is the hours since ICU admission at that hour.
- **Vendor threshold search.** Changed: 3.2 explains why searching from the most sensitive end
  finds the highest passing threshold, and that the vendor's 5% test is separate from CAB's
  α/4 tests.
- **Adaptation candidates.** Changed: 3.4 gives the 20% early-stopping subset (excluded from
  fitting), the boosting settings (learning rate 0.03, 15 leaves, at most 1,000 rounds, patience
  50), the meaning of decay 0.9 (LightGBM's refit: new leaf = 0.9 × imported + 0.1 × local
  estimate, confirmed in LightGBM 4.6's documentation), and that ties go to the first candidate.
- **Comparators.** Changed in Table 4 and the paragraph above it: NAIVE-500 uses the first 500
  in random order or all when fewer; CLOSED-TEST's tests, data and levels; LTT-DIRECT's choice
  when both or neither pass; point-estimate policies reuse their labelled patients for threshold
  and check; LABEL-FREE matches alerted patient-hours, a different quantity from (2).
- **Correct remedy is an evaluation reference.** Changed: 3.7 says so explicitly.
- **Evaluation populations.** Checked in `prepare_direction`: for transfers, labels come from
  the receiving hospital's training and validation patients and judging uses all its other
  patients; at home, both use only the test patients, which the source model never saw. Changed:
  3.7 states both, and that every patient used for fitting, early stopping, threshold selection
  or certification is excluded from judging.
- **Theorem scope.** Kept as stated. Its four conditions (model and τ_home fixed in advance,
  adapted model from the fit half only, certification half independent, patient-level counts)
  are A1–A3 and the definitions in 3.3.
- **Reproducibility.** Changed: 3.9 lists what the repository contains. Added to the submission
  checklist: cite the release or commit that produced the results.

## Second round (2026-11-02)

1. **Lemma 1, score domain.** Changed: the proof now states that model scores are predicted
   probabilities in [0, 1], so S(t) = 1 for t ≤ 0. With s* ∈ (0, 1) this makes u = inf U a
   number in [0, 1] without further assumptions. The limit in Case 2 is justified explicitly: as
   t decreases to u the events {W ≥ t} increase to {W > u}.
2. **Notation.** The certified threshold is now written τ in running text and in (3), matching
   Stage 1 and Algorithm 1. The previous τ̂ was a combining character that broke when text was
   copied from the PDF. Case labels in Lemmas 1 and 3 and in the theorem's proof are now bold
   "Case 1/2/3" and the stage names, because italics around "f*" and "s*" did not render. The
   rendered pages were checked.
3. **Lemma 3, Case 1.** Changed: it now says that KEEP deploys at τ_home but is reached only after
   the false-alert test at τ has passed.
4. **A3.** Changed: the adapted model "depends only on the fit half and is fixed before the
   certification half is examined".
5. **Home control wording.** Changed to: the source model was fitted on the training set, with
   the validation set used for early stopping and for choosing the vendor's threshold.
6. **Reproducibility.** The claim of exact reproducibility is removed. 3.9 now says the
   experiments ran in one fixed software environment and that every random choice is driven by
   recorded seeds.
7. **Vendor threshold edge cases.** Checked: all six vendor thresholds passed the vendor's 5%
   test (lower 95% bounds 0.752, 0.803 and 0.851 at hospital A; 0.751, 0.803 and 0.851 at
   hospital B, for s* = 0.75, 0.80, 0.85), so the code's fallback was never used. Ties are
   counted as reaching the threshold. Both now stated in 3.2.
8. **Detections after onset.** Changed: 3.3 says that because the window extends to 3 h after
   onset, a detection is not necessarily a warning before onset, and points to the lead-time
   analysis. Added to the submission checklist: keep this wording consistent in the abstract,
   results, discussion and conclusion.
9. **Home-control counts.** Rechecked against `E10baselines_oracle.csv`: KEEP in 13 of 18.

## Third round (2026-11-02)

1. **f* above 1.** Checked in `E10baselines_oracle.csv` and `E10units_oracle.csv`: across all
   settings f* ranges from 0.285 to 0.584. Changed: 3.3 states this range, and that if F_home + m
   reached 1, every threshold would meet the false-alert requirement, so no violation of it is
   possible and the guarantee is unaffected. (In the code a probability above 1 would make the
   test fail, which can only make CAB more cautious.)
2. **Notation in Lemma 1.** The count of scores strictly above u is now C(u), a plain symbol,
   instead of D⁺.
3. **Section 3.8 opening.** Changed to the reviewer's wording.
4. **Labelled patients excluded from judging.** Checked in `one_run`: every policy is judged on
   `comp = eligible & ~lab`, the eligible patients not labelled, which includes every patient used
   for fitting, early stopping, threshold selection or certification.
5. **Randomness.** Checked: data splits and source models use `SEED = 0`
   (`sepsis_e1_baselines.py`, `train_test_split` and LightGBM `random_state`); each run's seed
   depends only on scenario, budget and repetition and drives the label sample, the halves, the
   early-stopping split and the adapted and retrained models (`one_run`, `boost`). Changed: 3.9
   now names both kinds of seed.
6. **α/4 in the code.** Checked: `cab_select` sets `d = alpha / 4` and uses it for every
   threshold certification and false-alert test.
7. **Table 3.** Checked against `outputs/sepsis/worked_example.md`: all counts, bounds and
   decisions match.
