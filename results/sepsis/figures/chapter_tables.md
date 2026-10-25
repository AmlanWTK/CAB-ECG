# Chapter tables (sepsis CAB study)

## Table 1. Cohorts

| Hospital | Patients | Septic, n (%) | Age, median (IQR) | Male (%) | ICU hours, median (IQR) | Patient-hours |
| --- | --- | --- | --- | --- | --- | --- |
| Beth Israel | 20,336 | 1,790 (8.8) | 65 (52–76) | 58.2 | 39 (25–47) | 790,215 |
| Emory | 20,000 | 1,142 (5.7) | 62 (50–72) | 53.7 | 38 (23–47) | 761,995 |

## Table 2. Test-set performance: local and imported LightGBM, bedside scores

| Model | Trained at | Evaluated at | Threshold | AUROC | AUPRC | Utility | Sensitivity | Alarms/patient-day | Alert-hours (%) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LightGBM | Beth Israel | Beth Israel | 80% sens @ A val | 0.81 | 0.112 | 0.395 | 0.771 | 0.507 | 15.841 |
| LightGBM | Beth Israel | Emory | 80% sens @ A val | 0.777 | 0.06 | 0.27 | 0.632 | 0.324 | 9.587 |
| LightGBM | Emory | Beth Israel | 80% sens @ B val | 0.761 | 0.075 | 0.303 | 0.858 | 0.922 | 28.018 |
| LightGBM | Emory | Emory | 80% sens @ B val | 0.855 | 0.109 | 0.391 | 0.838 | 0.422 | 12.119 |
| qSOFA (modified) | – | Beth Israel | standard >= 2 | 0.575 | 0.026 | 0.018 | 0.265 | 0.534 | 4.206 |
| qSOFA (modified) | – | Emory | standard >= 2 | 0.559 | 0.017 | -0.006 | 0.211 | 0.379 | 2.816 |
| SIRS (modified) | – | Beth Israel | standard >= 2 | 0.615 | 0.033 | 0.082 | 0.832 | 1.709 | 34.384 |
| SIRS (modified) | – | Emory | standard >= 2 | 0.642 | 0.023 | -0.046 | 0.807 | 1.358 | 26.503 |
| NEWS2 (modified) | – | Beth Israel | standard >= 5 | 0.643 | 0.036 | 0.105 | 0.872 | 2.224 | 30.056 |
| NEWS2 (modified) | – | Emory | standard >= 5 | 0.67 | 0.028 | 0.02 | 0.789 | 1.439 | 18.642 |
| MEWS (modified) | – | Beth Israel | standard >= 4 | 0.608 | 0.033 | 0.08 | 0.5 | 0.739 | 8.336 |
| MEWS (modified) | – | Emory | standard >= 4 | 0.603 | 0.024 | 0.048 | 0.469 | 0.631 | 7.135 |

## Table 3. Imported vs local model at each hospital (95% patient-bootstrap CI)

| At | Imported from | metric | Local | Imported | Difference |
| --- | --- | --- | --- | --- | --- |
| Emory | Beth Israel | AUROC_hourly | 0.855 [0.834, 0.874] | 0.777 [0.748, 0.799] | -0.078 [-0.102, -0.057] |
| Emory | Beth Israel | utility | 0.391 [0.334, 0.442] | 0.27 [0.212, 0.325] | -0.12 [-0.169, -0.072] |
| Emory | Beth Israel | sensitivity_patient | 0.838 [0.791, 0.882] | 0.632 [0.572, 0.693] | -0.206 [-0.268, -0.143] |
| Emory | Beth Israel | false_alert_patients | 0.303 [0.289, 0.317] | 0.25 [0.237, 0.264] | -0.053 [-0.070, -0.036] |
| Emory | Beth Israel | alarms_per_patient_day | 0.422 [0.400, 0.444] | 0.324 [0.305, 0.342] | -0.098 [-0.122, -0.073] |
| Beth Israel | Emory | AUROC_hourly | 0.81 [0.784, 0.826] | 0.761 [0.735, 0.778] | -0.049 [-0.064, -0.032] |
| Beth Israel | Emory | utility | 0.395 [0.351, 0.436] | 0.303 [0.254, 0.351] | -0.092 [-0.131, -0.051] |
| Beth Israel | Emory | sensitivity_patient | 0.771 [0.727, 0.812] | 0.858 [0.821, 0.892] | 0.087 [0.039, 0.134] |
| Beth Israel | Emory | false_alert_patients | 0.339 [0.323, 0.354] | 0.669 [0.654, 0.685] | 0.33 [0.312, 0.348] |
| Beth Israel | Emory | alarms_per_patient_day | 0.507 [0.484, 0.532] | 0.922 [0.896, 0.952] | 0.415 [0.386, 0.445] |

