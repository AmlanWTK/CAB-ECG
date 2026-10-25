# E2: imported vs local model at each hospital (paired, 95% bootstrap CI)

Test patients of the target hospital only. Each model uses its home threshold (80% patient sensitivity on its own hospital's validation set).

```
target imported_from                 metric  local       local_CI  imported    imported_CI  difference    difference_CI  relative_change_pct
     B             A           AUROC_hourly  0.855 [0.834, 0.874]     0.777 [0.748, 0.799]      -0.078 [-0.102, -0.057]               -9.146
     B             A                utility  0.391 [0.334, 0.442]     0.270 [0.212, 0.325]      -0.120 [-0.169, -0.072]              -30.834
     B             A    sensitivity_patient  0.838 [0.791, 0.882]     0.632 [0.572, 0.693]      -0.206 [-0.268, -0.143]              -24.607
     B             A   false_alert_patients  0.303 [0.289, 0.317]     0.250 [0.237, 0.264]      -0.053 [-0.070, -0.036]              -17.410
     B             A alarms_per_patient_day  0.422 [0.400, 0.444]     0.324 [0.305, 0.342]      -0.098 [-0.122, -0.073]              -23.230
     A             B           AUROC_hourly  0.810 [0.784, 0.826]     0.761 [0.735, 0.778]      -0.049 [-0.064, -0.032]               -6.009
     A             B                utility  0.395 [0.351, 0.436]     0.303 [0.254, 0.351]      -0.092 [-0.131, -0.051]              -23.241
     A             B    sensitivity_patient  0.771 [0.727, 0.812]     0.858 [0.821, 0.892]       0.087   [0.039, 0.134]               11.232
     A             B   false_alert_patients  0.339 [0.323, 0.354]     0.669 [0.654, 0.685]       0.330   [0.312, 0.348]               97.611
     A             B alarms_per_patient_day  0.507 [0.484, 0.532]     0.922 [0.896, 0.952]       0.415   [0.386, 0.445]               81.821
```

## Calibration at the target (hourly)

```
target           model  observed_rate  mean_predicted  O_E_ratio  calibration_slope
     B imported from A         0.0143          0.0156     0.9128             0.7118
     B           local         0.0143          0.0134     1.0608             1.0106
     A imported from B         0.0215          0.0257     0.8374             0.7343
     A           local         0.0215          0.0227     0.9489             0.8093
```
