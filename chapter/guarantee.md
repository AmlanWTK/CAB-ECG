# CAB's safety guarantee: statement and proof

Working note for the chapter's Methods section (§ "Statistical guarantee"). Code references are to
`code/cabsepsis/cab.py`. Write the chapter text afresh from this note (Turnitin < 18%).

## Setting

- **Target population.** The patients the hospital will admit after deployment. A model `g` with
  threshold `t` alerts a patient if its score reaches `t` at any hour of the stay.
  - `S_g(t)` is the probability that a septic patient is alerted between 12 h before and 3 h after
    onset (sensitivity).
  - `F_g(t)` is the probability that a non-septic patient is alerted at any time (false-alert rate).
- **Monotonicity.** For a fixed model, both rates fall as the threshold rises.
- **Safety targets.** These are fixed before any target label is seen: the sensitivity target `s*`,
  and `f* = F_home + margin`, where `F_home` is the vendor's own home false-alert rate.
- **Vendor threshold.** `τ_home` is fixed by the vendor on its own data.
- **Safe deployment.** A deployment `(g, t)` is *safe* if `S_g(t) ≥ s*` and `F_g(t) ≤ f*`.
  Blocking is always safe: no model is switched on.
- **Labelled data.** The hospital labels `n` patients drawn at random from the target population.
  CAB splits them, within the septic and non-septic groups, into a *fit* half and a
  *certification* half, before any model is fitted.

## Assumptions

- **A1. Exchangeability.** The labelled patients and future patients are independent draws from
  the same population. So, given each patient's septic status, their alert times are independent
  draws from the population's distribution for that status.
- **A2. Labels are correct.** In particular, sepsis onset follows the same definition the targets
  use.
- **A3. No outside information enters the tests.**
  - `s*`, `f*`, `τ_home`, `α` and the imported model are fixed before labelling.
  - The adapted model `g_A` uses only the fit half: training, early stopping and the choice among
    the three adaptation variants (`fit_adapt` uses only fit-half patients).

## The procedure (`cab_select`)

Write `δ = α/4`. Write `k` and `m` for the numbers of septic and non-septic patients in the data
set being tested.

**Threshold certification (`certified_threshold`).** Sort the septic patients' window-maximum
scores in descending order. Let `d_min` be the smallest detection count `d` for which the exact
binomial test of `H0: S < s*` rejects, i.e. `P(Bin(k, s*) ≥ d) ≤ δ`. Return the threshold that
detects exactly `d_min` patients, which is the highest threshold that passes.

**False-alert test (`fa_test`).** Reject `H0: F(t) > f*` at threshold `t` if
`P(Bin(m, f*) ≤ observed false alerts) ≤ δ`.

**Stage 1, imported model `g_0`, on all labelled patients:**
- Find `τ` by threshold certification, then run the false-alert test at `τ`.
- If `τ` is not found, or the test fails, go to Stage 2.
- If the test passes, `τ_home ≤ τ`, and the false-alert test at `τ_home` also passes, deploy
  `(g_0, τ_home)`: **KEEP**.
- Otherwise deploy `(g_0, τ)`: **CALIBRATE**.

**Stage 2, adapted model `g_A`, on the certification half only:**
- Find `τ_A` by threshold certification on the certification half, then run the false-alert test
  at `τ_A`.
- If both pass, deploy `(g_A, τ_A)`: **ADAPT**.
- Otherwise **BLOCK**.

## Theorem

Under A1–A3, for any target population, any shift between the vendor's hospital and the target,
and any sample size `n`:

> P( CAB switches on an unsafe deployment ) ≤ α.

The bound holds exactly in finite samples. It needs no model of the shift and makes no assumption
that either model is well calibrated.

## Proof

Call a *sensitivity error* the event that the deployed pair has `S < s*` and a *false-alert
error* the event that it has `F > f*`. An unsafe deployment is a sensitivity error, a false-alert
error, or both. We bound each error in each stage by `δ`.

**Lemma 1 (threshold certification).** Fix a model and a set of `k` septic patients whose alert
times are i.i.d. from the population. Then

`P( the certified τ has S(τ) < s* ) ≤ δ`.

*Proof.* Let `t₊` be the lowest threshold with `S(t₊) < s*`. It depends only on the population,
not the sample. Write `t₊ = ∞` if there is none, in which case the event is empty.

Because `S` is monotone, every threshold with `S < s*` is at least `t₊`. Suppose the certified
`τ ≥ t₊`. Detections can only fall as the threshold rises, so the count `D(t₊)` of patients
detected at `t₊` satisfies `D(t₊) ≥ D(τ) = d_min`.

`D(t₊)` is `Bin(k, S(t₊))`, and `S(t₊) < s*`. So

`P(D(t₊) ≥ d_min) ≤ P(Bin(k, s*) ≥ d_min) ≤ δ`,

where the last inequality is the definition of `d_min`. ∎

This is the fixed-sequence form of Learn-then-Test. Thresholds are tested from the most sensitive
end, and the passing thresholds form a prefix, so no multiplicity correction is needed.

