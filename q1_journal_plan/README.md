# Q1 journal plan

Working folder for the journal version of CAB (Calibrate, Adapt, or Block). The book chapter in
`chapter/` is frozen as submitted to Springer (commit b409291) and is not edited from here.

## Relationship to the chapter

The journal paper must be a substantially different piece of work, not a rewrite of the chapter.

- The chapter covers the method, the two-hospital PhysioNet 2019 study and the prototype app.
- The journal paper adds many hospitals, its own Sepsis-3 labels, method improvements and
  post-deployment monitoring. It cites the chapter and declares it in the cover letter.
- Before signing the chapter's copyright form, check what it allows us to reuse (figures, text).
  Before submitting, check the target journal's prior-publication policy.
- No text is copied from the chapter. Methods are rewritten, which also keeps similarity low.

## Working claim

A certified deployment gate keeps the probability of switching on an unsafe imported clinical
model below a chosen level across hundreds of real hospital-to-hospital transfers, while the
usual ways of handling an imported model (as supplied, recalibrated, fine-tuned, locally
validated by point estimate) are unsafe in a large share of them.

## Work packages

Status: `todo`, `doing`, `done`, `blocked (reason)`.

| # | Work package | What done looks like | Status |
|---|---|---|---|
| WP0 | Access | PhysioNet credentialing (CITI course) and approved access to eICU-CRD v2.0 and MIMIC-IV. Only Amlan can do this. | blocked (user) |
| WP1 | Sepsis-3 labels (shared rules in `code/sepsis3.py`; extractors for both demos; relaxed definition decided, `notes/sepsis_labels.md`) | One labelling code path for eICU and MIMIC-IV: suspected infection (cultures + antibiotics) and a SOFA rise of 2 or more, giving an onset hour per stay. Built and tested on the open demo datasets, checked against published prevalence once full access arrives. | todo |
| WP2 | Hourly features | Same vital-sign and laboratory features as the chapter, built from eICU and MIMIC-IV, so a model can move between any two hospitals. | todo |
| WP3 | Multi-hospital transfer study | Hospitals in eICU with enough septic stays as sources and targets (hundreds of pairs), plus MIMIC-IV as a different health system and as a temporal split (train on early years, deploy on later years). Per-pair unsafe-activation rates for CAB and all comparators, and their distribution across pairs. | todo |
| WP4 | Clinician-facing criteria | Alerts per true case, alerts per bed-day, positive predictive value and lead time alongside sensitivity and false-alert rate. Targets set with an ICU clinician. | todo |
| WP5 | Model-agnostic | Imported models of three kinds: gradient boosting (as in the chapter), logistic regression, a small recurrent or transformer model. | todo |
| WP6 | Fewer labels | Prediction-powered inference using scores on unlabelled patients, a better split of the error budget between the stages, and sequential labelling that stops when evidence suffices. Must keep the guarantee; shows labels saved against the chapter's gate. | done on ECG, negative: no saving from score-steered labelling with an exact guarantee (`notes/wp6_design.md`); revisit on sepsis with other signals |
| WP7 | Stronger comparators | Conformal risk control, Bayesian updating, the Riley sample-size approach, and at least one domain-adaptation method, besides the chapter's comparators. | todo |
| WP8 | Monitoring after deployment | A sequential monitor that re-opens the gate when performance drifts, with its own error guarantee. Evaluated on the MIMIC-IV temporal split. | todo |
| WP9 | Reporting | TRIPOD+AI checklist, analysis plan written before the eICU runs, code released. | todo |
| WP10 | Optional: second domain | ECG classification across countries (PTB-XL to the USA, China and Brazil; `code/cabecg/` already indexes it). Turns the paper into a general gate for imported clinical AI. Design in `notes/ecg_design.md`. | doing |
| WP11 | Optional: local hospital | A small retrospective sample from a hospital in Bangladesh, needing a clinical partner and ethics approval. | todo |

## Order

1. WP0 (user) runs in parallel with WP1 and WP2 on the open demo datasets.
2. With full access: WP3 with the chapter's gate and comparators first, then WP4 and WP5.
3. WP6 to WP8: method contributions, tested on the same pairs.
4. Decide the angle and the journal from the results, then write.

## Target journals

Chosen after WP3. Clinical informatics: npj Digital Medicine or Lancet Digital Health (stretch);
JAMIA, Journal of Biomedical Informatics, Artificial Intelligence in Medicine, International
Journal of Medical Informatics, IEEE JBHI. Statistics: Statistics in Medicine, if WP6 is strong.
Check each journal's current quartile in Scimago or JCR for the subject category we submit under.

## Data

| Dataset | Access | Size | Use |
|---|---|---|---|
| MIMIC-IV Clinical Database Demo v2.2 | open (ODbL 1.0) | 15.4 MB zip, 100 patients | WP1/WP2 development |
| eICU-CRD Demo v2.0.1 | open (ODbL 1.0) | 130.4 MB zip, 20 hospitals | WP1/WP2 development |
| eICU-CRD v2.0 | credentialed | about 200,000 ICU admissions, 208 hospitals | WP3 |
| MIMIC-IV | credentialed | | WP3, WP8 |

Datasets go in `data/` (git-ignored), as for the chapter.

## Layout

```
q1_journal_plan/
├── README.md   this plan (kept up to date as work packages move)
├── code/       journal-only code; reuses code/cabsepsis/ for the gate
└── notes/      decisions, analysis plan, literature
```
