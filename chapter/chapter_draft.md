# Calibrate, Adapt, or Block: A Statistically Certified Deployment Gate for Imported Sepsis Early-Warning Models

Amlan Sarkar¹* and Md Tobibul Islam¹

¹ Department of Biomedical Engineering, Military Institute of Science and Technology (MIST), Dhaka, Bangladesh

\* Corresponding author: amlansarkar738@gmail.com · tobibul.islam@bme.mist.ac.bd

> Draft 1, written from the committed results. Every number is traceable to `outputs/sepsis/` (see
> the source notes in `chapter/abstract_draft.md` and the file named beside each table or figure).
> Before submission:
> - check every reference against the original;
> - move the text into the Springer chapter template (single column, 10 pt);
> - run it through Turnitin (the limit is below 18%).

---

## Abstract

**Background.** Hospitals increasingly use sepsis prediction models built at other institutions. These models often lose accuracy at the receiving site, and the receiving site has no principled way to decide whether to use the model as supplied, update it or reject it.

**Objective.** We set out to build a deployment gate that uses a limited number of locally labelled patients to choose the least invasive acceptable remedy for an imported model. The gate also bounds the probability of switching on a model that breaks safety requirements fixed in advance.

**Methodology.** We used 40,336 intensive care patients from two US hospitals in the PhysioNet/CinC Challenge 2019 data. A gradient-boosted model trained at each hospital was imported into the other hospital, and into each of its two ICU types. The method, CAB (Calibrate, Adapt, or Block), considers four options in a fixed order: keep the model, recalibrate its alert threshold, adapt it to local data, or block it. An option is switched on only if exact binomial tests certify patient-level sensitivity and false-alert rate. CAB was compared with eleven alternatives, from direct deployment to classical statistical updating and point-estimate validation. The comparison used 250 to 12,000 labelled patients, nine safety criteria and 100 repetitions per setting.

**Results.**
- Imported models failed in direction-specific ways: sensitivity fell to 63% against an 80% target at one hospital, and false alerts doubled at the other.
- The uncertified alternatives switched on unsafe models in 18–100% of runs, and conventional updating did so in 77–92%. CAB did so in under 1%, and stayed below the nominal level at error rates of 1%, 5% and 10%.
- CAB blocked an unrepairable model in every run from 250 labels, and certified the adapted model in 97% of runs at 12,000 labels.
- A closed-form calculator predicted the labels needed to within about 20%.

**Conclusion.** A certified gate prevents almost all unsafe activations at a measurable cost in labels. Hospitals should plan label collection, and their false-alert tolerance, before deployment.

**Keywords:** Sepsis early warning · Clinical decision support · Dataset shift · Model updating · Local validation · Statistical certification · Health informatics

---

## 1 Introduction

Sepsis is a dysregulated host response to infection that leads to organ dysfunction [1]. It remains a leading cause of death in intensive care, and each hour of delayed treatment worsens outcomes. Early-warning models that score a patient's risk every hour from routinely charted vital signs and laboratory values are therefore attractive.

Many hospitals do not build such models themselves. They buy them from a vendor, or adopt one published by another institution. The model arrives with a fixed alert threshold chosen on the developer's own patients, and the receiving hospital is expected to switch it on.

This practice has a well-documented weakness. A model's performance depends on the population, measurement habits and outcome definitions of the hospital where it was trained. When any of these change, performance can fall, a problem known as dataset shift [2,3]. An independent evaluation of a widely deployed proprietary sepsis model found far lower discrimination and sensitivity than the developer reported [4].

The failure is not always the same. A transported model may miss more septic patients. It may also alert many more patients who are not septic, which erodes clinicians' trust and adds to alarm fatigue. Which of these happens depends on the direction of transfer, so a single local check of "accuracy" is not enough.

A receiving hospital that collects some local labels has several options, ordered by how much they change the model:

- keep the model as it is;
- recalibrate it, for example by moving its alert threshold;
- adapt it, by continuing to train it on local patients;
- reject it and keep its usual care.

The clinical-prediction literature describes these updating methods in detail [5,6], and closed testing procedures choose among them with significance tests [7]. What these procedures do not provide is a guarantee about the decision that matters to patients: whether the model that is finally switched on meets the hospital's safety requirements. A point estimate computed on a few hundred local patients can look acceptable when the true performance is not.

This chapter presents **CAB (Calibrate, Adapt, or Block)**, a deployment gate built for that decision. Before any local label is seen, the hospital states two requirements:

- a minimum patient-level sensitivity;
- a maximum false-alert rate.

CAB then tests the remedies in order of increasing intervention. It switches on the first one whose compliance with both requirements is certified by exact binomial tests. If none is certified, it blocks the model. The tests are arranged so that, for any shift and any number of labels, the probability of switching on a model that breaks either requirement is at most a chosen level α (5% in our main analysis). The construction borrows the fixed-sequence idea of Learn-then-Test risk control [8,9]. It applies that idea to the ordered remedies a hospital actually has, and to patient-level alerting rules.

We evaluate CAB on the PhysioNet/CinC Challenge 2019 data [10]: two US hospitals, 40,336 ICU patients and six import scenarios. The evaluation includes a same-hospital control and 100 repeated samples per setting. The contributions are as follows:

1. **A certified deployment gate.** It chooses among keep, recalibrate, adapt and block with a finite-sample bound on unsafe activation, and needs no model of the shift (Section 3.4 and the proof in Section 3.5).
2. **A comparison with eleven alternatives** that hospitals use or that the literature recommends. These include classical closed-testing updating, point-estimate local validation, prevalence correction and unordered Learn-then-Test (Section 4).
3. **A closed-form label calculator** that tells a hospital, before it starts labelling, roughly how many septic and non-septic patients certification will need (Section 4.5).
4. **Practical findings** for hospitals and vendors. Blocking is a legitimate and frequent outcome. Typical validation samples are too small to certify anything. The hospital's false-alert tolerance, not the vendor's threshold headroom, decides how many labels are needed (Sections 4.6 and 4.7).
5. **A prototype application** that runs the gate on a hospital's labels and then monitors patients hour by hour with whatever the gate switched on. It is built on the same code as the experiments (Section 5).

---

## 2 Background and Related Work

### 2.1 Sepsis early warning and its transport

