## 3 Materials and Methods

### 3.1 Data and Cohorts

We used the publicly available training set of the PhysioNet/Computing in Cardiology Challenge 2019 [@reyna2020; @goldberger2000]. It contains hourly records of intensive care unit (ICU) stays from two US hospital systems: Beth Israel Deaconess Medical Center (hospital A, 20,336 patients) and Emory University Hospital (hospital B, 20,000 patients). Each hourly record contains up to 8 vital signs, 26 laboratory values and 6 demographic and administrative fields. Sepsis is defined by the Sepsis-3 criteria [@singer2016]. The Challenge labels each septic patient's hours from 6 h before the onset of sepsis onwards, so we recover the onset time as the first labelled hour plus 6 h. This is the onset defined by the Challenge's retrospective application of Sepsis-3 to the record, not an independently adjudicated clinical onset.

Table 2 describes the two cohorts. Septic patients made up 8.8% of hospital A and 5.7% of hospital B. Within each hospital, patients were assigned at random, stratified by sepsis status, to training (60%), validation (20%) and test (20%) sets, giving 24,201, 8,067 and 8,068 patients across both hospitals. No patient appears in more than one set.

**Table 2.** Characteristics of the two hospital cohorts.

| Hospital | Patients | Septic, n (%) | Age, median (IQR) | Male (%) | ICU hours, median (IQR) | Patient-hours |
|---|---|---|---|---|---|---|
| Beth Israel (A) | 20,336 | 1,790 (8.8) | 65 (52–76) | 58.2 | 39 (25–47) | 790,215 |
| Emory (B) | 20,000 | 1,142 (5.7) | 62 (50–72) | 53.7 | 38 (23–47) | 761,995 |

### 3.2 Source Models

At each hospital we trained a LightGBM gradient-boosted tree model [@ke2017] on every hour of the training patients' stays, with the Challenge's hourly label as the target. That label is positive for a septic patient from 6 h before onset onwards, including the hours after onset, and negative otherwise. The model therefore scores every hour of a stay, and its scores are evaluated at the patient level as described in Section 3.3. Every feature at a given hour uses only data recorded up to and including that hour:

- for each vital sign, the most recent value (carried forward), an indicator of whether it was measured in that hour, the hours since its last measurement, the mean, minimum, maximum and standard deviation over the current and five preceding hours, and its change over 1 h and 6 h;
- for each laboratory value, the most recent value and the hours since it was measured;
- age, sex, the time from hospital admission to ICU admission, the hours since ICU admission and the shock index.

The ICU-type indicators were excluded so that the model could not learn the identity of the site. Each model was trained on its hospital's training set (learning rate 0.05, 63 leaves, at least 200 rows per leaf), with early stopping on the validation set.

These models play the role of a vendor's product. Each vendor also chooses its alert threshold on its own validation patients. For each sensitivity target s*, the vendor's threshold τ_home is the highest threshold at which the hypothesis that patient-level sensitivity is below s* is rejected by a one-sided exact binomial test at the 5% level. Because sensitivity falls as the threshold rises, the thresholds that pass this test form a contiguous range, and searching from the most sensitive end finds the highest of them. Ties among scores are handled by counting every patient whose score reaches the threshold. All six vendor thresholds (two hospitals, three targets) passed this test, so no fallback was needed. The vendor's home false-alert rate F_home is the observed share of its validation non-septic patients alerted at τ_home. It is a fixed number, published with the model and known before the receiving hospital examines any label. The vendor's 5% test is separate from CAB's own tests, which run at the stricter level δ = α/4. For comparison with current practice, four bedside scores (SIRS, qSOFA, MEWS and NEWS2) were computed in modified form from the same hourly data, at their usual cut-offs [@rcp2017].

### 3.3 Alerting and Safety Requirements

The unit of safety is the patient, because clinicians respond to an alert about a patient rather than to an hourly score. A threshold t converts a model's hourly scores into alerts:

