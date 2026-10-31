# ECG domain: methods and results (draft 3)

Draft for the journal paper, 2026-10-31 (draft 3: further comparators and monitoring added; draft 2: whole-cohort judge primary). New text, not taken from the book chapter. Numbers
come from `outputs/ecg/` (seed 0 unless stated; seeds 1 and 2 as ranges). Figures are
`outputs/ecg/figures/F1-F6`. References [E1]-[E14] checked against the dataset pages and DOIs on
2026-10-30 and 2026-10-31; [E15] from the standard citation.

---

## Methods

### Cohorts

We imported an electrocardiogram (ECG) classifier trained in one country into six cohorts from
three other countries (Table E1). The source was PTB-XL v1.0.3 (Germany) [E1, E2]. The targets were the Georgia, CPSC 2018 and CPSC-Extra sets of the
PhysioNet/CinC Challenge 2021 v1.0.3 (USA and China) [E3, E4]; the
Chapman-Shaoxing and Ningbo parts of the ecg-arrhythmia database v1.0.0 (China) [E5, E6]; and part 0 of CODE-15% (Brazil) [E7, E8]. All are openly licensed (CC BY 4.0).

Table E1. Cohorts and findings judged.

| Role | Cohort | Country | ECGs | Findings judged |
|---|---|---|---|---|
| Source | PTB-XL | Germany | 21,799 | (training and home test) |
| Target | Georgia | USA | 10,344 | AF, IAVB, RBBB, LBBB, SB, STach |
| Target | CPSC 2018 | China | 6,877 | AF, IAVB, RBBB, LBBB |
| Target | CPSC-Extra | China | 3,453 | AF, IAVB, RBBB, STach |
| Target | Chapman-Shaoxing | China | 10,246 | AF, IAVB, RBBB, LBBB, SB, STach |
| Target | Ningbo | China | 34,904 | IAVB, RBBB, LBBB, SB, STach |
| Target | CODE-15%, part 0 | Brazil | 20,000 | AF, IAVB, RBBB, LBBB, SB, STach |

Six findings were studied: atrial fibrillation (AF), first-degree atrioventricular block
(IAVB), right and left bundle branch block (RBBB, LBBB), sinus bradycardia (SB) and sinus
tachycardia (STach). A transfer is one finding at one target cohort. A finding was judged at a
cohort only if at least 50 positives were expected to remain unlabelled at the largest label
budget used there. This rule gives 31 transfers. It excludes SB and STach at CPSC 2018, which
has no labels for them, and LBBB and SB at CPSC-Extra.

Every record was resampled to 100 Hz and cut to its first 10 s, in millivolts; shorter records
(down to 5 s) were zero-padded. Records that could not be read were dropped: one header in
ecg-arrhythmia is malformed and one record lacks lead I.

### Label audit

Before any gate was run on a target, we checked the label conventions of every cohort
(`code/audit_e0.py`). All diagnosis codes matched the Challenge 2021 mapping tables. Two
conventions differed between sites.

- Ningbo carries no AF code, but 21.8% of its ECGs carry the atrial flutter code, against
  0.3-4.3% elsewhere. The imported AF score on these ECGs had median 0.975, as for AF at the
  other sites (0.95-0.99) and unlike flutter at PTB-XL (0.11) and Georgia (0.30). We therefore
  left AF out of the primary Ningbo transfers and report "Ningbo AF from the flutter code" as a
  secondary transfer.
- CPSC 2018 has no code for incomplete RBBB. 32% of its RBBB-positive ECGs score below 0.1 on
  the imported RBBB output, against 1-6% at sites that code incomplete RBBB separately. CPSC
  2018 most likely files incomplete RBBB under RBBB. We kept it as a primary transfer: a site
  whose label means something broader is a shift a deployment gate has to handle.

The audit also found an error in our own indexing, which put one Ningbo record under Chapman.
It was fixed and the affected cohorts were rerun before the results below.

### Source model