## Table 4. Remedy selection, primary criterion (sensitivity >= 0.80; false alerts <= home + 0.05)

| Setting | Labelled n | Policy | Switched on (%) | Unsafe (%) | Silent failure (%) | Correct remedy (%) | Utility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Beth Israel → Beth Israel (control) | 250 | AS-IS | 100.0 | 0.0 | 0.0 |  | 0.395 |
| Beth Israel → Beth Israel (control) | 250 | CAB | 0.0 | 0.0 | 0.0 | 0.0 | 0.104 |
| Beth Israel → Beth Israel (control) | 250 | FINE-TUNE | 100.0 | 86.7 | 66.7 |  | 0.361 |
| Beth Israel → Beth Israel (control) | 250 | LABEL-FREE | 100.0 | 6.7 | 0.0 |  | 0.396 |
| Beth Israel → Beth Israel (control) | 250 | RECALIBRATE | 100.0 | 83.3 | 60.0 |  | 0.384 |
| Beth Israel → Beth Israel (control) | 250 | RETRAIN | 100.0 | 100.0 | 3.3 |  | 0.071 |
| Beth Israel → Beth Israel (control) | 500 | AS-IS | 100.0 | 0.0 | 0.0 |  | 0.396 |
| Beth Israel → Beth Israel (control) | 500 | CAB | 0.0 | 0.0 | 0.0 | 0.0 | 0.105 |
| Beth Israel → Beth Israel (control) | 500 | FINE-TUNE | 100.0 | 90.0 | 53.3 |  | 0.374 |
| Beth Israel → Beth Israel (control) | 500 | LABEL-FREE | 100.0 | 13.3 | 0.0 |  | 0.398 |
| Beth Israel → Beth Israel (control) | 500 | RECALIBRATE | 100.0 | 73.3 | 53.3 |  | 0.392 |
| Beth Israel → Beth Israel (control) | 500 | RETRAIN | 100.0 | 100.0 | 6.7 |  | 0.114 |
| Beth Israel → Beth Israel (control) | 1000 | AS-IS | 100.0 | 13.3 | 13.3 |  | 0.392 |
| Beth Israel → Beth Israel (control) | 1000 | CAB | 3.3 | 3.3 | 3.3 | 0.0 | 0.11 |
| Beth Israel → Beth Israel (control) | 1000 | FINE-TUNE | 100.0 | 86.7 | 70.0 |  | 0.376 |
| Beth Israel → Beth Israel (control) | 1000 | LABEL-FREE | 100.0 | 23.3 | 0.0 |  | 0.394 |
| Beth Israel → Beth Israel (control) | 1000 | RECALIBRATE | 100.0 | 53.3 | 50.0 |  | 0.391 |
| Beth Israel → Beth Israel (control) | 1000 | RETRAIN | 100.0 | 100.0 | 13.3 |  | 0.245 |
| Beth Israel → Beth Israel (control) | 2000 | AS-IS | 100.0 | 13.3 | 13.3 |  | 0.392 |
| Beth Israel → Beth Israel (control) | 2000 | CAB | 6.7 | 6.7 | 6.7 | 0.0 | 0.119 |
| Beth Israel → Beth Israel (control) | 2000 | FINE-TUNE | 100.0 | 76.7 | 60.0 |  | 0.386 |
| Beth Israel → Beth Israel (control) | 2000 | LABEL-FREE | 100.0 | 30.0 | 0.0 |  | 0.393 |
| Beth Israel → Beth Israel (control) | 2000 | RECALIBRATE | 100.0 | 56.7 | 53.3 |  | 0.393 |
| Beth Israel → Beth Israel (control) | 2000 | RETRAIN | 100.0 | 100.0 | 3.3 |  | 0.289 |
| Beth Israel model → Emory | 250 | AS-IS | 100.0 | 100.0 | 100.0 |  | 0.277 |
| Beth Israel model → Emory | 250 | CAB | 0.0 | 0.0 | 0.0 | 0.0 | 0.066 |
| Beth Israel model → Emory | 250 | FINE-TUNE | 100.0 | 100.0 | 36.7 |  | 0.189 |
| Beth Israel model → Emory | 250 | LABEL-FREE | 100.0 | 100.0 | 0.0 |  | 0.24 |
| Beth Israel model → Emory | 250 | RECALIBRATE | 100.0 | 100.0 | 40.0 |  | 0.201 |
| Beth Israel model → Emory | 250 | RETRAIN | 100.0 | 100.0 | 23.3 |  | -0.247 |
| Beth Israel model → Emory | 500 | AS-IS | 100.0 | 100.0 | 100.0 |  | 0.277 |
| Beth Israel model → Emory | 500 | CAB | 0.0 | 0.0 | 0.0 | 0.0 | 0.066 |
| Beth Israel model → Emory | 500 | FINE-TUNE | 100.0 | 100.0 | 46.7 |  | 0.217 |
| Beth Israel model → Emory | 500 | LABEL-FREE | 100.0 | 100.0 | 0.0 |  | 0.24 |
| Beth Israel model → Emory | 500 | RECALIBRATE | 100.0 | 100.0 | 26.7 |  | 0.188 |
| Beth Israel model → Emory | 500 | RETRAIN | 100.0 | 100.0 | 26.7 |  | 0.023 |
| Beth Israel model → Emory | 1000 | AS-IS | 100.0 | 100.0 | 100.0 |  | 0.276 |
| Beth Israel model → Emory | 1000 | CAB | 0.0 | 0.0 | 0.0 | 0.0 | 0.066 |
| Beth Israel model → Emory | 1000 | FINE-TUNE | 100.0 | 96.7 | 50.0 |  | 0.26 |
| Beth Israel model → Emory | 1000 | LABEL-FREE | 100.0 | 100.0 | 0.0 |  | 0.239 |
| Beth Israel model → Emory | 1000 | RECALIBRATE | 100.0 | 100.0 | 20.0 |  | 0.204 |
| Beth Israel model → Emory | 1000 | RETRAIN | 100.0 | 100.0 | 16.7 |  | 0.134 |
| Beth Israel model → Emory | 2000 | AS-IS | 100.0 | 100.0 | 100.0 |  | 0.276 |
| Beth Israel model → Emory | 2000 | CAB | 0.0 | 0.0 | 0.0 | 0.0 | 0.067 |
| Beth Israel model → Emory | 2000 | FINE-TUNE | 100.0 | 76.7 | 53.3 |  | 0.303 |
| Beth Israel model → Emory | 2000 | LABEL-FREE | 100.0 | 100.0 | 0.0 |  | 0.24 |
| Beth Israel model → Emory | 2000 | RECALIBRATE | 100.0 | 100.0 | 10.0 |  | 0.208 |
| Beth Israel model → Emory | 2000 | RETRAIN | 100.0 | 96.7 | 36.7 |  | 0.198 |
| Beth Israel model → Emory | 4000 | AS-IS | 100.0 | 100.0 | 100.0 |  | 0.277 |
| Beth Israel model → Emory | 4000 | CAB | 10.0 | 3.3 | 3.3 | 10.0 | 0.091 |
| Beth Israel model → Emory | 4000 | FINE-TUNE | 100.0 | 46.7 | 36.7 |  | 0.328 |
| Beth Israel model → Emory | 4000 | LABEL-FREE | 100.0 | 100.0 | 0.0 |  | 0.241 |
| Beth Israel model → Emory | 4000 | RECALIBRATE | 100.0 | 100.0 | 3.3 |  | 0.206 |
| Beth Israel model → Emory | 4000 | RETRAIN | 100.0 | 50.0 | 43.3 |  | 0.306 |
| Beth Israel model → Emory | 8000 | AS-IS | 100.0 | 100.0 | 100.0 |  | 0.276 |
| Beth Israel model → Emory | 8000 | CAB | 63.3 | 3.3 | 3.3 | 63.3 | 0.244 |
| Beth Israel model → Emory | 8000 | FINE-TUNE | 100.0 | 50.0 | 50.0 |  | 0.359 |
| Beth Israel model → Emory | 8000 | LABEL-FREE | 100.0 | 100.0 | 0.0 |  | 0.239 |
| Beth Israel model → Emory | 8000 | RECALIBRATE | 100.0 | 100.0 | 0.0 |  | 0.208 |
| Beth Israel model → Emory | 8000 | RETRAIN | 100.0 | 60.0 | 60.0 |  | 0.344 |
| Beth Israel model → Emory | 12000 | AS-IS | 100.0 | 100.0 | 100.0 |  | 0.279 |
| Beth Israel model → Emory | 12000 | CAB | 96.7 | 3.3 | 3.3 | 96.7 | 0.354 |
| Beth Israel model → Emory | 12000 | FINE-TUNE | 100.0 | 36.7 | 36.7 |  | 0.373 |
| Beth Israel model → Emory | 12000 | LABEL-FREE | 100.0 | 100.0 | 0.0 |  | 0.241 |
| Beth Israel model → Emory | 12000 | RECALIBRATE | 100.0 | 100.0 | 0.0 |  | 0.212 |
| Beth Israel model → Emory | 12000 | RETRAIN | 100.0 | 43.3 | 43.3 |  | 0.373 |
| Emory model → Beth Israel | 250 | AS-IS | 100.0 | 100.0 | 100.0 |  | 0.311 |
| Emory model → Beth Israel | 250 | CAB | 0.0 | 0.0 | 0.0 | 100.0 | 0.116 |
| Emory model → Beth Israel | 250 | FINE-TUNE | 100.0 | 100.0 | 26.7 |  | 0.285 |
| Emory model → Beth Israel | 250 | LABEL-FREE | 100.0 | 100.0 | 0.0 |  | 0.303 |
| Emory model → Beth Israel | 250 | RECALIBRATE | 100.0 | 100.0 | 13.3 |  | 0.298 |
| Emory model → Beth Israel | 250 | RETRAIN | 100.0 | 100.0 | 10.0 |  | 0.128 |
| Emory model → Beth Israel | 500 | AS-IS | 100.0 | 100.0 | 100.0 |  | 0.311 |
| Emory model → Beth Israel | 500 | CAB | 0.0 | 0.0 | 0.0 | 100.0 | 0.116 |
| Emory model → Beth Israel | 500 | FINE-TUNE | 100.0 | 100.0 | 13.3 |  | 0.315 |
| Emory model → Beth Israel | 500 | LABEL-FREE | 100.0 | 100.0 | 0.0 |  | 0.303 |
| Emory model → Beth Israel | 500 | RECALIBRATE | 100.0 | 100.0 | 6.7 |  | 0.313 |
| Emory model → Beth Israel | 500 | RETRAIN | 100.0 | 100.0 | 3.3 |  | 0.215 |
| Emory model → Beth Israel | 1000 | AS-IS | 100.0 | 100.0 | 100.0 |  | 0.311 |
| Emory model → Beth Israel | 1000 | CAB | 0.0 | 0.0 | 0.0 | 100.0 | 0.116 |
| Emory model → Beth Israel | 1000 | FINE-TUNE | 100.0 | 100.0 | 10.0 |  | 0.33 |
| Emory model → Beth Israel | 1000 | LABEL-FREE | 100.0 | 100.0 | 0.0 |  | 0.304 |
| Emory model → Beth Israel | 1000 | RECALIBRATE | 100.0 | 100.0 | 3.3 |  | 0.32 |
| Emory model → Beth Israel | 1000 | RETRAIN | 100.0 | 100.0 | 6.7 |  | 0.271 |
| Emory model → Beth Israel | 2000 | AS-IS | 100.0 | 100.0 | 100.0 |  | 0.311 |
| Emory model → Beth Israel | 2000 | CAB | 0.0 | 0.0 | 0.0 | 100.0 | 0.117 |
| Emory model → Beth Israel | 2000 | FINE-TUNE | 100.0 | 100.0 | 6.7 |  | 0.342 |
| Emory model → Beth Israel | 2000 | LABEL-FREE | 100.0 | 100.0 | 0.0 |  | 0.303 |
| Emory model → Beth Israel | 2000 | RECALIBRATE | 100.0 | 100.0 | 0.0 |  | 0.318 |
| Emory model → Beth Israel | 2000 | RETRAIN | 100.0 | 100.0 | 3.3 |  | 0.328 |
| Emory model → Beth Israel | 4000 | AS-IS | 100.0 | 100.0 | 100.0 |  | 0.307 |
| Emory model → Beth Israel | 4000 | CAB | 0.0 | 0.0 | 0.0 | 100.0 | 0.114 |
| Emory model → Beth Israel | 4000 | FINE-TUNE | 100.0 | 100.0 | 6.7 |  | 0.358 |
| Emory model → Beth Israel | 4000 | LABEL-FREE | 100.0 | 100.0 | 0.0 |  | 0.301 |
| Emory model → Beth Israel | 4000 | RECALIBRATE | 100.0 | 100.0 | 0.0 |  | 0.315 |
| Emory model → Beth Israel | 4000 | RETRAIN | 100.0 | 100.0 | 0.0 |  | 0.36 |
| Emory model → Beth Israel | 8000 | AS-IS | 100.0 | 100.0 | 100.0 |  | 0.308 |
| Emory model → Beth Israel | 8000 | CAB | 0.0 | 0.0 | 0.0 | 100.0 | 0.113 |
| Emory model → Beth Israel | 8000 | FINE-TUNE | 100.0 | 100.0 | 10.0 |  | 0.379 |
| Emory model → Beth Israel | 8000 | LABEL-FREE | 100.0 | 100.0 | 0.0 |  | 0.302 |
| Emory model → Beth Israel | 8000 | RECALIBRATE | 100.0 | 100.0 | 0.0 |  | 0.318 |
| Emory model → Beth Israel | 8000 | RETRAIN | 100.0 | 100.0 | 6.7 |  | 0.39 |
| Emory model → Beth Israel | 12000 | AS-IS | 100.0 | 100.0 | 100.0 |  | 0.309 |
| Emory model → Beth Israel | 12000 | CAB | 0.0 | 0.0 | 0.0 | 100.0 | 0.118 |
| Emory model → Beth Israel | 12000 | FINE-TUNE | 100.0 | 96.7 | 30.0 |  | 0.386 |
| Emory model → Beth Israel | 12000 | LABEL-FREE | 100.0 | 100.0 | 0.0 |  | 0.303 |
| Emory model → Beth Israel | 12000 | RECALIBRATE | 100.0 | 100.0 | 0.0 |  | 0.319 |
| Emory model → Beth Israel | 12000 | RETRAIN | 100.0 | 100.0 | 36.7 |  | 0.396 |
| Emory → Emory (control) | 250 | AS-IS | 100.0 | 0.0 | 0.0 |  | 0.388 |
| Emory → Emory (control) | 250 | CAB | 0.0 | 0.0 | 0.0 | 0.0 | 0.016 |
| Emory → Emory (control) | 250 | FINE-TUNE | 100.0 | 93.3 | 76.7 |  | 0.307 |
| Emory → Emory (control) | 250 | LABEL-FREE | 100.0 | 0.0 | 0.0 |  | 0.389 |
| Emory → Emory (control) | 250 | RECALIBRATE | 100.0 | 63.3 | 60.0 |  | 0.344 |
| Emory → Emory (control) | 250 | RETRAIN | 100.0 | 100.0 | 10.0 |  | -0.165 |
| Emory → Emory (control) | 500 | AS-IS | 100.0 | 0.0 | 0.0 |  | 0.389 |
| Emory → Emory (control) | 500 | CAB | 3.3 | 0.0 | 0.0 | 0.0 | 0.03 |
| Emory → Emory (control) | 500 | FINE-TUNE | 100.0 | 76.7 | 53.3 |  | 0.334 |
| Emory → Emory (control) | 500 | LABEL-FREE | 100.0 | 0.0 | 0.0 |  | 0.389 |
| Emory → Emory (control) | 500 | RECALIBRATE | 100.0 | 56.7 | 53.3 |  | 0.369 |
| Emory → Emory (control) | 500 | RETRAIN | 100.0 | 100.0 | 13.3 |  | 0.042 |
| Emory → Emory (control) | 1000 | AS-IS | 100.0 | 0.0 | 0.0 |  | 0.388 |
| Emory → Emory (control) | 1000 | CAB | 3.3 | 0.0 | 0.0 | 3.3 | 0.027 |
| Emory → Emory (control) | 1000 | FINE-TUNE | 100.0 | 70.0 | 50.0 |  | 0.36 |
| Emory → Emory (control) | 1000 | LABEL-FREE | 100.0 | 0.0 | 0.0 |  | 0.389 |
| Emory → Emory (control) | 1000 | RECALIBRATE | 100.0 | 60.0 | 60.0 |  | 0.369 |
| Emory → Emory (control) | 1000 | RETRAIN | 100.0 | 100.0 | 16.7 |  | 0.144 |
| Emory → Emory (control) | 2000 | AS-IS | 100.0 | 3.3 | 3.3 |  | 0.376 |
| Emory → Emory (control) | 2000 | CAB | 23.3 | 3.3 | 3.3 | 10.0 | 0.094 |
| Emory → Emory (control) | 2000 | FINE-TUNE | 100.0 | 50.0 | 50.0 |  | 0.368 |
| Emory → Emory (control) | 2000 | LABEL-FREE | 100.0 | 3.3 | 0.0 |  | 0.377 |
| Emory → Emory (control) | 2000 | RECALIBRATE | 100.0 | 50.0 | 50.0 |  | 0.364 |
| Emory → Emory (control) | 2000 | RETRAIN | 100.0 | 96.7 | 36.7 |  | 0.264 |