**Lemma 2 (false-alert test at a threshold chosen from the septic patients).** Let `t` be any
threshold computed from the septic patients only (for example `τ`), or fixed in advance (for
example `τ_home`). Then

`P( F(t) > f* and the false-alert test passes at t ) ≤ δ`.

*Proof.* By A1, given each patient's septic status, the non-septic patients' alert times are
independent of the septic patients' alert times. Condition on the septic patients, which makes
`t` fixed.

If `F(t) ≤ f*`, the event is empty. Otherwise the observed false-alert count is
`Bin(m, F(t))` with `F(t) > f*`. It is stochastically larger than `Bin(m, f*)`, so the exact test
rejects with probability at most `δ`. Removing the conditioning keeps the bound. ∎

**Stage 1 sensitivity.**
- CALIBRATE deploys at `τ`.
- KEEP deploys at `τ_home ≤ τ`, so by monotonicity `S(τ_home) ≥ S(τ)`.
- Either way, a sensitivity error implies `S(τ) < s*`, which has probability at most `δ` by
  Lemma 1.

**Stage 1 false alerts.** Condition on the septic patients, so `τ` is fixed. Since
`τ_home ≤ τ`, monotonicity gives `F(τ_home) ≥ F(τ)`. There are two cases.

- *Case `F(τ) > f*`.* Both routes require the test at `τ` to pass. By Lemma 2 this has
  probability at most `δ`.
- *Case `F(τ) ≤ f* < F(τ_home)`.* CALIBRATE is safe. Only KEEP can err, and KEEP requires the
  test at `τ_home` to pass. By Lemma 2 this has probability at most `δ`.

The cases are decided by the septic data alone, so conditionally, and hence unconditionally, a
Stage 1 false-alert error has probability at most `δ`. The two false-alert tests do *not* cost
`2δ`.

**Stage 2.** By A3, `g_A` is a fixed function of the fit half. The fit half is independent of the
certification half (A1, and the split is made before fitting). Condition on the fit half.
Lemmas 1 and 2 then apply on the certification half and bound the Stage 2 sensitivity and
false-alert errors by `δ` each.

**Union.** CAB deploys at most one pair, so

`P(unsafe) ≤ P(Stage 1 error) + P(Stage 2 error) ≤ 2δ + 2δ = 4δ = α`. ∎

## Remarks for the chapter

1. **What is and is not promised.**
   - The guarantee is about the *decision*: an unsafe model is switched on in at most `α` of
     hospitals that follow the procedure.
   - It is not a promise that CAB *will* switch on a safe model. That is power, which depends on
     the labels and on how much slack the model has against the targets (E5 calculator, E11).
   - It also says nothing about drift *after* certification. That needs monitoring (future work:
     sequential tests).
2. **Variants.**
   - With the label-free skip screen, Stage 1 is not run and Stage 2 runs at `α/2`, so the bound
     is `2·α/2 = α`. The screen uses unlabelled data only, so A3 holds.
   - CAB-70 changes only the split, so the proof is unchanged.
3. **Conservativeness.** The union bound and the exact tests make CAB conservative.
   - Measured unsafe rates were 0.3–1.0% at `α = 0.05` (E12).
   - The price is power. Natural relaxations: a Bonferroni split weighted by expected power, or
     closed testing in place of the union bound.
4. **Why the measured rate can exceed α in a single setting.** Safety in the experiments is judged
   on the unlabelled eligible patients, not on the population.
   - At home with 2,000 labels, only about 110–180 septic patients remain for judging.
   - A deployment whose true sensitivity is exactly `s*` is then judged unsafe about half the time.
   - So a measured 6–7% in a few home settings is consistent with the bound. With 100 repeats,
     even a true rate of exactly 5% shows above 5% in about 38% of settings.
5. **Evidence (E12, `outputs/sepsis/E12_validity.md`).** CAB stayed well under the nominal level at
   every α. No setting's exact 95% interval lay wholly above α.

   | α | Group | Settings | Mean unsafe | Worst setting | Pooled 95% upper bound |
   |---|---|---|---|---|---|
   | 0.01 | cross-hospital | 126 | 0.11% | 2% | 0.19% |
   | 0.01 | home | 72 | 0.14% | 2% | 0.26% |
   | 0.05 | cross-hospital | 126 | 0.51% | 6% | 0.65% |
   | 0.05 | home | 72 | 0.97% | 7% | 1.23% |
   | 0.05 | ICU unit | 162 | 0.28% | 5% | 0.38% |
   | 0.10 | cross-hospital | 126 | 0.91% | 13% | 1.09% |
   | 0.10 | home | 72 | 2.06% | 12% | 2.41% |

   The error level trades safety for approval. A→B (primary criterion, 12,000 labels) was certified
   in 82%, 97% and 98% of runs at α = 0.01, 0.05 and 0.10. At 8,000 labels the figures were 35%,
   70% and 81%. At home, B→B with 2,000 labels was approved in 3%, 25% and 45% of runs. B→A was
   blocked in every run at every α.
6. **Assumption A1 in practice.**
   - The hospital must label a random sample, or a stratified one with known sampling weights.
   - Labelling only the patients clinicians flagged would break exchangeability. So would
     labelling only an early period followed by seasonal change.
