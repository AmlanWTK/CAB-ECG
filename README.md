# CAB-ECG

**Calibrate, Adapt, or Block?** Label-budgeted remedy selection for imported clinical AI.

The repository has two domains that share the same method:

1. **Sepsis early warning in the ICU (book chapter, current priority).** A deterioration model trained at one hospital (PhysioNet/CinC Challenge 2019: Beth Israel Deaconess or Emory) is imported by the other. Code: `code/cabsepsis/`, `code/sepsis_*.py`.
2. **12-lead ECG classification across four countries (second domain for the journal version).** Code: `code/cabecg/`, `code/build_index.py`, `code/audit_e0.py`.

### ECG domain

An ECG classifier trained on PTB-XL (Germany) is imported by target sites in the USA, China and Brazil. Using a small local labelled sample plus the site's unlabelled ECGs, the procedure chooses the cheapest remedy that restores pre-specified sensitivity and specificity, while controlling the probability of activating an unsafe model:

- **CALIBRATE**: keep the model, re-fit intercept, slope and threshold per label
- **ADAPT**: re-fit the classification head on the frozen encoder
- **BLOCK**: do not deploy the label at this site

## Repository policy

- Commit code, configs and small text files only.
- Never commit datasets, model checkpoints, embeddings or run outputs. They stay on the compute desktop in `data/` and `outputs/`, which are git-ignored.
- Exception: small final results (reports, summary CSVs, figures, tables) are copied into the tracked `results/` folder by `python scripts\publish_results.py`, so they can be shared and pulled on other computers.

## Layout

```
CAB-ECG/
├── code/       source code
├── scripts/    dataset download and check scripts (PowerShell)
├── data/       datasets (git-ignored, see data/README.md)
├── outputs/    checkpoints, embeddings, run outputs (git-ignored, created when needed)
├── results/    small final results copied from outputs/ (tracked)
└── README.md
```

## Datasets

All are open downloads with no account or approval. Cite them as their licences require.

| Dataset | Country | Role | Licence | Source |
| --- | --- | --- | --- | --- |
| PTB-XL v1.0.3 | Germany | Source | CC BY 4.0 | https://physionet.org/content/ptb-xl/1.0.3/ |
| Georgia 12-lead ECG Challenge Database (PhysioNet/CinC Challenge 2021 v1.0.3) | USA | Target | CC BY 4.0 | https://physionet.org/content/challenge-2021/1.0.3/ |
| Chapman-Shaoxing + Ningbo: "A large scale 12-lead ECG database for arrhythmia study" v1.0.0 | China | Targets | CC BY 4.0 | https://physionet.org/content/ecg-arrhythmia/1.0.0/ |
| CPSC 2018 + CPSC-Extra (PhysioNet/CinC Challenge 2021 v1.0.3) | China | Target | CC BY 4.0 | https://physionet.org/content/challenge-2021/1.0.3/ |
| CODE-15% | Brazil | Target | CC BY 4.0 | https://zenodo.org/records/4916206 |

## Setting up on the compute desktop

```
git clone https://github.com/AmlanWTK/CAB-ECG.git
cd CAB-ECG
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Then download the datasets into `data/` following `data/README.md`.

## E0: index and label audit

```
python code\build_index.py
python code\audit_e0.py
```

`build_index.py` writes one row per record for all six cohorts to `outputs/index/index.csv`.
`audit_e0.py` checks label codes, counts, prevalence, labelling conventions, durations and
signal amplitudes, and writes `outputs/audit/E0_audit.md`.

## Sepsis domain

Download the PhysioNet/CinC Challenge 2019 training data (40,336 ICU patients, about 42 MB, CC BY 4.0):

```
python scripts\download_sepsis2019.py
```

E1/E2: each hospital's LightGBM model and modified qSOFA / SIRS / NEWS2 / MEWS on internal test
patients, then each model imported unchanged to the other hospital:

```
python code\sepsis_e1_baselines.py
```

Writes `outputs/sepsis/E1_E2_results.csv` and `outputs/sepsis/E1_E2_report.md`. The first run reads
all 40,336 files and caches them in `outputs/sepsis/rows.pkl`; later runs start from the cache.

E2 with paired 95% bootstrap CIs and calibration of the imported model (needs E1 models):

```
python code\sepsis_e2_ci.py
```

E3 (v2), certified Calibrate / Adapt / Block selection against AS-IS, LABEL-FREE, RECALIBRATE,
FINE-TUNE and RETRAIN across label budgets, for both cross-hospital directions plus a same-hospital
positive control (resumable; rerun the same command after a stop):

```
python code\sepsis_e3_cab.py --reps 2 --budgets 1000
python code\sepsis_e3_cab.py
python code\sepsis_e3_cab.py --summary-only
```

Outputs: `outputs/sepsis/E2_ci.md`, `outputs/sepsis/E3v2_report.md` and the CSVs beside them.
The v1 E3 files (`E3_*`) are kept for the record.

Chapter figures (PDF + 300 dpi PNG) and tables from the E1, E2 and E3v2 outputs:

```
python code\sepsis_figures.py
```

Writes `outputs/sepsis/figures/` (fig1_transfer, fig2_cab_decisions, fig3_unsafe, fig4_overall,
chapter_tables.md).
