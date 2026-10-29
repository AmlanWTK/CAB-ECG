# Finishing the ECG study (WP10)

Draft, 2026-10-29. Goal: the ECG domain complete enough to stand as a section of the journal
paper, with every result reproducible from committed code. Design and results so far are in
`ecg_design.md`.

## Steps

| # | Step | What done looks like | Effort |
|---|---|---|---|
| 1 | Label audit (E0) | `code/audit_e0.py` run on all seven cohorts. Decisions recorded for: Ningbo AF (no positives under the AF code: missing, or coded differently?), CPSC 2018 RBBB (does it include incomplete RBBB?), AF vs atrial flutter at each site. Any change to the label map reruns E1 scoring and E3. | half a day |
| 2 | Source-model seeds | Two more training seeds (1, 2) of the PTB-XL ResNet, each scored and run through E3. Report the spread of the CAB and comparator results across the three seeds. | about 1 hour of compute per seed |
| 3 | CODE-15% amplitude | E3 rerun on CODE-15% with signals halved, as the pre-specified sensitivity analysis. Shows whether the all-BLOCK result there is a scaling artefact. | 1 hour |
| 4 | Conformal risk control | Added as a comparator (WP7): threshold chosen by CRC on the labelled ECGs to control the expected miss rate. Judged with both judges, like the others. | half a day |
| 5 | Labels needed | For each transfer: the smallest budget at which CAB switches on in at least half of runs, against prevalence. Plus the analytic floor (positives needed at delta = alpha/4, divided by prevalence). | 2 hours |
| 6 | Clinician-facing numbers | At each switched-on threshold: positive predictive value and alerts per 1,000 ECGs, next to sensitivity and FPR (WP4 for ECG). | 2 hours |
| 7 | Figures | (a) unsafe rate per transfer by policy; (b) CAB decisions by budget; (c) labels needed vs prevalence; (d) primary vs cohort judge. | 1 day |
| 8 | Results write-up | ECG methods and results in journal form (new text, not from the chapter), with a list of what was pre-specified and what was added later: budgets 8,000 and 16,000, the cohort judge, the judging-rule fix. | 1-2 days |

Order: 1 first, because a label change reruns everything after it. Then 2-4 (compute, can
run together), then 5-6 (analysis of the final runs), then 7-8.

## Out of scope here

- Positive-enriched labelling, which would fix rare-finding blocking: this is WP6, tested on
  ECG and sepsis together.
- More CODE-15% parts (only part 0 of 18 is downloaded): only if step 3 makes Brazil worth it.

## Decisions needed

- Number of seeds: 3 in total proposed.
- Comparators now: CRC only, the rest of WP7 later.
