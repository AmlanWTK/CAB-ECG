# Response to the review of Section 6

2026-11-02. "Changed" means Section 6 now says this.

## Highest priority

1.1 **More labels.** Changed: the claim that more labels "did not remove the problem" is replaced
by the observed fact (NAIVE-VAL still unsafe in 29% of runs for B→A with 12,000 labels,
`E10baselines_runs.csv`) and the reviewer's sentence: larger samples improve estimation but do
not by themselves give a point-estimate rule a finite-sample bound.

1.2 **"Whatever the shift."** Changed to the reviewer's wording, with the probability space
explicit (over repeated labelled samples) and the dependence on the receiving hospital's
sampling and certification procedure.

1.3 **Label noise.** Changed to the reviewer's wording: fewer deployments in a limited experiment,
not robustness to other label errors.

1.4 **Regulatory monitoring.** Changed to the reviewer's safer formulation: frameworks address
lifecycle oversight, controlled changes and, where applicable, post-market monitoring; the
obligations depend on the system and its regulatory context.

1.5 **Blocking is not "safe".** Changed: blocking is "the appropriate decision under CAB's rule";
it avoids deploying an uncertified model but does not guarantee the fallback meets the same
requirements (no bedside score met both, `E7_fallback.md`).

1.6 **Conservativeness.** Changed to the reviewer's wording: the low observed rates motivate
investigating less conservative allocations, which would need their own theoretical
justification.

## Other changes

2.1 **340 septic patients.** Changed: stated as a simulation estimate for A→B at the primary
requirements (`E5_report.md`, part B: 343 septic), not a general minimum; the calculator caveat
stays next to it.

2.2 **"Twice the evidence."** Changed to the mechanism: testing the unchanged model first keeps
the full labelled sample for its certification, whereas an unordered procedure has less
independent certification data. The supporting result (same-hospital control: correct remedy in
7.9% of runs for CAB against 5.7% for the unordered procedure) is in Section 4.3.

2.3 **Sequential testing.** Changed: prediction-powered inference "provided the procedure
preserves the guarantee"; "sequentially valid tests or confidence sequences", with an explicit
note that repeatedly applying the fixed-sample tests used here would not preserve error control.

2.4 **The label-free screen.** The reviewer is right that not using labels is not enough on its
own. Checked in `sepsis_e3_cab.py` (`prepare_direction`): in the experiments the skip decision is
a fixed function of the unlabelled pool for each direction and target, computed once before any
label is drawn, so conditional on it the argument of Section 3.5 gives α (Stage 2 alone, two
tests at α/2). In practice this holds only if the screen is computed before labelling on data
independent of the labelled sample. A screen computed on data overlapping the labelled patients
would not be covered: the simple union bound then gives only 1.5α (Stage 1 at α/2 plus Stage 2 at
α). Changed: the variations now have their own subsection (6.5, "Two Variations of CAB"), separate
from future work, stating this condition and that they are empirical explorations, not part of the
method evaluated in Section 4.

## Limitations

The finite-population limitation now says the intervals describe repeated sampling conditional on
the two hospitals' data, not uncertainty over other hospitals or future populations. The other
limitations are unchanged.

## Second round (2026-11-02)

1. **"Local samples of a few hundred patients"** — changed to the reviewer's wording ("In our
   evaluated settings ... were often enough ... rarely enough").
2. **The 340-patient figure** — checking it exposed an interpretation error, also present in
   Section 4.5 (frozen), now corrected in both. In `sepsis_e5_labels.py` the calculator's estimate
   for ADAPT (6,127) already doubles for the fit half, and the simulation (6,000 patients, 343
   septic) also splits each sample 50/50; what it holds fixed is an adapted model fitted on the
   receiving hospital's full training set. So 340 septic patients is not "certification alone",
   and the doubling to 12,000 (686 septic, the full experiment) is not "including fitting" but the
   cost of refitting the adapted model on the fit half of each sample. Section 4.5 and 6.3 now say
   this, and 4.5 adds that it is consistent with a model fitted on a few thousand local patients
   having a smaller margin than one fitted on the full training set.
