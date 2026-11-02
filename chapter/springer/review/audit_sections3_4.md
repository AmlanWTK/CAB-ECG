# Cross-check of Sections 3 and 4

2026-11-02. The four agreed clarifications, then a consistency check of Sections 3 and 4 against
each other and against the code and result files. Exact wording of every change below.

## The four agreed clarifications

1. **Section 4.4, independence of runs.** Added before the sentence about requirement pairs:
   "Given the fixed hospital data, each repetition draws its own labelled sample, fits its own
   adapted model and is judged on its own unlabelled patients, using a seed of its own; the 100
   outcomes of a setting are therefore independent, and each per-setting interval describes the
   probability of an unsafe deployment under this repeated-sampling design for these hospitals'
   patients, not uncertainty about a wider population."
   Checked in `one_run`: each run creates its own random generator from its seed and uses it for
   the label sample and the halves; the adapted and retrained models are fitted with that seed; the
   judging set is the run's own unlabelled patients. The only objects shared across runs are fixed,
   non-random ones (the source model, the vendor threshold, the eligible pool and the correct-remedy
   reference). Within a run, samples are drawn without replacement.
2. **Section 4.7, sampling with replacement.** Added: "The larger budgets therefore contain repeated
   patients and represent repeated sampling from the test patients' empirical distribution; they
   show how approval responds to headroom and tolerance, and should not be read as the evidence
   that labelling the same number of distinct patients would provide."
3. **Section 4.5, calculator check.** Added: "Because the simulated samples are drawn with
   replacement, they may contain the same patient more than once, so this agreement is empirical
   evidence under that sampling design rather than a guarantee of the number of distinct patients a
   hospital would need."
4. **Section 3.8 (frozen), terminology.** "on resampled patients" → "on patients resampled with
   replacement".

## Findings of the cross-check

| # | Area | Finding | Change |
|---|---|---|---|
| 1 | Sampling design (budgets) | **Discrepancy.** Section 3.7 said the ICU-type transfers were limited to 4,000 labels. The result files show 4,000 for the transfers into hospital B's units but 2,000 for those into hospital A's units (`E10units_summary.csv`). This is also what gives Table 7's 162 ICU settings (2 units × 5 budgets × 9 pairs + 2 units × 4 budgets × 9 pairs). | Section 3.7 (frozen) now states both limits, and lists the whole-hospital budgets (250 to 12,000, seven values) explicitly. |
| 2 | Patient populations | "Eligible patients" was used in 3.7 and 4.1 without being defined. In the code, eligible = all patients of the receiving hospital (or unit) in the transfers, and its test patients in the home control. | Section 3.7 (frozen) now defines it in one clause. |
| 3 | Repetition counts in captions | Figs. 4, 5 and 6(b, c) did not state their repetition counts. | Fig. 4: "100 runs per budget"; Fig. 5: "100 runs per setting"; Fig. 6(b, c): samples with replacement from the test patients, 200 per point, approval = KEEP or CALIBRATE. |
| 4 | Table 9 | The note did not say whether the CAB row covers every run. CAB deployed in all 20 runs (`E13_leadtime.md`, CAB runs = 20). | Note now says so. |
| 5 | Threshold selection | Consistent: vendor thresholds fixed in advance (3.2, Table 5); point-estimate policies choose and check thresholds on the same labelled patients (3.6); CALIBRATE and ADAPT choose thresholds from data, so the calculator is a planning approximation (3.8, 4.5); Table 9's local reference has its threshold set on its own evaluation patients (stated in the note). | None. |
| 6 | Guarantee versus empirical results | Consistent: 3.5 states the theorem for any shift and sample size under A1–A3; 4.4 says the simulations are consistent with it, conditional on these hospitals' data, and do not prove it. | None (beyond clarification 1). |
| 7 | Labelled patients excluded from judging | Consistent in 3.7, 4.4 and Table 9's note; checked in code (`comp = eligible & ~lab`). | None. |
| 8 | Setting counts | Consistent: whole hospital 126 = 2 × 7 × 9; same hospital 72 = 2 × 4 × 9; ICU type 162 (finding 1). | None. |
| 9 | Correct remedy | Consistently described as an evaluation reference (3.7, opening of Section 4, Fig. 3). | None. |
| 10 | Denominators and intervals | Consistent: Table 5 paired percentile bootstrap on test patients; Table 8 per-setting Clopper–Pearson, group means descriptive; 4.6 per 100 admissions and per patient-day; Table 9 lead time among detected patients, last column among all septic patients. | None. |

## Changes to Section 3 (frozen)

Three wording changes, none to the method:
- 3.8: "patients resampled with replacement" (agreed).
- 3.7: the ICU-type budget limits corrected (4,000 and 2,000) and the whole-hospital budgets listed
  (finding 1). This corrects a factual error in the description, not the experiment.
- 3.7: "eligible patients" defined (finding 2).

## Final verification before freezing (2026-11-02)

1. **Budgets and setting counts** (`E10baselines_summary.csv`, `E10units_summary.csv`):
   A→B and B→A: 250, 500, 1,000, 2,000, 4,000, 8,000, 12,000 (126 settings); A→A and B→B: 250 to
   2,000 (72); transfers into hospital B's units: 250 to 4,000; into hospital A's units: 250 to
   2,000 (162 in total). These match Section 3.7 and Tables 7 and 8.
2. **Section 4.4 independence statement**: it is conditional on the fixed hospital data and says
   the intervals describe the repeated-sampling procedure for these hospitals' patients, not a
   wider population.
3. **Run counts**: Figs. 3 and 4 (`E3mac100_summary.csv`) and Fig. 5 (`E10baselines_summary.csv`)
   have 100 runs per setting; Fig. 6(b, c) has 200 samples per point (`sepsis_e11_headroom.py`,
   default `--reps 200`, and `E11_headroom.md`); Table 9 has 20 runs with CAB deploying in all 20
   (`E13_leadtime.md`).

Sections 3 and 4 frozen.
