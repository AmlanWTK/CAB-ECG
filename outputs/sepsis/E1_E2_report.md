# E1/E2 results

## Cohorts

```
                 patients  septic_pct  median_icu_hours  patient_hours  MICU_pct  SICU_pct  unit_unknown_pct  median_age
site                                                                                                                    
A (Beth Israel)     20336         8.8                39         790215      26.3      26.9              46.8   64.669998
B (Emory)           20000         5.7                38         761995      34.6      34.9              30.5   62.000000
```

## Results (test patients only)

```
   method trained_at evaluated_at              setting   threshold_rule  AUROC_hourly  AUPRC_hourly  utility  sensitivity_patient  median_lead_h  alarms_per_patient_day  alert_hours_pct
 LightGBM          A            A             internal 80% sens @ A val         0.810         0.112    0.395                0.771           12.0                   0.507           15.841
 LightGBM          A            B imported (zero-shot) 80% sens @ A val         0.777         0.060    0.270                0.632           11.5                   0.324            9.587
qSOFA_mod          A            A             internal 80% sens @ A val         0.575         0.026    0.028                0.905           11.0                   2.806           37.852
qSOFA_mod          A            B imported (zero-shot) 80% sens @ A val         0.559         0.017   -0.211                0.785            9.0                   2.347           31.583
 SIRS_mod          A            A             internal 80% sens @ A val         0.615         0.033    0.082                0.832           11.0                   1.709           34.384
 SIRS_mod          A            B imported (zero-shot) 80% sens @ A val         0.642         0.023   -0.046                0.807            8.0                   1.358           26.503
NEWS2_mod          A            A             internal 80% sens @ A val         0.643         0.036    0.105                0.872           11.0                   2.224           30.056
NEWS2_mod          A            B imported (zero-shot) 80% sens @ A val         0.670         0.028    0.020                0.789            8.0                   1.439           18.642
 MEWS_mod          A            A             internal 80% sens @ A val         0.608         0.033    0.012                0.950           12.0                   2.823           47.510
 MEWS_mod          A            B imported (zero-shot) 80% sens @ A val         0.603         0.024   -0.285                0.912           11.0                   2.492           43.543
 LightGBM          B            A imported (zero-shot) 80% sens @ B val         0.761         0.075    0.303                0.858           12.0                   0.922           28.018
 LightGBM          B            B             internal 80% sens @ B val         0.855         0.109    0.391                0.838            8.0                   0.422           12.119
qSOFA_mod          B            A imported (zero-shot) 80% sens @ B val         0.575         0.026    0.028                0.905           11.0                   2.806           37.852
qSOFA_mod          B            B             internal 80% sens @ B val         0.559         0.017   -0.211                0.785            9.0                   2.347           31.583
 SIRS_mod          B            A imported (zero-shot) 80% sens @ B val         0.615         0.033   -0.112                0.961           12.0                   1.760           70.263
 SIRS_mod          B            B             internal 80% sens @ B val         0.642         0.023   -0.462                0.974           12.0                   1.692           62.393
NEWS2_mod          B            A imported (zero-shot) 80% sens @ B val         0.643         0.036    0.064                0.939           12.0                   2.583           44.681
NEWS2_mod          B            B             internal 80% sens @ B val         0.670         0.028   -0.056                0.873           10.0                   1.913           29.375
 MEWS_mod          B            A imported (zero-shot) 80% sens @ B val         0.608         0.033    0.012                0.950           12.0                   2.823           47.510
 MEWS_mod          B            B             internal 80% sens @ B val         0.603         0.024   -0.285                0.912           11.0                   2.492           43.543
qSOFA_mod          -            A             internal    standard >= 2         0.575         0.026    0.018                0.265            6.0                   0.534            4.206
qSOFA_mod          -            B             internal    standard >= 2         0.559         0.017   -0.006                0.211            5.0                   0.379            2.816
 SIRS_mod          -            A             internal    standard >= 2         0.615         0.033    0.082                0.832           11.0                   1.709           34.384
 SIRS_mod          -            B             internal    standard >= 2         0.642         0.023   -0.046                0.807            8.0                   1.358           26.503
NEWS2_mod          -            A             internal    standard >= 5         0.643         0.036    0.105                0.872           11.0                   2.224           30.056
NEWS2_mod          -            B             internal    standard >= 5         0.670         0.028    0.020                0.789            8.0                   1.439           18.642
 MEWS_mod          -            A             internal    standard >= 4         0.608         0.033    0.080                0.500            6.0                   0.739            8.336
 MEWS_mod          -            B             internal    standard >= 4         0.603         0.024    0.048                0.469            5.0                   0.631            7.135
```

## Key comparison: imported vs local LightGBM

```
                         AUROC_hourly  utility  sensitivity_patient  alarms_per_patient_day
trained_at evaluated_at                                                                    
A          A                    0.810    0.395                0.771                   0.507
           B                    0.777    0.270                0.632                   0.324
B          A                    0.761    0.303                0.858                   0.922
           B                    0.855    0.391                0.838                   0.422
```