The imported model was a one-dimensional residual network (about 3.4 million parameters) with
six sigmoid outputs, trained on PTB-XL folds 1-8 (17,418 ECGs) with early stopping on mean
validation AUROC over fold 9 (2,183). Fold 10 (2,198) served as the vendor's home test set.
Training used AdamW (learning rate 10^-3, weight decay 10^-2, cosine schedule), a
class-weighted binary cross-entropy, and random time shifts of up to 0.5 s. We trained three
seeds (0, 1, 2); validation mean AUROC was 0.986 for each.

### Operating point and safety criteria

The vendor ships each finding with the highest threshold that reaches sensitivity s* = 0.90 on
the home test set. A finding switched on at a hospital is safe if, on that hospital's ECGs,

- sensitivity is at least s* = 0.90, and
- the false-positive rate (FPR) is at most f* = max(2 x home FPR, home FPR + 0.01).

The FPR limit lets false positives at most double, with at least one percentage point allowed.
It was fixed before any gate was run, because four findings have home FPRs of 0.5-1.0% (Table
E2), where a fixed margin of five points would allow a tenfold rise. Secondary criteria were
s* = 0.80 and the absolute limit f* = home FPR + 0.05.

Table E2. Vendor operating points on the home test set (seed 0, s* = 0.90).

| Finding | Threshold | Home FPR | f* (primary) |
|---|---|---|---|
| AF | 0.469 | 0.008 | 0.018 |
| IAVB | 0.159 | 0.079 | 0.158 |
| RBBB | 0.927 | 0.005 | 0.015 |
| LBBB | 0.870 | 0.005 | 0.015 |
| SB | 0.133 | 0.129 | 0.258 |
| STach | 0.796 | 0.010 | 0.021 |

### Gate, remedies and comparators

For each transfer the hospital labels a random sample of n of its ECGs. The same sample is used
for all findings, since an ECG is read once. CAB then tries four remedies in a fixed order:

1. KEEP: the imported model and threshold.
2. CALIBRATE: the imported model with a new threshold.
3. ADAPT: a new logistic-regression head (L2 penalty, C = 0.1) on the network's frozen
   256-dimensional embedding and the imported logit. It is fitted on one half of the labels,
   stratified by the finding, and certified on the other half.
4. BLOCK: the finding is not shown.

A remedy is accepted only if exact one-sided binomial tests show, at level alpha/4 each, that
both criteria hold. Thresholds are certified by fixed-sequence testing. With alpha = 0.05 this
bounds the probability of switching on a finding that fails either criterion by alpha. The gate
is the same code as in our sepsis study [chapter], with one score per ECG.

We compared CAB with nine alternatives, all given the same labelled ECGs:

- as supplied (vendor model and threshold);
- a label-free threshold reset to the vendor's home rate of positive calls;
- recalibration and fine-tuning, each with the threshold set to s* by point estimate;
- local validation, accepting CAB's remedies in CAB's order on point estimates;
- local validation on the first 500 labelled ECGs only;
- Learn-then-Test over both models without CAB's order;
- CAB without the adapt stage;
- conformal risk control (CRC) [E9]. On the imported
  model, CRC takes the highest threshold whose bound on the miss rate is at most 1 - s*, and
  switches the finding on only if its bound on the FPR is at most f*. CRC controls both rates in
  expectation over the labelled sample. CAB controls them with high probability.

### Further comparators

A second set of comparators tested approaches a hospital might use instead of local validation.
All used the same labelled ECGs as CAB and the same judge, under the primary criterion.

- **Bayesian updating, flat prior.** On the imported model, the highest threshold with posterior
  probability at least 0.95 that sensitivity is at least s* (Beta(1, 1) prior), switched on if
  the posterior probability that the FPR is at most f* is also at least 0.95.
- **Bayesian updating at CAB's strictness.** The same, with posterior probability 1 - alpha/4 =
  0.9875 for each criterion, matching the level of CAB's tests.
- **Bayesian updating with the vendor's validation as prior.** At each threshold, the source's
  home counts (PTB-XL fold 10) are added to the target's, as when a hospital treats the
  vendor's validation as prior knowledge.
- **A minimum sample size, then point estimates.** Following the precision-based approach to
  sample size for external validation [E10, E11], here applied to the two criteria: the finding
  is switched on only once the labels hold enough positives to estimate sensitivity at s* to
  within ±0.05 (139 positives) and enough negatives to estimate the FPR at f* to within ±f*/2
  (95% intervals). Remedies are then accepted on point estimates, as in local validation.