- a septic patient is **detected** if any hourly score in the window from 12 h before to 3 h after onset reaches t, the clinically useful window used by the Challenge's utility score [@reyna2020];
- a non-septic patient is **falsely alerted** if any hourly score during the stay reaches t.

Because the window extends to 3 h after onset, a detection is not necessarily a warning before onset; Section 4.8 reports separately how early the alerts came. Let w_i be the highest hourly score of septic patient i within the window, and v_j the highest hourly score of non-septic patient j during the stay. A patient counts once, however many alerts fire. On a set of K septic and M non-septic patients, the sensitivity S(t) and the false-alert rate F(t) are the shares detected and falsely alerted:

$$ S(t)=\frac{1}{K}\sum_{i=1}^{K}{\mathbf{1}[w_i \ge t]}, \qquad F(t)=\frac{1}{M}\sum_{j=1}^{M}{\mathbf{1}[v_j \ge t]} $$ (1)

The corresponding population rates, which we also write S(t) and F(t), are the probabilities that a septic patient is detected and that a non-septic patient is falsely alerted. Both fall as t rises.

Before any local label is examined, the receiving hospital fixes two requirements: a sensitivity target s*, and a false-alert limit f* = F_home + m, where m is the additional false-alert rate the hospital is willing to accept over the rate the vendor reported. Because F_home is the vendor's observed rate, f* is a fixed constant benchmarked against that report, not against the vendor's unobservable population rate. In every setting studied, f* lay between 0.29 and 0.58. Were F_home + m to reach 1, every threshold would satisfy the false-alert requirement, so no violation of it would be possible and the guarantee below would be unaffected. A deployment, consisting of a model and a threshold t, is **safe** if, in the receiving hospital's population,

$$ S(t) \ge s^{*} \quad \text{and} \quad F(t) \le f^{*}. $$ (2)

We studied nine pairs of requirements, s* ∈ {0.75, 0.80, 0.85} crossed with m ∈ {0, 0.05, 0.10}. The primary pair is s* = 0.80 and m = 0.05. Blocking deploys nothing and is therefore safe by this definition; its clinical cost is examined separately (Section 4.6).

### 3.4 The CAB Procedure

Fig. 1 summarises the procedure and Algorithm 1 states it exactly. The hospital labels n patients drawn at random from its own population. Before any model is fitted, CAB divides these patients, separately within the septic and the non-septic patients, into a fit half and a certification half. Let δ = α/4. Two building blocks are used.

- **Threshold certification.** Given K labelled septic patients, sort their window-maximum scores from highest to lowest. Find the smallest number of detections d_min for which the exact binomial test of H0: S < s* rejects at level δ, and return the threshold that detects d_min patients. This is the highest threshold whose sensitivity is certified. It is the fixed-sequence form of Learn-then-Test [@angelopoulos2021]: thresholds are tested from the most sensitive end, and because sensitivity falls monotonically as the threshold rises, the thresholds that pass form a contiguous range.
- **False-alert test.** Given M labelled non-septic patients and a threshold t, reject H0: F(t) > f* if, when the true rate is f*, the exact binomial probability of observing the actual number of false alerts or fewer is at most δ.

In symbols, with w_(1) ≥ … ≥ w_(K) the sorted window-maximum scores of the labelled septic patients and x(t) the number of labelled non-septic patients alerted at t, the certified threshold and the false-alert test are

$$ d_{\min}=\min\{d : \Pr[\mathrm{Bin}(K,s^{*}) \ge d] \le \delta\}, \qquad \tau=w_{(d_{\min})} $$ (3)

$$ \text{reject } F(t)>f^{*} \text{ if } \Pr[\mathrm{Bin}(M,f^{*}) \le x(t)] \le \delta $$ (4)

If no d ≤ K satisfies the condition in (3), that is, if even detecting every labelled septic patient would not reject H0, d_min is undefined and no threshold is certified. Ties among scores are allowed: the certified threshold then detects at least d_min patients.

The gate then runs in two stages.

