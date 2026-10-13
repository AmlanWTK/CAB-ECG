# CAB-ECG

**Calibrate, Adapt, or Block?** Label-budgeted remedy selection for imported ECG AI across four countries.

An ECG classifier trained on PTB-XL (Germany) is imported by target sites in the USA, China and Brazil. Using a small local labelled sample plus the site's unlabelled ECGs, the procedure chooses the cheapest remedy that restores pre-specified sensitivity and specificity, while controlling the probability of activating an unsafe model:

- **CALIBRATE**: keep the model, re-fit intercept, slope and threshold per label
- **ADAPT**: re-fit the classification head on the frozen encoder
- **BLOCK**: do not deploy the label at this site

## Repository policy

- Commit code, configs and small text files only.
- Never commit datasets, model checkpoints, embeddings or run outputs. They stay on the compute desktop in `data/` and `outputs/`, which are git-ignored.

## Layout

```
CAB-ECG/
├── code/       source code
├── scripts/    dataset download and check scripts (PowerShell)
├── data/       datasets (git-ignored, see data/README.md)
├── outputs/    checkpoints, embeddings, results (git-ignored, created when needed)
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
```

Then download the datasets into `data/` following `data/README.md`.