Rule-based bedside scores are widely used to flag deteriorating patients. Examples are the Systemic Inflammatory Response Syndrome (SIRS) criteria, the quick Sequential Organ Failure Assessment (qSOFA), the Modified Early Warning Score (MEWS) and the National Early Warning Score 2 (NEWS2) [11]. They are transparent and need no training data, but their discrimination for sepsis is modest.

Machine-learning models trained on electronic health records do better at the hospital where they are built. The 2019 PhysioNet/Computing in Cardiology Challenge [10] made data from two hospitals openly available so that algorithms could be compared on the same footing. Its organisers deliberately held out a third hospital, and reported that performance fell there. Prospective deployment studies show that well-run sepsis alert systems can help [12]. External evaluations show that the same promise does not carry over automatically to new sites [4].

### 2.2 Updating an imported model

Clinical prediction research distinguishes a hierarchy of updates [5,6]:

- recalibration in the large (changing the intercept);
- logistic recalibration (intercept and slope);
- model revision (re-estimating some or all coefficients);
- full redevelopment.

Vergouwe and colleagues proposed a closed testing procedure that moves up this hierarchy only when a likelihood-ratio test shows that the next level fits significantly better [7]. Sample-size guidance for external validation [13] tells a hospital how many patients it needs to estimate performance with a given precision.

These tools answer statistical questions about fit and precision. They do not bound the probability that the model finally put into use fails the hospital's own operating requirements. As our results show, that probability can be large.

### 2.3 Distribution-free risk control

Distribution-free predictive inference offers a different kind of guarantee. Risk-controlling prediction sets [9] and Learn-then-Test [8] calibrate a parameter of any black-box model, such as a threshold, so that a chosen risk is controlled with high probability. They need only the assumption that the calibration data are exchangeable with future data.

Learn-then-Test casts calibration as multiple hypothesis testing, and uses fixed-sequence testing when the risk is monotone in the parameter. CAB uses this machinery and adds three things:

1. two risks at once (missed septic patients and false alerts), defined at the patient level;
2. a fixed order of remedies that reflects their cost to the hospital;
3. an adapted model that must be fitted and certified on separate patients.

### 2.4 Correcting for shift without labels

When the outcome rate differs between hospitals but the relation between features and outcome does not (label shift), predicted probabilities can be corrected using unlabelled target data [14,15]. Covariate-shift methods reweight source data instead. Both depend on assumptions about the type of shift that cannot be checked without labels.

We include a prevalence correction as a comparator, to test whether such a correction is enough in this setting.

---

## 3 Materials and Methods

### 3.1 Data and cohorts

We used the training set of the PhysioNet/CinC Challenge 2019 [10,16]. It contains hourly records of ICU stays from two hospitals:

- Beth Israel Deaconess Medical Center (hospital A): 20,336 patients;
- Emory University Hospital (hospital B): 20,000 patients.

Each record contains up to 8 vital signs, 26 laboratory values and 6 demographic and administrative fields. Sepsis follows the Sepsis-3 definition [1]. The Challenge labels each septic patient's hours from 6 h before the clinical onset time, and we recover the onset as the first labelled hour plus 6 h.

Table 1 describes the cohorts. Septic patients made up 8.8% of hospital A and 5.7% of hospital B. Within each hospital, patients were split at random into training (60%), validation (20%) and test (20%) sets, giving 24,201, 8,067 and 8,068 patients overall. No patient appears in more than one set.

**Table 1.** Cohorts (`outputs/sepsis/figures/chapter_tables.md`, Table 1).

| Hospital | Patients | Septic, n (%) | Age, median (IQR) | Male (%) | ICU hours, median (IQR) | Patient-hours |
|---|---|---|---|---|---|---|
| Beth Israel (A) | 20,336 | 1,790 (8.8) | 65 (52–76) | 58.2 | 39 (25–47) | 790,215 |
| Emory (B) | 20,000 | 1,142 (5.7) | 62 (50–72) | 53.7 | 38 (23–47) | 761,995 |

### 3.2 Source models

At each hospital we trained a LightGBM gradient-boosted tree model [17] to predict, hour by hour, whether a patient would become septic. Every feature uses only data available up to that hour:

- For each vital sign: the last value, a flag for whether it was measured that hour, hours since the last measurement, the 6-hour rolling mean, minimum, maximum and standard deviation, and the change over 1 and 6 hours.
- For each laboratory value: the last value and hours since it was measured.
- Age, sex, hours since hospital admission, ICU length of stay and the shock index.

The ICU-type indicators were deliberately left out, so that the model could not learn site identity. Training used the training split and early stopping on the validation split.

These models play the role of the vendor's product. Each "vendor" also chooses its alert threshold on its own validation patients. For each sensitivity target s*, the vendor's threshold τ_home is the highest threshold whose sensitivity of at least s* passes a one-sided exact test at the 5% level on the home validation patients. The vendor's home false-alert rate at that threshold is F_home. For comparison, the four bedside scores were computed in modified form from the same hourly data, at their usual cut-offs.

### 3.3 Alerting and safety criteria

The unit of safety is the patient, because a clinician responds to an alert about a patient, not to an hourly score. A threshold t turns a model's hourly scores into alerts:

- A septic patient counts as **detected** if any hourly score in the window from 12 h before to 3 h after onset reaches t. This is the clinically useful window used by the Challenge's utility score.
- A non-septic patient counts as **falsely alerted** if any hourly score during the stay reaches t.

Sensitivity S(t) is the share of septic patients detected, and the false-alert rate F(t) is the share of non-septic patients falsely alerted. Both rates fall as t rises.

Before any target label is seen, the receiving hospital fixes two safety requirements:

- a sensitivity target s*;
- a false-alert limit f* = F_home + m, where m is the extra false-alert rate the hospital is willing to accept over what the vendor achieved at home.

A deployment (model, threshold) is **safe** if S ≥ s* and F ≤ f*. We studied nine criteria, s* ∈ {0.75, 0.80, 0.85} crossed with m ∈ {0, 0.05, 0.10}. The primary criterion is s* = 0.80 and m = 0.05. Blocking switches nothing on and is always safe by this definition. Its clinical cost is examined separately (Section 4.6).

### 3.4 The CAB procedure

Fig. 1 summarises the procedure and Algorithm 1 states it exactly. The hospital labels n patients drawn at random from its own population. Before any model is fitted, CAB divides these patients, within the septic and non-septic groups separately, into a fit half and a certification half. Let δ = α/4.

