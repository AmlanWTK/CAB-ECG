# data/

Everything in this folder except this file is git-ignored. Datasets are downloaded on the compute desktop only.

## Expected layout

```
data/
├── ptbxl/            PTB-XL v1.0.3 (21,799 records, 100 Hz and 500 Hz)
├── ecg_arrhythmia/   Chapman-Shaoxing + Ningbo, ecg-arrhythmia v1.0.0 (45,152 records)
├── challenge2021/    Challenge 2021 v1.0.3: Georgia (10,344), CPSC 2018 (6,877), CPSC-Extra (3,453)
│                     plus dx_mapping_scored.csv, dx_mapping_unscored.csv, weights.csv
├── code15/           CODE-15%: exams.csv + HDF5 parts
└── sepsis2019/       PhysioNet/CinC Challenge 2019 v1.0.0
    └── training/
        ├── training_setA/   20,336 patients (hospital A, Beth Israel Deaconess)
        └── training_setB/   20,000 patients (hospital B, Emory)
```

## How to download (Windows PowerShell, from the repository root)

PhysioNet's own server is very slow from Bangladesh (about 10-20 KB/s per connection), so
PTB-XL and ecg-arrhythmia come from PhysioNet's official open-data mirror on Amazon S3.

**PTB-XL** (zip size must be 1839504686 bytes):

```
curl.exe -L -C - -o data\ptbxl\ptb-xl-1.0.3.zip https://physionet-open.s3.amazonaws.com/ptb-xl/ptb-xl-1.0.3.zip
tar -xf data\ptbxl\ptb-xl-1.0.3.zip -C data\ptbxl
```

**Chapman-Shaoxing + Ningbo** (zip size must be 2498709074 bytes):

```
curl.exe -L -C - -o data\ecg_arrhythmia\ecg-arrhythmia-1.0.0.zip https://physionet-open.s3.amazonaws.com/ecg-arrhythmia/ecg-arrhythmia-1.0.0.zip
tar -xf data\ecg_arrhythmia\ecg-arrhythmia-1.0.0.zip -C data\ecg_arrhythmia
```

**Challenge 2021 label tables:**

```
curl.exe -L -o data\challenge2021\dx_mapping_scored.csv https://raw.githubusercontent.com/physionetchallenges/evaluation-2021/main/dx_mapping_scored.csv
curl.exe -L -o data\challenge2021\dx_mapping_unscored.csv https://raw.githubusercontent.com/physionetchallenges/evaluation-2021/main/dx_mapping_unscored.csv
curl.exe -L -o data\challenge2021\weights.csv https://raw.githubusercontent.com/physionetchallenges/evaluation-2021/main/weights.csv
```

**Georgia + CPSC** (only on PhysioNet; needs wget: `winget install --id JernejSimoncic.Wget -e`):

```
powershell -ExecutionPolicy Bypass -File scripts\download_challenge2021.ps1
powershell -ExecutionPolicy Bypass -File scripts\check_challenge2021.ps1
```

**CODE-15%** (first 4 of 18 parts by default):

```
powershell -ExecutionPolicy Bypass -File scripts\download_code15.ps1
```

**Challenge 2019 sepsis data** (from PhysioNet's S3 mirror, 32 parallel downloads, resumable):

```
python scripts\download_sepsis2019.py
```

It ends with `RESULT: Challenge 2019 sepsis data is COMPLETE and intact.` If not, run it again;
files already downloaded are skipped.