- **Unsupervised domain adaptation (CORAL [E12]).** The target embeddings are aligned to the
  mean and covariance of the source's training embeddings and scored by the network's own
  output layer at the vendor threshold. The output layer was recovered from the stored source
  scores and embeddings; it reproduces the imported scores to within 0.00002. A second version
  recalibrates the threshold on the labels and switches on if the point estimates meet both
  criteria.

### Monitoring after deployment

Once a finding is switched on, the population it reads may change. We tested a monitor that
re-opens the gate when the switched-on model and threshold stop meeting the criteria.

- **Audits.** After deployment, a random sample of the ECGs the model reads is labelled, one at
  a time.
- **Monitor.** Two betting tests [E13], one per criterion, each at level 0.025:
  - for each audited positive, x = s* - 1(alerted), whose mean is at most 0 while sensitivity
    is at least s*;
  - for each audited negative, x = 1(alerted) - f*, whose mean is at most 0 while the FPR is at
    most f*.

  The capital is the product of (1 + lambda x) over audits. Each bet lambda ≥ 0 is set from the
  previous 100 observations only (a windowed aGRAPA bet [E13]) and clipped so that each factor is
  at least 0.5. An alarm is raised when either capital reaches 2/0.05 = 40. While every audit
  comes from a population on which the configuration is safe, each capital is a nonnegative
  supermartingale. Ville's inequality [E15] then bounds the probability of any false alarm, over an
  unlimited number of audits, by 0.05. The window lets the bets respond to recent audits rather
  than being held at zero by a long safe history.
- **Comparators.**
  - a CUSUM e-detector [E14] with the same bets, which guarantees an average of at least 5,000
    or 20,000 audits before a false alarm instead of bounding its probability;
  - point-estimate checks every 250 audits, on the last 250;
  - exact binomial tests every 250 audits, on the last 250, at 0.025 each, uncorrected for the
    repeated looks.
- **Experiment.**
  - Each target cohort in turn was the deployment site, with CAB run at the site's largest
    budget and repeated 200 times per finding. Runs that CAB blocked were not monitored.
  - 2,000 audits came from the deployment site, then 4,000 (or, in a second run, 16,000) from a
    second population. That population was the same cohort (no change), another cohort with at
    least 50 positives for the finding, or CODE-15% with halved signals (a change of device).
  - The truth was whether the deployed configuration met both criteria on the whole cohort
    being read.

### Experiment

Label budgets were 250, 500, 1,000, 2,000 and 4,000 ECGs, plus 8,000 and 16,000. A budget was
used at a cohort only if it was at most half the cohort, so 8,000 was used at Ningbo and
CODE-15% and 16,000 at Ningbo only. Each transfer and budget was repeated 100 times with fixed
seeds, giving 15,900 runs per policy and seed.

Safety was judged on the whole cohort. The cohort is the population the hospital's labelled
ECGs are drawn from, so its sensitivity and FPR at a threshold are the quantities CAB's guarantee
is about. For sampling without replacement from a finite cohort, the exact binomial tests are
conservative. For an adapted head, the ECGs it was fitted on were left out of the judge. A
policy's unsafe rate is the share of runs in which it switched on a finding that failed a
criterion on the cohort. We report its mean over transfers, the worst transfer, and the number
of transfers above alpha.

Two judges measured on a sample served as sensitivity analyses: the cohort's unlabelled ECGs,
and a fixed evaluation set of 30% of each cohort that was never available for labelling (with
budgets drawn from the remaining 70%). Any judge measured on a sample has sampling error of its
own, so it counts some thresholds that meet the criteria on the cohort as failures. These
analyses show how large that effect is.

For every transfer we also computed the following.

- **Label floor.** Even with no misses, the exact test needs 42 positives to certify
  sensitivity 0.90 at level alpha/4. So recalibration needs at least 42 / prevalence labels,
  and adaptation twice that.
- **Oracle check.** Whether any safe remedy exists at all. CALIBRATE: the threshold for s* on
  all of the cohort's positives, with its FPR compared against f*. ADAPT: a head fitted on a
  random half of the cohort and judged on the other half.