Two building blocks are used:

- **Threshold certification.** Given k labelled septic patients, sort their window-maximum scores from highest to lowest. Find the smallest number of detections d_min for which the exact binomial test of H0: S < s* rejects at level δ. Return the threshold that detects exactly d_min patients. This is the highest threshold whose sensitivity is certified, and it is the fixed-sequence form of Learn-then-Test [8]: thresholds are tested from the most sensitive end, and because sensitivity falls monotonically, the passing thresholds form a prefix.
- **False-alert test.** Given m labelled non-septic patients and a threshold t, reject H0: F(t) > f* if the exact binomial probability of the observed number of false alerts or fewer is at most δ when the true rate is f*.

The gate then runs in two stages.

**Stage 1 (imported model, all n labels).**
1. Certify a threshold τ and test the false-alert rate at τ.
2. If both pass, and the vendor's threshold τ_home is no higher than τ, test the false-alert rate at τ_home as well. If that also passes, **KEEP** the model with the vendor's threshold.
3. Otherwise, if both tests at τ passed, **CALIBRATE**: keep the model and use threshold τ.
4. If either test at τ failed, go to Stage 2.

**Stage 2 (adapted model, certification half).**
1. Fit an adapted model on the fit half. Three candidates are fitted:
   - extra boosting rounds on top of the imported trees;
   - a LightGBM refit of the imported trees' leaf values (decay 0.9);
   - both of these together.
   
   The candidate with the best hourly AUROC on a 20% early-stopping subset of the fit half is kept.
2. Certify a threshold τ_A for the adapted model and test its false-alert rate on the certification half. If both pass, **ADAPT**.
3. Otherwise **BLOCK**: the model is not switched on, and the hospital continues its usual care.

**Algorithm 1.** CAB (Calibrate, Adapt, or Block).

```
Input:  imported model g0 with vendor threshold τ_home; targets s*, f*; error level α;
        n labelled patients L, drawn at random from the target hospital
Output: KEEP (g0, τ_home), CALIBRATE (g0, τ), ADAPT (gA, τA) or BLOCK

 1  δ ← α/4
 2  split L, within septic and non-septic patients, into L_fit and L_cert (halves)
 3  τ ← CERTIFY(g0, L)                         // Stage 1: imported model, all labels
 4  if τ exists and FALSE_ALERT_OK(g0, L, τ):
 5      if τ_home ≤ τ and FALSE_ALERT_OK(g0, L, τ_home):  return KEEP (g0, τ_home)
 6      return CALIBRATE (g0, τ)
 7  gA ← ADAPT(g0, L_fit)                       // Stage 2: fitted on L_fit only
 8  τA ← CERTIFY(gA, L_cert)
 9  if τA exists and FALSE_ALERT_OK(gA, L_cert, τA):  return ADAPT (gA, τA)
10  return BLOCK                                // usual care continues

CERTIFY(g, S):  w(1) ≥ ... ≥ w(k) ← window-maximum scores of the k septic patients in S
                d_min ← smallest d with P(Binomial(k, s*) ≥ d) ≤ δ
                return w(d_min)   (none if d_min > k)
FALSE_ALERT_OK(g, S, t):  x ← non-septic patients in S (of m) with a stay-maximum score ≥ t
                return P(Binomial(m, f*) ≤ x) ≤ δ
```

The order matters. A hospital prefers to keep a vendor model unchanged, because the vendor supports it and it is easier to govern. A threshold change is the next least intrusive option. A retrained model needs local validation and maintenance. CAB therefore always tries the cheapest acceptable option first.

**Illustration.** Table 2 shows CAB's evidence in three real runs at the primary criterion (s* = 0.80, f* = home rate + 0.05), each drawn from the 100 repeats of Section 4.

**A→B with 12,000 labels (672 septic patients).**
- **Keep.** The imported model at the vendor's threshold detected 443 of the 672 labelled septic patients (65.9%). The exact lower bound of 61.7% is far below the target, so KEEP fails.
- **Calibrate.** The lowest threshold that proved 80% sensitivity alerted 62.4% of non-septic patients, against a limit of 45.1%, so CALIBRATE fails too.
- **Adapt.** The adapted model, tested on the 336 septic and 5,664 non-septic patients of the certification half, detected 286 septic patients (lower bound 80.2%). Its false-alert rate was 41.7% (upper bound 43.1%). Both tests passed, and CAB switched on ADAPT.
- **Check.** On the 8,000 target patients that were never labelled, the deployed model detected 86.6% of septic patients and alerted 43.5% of non-septic patients, so it was safe.

**A→B with only 1,000 labels (47 septic patients).**
- With so few septic patients, proving 80% sensitivity forced the threshold so low that almost every non-septic patient was alerted (96.7% for calibration, 97.7% for the adapted model).
- CAB therefore blocked. This is the right action for the evidence available, even though ADAPT would have been correct with enough labels.

**B→A with 1,000 labels.**
- Every option alerted 70–76% of non-septic patients, against a limit of 37.9%.
- CAB blocked, which was also the correct remedy given the full data.

**Table 2.** CAB's evidence in three real runs (primary criterion). Counts are detected/labelled septic patients and alerted/labelled non-septic patients. Bounds are one-sided exact bounds at α/4 = 0.0125.

| Run | Step | Data | Septic detected | Sensitivity (lower bound) | Non-septic alerted | False-alert rate (upper bound) | Limit f* | Passed |
|---|---|---|---|---|---|---|---|---|
| A→B, n = 12,000 | Keep | all labels | 443/672 | 0.659 (0.617) | 3,560/11,328 | 0.314 (0.324) | 0.451 | no |
| | Calibrate | all labels | 561/672 | 0.835 (0.800) | 7,070/11,328 | 0.624 (0.634) | 0.451 | no |
| | Adapt | certification half | 286/336 | 0.851 (0.802) | 2,360/5,664 | 0.417 (0.431) | 0.451 | **yes** |
| A→B, n = 1,000 | Keep | all labels | 31/47 | 0.660 (0.486) | 320/953 | 0.336 (0.371) | 0.451 | no |
| | Calibrate | all labels | 44/47 | 0.936 (0.807) | 922/953 | 0.967 (0.979) | 0.451 | no |
| | Adapt | certification half | 23/23 | 1.000 (0.827) | 465/476 | 0.977 (0.990) | 0.451 | no → BLOCK |
| B→A, n = 1,000 | Keep | all labels | 83/93 | 0.892 (0.799) | 635/907 | 0.700 (0.734) | 0.379 | no |
| | Calibrate | all labels | 84/93 | 0.903 (0.812) | 686/907 | 0.756 (0.788) | 0.379 | no |
| | Adapt | certification half | 43/46 | 0.935 (0.803) | 337/453 | 0.744 (0.789) | 0.379 | no → BLOCK |

