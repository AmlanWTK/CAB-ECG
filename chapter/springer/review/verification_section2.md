# Verification for Section 2.3: the shared α/4 for the imported model's false-alert tests

2026-11-02, revised after review. Section 2.3 states that the imported model's two false-alert tests share one α/4
allocation, because, given the septic patients, at most one of them can lead to an unsafe
deployment. This note states that claim as a lemma and proves it. The same argument appears in
Section 3.5 (full version: `chapter/guarantee.md`; code: `code/cabsepsis/cab.py`, `cab_select`).

## Setting

- Imported model g₀, with the vendor's threshold τ_home fixed before any local label is seen.
- For a threshold t: S(t) is the sensitivity (the probability that a septic patient is alerted in
  the window around onset), and F(t) the false-alert rate (the probability that a non-septic
  patient is alerted during the stay). Both are population quantities and both fall as t rises.
- Requirements s* and f*, fixed in advance; δ = α/4.
- **Assumption A1 (sampling).** The labelled patients and the patients the deployed model will
  serve are independent and identically distributed draws from the receiving hospital's patient
  population. Consequently, given their class, the K labelled septic patients are independent
  with a common distribution, and so are the M labelled non-septic patients; the two groups are
  independent of each other. For a threshold t fixed independently of them, each non-septic
  patient's alert indicator is a Bernoulli variable with probability F(t), and each septic
  patient's detection indicator is a Bernoulli variable with probability S(t).
- **Counts are of patients, not alerts.** x(t) is the number of the M non-septic patients with at
  least one alert during the stay, that is, whose highest hourly score reaches t (in the code,
  `fa_test` counts patients whose stay-maximum score is at least t). Likewise, a septic patient
  counts as detected once, however many alerts fire in the window.

Stage 1 of CAB, on all labelled patients:

1. τ = the certified threshold, a function of the K septic patients' scores only.
2. FA-test(t): with x(t) the number of the M non-septic patients alerted at t, pass if
   P[Bin(M, f*) ≤ x(t)] ≤ δ.
3. If FA-test(τ) passes: deploy KEEP (g₀, τ_home) if τ_home ≤ τ and FA-test(τ_home) also passes;
   otherwise deploy CALIBRATE (g₀, τ). If FA-test(τ) fails, go to Stage 2.

## Lemma

P[Stage 1 deploys a configuration whose false-alert rate exceeds f*] ≤ δ.

## Proof

**Step 1: a single test at a threshold fixed in advance.** For a threshold t fixed independently
of the non-septic patients, their patient-level alert indicators are independent Bernoulli
variables with common probability F(t) (A1). Then x(t) ~ Bin(M, F(t)). The test compares x(t)
with the exact Bin(M, f*) null distribution. If F(t) > f*, x(t) is stochastically larger than
Bin(M, f*). So
P[FA-test(t) passes] = P[P(Bin(M, f*) ≤ x(t)) ≤ δ] ≤ δ, by the validity of the exact one-sided
binomial test.

**Step 2: condition on the septic patients.** Let 𝒮 be the septic patients' data. Given each
patient's class (A1), the non-septic patients are independent of 𝒮. Conditional on 𝒮, τ is
therefore a fixed number, τ_home is fixed by assumption, and Step 1 applies at either threshold.

**Step 3: case analysis, conditional on 𝒮.** Write E for the event in the lemma.

- **Case A: F(τ) > f*.** CALIBRATE deploys at τ, and KEEP can be reached only after FA-test(τ)
  passes. So every route to E requires FA-test(τ) to pass. P[E | 𝒮] ≤ δ by Step 1.
- **Case B: F(τ) ≤ f*, and KEEP is possible (τ_home ≤ τ) with F(τ_home) > f*.** CALIBRATE at τ is
  not in E. E requires deploying KEEP, which requires FA-test(τ_home) to pass. P[E | 𝒮] ≤ δ by
  Step 1.
- **Case C: all other cases.** Either F(τ) ≤ f* and KEEP is impossible (τ_home > τ), or
  F(τ) ≤ f* and F(τ_home) ≤ f*. No configuration that Stage 1 can deploy has a false-alert rate
  above f*, so P[E | 𝒮] = 0.

The case is determined by 𝒮 alone, because F(τ) and F(τ_home) are population values at thresholds
fixed given 𝒮. In every case P[E | 𝒮] ≤ δ.

**Step 4: remove the conditioning.** P[E] = E[P[E | 𝒮]] ≤ δ. ∎

The same holds for any K, M ≥ 1, so it also holds when the numbers of septic and non-septic
patients labelled are random. If K = 0 or M = 0, the code returns no certified threshold or fails
the test, and Stage 1 deploys nothing.

## How it fits the overall bound

| Unsafe-deployment event | Allocation |
|---|---|
| Stage 1, sensitivity below s* (KEEP's threshold is at most τ, so S(τ_home) ≥ S(τ); only τ can err) | δ |
| Stage 1, false-alert rate above f* (the lemma; both tests share this allocation) | δ |
| Stage 2, sensitivity below s* (adapted model, certification half) | δ |
| Stage 2, false-alert rate above f* (adapted model, certification half) | δ |
| Union bound | 4δ = α |

For Stage 2 the same two arguments apply on the certification half, conditional on the fit half.
The labelled patients are divided, separately within septic and non-septic patients, into a
**fit half**, which alone determines the adapted model (its training, early stopping and the
choice among adaptation variants; assumption A3), and a **certification half**, which alone is
used for its threshold and both tests. Under A1 the certification half is independent of the
fit half, so conditional on the fit half the adapted model is a fixed function and Steps 1–4
apply to it. Stage 1 uses all labelled patients, which is valid because the imported model and
τ_home are fixed before labelling. Reaching Stage 2 depends on all the labelled patients, but the bound covers
the joint event "the adapted model is unsafe and its certification passes", whose probability is
at most 2δ whether or not Stage 2 is reached.

## Every test is run at level δ = α/4

In `cab_select`, `d = alpha / 4` is used for the threshold certification and for every
false-alert test, in both stages. The lemma is what makes the imported model's two false-alert
tests cost δ in total rather than 2δ.