## Table S1. Correct remedy (from full target data) for every safety criterion

| Setting | s_star | margin | f_star | oracle_remedy |
| --- | --- | --- | --- | --- |
| Beth Israel model → Emory | 0.75 | 0.0 | 0.31 | ADAPT |
| Beth Israel model → Emory | 0.75 | 0.05 | 0.36 | ADAPT |
| Beth Israel model → Emory | 0.75 | 0.1 | 0.41 | ADAPT |
| Beth Israel model → Emory | 0.8 | 0.0 | 0.401 | ADAPT |
| Beth Israel model → Emory | 0.8 | 0.05 | 0.451 | ADAPT |
| Beth Israel model → Emory | 0.8 | 0.1 | 0.501 | ADAPT |
| Beth Israel model → Emory | 0.85 | 0.0 | 0.484 | ADAPT |
| Beth Israel model → Emory | 0.85 | 0.05 | 0.534 | ADAPT |
| Beth Israel model → Emory | 0.85 | 0.1 | 0.584 | ADAPT |
| Emory model → Beth Israel | 0.75 | 0.0 | 0.298 | BLOCK |
| Emory model → Beth Israel | 0.75 | 0.05 | 0.348 | ADAPT |
| Emory model → Beth Israel | 0.75 | 0.1 | 0.398 | ADAPT |
| Emory model → Beth Israel | 0.8 | 0.0 | 0.329 | BLOCK |
| Emory model → Beth Israel | 0.8 | 0.05 | 0.379 | BLOCK |
| Emory model → Beth Israel | 0.8 | 0.1 | 0.429 | ADAPT |
| Emory model → Beth Israel | 0.85 | 0.0 | 0.399 | BLOCK |
| Emory model → Beth Israel | 0.85 | 0.05 | 0.449 | ADAPT |
| Emory model → Beth Israel | 0.85 | 0.1 | 0.499 | ADAPT |
| Beth Israel → Beth Israel (control) | 0.75 | 0.0 | 0.31 | ADAPT|BLOCK |
| Beth Israel → Beth Israel (control) | 0.75 | 0.05 | 0.36 | KEEP |
| Beth Israel → Beth Israel (control) | 0.75 | 0.1 | 0.41 | KEEP |
| Beth Israel → Beth Israel (control) | 0.8 | 0.0 | 0.401 | CALIBRATE |
| Beth Israel → Beth Israel (control) | 0.8 | 0.05 | 0.451 | KEEP |
| Beth Israel → Beth Israel (control) | 0.8 | 0.1 | 0.501 | KEEP |
| Beth Israel → Beth Israel (control) | 0.85 | 0.0 | 0.484 | KEEP |
| Beth Israel → Beth Israel (control) | 0.85 | 0.05 | 0.534 | KEEP |
| Beth Israel → Beth Israel (control) | 0.85 | 0.1 | 0.584 | KEEP |
| Emory → Emory (control) | 0.75 | 0.0 | 0.298 | CALIBRATE |
| Emory → Emory (control) | 0.75 | 0.05 | 0.348 | KEEP |
| Emory → Emory (control) | 0.75 | 0.1 | 0.398 | KEEP |
| Emory → Emory (control) | 0.8 | 0.0 | 0.329 | CALIBRATE |
| Emory → Emory (control) | 0.8 | 0.05 | 0.379 | KEEP |
| Emory → Emory (control) | 0.8 | 0.1 | 0.429 | KEEP |
| Emory → Emory (control) | 0.85 | 0.0 | 0.399 | CALIBRATE |
| Emory → Emory (control) | 0.85 | 0.05 | 0.449 | KEEP |
| Emory → Emory (control) | 0.85 | 0.1 | 0.499 | KEEP |