### 3.5 Statistical guarantee

**Theorem.** Assume the following:

- **(A1)** The labelled patients and future patients are exchangeable draws from the target population.
- **(A2)** The labels are correct.
- **(A3)** The targets, the vendor's threshold and the imported model are fixed before labelling, and the adapted model uses only the fit half.

Then, for any shift between the hospitals and any n, the probability that CAB switches on an unsafe deployment is at most α.

*Proof sketch.* The full proof is in the supplementary material.

**Threshold certification errs with probability at most δ.** Let t₊ be the lowest threshold whose true sensitivity is below s*. This depends only on the population, not the sample. If the certified threshold is t₊ or higher, then, because detections can only fall as the threshold rises, the number of septic patients detected at t₊ is at least d_min. That count is binomial with a success probability below s*, so its chance of reaching d_min is at most δ.

**The false-alert test at a threshold chosen from the septic patients errs with probability at most δ.** Given the septic patients, the non-septic patients' scores are independent of them, so the threshold can be treated as fixed.

**Stage 1 costs 2δ, not 3δ.**
- KEEP uses a threshold no higher than τ, so its sensitivity is at least that of τ. Sensitivity therefore costs δ for either route.
- For false alerts, condition on the septic patients. If F(τ) > f*, both routes require the test at τ to pass. If F(τ) ≤ f* but F(τ_home) > f*, only KEEP can err, and it requires the test at τ_home to pass. Either way the cost is δ.

**Stage 2 costs another 2δ.** The adapted model is a fixed function of the fit half, which is independent of the certification half, so the same two arguments apply.

**Union bound.** At most one deployment is switched on, so the total probability of an unsafe deployment is at most 4δ = α. ∎

The bound holds exactly for finite samples. It needs no model of the shift and no assumption that the model's probabilities are well calibrated.

Three things are *not* guaranteed:
- that a safe remedy will be found when one exists, which is a matter of power and labels;
- that the deployed model will remain safe if the population later drifts.

### 3.6 Comparators

**Table 3.** The eleven comparators.

| Group | Policy | What it does |
|---|---|---|
| Without labels | AS-IS | The imported model with the vendor's threshold. |
| Without labels | LABEL-FREE | Moves the threshold so that the share of the target's unlabelled patient-hours that are alerted matches the vendor's home share. |
| Without labels | LABEL-SHIFT | Corrects the imported model's probabilities for the target's sepsis prevalence, estimated from unlabelled data as a ratio of mean predictions [14], and keeps the vendor's threshold. |
| With labels, point estimates | RECALIBRATE | The imported model with the highest threshold that reaches s* on the n labels. |
| With labels, point estimates | FINE-TUNE | The adapted model, with the threshold set the same way on the certification half. |
| With labels, point estimates | RETRAIN | A new LightGBM model trained only on the fit half, with the threshold set on the certification half. |
| With labels, point estimates | CLOSED-TEST | Classical updating after Vergouwe et al. [7]. A likelihood-ratio test of logistic recalibration against no change, then a 200-sample patient bootstrap of revision (the adapted model) against recalibration. Each at the 5% level; the threshold of the chosen model is set by point estimate. |
| With labels, point estimates | NAIVE-VAL | CAB's order, but each remedy is accepted if its point estimates meet both requirements (no test). |
| With labels, point estimates | NAIVE-500 | Typical practice: keep or recalibrate, judged by point estimates on the first 500 labelled patients only. |
| Certified | LTT-DIRECT | Learn-then-Test without CAB's order. The imported and the adapted model are both certified on the certification half, and the one with the lower false-alert rate is used. |
| Certified | CERT-RECAL | CAB without the adapt stage (an ablation). |

### 3.7 Experimental design

**Scenarios.** Six import scenarios were studied:

- hospital A's model at hospital B (A→B);
- hospital B's model at hospital A (B→A);
- each of these restricted to the target's medical ICU (MICU) or surgical ICU (SICU).

In addition, each hospital's model was "imported" into its own hospital (A→A, B→B). This positive control has no shift, so the correct remedy is KEEP.

**Label budgets.** Cross-hospital budgets ranged from 250 to 12,000 labelled patients, drawn at random from the target's training and validation patients. In the home control, labels came from the test patients, so budgets were limited to 2,000. In the ICU-type scenarios, the patient pools limited budgets to 4,000.

**Judging safety.** For every policy, safety was judged on the target patients that had not been labelled.

**Repetitions.** Each combination of scenario, budget and criterion was repeated 100 times with different random samples. The random seed depended only on the scenario, budget and repetition, so all policies saw exactly the same labelled patients.

**The correct remedy.** For each scenario and criterion, the correct remedy was the first of KEEP, CALIBRATE and ADAPT that met both requirements on all eligible target patients, or BLOCK if none did. The ADAPT model for this purpose was fitted on the target's training split and checked on its test split.

**Outcomes.** We report the share of runs in which each policy:
- switched on an unsafe deployment (**unsafe**);
- did so while looking safe on its own labelled data (**silent failure**);
- chose the correct remedy (**correct**).

We also report clinical impact per 100 admissions. When CAB blocks, the hospital is assumed to fall back to modified NEWS2 at 5 or more.

### 3.8 Label calculator

Each CAB decision consists of two exact binomial tests at level δ. The labels needed therefore depend on two things: how far the model's true rates are from the targets on the safe side, which we call the gap, and the share of septic patients among those labelled.

For a given gap, the calculator finds the smallest number of septic patients for which the sensitivity test passes with probability √0.9. It does the same for non-septic patients and the false-alert test, so that both tests pass together with probability at least 0.9. These counts are converted into total patients at the hospital's prevalence. They are doubled for ADAPT, because half the labels are used for fitting.

A hospital can use the calculator in advance, with the vendor's published operating curve as a guess for the gap. We checked its predictions against simulations of CAB's rule on resampled target patients.