**Stage 1: the imported model, on all labelled patients.** CAB certifies a threshold τ. If τ is certified and the false-alert test at τ passes, CAB deploys the imported model with the vendor's threshold (KEEP) if τ_home is no higher than τ and the false-alert test at τ_home also passes; otherwise it deploys the imported model with threshold τ (CALIBRATE). If no threshold is certified, or the false-alert test at τ fails, CAB proceeds to Stage 2.

**Stage 2: an adapted model, on the certification half.** A random 20% of the fit-half patients is set aside as an early-stopping subset, and three adapted candidates are fitted on the remaining 80%: additional boosting rounds added to the imported trees, with early stopping on the subset (learning rate 0.03, 15 leaves, at most 1,000 rounds, patience 50); a re-estimation of the imported trees' leaf values on local data, in which each new leaf value is 0.9 times the imported value plus 0.1 times the locally estimated value (LightGBM's refit with decay 0.9); and the leaf re-estimation followed by additional boosting rounds. The candidate with the highest hourly AUROC on the early-stopping subset is retained, with ties broken in the order listed. CAB certifies a threshold τ_A for this model and tests its false-alert rate, both on the certification half only. If both pass, it deploys the adapted model with threshold τ_A (ADAPT). Otherwise the model is blocked (BLOCK), and the hospital continues its usual care.

**Algorithm 1.** CAB (Calibrate, Adapt, or Block).

```
Input:  imported model g0, vendor threshold t_home; targets s*, f*;
        error level alpha; n labelled patients L, drawn at random
        from the receiving hospital
Output: KEEP (g0, t_home), CALIBRATE (g0, t), ADAPT (gA, tA) or BLOCK

 1  delta <- alpha / 4
 2  split L, within septic and non-septic patients, into halves
    L_fit and L_cert
 3  t <- CERTIFY(g0, L)                       # Stage 1: all labels
 4  if t exists and FALSE_ALERT_OK(g0, L, t):
 5      if t_home <= t and FALSE_ALERT_OK(g0, L, t_home):
 6          return KEEP (g0, t_home)
 7      return CALIBRATE (g0, t)
 8  gA <- ADAPT(g0, L_fit)                    # Stage 2: fit half only
 9  tA <- CERTIFY(gA, L_cert)
10  if tA exists and FALSE_ALERT_OK(gA, L_cert, tA):
11      return ADAPT (gA, tA)
12  return BLOCK                              # usual care continues

CERTIFY(g, D):
    w(1) >= ... >= w(K): window-maximum scores of the K septic
                         patients in D
    d_min <- smallest d with P(Bin(K, s*) >= d) <= delta
    return w(d_min), or none if d_min > K
FALSE_ALERT_OK(g, D, t):
    x <- number of the M non-septic patients in D whose stay-maximum
         score is at least t
    return P(Bin(M, f*) <= x) <= delta
```

The order reflects the cost of each option to the hospital. A hospital prefers to keep a vendor's model unchanged, because the vendor supports it and it is easier to govern. Changing the threshold is the next least intrusive option. A retrained model requires local validation and maintenance. CAB therefore tries the least intrusive option first. Stage 1 also uses all the labelled patients, not only the certification half, because the imported model and τ_home are fixed before labelling and no fitting takes place.

**Illustration.** Table 3 shows CAB's evidence in three runs at the primary requirements (s* = 0.80, f* = F_home + 0.05), each drawn from the 100 repetitions of Section 3.7.