3. **Unsafe-rate denominator** — the share of all runs, with blocked runs counted as safe (the
   probability the guarantee bounds). 6.1 states this for the whole chapter; 6.5 now gives both
   denominators (1.2% vs 0.8% of all runs; 4.9% vs 3.6% of runs that deployed) and notes that with
   100 runs per setting the share of all runs equals the mean of the per-setting rates
   (`E9skip_summary.csv`).
4. **Regulatory sentence** — changed to the reviewer's wording ("propose ... where permitted by the
   applicable regulatory framework ... proposed acceptance criteria"), with the disclaimer kept
   immediately after.
5. **Other classifiers** — changed to the reviewer's wording.

Editorial: "Finite evaluation populations" and the tolerance sentence changed as suggested.
"labelnoise" and "AIenabled" are spelled with hyphens in the Word file; the hyphen is lost when
text is copied from the PDF at a line break. The EU AI Act is cited as Regulation (EU) 2024/1689
together with its 2026 amendment (Regulation (EU) 2026/1744); whether to cite the consolidated
text instead is on the submission checklist.

## Third round (2026-11-02)

- **6,000 versus 12,000 (6.3).** Rewritten so each figure says what it is. CAB always splits the
  labelled sample in half. In the simulation (`sepsis_e5_labels.py`, part B), the adapted model is
  fixed (fitted on the full training set), so the fit half is unused; 6,000 is the total labelled
  sample (343 septic, about 170 in the certification half) at which CAB certified that model in
  90% of 400 samples. In the full experiment CAB refits the adapted model on the fit half of each
  sample; 12,000 total labelled patients (686 septic) were needed for the same 90%.
- **Repeated phrase** — merged as suggested, "3 percentage points".
- **Denominators in 6.5** — changed to the suggested sentence.
- **Terminology** — "unsafe-deployment rate" now used in Sections 4 and 6 wherever "unsafe rate"
  appeared (four places).
- **Hyphens** ("labelnoise", "wholehospital", "finitesample", "AIenabled") — all hyphenated in the
  Word file; the hyphen is dropped when text is copied out of the PDF at a line break. Reviewing
  the Word file avoids this.

## Fourth round (2026-11-02)

- **Fixed-model simulation is like-for-like.** Checked in `sepsis_e5_labels.py`: `simulate` is
  called with the adapted model fitted on the receiving hospital's full training set
  (`P["ora_ad"]`), held fixed; each resampled sample is split 50/50 and CAB's rule certifies the
  adapted model on the certification half only, so the fit half is unused. Clause revised to the
  reviewer's wording.
- **Italics in 6.3.** The five paragraphs of 6.3 began with italic run-in sentences; all five now
  start with short bold run-in headings (Springer's paragraph-heading style): Planning for
  blocking; Planning label collection; Tolerance and headroom; Order of the options; Change
  control. The tolerance finding is now an ordinary sentence.
- **6.5 aggregation.** The conditional rates are pooled ratios, not averages across settings:
  1.21% / 24.89% = 4.9% and 0.76% / 20.95% = 3.6% (`E9skip_summary.csv`; with 100 runs in every
  setting, pooled counts and setting means coincide for the unconditional rates). Wording now says
  "Pooling all runs across settings".
- **Hyphens and [30]'s title.** As before, all are hyphenated in the Word file (reference [30] reads
  "Prediction-Powered Inference"); the hyphen is lost only when copying from the PDF at a line
  break.
- **Cross-section reconciliation.** Every number in Section 6 traced to Section 4 or the results:
  29% (4.3, `E10baselines_runs.csv`); 6,000 / 340 / 170 / 12,000 / 690 (4.5, `E5_report.md`);
  4% / 98% / 8,000 / 3 points (4.7, `E11_headroom.md`); 12 h, 3 h, 6 h (3.3, 4.8); a fifth of the
  nominal level (Table 8); 25% / 21% / 1.2% / 0.8% / 4.9% / 3.6% and 30% / 70% (6.5 only,
  `E9skip_summary.csv`, `E8variants_summary.csv`). Assumptions in 6.2 match A1–A3 of 3.5
  (class-stratified sampling is covered because the proof conditions on the numbers of septic and
  non-septic patients); the evidence types in 6.1 and the retrospective limitation in 6.4 match
  Sections 4.4 and 5.1.