### 3.9 Prototype application

The gate is implemented in a research prototype, *CAB Sepsis Monitor*, built on the same code as the experiments. It is described in Section 5.

### 3.10 Implementation

The analysis is written in Python with LightGBM, NumPy, pandas, SciPy and scikit-learn. All final experiments ran on one computer, so that thresholds were bit-for-bit reproducible. The code, the calculator and the application are openly available [repository link to be added].

---

## 4 Results

### 4.1 Imported models failed, differently in each direction

Imported unchanged with the vendor's 80%-sensitivity threshold, both models broke the hospital's requirements, but in opposite ways (Fig. 2; Table 4).

**Hospital A's model at hospital B (A→B)** was the less sensitive.
- Hourly AUROC fell from the local model's 0.855 to 0.777 (difference −0.078, 95% CI −0.102 to −0.057).
- Only 63% of septic patients were detected, against 84% for the local model and a target of 80%.

**Hospital B's model at hospital A (B→A)** stayed sensitive (86%) but became indiscriminate.
- 67% of non-septic patients were alerted, against 34% for the local model (difference +0.33, 95% CI 0.31 to 0.35).
- Alarms per patient-day nearly doubled, from 0.51 to 0.92.

**Table 4.** Imported vs local model at each target hospital, with paired 95% patient-bootstrap confidence intervals (`E2_ci.csv`).

| At | Imported from | Measure | Local | Imported | Difference |
|---|---|---|---|---|---|
| Emory (B) | Beth Israel (A) | Hourly AUROC | 0.855 | 0.777 | −0.078 [−0.102, −0.057] |
| Emory (B) | Beth Israel (A) | Sensitivity (patients) | 0.838 | 0.632 | −0.206 [−0.268, −0.143] |
| Emory (B) | Beth Israel (A) | Non-septic patients alerted | 0.303 | 0.250 | −0.053 [−0.070, −0.036] |
| Beth Israel (A) | Emory (B) | Hourly AUROC | 0.810 | 0.761 | −0.049 [−0.064, −0.032] |
| Beth Israel (A) | Emory (B) | Sensitivity (patients) | 0.771 | 0.858 | +0.087 [0.039, 0.134] |
| Beth Israel (A) | Emory (B) | Non-septic patients alerted | 0.339 | 0.669 | +0.330 [0.312, 0.348] |

These results determined the correct remedy in each direction (Fig. 3):
- **A→B:** recalibration could not restore both requirements, but adaptation could. The correct remedy was ADAPT for all nine criteria.
- **B→A:** no remedy could meet the primary criterion, so the correct decision was BLOCK.
- **Home control:** the correct remedy was KEEP.

No bedside score met the requirements at any cut-off in any of the 72 combinations of hospital, criterion and score that we checked. A blocked model therefore leaves the hospital with its usual care rather than with a certified alternative.

### 4.2 CAB rarely switched on an unsafe model; conventional updating usually did

Fig. 4 shows, for the primary criterion, the share of runs in which each policy switched on an unsafe deployment. Fig. 5 averages over all criteria and budgets.

**Conventional policies were unsafe in most runs** (Fig. 5):

| Policy | Unsafe | Silent failure |
|---|---|---|
| AS-IS | 77.4% | 77.4% |
| LABEL-FREE | 79.2% | – |
| FINE-TUNE | 82.3% | 39.9% |
| RECALIBRATE | 88.1% | 25.8% |
| RETRAIN | 91.9% | 18.2% |
| Classical closed testing | 80.9% | 32.4% |

AS-IS was a silent failure in every unsafe run, because the vendor's own figures always looked acceptable. For the updating policies, between a fifth and two fifths of runs were silent failures: the local data suggested the deployment was safe when it was not.

**CAB was unsafe in 0.7% of runs overall**, with a silent-failure rate of 0.7%:

| Setting | Settings | Mean unsafe | Worst setting |
|---|---|---|---|
| Cross-hospital | 126 | 0.5% | 6% |
| Home control | 72 | 1.0% | 7% |
| ICU-type imports | 162 | 0.3% | 5% |

At the ICU level, classical closed testing was unsafe in 97% of runs.

**CAB's decisions followed the correct remedy as labels grew** (Fig. 3):

- **B→A.** CAB blocked the unrepairable model in every run at every budget from 250 labels upward.
- **A→B.** CAB blocked while the evidence was insufficient. It then certified the adapted model in 10% of runs at 4,000 labels, 70% at 8,000 and 97% at 12,000 (about 690 septic patients).
- **Home control.** CAB approved the unchanged model rarely, in at most 25% of runs at 2,000 labels. The reason is given in Section 4.7.

The ablation without the adapt stage (CERT-RECAL) was almost never unsafe. It also almost never switched anything on across hospitals, because recalibration alone could not repair either model. The adapt stage is therefore what allows CAB to deploy at all after a real shift.

### 4.3 Comparison with practical alternatives

Fig. 6 compares CAB with the alternatives a hospital is most likely to use instead.

**Prevalence correction did not help.** LABEL-SHIFT estimated the target's sepsis prevalence reasonably well, at 1.7% and 2.4% of patient-hours against true values of 1.4% and 2.2%. Yet it was unsafe in 100% of cross-hospital runs. The models failed because the relation between measurements and sepsis differed between the hospitals, not because sepsis was more or less common.

**Point-estimate validation was often unsafe.** It was unsafe in about a third of runs, both across hospitals (34.9%) and at home (33.7%). The typical 500-patient validation was unsafe in 20.4% and 30.4% of runs.
- Point estimates often *chose* the correct remedy, in 64–66% of runs, but they also often accepted a deployment that was just short of the requirements.
- More labels did not fix this. In B→A at 12,000 labels, point-estimate validation still switched on an unsafe model in 29% of runs.
- The same pattern held at the ICU level: point-estimate validation was unsafe in 35.9% of runs on average and in up to 72% in the worst setting, against 0.3% for CAB.

**Learn-then-Test without CAB's order made exactly the same decision as CAB in every cross-hospital run.** At home it approved the model less often than CAB, in 3.1% against 8.0% of runs (correct in 5.7% against 7.9%). The reason is that CAB tests the unchanged model on *all* the labels, whereas unordered certification spends half of them on fitting an adapted model that was never needed. At hospital B with 2,000 labels, CAB was correct in 9% of runs and unordered Learn-then-Test in none.