- **Ward numbers.** In runs where a finding was switched on: positive predictive value (PPV)
  and alerts per 1,000 ECGs.

Sensitivity analyses covered the two other training seeds, the four combinations of criteria,
and CODE-15% with its signals halved. Its amplitudes are about twice those of every other
cohort (99th-percentile lead II amplitude 1.56 mV, against 0.53-0.66 mV).

### Changes after the first results

The following were added or changed after the first gate results were seen. All are reported.

- **Budgets.** The 8,000 and 16,000 budgets were added to test whether rare findings were
  blocked for lack of labels.
- **Judge.** The analysis plan named the unlabelled ECGs as the judge. At large budgets that
  judge flagged thresholds that met the criteria on the cohort, so we added the whole-cohort
  judge and then a fixed evaluation set. The fixed set flagged even more of them (below). We
  made the whole cohort the primary judge because it measures the quantity the guarantee is
  about. Both sample judges are reported in full.
- **Judging rule.** The code had first selected findings with at least 20 positives in total,
  instead of the rule written above. It was corrected, which removed two transfers that CAB had
  blocked in every run.
- **Audit decisions.** The Ningbo AF decision and the fix to our indexing error both followed
  the label audit.
- **New comparator.** CRC was added as a comparator.
- **Further comparators and monitoring.** All were added after the gate results above. Bayesian
  updating at CAB's strictness was added after the flat-prior version came close to CAB. The
  monitor's window was fixed at 100 before its first run; the window sensitivity analysis
  (50 to 500), the CUSUM detector and the 16,000-audit horizon were added after it.

---

## Results

### The imported model ranked well but missed its operating point

The source model transported well in ranking, with AUROC of 0.88-0.996 at the four Chinese
cohorts and Georgia, apart from LBBB at CPSC-Extra (0.60, 38 positives; not judged). In
CODE-15% AUROC was lower (0.81-0.93). It was 0.86-0.95 with the signals halved (Table E3).

Table E3. AUROC of the imported model (seed 0).

| Cohort | AF | IAVB | RBBB | LBBB | SB | STach |
|---|---|---|---|---|---|---|
| PTB-XL (home test) | 0.983 | 0.974 | 0.998 | 0.994 | 0.962 | 0.990 |
| Georgia | 0.923 | 0.950 | 0.959 | 0.954 | 0.979 | 0.991 |
| CPSC 2018 | 0.984 | 0.925 | 0.858 | 0.929 | – | – |
| CPSC-Extra | 0.975 | 0.923 | 0.986 | 0.597 | 0.898 | 0.978 |
| Chapman-Shaoxing | 0.983 | 0.946 | 0.974 | 0.882 | 0.987 | 0.994 |
| Ningbo | – | 0.950 | 0.993 | 0.996 | 0.974 | 0.991 |
| CODE-15% | 0.890 | 0.810 | 0.933 | 0.904 | 0.806 | 0.889 |

Good ranking did not keep the vendor's threshold safe. Used as supplied, the model failed a
criterion on the cohort in 94% of runs, and in 29 of the 31 transfers more often than alpha.

### CAB kept unsafe activation below alpha in every transfer

Table E4 and Figure F1 give the unsafe rate of every policy. CAB switched on an unsafe finding
in 0.1% of runs on average (worst transfer 0.8%), and in no transfer, at any budget, more often
than alpha.

The other approaches fared as follows:

- **Local validation by point estimate** was unsafe in 33% of runs (worst 69%), with 25
  transfers above alpha.
- **The 500-ECG variant** was unsafe in 27% of runs (worst 62%).
- **Recalibration and fine-tuning** were unsafe in 86% and 85% of runs.
- **CRC** was unsafe in 15% of runs (worst 44%), with 17 transfers above alpha.

Table E4. Unsafe activation by policy: 31 transfers, all budgets, primary criterion, judged
on the whole cohort. Seed 0, with the range over three seeds in brackets.