- *A→B with 12,000 labels (672 septic patients).* At the vendor's threshold the imported model detected 443 of the 672 septic patients (65.9%, exact lower bound 61.7%), so KEEP failed. The lowest threshold that certified 80% sensitivity alerted 62.4% of non-septic patients against a limit of 45.1%, so CALIBRATE failed. The adapted model, tested on the 336 septic and 5,664 non-septic patients of the certification half, passed both tests and was deployed. On the 8,000 patients of the receiving hospital that were never labelled, it detected 86.6% of septic patients and alerted 43.5% of non-septic patients, so the deployment was safe.
- *A→B with 1,000 labels (47 septic patients).* With so few septic patients, certifying 80% sensitivity required a threshold so low that almost every non-septic patient was alerted (96.7% for the imported model and 97.7% for the adapted model). CAB therefore blocked. Blocking is the appropriate decision for this amount of evidence, although ADAPT would have been certified with more labels.
- *B→A with 1,000 labels.* Every option alerted 70–76% of non-septic patients, against a limit of 37.9%. CAB blocked, which was also the correct remedy given the full data.

**Table 3.** CAB's evidence in three runs at the primary requirements. Counts are detected over labelled septic patients and alerted over labelled non-septic patients; bounds are one-sided exact bounds at δ = α/4 = 0.0125. Keep and Calibrate are tested on all labelled patients, Adapt on the certification half. The false-alert limit f* is 0.451 for A→B and 0.379 for B→A.

| Option | Detected | Sensitivity (lower bound) | Alerted | False-alert rate (upper bound) | Passed |
|---|---|---|---|---|---|
| **A→B, 12,000 labels** | | | | | |
| Keep | 443/672 | 0.659 (0.617) | 3,560/11,328 | 0.314 (0.324) | No |
| Calibrate | 561/672 | 0.835 (0.800) | 7,070/11,328 | 0.624 (0.634) | No |
| Adapt | 286/336 | 0.851 (0.802) | 2,360/5,664 | 0.417 (0.431) | **Yes** |
| **A→B, 1,000 labels** | | | | | |
| Keep | 31/47 | 0.660 (0.486) | 320/953 | 0.336 (0.371) | No |
| Calibrate | 44/47 | 0.936 (0.807) | 922/953 | 0.967 (0.979) | No |
| Adapt | 23/23 | 1.000 (0.827) | 465/476 | 0.977 (0.990) | No: block |
| **B→A, 1,000 labels** | | | | | |
| Keep | 83/93 | 0.892 (0.799) | 635/907 | 0.700 (0.734) | No |
| Calibrate | 84/93 | 0.903 (0.812) | 686/907 | 0.756 (0.788) | No |
| Adapt | 43/46 | 0.935 (0.803) | 337/453 | 0.744 (0.789) | No: block |

### 3.5 Statistical Guarantee

We use three assumptions.

- **(A1) Sampling.** The labelled patients and the patients the deployed model will serve are independent and identically distributed draws from the receiving hospital's population. Consequently, given their class, the labelled septic patients are independent with a common distribution, as are the labelled non-septic patients, and the two groups are independent of each other. For a threshold fixed independently of the labelled patients, each septic patient's detection and each non-septic patient's false alert is therefore a Bernoulli variable, with probability S(t) or F(t).
- **(A2) Labels.** The labels, including the onset times that define the detection window, are correct.
- **(A3) Prespecification.** The requirements s* and f*, the level α, the imported model and τ_home are fixed before labelling. The adapted model, including its training, early stopping and the choice among candidates, depends only on the fit half and is fixed before the certification half is examined.

**Theorem.** Under (A1)–(A3), for any shift between the developing and the receiving hospital and any number of labelled patients,

$$ \Pr[\text{CAB deploys a configuration that violates (2)}] \le 4\delta = \alpha. $$ (5)

The proof combines three lemmas. Throughout, the numbers K and M of septic and non-septic patients in the data being tested are held fixed by conditioning; since each bound holds for every K and M, it also holds unconditionally.

**Lemma 1 (threshold certification).** The certified threshold τ satisfies Pr[S(τ) < s*] ≤ δ.