### 4.4 The guarantee held at every error level

Every setting was repeated 100 times, so its measured unsafe rate is a binomial proportion with sampling error. Fig. 8 plots each setting's measured rate against the nominal level α for α = 0.01, 0.05 and 0.10. Table 5 summarises it.

**Table 5.** CAB's measured unsafe rate against the nominal level (`E12_validity.md`).

| α | Group | Settings | Mean | Worst setting | Pooled 95% upper bound | Settings significantly above α |
|---|---|---|---|---|---|---|
| 0.01 | Cross-hospital | 126 | 0.11% | 2% | 0.19% | 0 |
| 0.01 | Home | 72 | 0.14% | 2% | 0.26% | 0 |
| 0.05 | Cross-hospital | 126 | 0.51% | 6% | 0.65% | 0 |
| 0.05 | Home | 72 | 0.97% | 7% | 1.23% | 0 |
| 0.05 | ICU type | 162 | 0.28% | 5% | 0.38% | 0 |
| 0.10 | Cross-hospital | 126 | 0.91% | 13% | 1.09% | 0 |
| 0.10 | Home | 72 | 2.06% | 12% | 2.41% | 0 |

**The few settings above α are within chance.** At α = 0.05, one cross-hospital setting and three home settings exceeded 5%. No setting's exact confidence interval lay wholly above α. If every setting's true rate were exactly 5%, 48 of the 126 cross-hospital settings would show a rate above 5% by chance alone.

The home settings that exceeded α were those with the largest budgets. There, only 110–180 septic patients remained unlabelled to judge safety, so a deployment whose true sensitivity is exactly at the target is judged unsafe about half the time.

**The error level trades safety against approval.** For A→B at 12,000 labels, CAB certified adaptation in 82%, 97% and 98% of runs at α = 0.01, 0.05 and 0.10. At 8,000 labels the figures were 35%, 70% and 81%. B→A was blocked in every run at every α.

### 4.5 How many labels certification needs

**The calculator.** The labels needed fall steeply as the model's margin over the target grows (Fig. 7). To certify sensitivity at s* = 0.80, the calculator requires:

| True sensitivity above the target | Septic patients needed |
|---|---|
| 2 points | about 5,800 |
| 5 points | about 870 |
| 10 points | about 190 |

**Checked against simulation.** Run on each scenario's real operating curve, the calculator matched simulations of CAB's exact rule to within about 10–20%. For example, for A→B at the primary criterion it predicted 6,127 patients for certification alone, against 6,000 in simulation.

**Fitting the adapted model doubles the cost.** The full procedure, which also fits the adapted model on half the labels, needed about twice as many: 12,000 patients, or about 690 septic.

**The home control.** At hospital A, the vendor's threshold detected 81.6% of septic patients on the test patients, against a target of 80%. Proving a margin of 1.6 points requires about 9,600 septic patients, or roughly 109,000 admissions. This explains why CAB almost never kept the unchanged model at home with up to 2,000 labels, even though KEEP was correct. The model was not unsafe; its safety simply could not be demonstrated with so few labels.

**ICU types.** No single ICU type had enough patients to certify an adapted model. In the ICU-level A→B imports, CAB certified ADAPT in only 7–11% of runs at the largest budget the pools allowed (4,000).

### 4.6 What blocking costs

A blocked model does not leave the ward without monitoring; the hospital keeps its usual care. Modelled as modified NEWS2 at 5 or more, the fallback:

- missed few septic patients (about 1.1–1.2 per 100 admissions);
- alerted about 71 non-septic patients per 100 admissions;
- raised 2.2 alarms per patient-day.

The AI policies alerted 28–56 non-septic patients per 100 admissions.

So the benefit of blocking is avoiding an *unsafe* model. It does not avoid alarms. For B→A at 12,000 labels, every point-estimate policy switched on a model that broke a requirement in 99–100% of runs, while CAB never did. CAB's price was the noisier bedside fallback.

When CAB adapted the model (A→B at 12,000 labels), it met both requirements in 98% of runs:
- 0.87 missed septic patients per 100 admissions;
- 37 false-alerted patients per 100 admissions;
- 0.55 alarms per patient-day.

### 4.7 Hospital tolerance, not vendor headroom, decides the labels needed

**Headroom.** One might expect a vendor to make certification easier by shipping a threshold with extra headroom above the sensitivity target. We varied that headroom from 0 to 10 points (Fig. 9). Approval at home did not change: about 46% of runs at hospital A and 66% at hospital B, averaged over budgets.

The reason is that CAB's calibrate step chooses its own threshold from the hospital's labels. Headroom only changes whether an approval is recorded as KEEP or CALIBRATE. Large headroom (8–10 points) also raised the vendor's own false-alert rate by 6–15 points and could take it above the hospital's limit.

**Tolerance.** What did change approval was the hospital's false-alert tolerance m (Fig. 9). With 8,000 labels, approval at hospital A was:

| Tolerance m | Approval at hospital A |
|---|---|
| 0 points | 4% |
| 5 points | 54% |
| 10 points | 98% |

The pattern at hospital B was similar.

The practical rule follows. The hospital should set its tolerance deliberately before it starts labelling. The vendor should publish the full home operating curve, rather than a single threshold, so that the hospital can plan its labels with the calculator.

---

## 5 Application: the CAB Sepsis Monitor

The prototype shows how the gate fits into a hospital's adoption of an external model. A safety officer runs the gate before anything reaches a ward, and clinicians later see which alerting system is in use and whether it was certified. It has two screens. The figures show the Beth Israel model being installed at Emory, with a random sample of 12,000 labelled patients. This sample is drawn by the application, so it differs from the one in Table 2.

### 5.1 Deployment gate

The deployment gate (Fig. 10) collects the three things CAB needs and nothing more:

- **The hospital's requirements.** Two sliders set the sensitivity target and the extra false-alert rate the hospital will accept above the vendor's home rate.
- **Its labelled patients.** The user enters how many patients have been labelled and how they were chosen. Labels can be a random sample, or enriched so that half are septic. Enrichment keeps the tests valid, because sensitivity is estimated only from septic patients and false alerts only from non-septic ones.
- **What arrived with the model.** A "vendor package" panel shows the shipped threshold, the vendor's home validation counts, and the limits these imply at this hospital.