| Policy | Mean unsafe | Worst transfer | Transfers above alpha | Runs switched on |
|---|---|---|---|---|
| As supplied | 93.5% (93.5-96.8) | 100% | 29 (29-30) | 100% |
| Label-free reset | 100% (93.7-100) | 100% | 31 (30-31) | 100% |
| Recalibrate | 86.0% (85.6-86.6) | 100% | 31 | 99.8% |
| Fine-tune | 84.6% (83.5-84.9) | 100% | 31 | 98.5% |
| Local validation | 32.8% (32.8-36.6) | 69.0% (65.0-69.8) | 25 (25-27) | 52.7% |
| Local validation, first 500 | 27.2% (27.2-31.0) | 61.7% (59.2-61.7) | 22 (22-24) | 42.3% |
| Conformal risk control | 15.1% (13.8-15.7) | 43.8% (43.8-47.2) | 17 (17-19) | 31.9% |
| Learn-then-Test, no order | 0.1% | 0.6% (0.6-0.9) | 0 | 12.7% |
| CAB without adapt | 0.1% | 0.8% (0.8-0.9) | 0 | 12.3% |
| CAB | 0.1% | 0.8% (0.8-0.9) | 0 | 14.4% |

CRC failed for a reason its guarantee predicts. It controls the expected miss rate, so a
threshold that meets s* on average across labelled samples still falls short in about half of
them. In runs where CRC switched a finding on, 51% were unsafe, nearly all on sensitivity (48%)
rather than FPR (4%). Larger budgets made this worse: CRC was unsafe in 10% of runs at 250
labels and 42% at 16,000, because it switched on more often while still missing s* about half
the time.

The result held at every site. CAB's mean unsafe rate per cohort was at most 0.2%, while local
validation's ranged from 12% (CODE-15%) to 46% (Ningbo).

### What CAB switched on, and why it blocked the rest

CAB switched a finding on in 14.4% of runs: CALIBRATE in 12.0%, ADAPT in 2.1% and KEEP in
0.3% (Figure F2). Sinus bradycardia was switched on in 97-100% of runs from 250 labels at
Chapman and Ningbo, and in at least 91% from 500 labels at Georgia. At Ningbo, IAVB, RBBB,
LBBB and STach were blocked at 4,000 labels in 90% or more of runs. At 16,000 labels they were
switched on in 61%, 95%, 49% and 97% of runs.

The oracle check sorts the 31 transfers into three groups (seed 0; seeds 1 and 2 in brackets).

| Outcome | Transfers |
|---|---|
| Switched on in at least half of runs at some budget | 7 (8, 10) |
| Blocked: no safe remedy exists, even with every ECG labelled | 14 (12, 13) |
| Blocked: a safe remedy exists, but the budgets were too small | 10 (11, 8) |

So in most blocked transfers, blocking was correct. CODE-15% was blocked throughout: only SB
had a safe remedy there, and it needed more labels than the budgets allowed. This held with
the signals halved (SB switched on in 2% of runs at 8,000 labels, everything else blocked).

The transfers blocked for lack of labels are rare findings (Figure F3). The 42-positive floor
means at least 111 labels for SB at Chapman (prevalence 38%) but 5,912 for LBBB at Ningbo
(0.7%), and twice these for ADAPT. Six transfers changed group between seeds. All were
borderline, and none moved from switched on to no safe remedy.

### What a switched-on finding means on the ward

In runs where CAB switched a finding on, median sensitivity on the cohort was 0.92-0.95
throughout. PPV depended on prevalence and on how much FPR the criterion allowed:

| Finding (site) | PPV |
|---|---|
| SB (Chapman, Ningbo) | 0.90-0.95 |
| STach (Chapman, Ningbo) | 0.93 |
| RBBB (Ningbo) | 0.79 |
| LBBB (Ningbo) | 0.53 |
| IAVB | 0.16-0.56 |

Alerts ranged from 13 to 374 per 1,000 ECGs. The criteria are defined against home
performance, so a finding can pass them and still produce mostly false alerts where it is rare.

### Robustness

**Seeds.** Across the three seeds, CAB's mean unsafe rate was 0.1% and its worst transfer
0.8-0.9%, with no transfer above alpha. All comparators kept their order (Table E4).

**Criteria.** Under the other three combinations of s* and FPR limit, CAB's mean unsafe rate was
0.1-0.2% (worst transfer 0.8-1.0%). Local validation's was 36-42% and CRC's 20-28%.