*Proof.* Model scores are predicted probabilities, so the window-maximum score W of a septic patient drawn from the population lies in [0, 1], and S(t) = Pr[W ≥ t] equals 1 for every t ≤ 0. Let D(t) be the number of the K labelled septic patients with w_i ≥ t. Since τ is the d_min-th highest score, at least d_min labelled patients score at or above τ, so D(τ) ≥ d_min; ties only increase D(τ). Let U = {t : S(t) < s*}. Because S is non-increasing, U is either empty, in which case the event S(τ) < s* is impossible, or an interval unbounded above. Since S(t) = 1 > s* for t ≤ 0, its lower end u = inf U lies in [0, 1]; it depends only on the population. Two cases arise.

- **Case 1.** u ∈ U, so that S(u) < s*. If S(τ) < s*, then τ ≥ u, and since detections can only fall as the threshold rises, D(u) ≥ D(τ) ≥ d_min.
- **Case 2.** u ∉ U. Every t > u lies in U. As t decreases to u the events {W ≥ t} increase to {W > u}, so Pr[W > u] is the limit of S(t), and it is at most s*. If S(τ) < s*, then τ > u, and the number C(u) of labelled septic patients with w_i > u satisfies C(u) ≥ D(τ) ≥ d_min.

In either case the event S(τ) < s* implies that a count at a fixed, population-defined threshold, D(u) or C(u), is at least d_min. By (A1) that count is binomial with K trials and success probability S(u) < s* or Pr[W > u] ≤ s*, so it is stochastically no larger than Bin(K, s*). Hence Pr[S(τ) < s*] ≤ Pr[Bin(K, s*) ≥ d_min] ≤ δ by (3). ∎

**Lemma 2 (false-alert test at a threshold chosen from the septic patients).** Let t be a threshold that depends only on the septic patients' data. Then Pr[F(t) > f* and the false-alert test passes at t] ≤ δ.

*Proof.* Condition on the septic patients' data, which fixes t. By (A1) the non-septic patients are independent of the septic patients, so the number x(t) of non-septic patients alerted at t is Bin(M, F(t)). If F(t) ≤ f*, the event is empty. If F(t) > f*, then x(t) is stochastically larger than Bin(M, f*), so the exact test (4) passes with probability at most δ. Removing the conditioning preserves the bound. ∎

**Lemma 3 (Stage 1 false alerts share one allocation).** The probability that Stage 1 deploys a configuration whose false-alert rate exceeds f* is at most δ.

*Proof.* Condition on the septic patients' data. This fixes τ, and τ_home is fixed by (A3), so the population rates F(τ) and F(τ_home) are fixed numbers. Three cases are possible.

- **Case 1.** F(τ) > f*. CALIBRATE deploys at τ. KEEP deploys at τ_home, but it too is reached only after the false-alert test at τ has passed. Every unsafe deployment therefore requires the test at τ to pass, which has probability at most δ by Lemma 2.
- **Case 2.** F(τ) ≤ f*, KEEP is possible (τ_home ≤ τ) and F(τ_home) > f*. CALIBRATE is safe. An unsafe deployment requires KEEP, and therefore the test at τ_home to pass, which has probability at most δ by Lemma 2.
- **Case 3.** Otherwise, every configuration that Stage 1 can deploy has a false-alert rate of at most f*, and the probability is zero.

The case is determined by the septic patients alone, so in every case the conditional probability is at most δ, and so is the unconditional probability. ∎

*Proof of the theorem.*

- **Stage 1, sensitivity.** CALIBRATE deploys at τ. KEEP deploys at τ_home ≤ τ, so S(τ_home) ≥ S(τ). A sensitivity violation by either option therefore implies S(τ) < s*, which has probability at most δ by Lemma 1.
- **Stage 1, false alerts.** At most δ, by Lemma 3.
- **Stage 2.** By (A3) the adapted model is a fixed function of the fit half, and by (A1) the certification half is independent of the fit half. Conditional on the fit half, Lemmas 1 and 2 apply on the certification half and bound the adapted model's sensitivity and false-alert violations by δ each. Whether Stage 2 is reached depends on all the labelled patients, including the certification half; this does not affect the bound, because the event "Stage 2 deploys an unsafe adapted model" is contained in the event "the adapted model is unsafe and passes certification", whose probability is at most 2δ whether or not Stage 2 is reached.
- **Union bound.** CAB deploys at most one configuration, so the probability that it deploys an unsafe one is at most δ + δ + 2δ = 4δ = α. ∎