Pressing *Run the gate* shows three things:
- the decision, as a coloured banner;
- the evidence for each option, cheapest first: the counts, the exact bound and whether each test passed;
- in this retrospective setting only, a simulation check of what each choice would have done on the patients the gate never saw.

In Fig. 10, keeping the model fails, because its sensitivity can only be proven to be at least 62.3%. Recalibration proves 80% sensitivity but fails the false-alert test, with an upper bound of 63.2% against a limit of 45.1%. The adapted model passes both tests (80.2% and 37.1%).

The simulation check shows why the proof matters. On 8,000 unseen patients, the adapted model detected 84.5% of septic patients and alerted 35.4% of non-septic patients. A simple, unproven recalibration that looked acceptable on the labelled patients would have alerted 55.6% of non-septic patients.

### 5.2 Ward monitor

The ward monitor (Fig. 11) replays held-out ICU patients hour by hour, using whatever the gate switched on. If the gate blocked, it uses modified NEWS2. A header states which alerting system is in use and whether the gate certified it.

**The ward table** lists each bed with:
- the current score relative to the alert threshold;
- the alert status and how long the alert has been active;
- a 24-hour trend.

**The patient view** plots the risk score against the threshold, together with the main vital signs and laboratory results. A clinician can therefore see why an alert fired.

### 5.3 Engineering

- **One code path.** The application calls the same gate function as the experiments. An automated test confirms identical decisions on 3,000 random cases covering all four outcomes.
- **Runs locally.** It runs on a single workstation, and no patient data leave it.
- **The vendor package as a specification.** It states the minimum a vendor must supply for a hospital to run the gate: the model, its threshold and its home validation counts. Ideally the vendor also supplies the full operating curve, so that the hospital can plan its labels with the calculator.
- **Not yet deployable.** Integration with an electronic health record, for example through HL7 FHIR, and prospective testing are needed before any clinical use. The prototype is not intended for clinical use.

## 6 Discussion

### 6.1 Principal findings

Three findings stand out.

**Transported sepsis models broke safety requirements in direction-specific ways that a single summary measure would hide.** One model became insensitive. The other alerted two thirds of non-septic patients.

**The usual ways of handling an imported model switched on unsafe models most of the time.** This held for using it as supplied, adjusting its threshold, retraining it or applying classical updating. These policies were often silent failures: the hospital's own sample suggested the model was safe when it was not. Point-estimate validation, the closest analogue of current local validation practice, was unsafe in about a third of runs. More labels did not cure it, because the problem is a decision rule that ignores uncertainty, not a lack of data.

**A certified gate can keep the probability of unsafe activation below a chosen level with no assumptions about the shift.** CAB did so in every setting we examined, at three error levels. Its cost is explicit: it needs enough labels to prove safety, and when they are not available it blocks.

### 6.2 Implications for hospitals and vendors

**Blocking should be a planned outcome.** In our scenarios, blocking was the correct decision for one import direction, and the safe decision whenever labels were too few. A hospital adopting an external model should decide in advance what care it will provide if the model is blocked. Our analysis of bedside scores suggests that this fallback will not itself meet a strict false-alert requirement.

**Label collection should be planned.** Typical local validation samples of a few hundred patients contain a few dozen septic cases. That is enough to block a badly broken model, but too few to certify a working one. The calculator lets a hospital estimate in advance whether certification is achievable with the labels it can afford. The septic patients, not the total, are the binding resource. With the models held fixed, certification alone needed about 340 septic patients for the adapted model in A→B. Fitting it as well doubled that.

**The hospital's tolerance matters more than the vendor's threshold.** Hospitals should state how many extra false alerts they will accept, because this one number moves the labels needed by an order of magnitude. Vendors can help most by publishing their full operating curve with confidence intervals, rather than one tuned threshold.

**Order saves labels.** Testing the unchanged model first, on all the labels, lets a hospital approve a model that needs no change with twice the evidence that an unordered procedure would have. This was visible in the home control.

### 6.3 Limitations

- **Two hospitals from one country.** The Challenge data come from two US hospitals and a single, retrospectively applied sepsis definition. Validation on a multi-hospital database such as eICU [18] is the natural next step.
- **Random labelling.** The guarantee requires a random (or known-probability) sample of labelled patients. Labelling only patients that clinicians flagged, or only an early period before a seasonal change, would break it.
- **Label accuracy.** Labels were assumed correct. In practice, sepsis onset times are uncertain.
- **The safety criteria are a simplification.** They count detected patients within a fixed window. They do not weigh how early an alert comes, or the consequences of each missed case.
- **Noisy judging in small settings.** Safety was judged on finite held-out patients, so in the settings with the fewest unlabelled septic patients the measured unsafe rate is itself noisy.
- **Conservativeness.** The union bound and exact tests make CAB conservative. Measured unsafe rates were about a fifth of the nominal level, which suggests power can be recovered.
- **No monitoring after deployment.** The guarantee covers the decision at deployment, not drift afterwards.

### 6.4 Future work

Four extensions follow directly:

1. **Fewer labels.** Prediction-powered inference [19] could use the model's scores on unlabelled patients to reduce the labels needed. Sequential tests could stop labelling as soon as the evidence suffices.
2. **Less conservative error splitting.** The error could be split between the stages more efficiently than the equal Bonferroni split.
3. **Monitoring after deployment.** Combining the gate with sequential monitoring would extend the guarantee past the moment of deployment.
4. **Other domains.** The same gate applies to any imported classifier with a threshold, for example electrocardiogram interpretation across countries.

Among the variations we tested, two ablations deserve mention:
- Changing the split to 30% fit and 70% certification did not help.
- A label-free screen that skips Stage 1 when the alert rate on unlabelled target data shows a large shift saved about 8% of labels. It raised the mean unsafe rate from 0.8% to 1.2%, still well within the bound.

---

## 7 Conclusion

Importing a sepsis early-warning model is a decision with patient-safety consequences, and it can be made with a statistical guarantee. CAB tests the available remedies in order of intervention: keep, recalibrate, adapt. It switches on the first one whose sensitivity and false-alert rate are certified by exact tests, and blocks otherwise. In two hospitals and six import scenarios, CAB kept the rate of unsafe activation below the chosen level in every setting, while the alternatives did not. Its cost is the labels that proof requires. Hospitals should therefore plan for blocking, fix their false-alert tolerance before labelling, and size their local validation with a calculator, before they switch on a model built somewhere else.