**Judges measured on a sample.** Judged on the unlabelled ECGs only, CAB's mean unsafe rate was
0.4% (worst transfer 2.2%), and three single cells (one transfer at one budget) exceeded alpha:

| Transfer | Budget | Unlabelled ECGs | Whole cohort |
|---|---|---|---|
| Georgia IAVB | 4,000 | 0.07 | 0.01 |
| Ningbo LBBB | 16,000 | 0.07 | 0.00 |
| Ningbo STach | 16,000 | 0.06 | 0.00 |

Judged on the fixed 30% evaluation set (28 transfers; CPSC-Extra AF, IAVB and RBBB have fewer
than 50 positives in it), CAB's mean unsafe rate was 0.6-1.3% over the three seeds. Four to
eight of 150 cells exceeded alpha, among them Ningbo LBBB at 16,000 labels, at 46-98%. The
evaluation set holds 63 LBBB positives, and they happen to be harder than the cohort's: the
vendor threshold detects 86% of them against 92% of the cohort, and CAB's recalibrated
thresholds 89% against 94%. Because the set is fixed, this one draw fails nearly every run. On
the whole cohort the same runs gave no cell above alpha.

The excess has one cause. At large budgets CAB certifies thresholds just above s*, and a judge
measured on a sample then puts many of them below s* by chance. This happens when the remainder
is small and moves against the labelled sample, as here, or when a fixed set is unrepresentative.
Nearly all failures in the flagged cells were on sensitivity, close to the limit. The
comparators' unsafe rates changed little between judges (Figure F4). The whole-cohort judge has
one weakness: an adapted head is judged on records near those it was fitted on. In
switched-on runs its sensitivity was 0.1-0.3 percentage points above the remainder's, and
ADAPT made up 2% of CAB's runs.

### Secondary transfer: Ningbo AF

With AF taken from the flutter code (7,615 positives), CAB blocked AF in every run. This was
correct: even the oracle threshold for s* gives FPR 0.043 against f* = 0.018, and an adapted
head 0.021. The false positives were mostly sinus tachycardia, premature atrial contractions
and atrial tachycardia. Local validation switched AF on anyway and was unsafe in 13-36% of
runs, depending on the budget. Under the absolute FPR limit, CAB switched it on in 41% of runs,
with 0.6% unsafe.

---

### Stronger comparators did not close the gap

Table E7 and Figure F5 give the further comparators.

- **Domain adaptation without labels** left 30 of 31 transfers unsafe (mean 96.8%). Aligning
  the embeddings did not restore the operating point. With the threshold recalibrated on the
  labels it was unsafe in 27.8% of runs, close to local validation.
- **Bayesian updating with the vendor's validation as prior** was unsafe in 11.5% of runs, with
  14 transfers above alpha. With few labels the prior, which no longer holds after the
  transfer, dominated: it was unsafe in 15% of runs at 250 labels and 3% at 16,000.
- **The minimum sample size** did not make point estimates safe. Once the labels sufficed it
  behaved like local validation, and its unsafe rate rose with the budget: 0% at 250 labels,
  where it almost never switched on, 16-18% at 2,000-8,000 and 38% at 16,000.
- **Bayesian updating from a flat prior** came close to CAB: unsafe in 0.5% of runs, worst
  transfer 3.4%. At CAB's strictness it was as safe as CAB (0.1%, worst 0.8%) but switched on
  less often: 12.4% of runs against 14.4%, and 49% against 80% at Ningbo's 16,000 labels.
  - The difference is the adapt stage. Of 340 runs in which CAB switched on an adapted model,
    the matched Bayesian policy switched on 3.
  - Where both work on the imported model, they agree: in every run where CAB recalibrated or
    kept the model, the matched Bayesian policy switched it on too.

Table E7. Further comparators: 31 transfers, all budgets, primary criterion, judged on the
whole cohort, seed 0. CAB, local validation and CRC from Table E4.

