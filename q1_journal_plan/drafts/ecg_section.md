# ECG domain: methods and results (draft 2)

Draft for the journal paper, 2026-10-30 (draft 2: whole-cohort judge primary). New text, not taken from the book chapter. Numbers
come from `outputs/ecg/` (seed 0 unless stated; seeds 1 and 2 as ranges). Figures are
`outputs/ecg/figures/F1-F4`. References marked [to verify] must be checked before submission.

---

## Methods

### Cohorts

We imported an electrocardiogram (ECG) classifier trained in one country into six cohorts from
three other countries (Table E1). The source was PTB-XL v1.0.3 (Germany) [to verify: Wagner et
al., Sci Data 2020]. The targets were the Georgia, CPSC 2018 and CPSC-Extra sets of the
PhysioNet/CinC Challenge 2021 v1.0.3 (USA and China) [to verify: Reyna et al., CinC 2021]; the
Chapman-Shaoxing and Ningbo parts of the ecg-arrhythmia database v1.0.0 (China) [to verify:
Zheng et al., PhysioNet 2022]; and part 0 of CODE-15% (Brazil) [to verify: Ribeiro et al., Nat
Commun 2020]. All are openly licensed (CC BY 4.0).

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
- conformal risk control (CRC) [to verify: Angelopoulos et al., ICLR 2024]. On the imported
  model, CRC takes the highest threshold whose bound on the miss rate is at most 1 - s*, and
  switches the finding on only if its bound on the FPR is at most f*. CRC controls both rates in
  expectation over the labelled sample. CAB controls them with high probability.

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

## References to verify

- PTB-XL: Wagner P, Strodthoff N, Bousseljot RD, et al. Sci Data 2020.
- PhysioNet/CinC Challenge 2021: Reyna MA, Sadr N, Perez Alday EA, et al. Computing in
  Cardiology 2021.
- ecg-arrhythmia: Zheng J, et al. PhysioNet, v1.0.0, 2022.
- CODE-15%: Ribeiro AH, Ribeiro MH, Paixão GMM, et al. Nat Commun 2020; dataset on Zenodo,
  record 4916206.
- Conformal risk control: Angelopoulos AN, Bates S, Fisch A, Lei L, Schuster T. ICLR 2024.