---

## Declarations

**Data availability.** The PhysioNet/CinC Challenge 2019 data are openly available from PhysioNet under the Creative Commons Attribution 4.0 licence [10,16].

**Code availability.** [Repository link to be added before submission.]

**Competing interests.** [To be completed by the authors.]

**Funding.** [To be completed by the authors.]

**Author contributions.** [To be completed by the authors.]

---

## Figures

The figure files are in `outputs/sepsis/figures/` (PDF for the publisher, 300 dpi PNG for drafts).

- **Fig. 1** (`fig_workflow`). The CAB procedure. Before any local label, the hospital fixes its targets and error level. Stage 1 tests the imported model on all labels; Stage 2, reached only if Stage 1 fails, tests a model adapted on the fit half using the certification half. The first option certified is switched on; otherwise the model is blocked.
- **Fig. 2** (`fig1_transfer`). Local and imported model at each hospital: hourly AUROC, normalised utility, patient sensitivity and non-septic patients alerted, with 95% bootstrap CIs.
- **Fig. 3** (`fig2_cab_decisions`). What CAB switched on, by number of labelled patients, in each scenario (primary criterion). The correct remedy is shown above each panel.
- **Fig. 4** (`fig3_unsafe`). Share of runs that switched on an unsafe deployment, by policy and number of labels (primary criterion). The dashed line marks CAB's 5% bound.
- **Fig. 5** (`fig4_overall`). Unsafe and silent-failure rates per policy, averaged over all scenarios, criteria and budgets.
- **Fig. 6** (`fig5_baselines`). CAB against practical alternatives: unsafe and correct decisions, cross-hospital and home control.
- **Fig. 7** (`fig6_labels`). Septic patients needed to certify sensitivity, by the true margin over the target.
- **Fig. 8** (`fig7_validity`). Measured unsafe rate of every setting against the nominal α.
- **Fig. 9** (`fig8_tolerance`). Approval at home by the hospital's false-alert tolerance (models held fixed).
- **Fig. 10** (`fig_app_gate`). The deployment gate of the prototype application: the hospital's requirements, its labelled patients and the vendor package (top); the decision, the evidence for each option, cheapest first, and the retrospective simulation check (bottom).
- **Fig. 11** (`fig_app_ward`). The ward monitor, replaying ICU patients at hour 24 with the adapted model certified in Fig. 10: the ward table with each patient's score relative to the threshold, alert status and 24-hour trend, and one patient's risk trajectory against the alert threshold.

> Length note: Springer's 15–20 pages leaves room for about eight figures. Keep Figs. 1–4, 6, 10 and 11.
> Merge Figs. 7 and 9 into one two-panel figure, and move Figs. 5 and 8 to the supplement (with
> Table 5 kept in the text).

---

## References

> Check every entry (authors, year, volume, pages) against the original before submission, and
> convert to the Springer reference style the editors specify.

1. Singer M, Deutschman CS, Seymour CW, et al. The Third International Consensus Definitions for Sepsis and Septic Shock (Sepsis-3). JAMA. 2016;315(8):801–810.
2. Finlayson SG, Subbaswamy A, Singh K, et al. The clinician and dataset shift in artificial intelligence. N Engl J Med. 2021;385(3):283–286.
3. Subbaswamy A, Saria S. From development to deployment: dataset shift, causality, and shift-stable models in health AI. Biostatistics. 2020;21(2):345–352.
4. Wong A, Otles E, Donnelly JP, et al. External validation of a widely implemented proprietary sepsis prediction model in hospitalized patients. JAMA Intern Med. 2021;181(8):1065–1070.
5. Steyerberg EW. Clinical Prediction Models: A Practical Approach to Development, Validation, and Updating. 2nd ed. Springer; 2019.
6. Van Calster B, McLernon DJ, van Smeden M, et al. Calibration: the Achilles heel of predictive analytics. BMC Med. 2019;17:230.
7. Vergouwe Y, Nieboer D, Oostenbrink R, et al. A closed testing procedure to select an appropriate method for updating prediction models. Stat Med. 2017;36(28):4529–4539.
8. Angelopoulos AN, Bates S, Candès EJ, Jordan MI, Lei L. Learn then Test: calibrating predictive algorithms to achieve risk control. arXiv:2110.01052. 2021.
9. Bates S, Angelopoulos A, Lei L, Malik J, Jordan M. Distribution-free, risk-controlling prediction sets. J ACM. 2021;68(6):43.
10. Reyna MA, Josef CS, Jeter R, et al. Early prediction of sepsis from clinical data: the PhysioNet/Computing in Cardiology Challenge 2019. Crit Care Med. 2020;48(2):210–217.
11. Royal College of Physicians. National Early Warning Score (NEWS) 2: Standardising the assessment of acute-illness severity in the NHS. London: RCP; 2017.
12. Adams R, Henry KE, Sridharan A, et al. Prospective, multi-site study of patient outcomes after implementation of the TREWS machine learning-based early warning system for sepsis. Nat Med. 2022;28:1455–1460.
13. Riley RD, Debray TPA, Collins GS, et al. Minimum sample size for external validation of a clinical prediction model with a binary outcome. Stat Med. 2021;40(19):4230–4251.
14. Saerens M, Latinne P, Decaestecker C. Adjusting the outputs of a classifier to new a priori probabilities: a simple procedure. Neural Comput. 2002;14(1):21–41.
15. Lipton ZC, Wang YX, Smola AJ. Detecting and correcting for label shift with black box predictors. In: Proc. 35th Int. Conf. Machine Learning (ICML). 2018.
16. Goldberger AL, Amaral LAN, Glass L, et al. PhysioBank, PhysioToolkit, and PhysioNet: components of a new research resource for complex physiologic signals. Circulation. 2000;101(23):e215–e220.
17. Ke G, Meng Q, Finley T, et al. LightGBM: a highly efficient gradient boosting decision tree. In: Advances in Neural Information Processing Systems 30 (NeurIPS). 2017.
18. Pollard TJ, Johnson AEW, Raffa JD, et al. The eICU Collaborative Research Database, a freely available multi-center database for critical care research. Sci Data. 2018;5:180178.
19. Angelopoulos AN, Bates S, Fannjiang C, Jordan MI, Zrnic T. Prediction-powered inference. Science. 2023;382(6671):669–674.