The bound holds exactly in finite samples. It requires no model of the shift and no assumption that the model's predicted probabilities are well calibrated. Two things are not guaranteed: that CAB finds a safe configuration when one exists, which depends on the number of labels; and that the deployed configuration remains safe if the population changes after deployment.

### 3.6 Comparators

CAB was compared with the eleven alternatives in Table 4. They cover what a hospital might do without local labels, the updating and validation practices that use labels without certification, and two certified alternatives. The point-estimate policies set their thresholds and judge whether the requirements are met on the same labelled patients, as a hospital without certification would; this reuse of data is part of what the comparison examines. LABEL-FREE matches the share of alerted patient-hours, a different quantity from the patient-level false-alert rate in (2).

**Table 4.** The eleven comparators.

| Group | Policy | What it does |
|---|---|---|
| Without labels | AS-IS | Imported model, vendor's threshold. |
| Without labels | LABEL-FREE | Threshold that matches the vendor's home share of alerted patient-hours on unlabelled local data. |
| Without labels | LABEL-SHIFT | Probabilities corrected for the local sepsis prevalence [@saerens2002]; vendor's threshold. |
| Labels, point estimates | RECALIBRATE | Imported model, highest threshold reaching s* on the labelled patients. |
| Labels, point estimates | FINE-TUNE | Adapted model, threshold set the same way on the certification half. |
| Labels, point estimates | RETRAIN | New model trained on the fit half, threshold set on the certification half. |
| Labels, point estimates | CLOSED-TEST | Classical updating by significance tests of model fit [@vergouwe2017]; never blocks. |
| Labels, point estimates | NAIVE-VAL | CAB's order of options, each accepted on point estimates without a test. |
| Labels, point estimates | NAIVE-500 | Keep or recalibrate on point estimates from the first 500 labelled patients. |
| Certified | LTT-DIRECT | Imported and adapted models both certified on the certification half; no order. |
| Certified | CERT-RECAL | CAB without the adapt stage (an ablation). |

The rules of four comparators need more detail. LABEL-SHIFT estimates the local prevalence from unlabelled patient-hours as the vendor's prevalence multiplied by the ratio of the mean local prediction to the mean home prediction. CLOSED-TEST first applies a likelihood-ratio test (2 degrees of freedom, all labelled patient-hours) of logistic recalibration against the model as supplied, and then a one-sided bootstrap test (200 resamples of certification-half patients) of whether the adapted model's patient-level log-likelihood exceeds that of a recalibration fitted on the fit half; each test is at the 5% level, and the policy chooses ADAPT if revision is significant, otherwise CALIBRATE if recalibration is significant, otherwise KEEP, with the threshold set as in FINE-TUNE, RECALIBRATE or AS-IS respectively. NAIVE-500 uses the first 500 labelled patients in random order, or all of them when fewer are labelled, and blocks if neither option meets the requirements. LTT-DIRECT applies CAB's tests to both models on the certification half; if both pass, it deploys the one with the lower observed false-alert rate there, and if neither passes it blocks.

### 3.7 Experimental Design

**Scenarios.** We studied six transfer scenarios. Two are whole-hospital transfers: hospital A's model at hospital B (A→B) and hospital B's model at hospital A (B→A). Four are transfers into a single ICU type: each of these models imported into the receiving hospital's medical ICU (MICU) or surgical ICU (SICU). In addition, each hospital's model was imported into its own hospital (A→A and B→B), a control in which nothing has shifted.