| Policy | Mean unsafe | Worst transfer | Transfers above alpha | Runs switched on |
|---|---|---|---|---|
| Domain adaptation, no labels | 96.8% | 100% | 30 | 100% |
| Domain adaptation, recalibrated | 27.8% | 57.7% | 23 | 43.1% |
| Bayesian, vendor's validation as prior | 11.5% | 58.0% | 14 | 33.1% |
| Minimum sample size, then point estimates | 8.6% | 41.6% | 11 | 19.7% |
| Bayesian, flat prior (95%) | 0.5% | 3.4% | 0 | 15.6% |
| Bayesian, flat prior (CAB's strictness) | 0.1% | 0.8% | 0 | 12.4% |
| Local validation | 32.8% | 69.0% | 25 | 52.7% |
| Conformal risk control | 15.1% | 43.8% | 17 | 31.9% |
| CAB | 0.1% | 0.8% | 0 | 14.4% |

So, on these data, a careful Bayesian analysis of the imported model would have been about as
safe as CAB. What CAB adds is a guarantee stated in advance, which does not depend on the
transfers lying far from the criteria, and a certified way to adapt the model when a new
threshold is not enough.

### A betting monitor caught drifts without false alarms

Of 6,200 deployments (site, finding and repeat), CAB switched on 1,533. Three were unsafe at the
deployment site and were left out. This left 3,245 runs in which the configuration stayed safe
after the change and 5,802 runs, in 58 scenarios, in which it became unsafe.

- **False alarms.** Over 6,000 audits the betting monitor raised no false alarm. Over 18,000
  audits it raised one in 0.1% of safe runs (Figure F6). Point-estimate checks raised false
  alarms in 99-100% of safe runs. Uncorrected repeated tests raised them in 9-12% of safe runs
  over 6,000 audits and 25-32% over 18,000, rising with every look.
- **Detection.** Within 4,000 audits of the change, the monitor detected 65% of drifts; within
  16,000, 87%, with a median of 1,338 audits to the alarm.
  - It detected 99% of large drifts (sensitivity more than 0.05 below s*, or FPR above twice
    f*) and 67% of small ones.
  - Drifts just past a criterion were the hardest. A sensitivity of 0.88 against s* = 0.90
    needs many audited positives to show, and at a prevalence of 2-4% audits supply few.
- **Repeated tests** detected more (83% within 4,000 audits, 94% within 16,000), partly through
  the same readiness to alarm that gave them false alarms on safe deployments.
- **The CUSUM detector** raised no false alarms but detected fewer drifts, and later: 45-48%
  within 4,000 audits and 79-81% within 16,000. Promising a long average time to a false alarm
  needs a far higher alarm level (log 20,000 against log 40), and the window already keeps the
  betting monitor responsive after a long safe stretch.
- **The window** was not what limited power. Windows from 50 to 500 observations gave detection
  of 63-66% within 4,000 audits, and at most 0.2% false alarms.

## Figure captions

**F1.** Unsafe activation per transfer, by policy. Each point is one of 31 transfers (finding
at target cohort), pooled over label budgets; primary criterion, judged on the whole cohort,
seed 0. The vertical
tick marks the mean and the horizontal line its range over three training seeds. The dashed
line is alpha = 5%.

**F2.** Share of runs in which CAB switched each finding on, by label budget. A dash marks a
budget above half the cohort, which was not run.

**F3.** Labels needed against prevalence. Points show the first budget at which CAB switched
the finding on in at least half of runs, or else the largest budget tried, by outcome. Lines
show the least number of labels at which certification is possible: 42 positives for CALIBRATE
and 84 for ADAPT.

**F4.** Unsafe rate per transfer and budget, judged on the unlabelled ECGs only (x) and on the
whole cohort (y, primary), for CAB, CRC and local validation. Axes are linear below 5% and
logarithmic above.

**F5.** Unsafe activation per transfer for the further comparators, with CAB. Each point is one
of 31 transfers, pooled over label budgets; primary criterion, judged on the whole cohort, seed
0. The tick marks the mean. The dashed line is alpha = 5%.

**F6.** Monitoring after deployment. Left: share of safe deployments with any alarm over 18,000
audits (3,245 runs). Right: share of drifts to an unsafe population detected, by the number of
audits after the change (5,802 runs in 58 scenarios; 2,000 audits before the change, up to
16,000 after). Alarms raised before the change are not counted as detections.

## References

- [E1] Wagner P, Strodthoff N, Bousseljot RD, Kreiseler D, Lunze FI, Samek W, Schaeffter T.
  PTB-XL, a large publicly available electrocardiography dataset. Sci Data. 2020;7:154.
  doi:10.1038/s41597-020-0495-6
- [E2] Wagner P, Strodthoff N, Bousseljot R, Samek W, Schaeffter T. PTB-XL, a large publicly
  available electrocardiography dataset (version 1.0.3). PhysioNet. 2022.
  doi:10.13026/kfzx-aw45
- [E3] Reyna MA, Sadr N, Perez Alday EA, Gu A, Shah AJ, Robichaux C, et al. Will two do? Varying
  dimensions in electrocardiography: the PhysioNet/Computing in Cardiology Challenge 2021.
  2021 Computing in Cardiology (CinC); 2021:1-4. doi:10.23919/CinC53138.2021.9662687
- [E4] Reyna M, Sadr N, Gu A, Perez Alday EA, Liu C, Seyedi S, Shah A, Clifford G. Will two do?
  Varying dimensions in electrocardiography: the PhysioNet/Computing in Cardiology Challenge
  2021 (version 1.0.3). PhysioNet. 2022. doi:10.13026/34va-7q14
- [E5] Zheng J, Chu H, Struppa D, Zhang J, Yacoub SM, El-Askary H, et al. Optimal multi-stage
  arrhythmia classification approach. Sci Rep. 2020;10:2898. doi:10.1038/s41598-020-59821-7
- [E6] Zheng J, Guo H, Chu H. A large scale 12-lead electrocardiogram database for arrhythmia
  study (version 1.0.0). PhysioNet. 2022. doi:10.13026/wgex-er52
- [E7] Ribeiro AH, Ribeiro MH, Paixão GMM, Oliveira DM, Gomes PR, Canazart JA, et al. Automatic
  diagnosis of the 12-lead ECG using a deep neural network. Nat Commun. 2020;11:1760.
  doi:10.1038/s41467-020-15432-4
- [E8] Ribeiro AH, Paixao GMM, Lima EM, Horta Ribeiro M, Pinto Filho MM, Gomes PR, et al.
  CODE-15%: a large scale annotated dataset of 12-lead ECGs (version 1.0.0). Zenodo. 2021.
  doi:10.5281/zenodo.4916206
- [E9] Angelopoulos AN, Bates S, Fisch A, Lei L, Schuster T. Conformal risk control. In:
  International Conference on Learning Representations (ICLR); 2024. arXiv:2208.02814

- [E10] Riley RD, Debray TPA, Collins GS, Archer L, Ensor J, van Smeden M, Snell KIE. Minimum
  sample size for external validation of a clinical prediction model with a binary outcome.
  Stat Med. 2021;40:4230-4251. doi:10.1002/sim.9025
- [E11] Riley RD, Snell KIE, Archer L, Ensor J, Debray TPA, van Calster B, et al. Evaluation of
  clinical prediction models (part 3): calculating the sample size required for an external
  validation study. BMJ. 2024;384:e074821. doi:10.1136/bmj-2023-074821
- [E12] Sun B, Feng J, Saenko K. Return of frustratingly easy domain adaptation. Proceedings of
  the AAAI Conference on Artificial Intelligence. 2016;30:2058-2065.
  doi:10.1609/aaai.v30i1.10306
- [E13] Waudby-Smith I, Ramdas A. Estimating means of bounded random variables by betting. J R
  Stat Soc Series B Stat Methodol. 2024;86(1):1-27. doi:10.1093/jrsssb/qkad009
- [E14] Shin J, Ramdas A, Rinaldo A. E-detectors: a nonparametric framework for sequential change
  detection. New Engl J Stat Data Sci. 2023:229-260. doi:10.51387/23-NEJSDS51
- [E15] Ville J. Étude critique de la notion de collectif. Paris: Gauthier-Villars; 1939.

PhysioNet also asks users to cite the platform: Pollard T, Moody BE, Lehman L, et al. PhysioNet
as a global platform for biomedical research. Nature Health. 2026. doi:10.1038/s44360-026-00096-z
(added to the paper's main reference list, not repeated here).