**Label budgets and patient sets.** In the whole-hospital and ICU-type transfers, labelled patients were drawn at random from the receiving hospital's training and validation patients, and deployments were judged on all its other patients, including its test set. Budgets were 250, 500, 1,000, 2,000, 4,000, 8,000 and 12,000 labelled patients in the whole-hospital transfers; the size of each unit limited them to 4,000 in the transfers into hospital B's units and to 2,000 in those into hospital A's units. In the home control, the source model had been fitted on the hospital's training set, with its validation set used for early stopping and for choosing the vendor's threshold, so both labelling and judging used only its test patients, which limited budgets to 2,000.

**Separation of labelled and judged patients.** The labelled patients, including those used for fitting, early stopping, threshold selection and certification, were used only by the policies being compared. Every resulting deployment was then judged on the receiving hospital's eligible patients that had not been labelled; the eligible patients are all of its patients (or all of the unit's) in the transfers, and its test patients in the home control.

**Repetitions.** Each combination of scenario, budget and pair of requirements was repeated 100 times with different random samples. The random seed depended only on the scenario, the budget and the repetition, so all policies saw exactly the same labelled patients and the same split into fit and certification halves.

**Correct remedy.** As an evaluation reference, not a procedure available to a hospital, we defined the correct remedy for each scenario and pair of requirements as the first of KEEP, CALIBRATE and ADAPT that met both requirements on all eligible patients of the receiving hospital, or BLOCK if none did. For the transfers, the adapted model used for this purpose was fitted on the receiving hospital's training set, with early stopping on its validation set, and checked on its test set. In the home control the correct remedy was determined in the same way. Because f* is benchmarked against the vendor's observed validation rate rather than its population rate, KEEP was the correct remedy in 13 of the 18 home settings, including both at the primary requirements; with no additional tolerance (m = 0), the vendor's threshold sometimes exceeded f* on the test patients.

**Outcomes.** We report the share of runs in which each policy deployed an unsafe configuration (*unsafe*); deployed an unsafe configuration that appeared safe on its own labelled patients (*silent failure*); and chose the correct remedy (*correct*). We also report clinical impact per 100 admissions; when CAB blocks, the hospital is assumed to fall back to a modified NEWS2 score of 5 or more.

### 3.8 Label Calculator

Each candidate configuration is assessed against the two requirements, minimum patient-level sensitivity and maximum patient-level false-alert rate, using exact binomial tests at level δ. The number of labels needed therefore depends on two quantities: the margin by which the model's true rates satisfy the requirements, and the share of septic patients among those labelled.

The calculator works at a fixed operating point with given true rates. It finds the smallest number of septic patients for which the sensitivity test passes with probability √0.9, and the smallest number of non-septic patients for which the false-alert test does. At a fixed threshold the two tests use independent groups of patients, so both then pass with probability at least 0.9. These counts are converted into total patients at the hospital's prevalence and doubled for ADAPT, because half the labelled patients are used for fitting. In CAB the threshold of CALIBRATE and ADAPT is chosen from the septic patients, so the two outcomes are not independent and the 90% figure is a planning approximation rather than a guarantee for the full procedure. A hospital can apply the calculator before labelling, using the vendor's published operating curve as an estimate of the margin. We checked its predictions against simulations of CAB's exact rule on patients resampled with replacement from the receiving hospital (Section 4.5).

### 3.9 Implementation and Prototype

The analysis was written in Python using LightGBM, NumPy, pandas, SciPy and scikit-learn. All final experiments ran in a single fixed software environment. Every random choice is driven by fixed seeds recorded in the code: one seed for the data splits and the source models, and, for each run, a seed that depends only on the scenario, the budget and the repetition, which drives the label sample, the fit and certification halves and the fitting of the adapted and retrained models. The gate is also implemented in a research prototype, the CAB Sepsis Monitor, which shares its code with the experiments and is described in Section 5. The code, including the exact tests, the data splits, the random seeds, the model parameters, the adaptation candidates, the calculator and the scripts that produce every table and figure, is openly available with the application at https://github.com/AmlanWTK/CAB-ECG; the version that produced the results in this chapter is release springer-chapter-v1.0 (https://github.com/AmlanWTK/CAB-ECG/tree/springer-chapter-v1.0).
