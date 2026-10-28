# E15window6: Calibrate, Adapt, or Block?

Each row: one direction, one label budget n (patients labelled at the target), one policy,
averaged over repeated random label samples; judged on the target's unlabelled eligible patients.
unsafe = switched on something that fails sensitivity >= s* or false-alert <= f* on those patients.
silent failure = unsafe although its own data said it met both criteria.

## Oracle remedy for each criterion

```
direction  s_star  margin  vendor_threshold  home_sens  home_fa  f_star oracle_remedy  keep_sens  keep_fa  calibrate_fa_at_s_star  adapt_fa_at_s_star  local_model_fa_at_s_star
     A->B    0.75    0.00             0.029      0.791    0.333   0.333         ADAPT      0.609    0.249                   0.481               0.195                     0.209
     A->B    0.75    0.05             0.029      0.791    0.333   0.383         ADAPT      0.609    0.249                   0.481               0.195                     0.209
     A->B    0.75    0.10             0.029      0.791    0.333   0.433         ADAPT      0.609    0.249                   0.481               0.195                     0.209
     A->B    0.80    0.00             0.021      0.838    0.446   0.446         ADAPT      0.682    0.360                   0.579               0.255                     0.284
     A->B    0.80    0.05             0.021      0.838    0.446   0.496         ADAPT      0.682    0.360                   0.579               0.255                     0.284
     A->B    0.80    0.10             0.021      0.838    0.446   0.546         ADAPT      0.682    0.360                   0.579               0.255                     0.284
     A->B    0.85    0.00             0.017      0.883    0.551   0.551         ADAPT      0.732    0.445                   0.669               0.339                     0.347
     A->B    0.85    0.05             0.017      0.883    0.551   0.601         ADAPT      0.732    0.445                   0.669               0.339                     0.347
     A->B    0.85    0.10             0.017      0.883    0.551   0.651         ADAPT      0.732    0.445                   0.669               0.339                     0.347
     B->A    0.75    0.00             0.021      0.799    0.303   0.303         BLOCK      0.841    0.685                   0.568               0.380                     0.346
     B->A    0.75    0.05             0.021      0.799    0.303   0.353         BLOCK      0.841    0.685                   0.568               0.380                     0.346
     B->A    0.75    0.10             0.021      0.799    0.303   0.403         ADAPT      0.841    0.685                   0.568               0.380                     0.346
     B->A    0.80    0.00             0.018      0.847    0.331   0.331         BLOCK      0.866    0.722                   0.633               0.426                     0.402
     B->A    0.80    0.05             0.018      0.847    0.331   0.381         BLOCK      0.866    0.722                   0.633               0.426                     0.402
     B->A    0.80    0.10             0.018      0.847    0.331   0.431         ADAPT      0.866    0.722                   0.633               0.426                     0.402
     B->A    0.85    0.00             0.012      0.891    0.438   0.438         BLOCK      0.930    0.829                   0.694               0.484                     0.494
     B->A    0.85    0.05             0.012      0.891    0.438   0.488         ADAPT      0.930    0.829                   0.694               0.484                     0.494
     B->A    0.85    0.10             0.012      0.891    0.438   0.538         ADAPT      0.930    0.829                   0.694               0.484                     0.494
```

## Primary criterion, A->B (s* = 0.8, margin = 0.05)

```
 n_labelled  septic_labelled      policy  reps  activated_rate  unsafe_rate  unsafe_upper95  silent_failure_rate correct_rate  sens_mean  false_alert_mean  utility_mean  alarms_per_day_mean
       1000           57.533       AS-IS    30           1.000        1.000           1.000                1.000          NaN      0.682             0.360         0.310                0.457
       1000           57.533         CAB    30           0.033        0.000           0.095                0.000     0.033333      0.801             0.398         0.085                1.398
       1000           57.533  CERT-RECAL    30           0.000        0.000           0.095                0.000          0.0        NaN               NaN         0.075                1.427
       1000           57.533 CLOSED-TEST    30           1.000        1.000           1.000                0.233     0.066667      0.795             0.564         0.219                0.764
       1000           57.533   FINE-TUNE    30           1.000        0.900           0.972                0.467          NaN      0.779             0.518         0.276                0.688
       1000           57.533  LABEL-FREE    30           1.000        1.000           1.000                0.000          NaN      0.781             0.541         0.244                0.736
       1000           57.533 RECALIBRATE    30           1.000        1.000           1.000                0.200          NaN      0.797             0.573         0.214                0.777
       1000           57.533     RETRAIN    30           1.000        1.000           1.000                0.133          NaN      0.792             0.702         0.132                0.894
       4000          227.067       AS-IS    30           1.000        1.000           1.000                1.000          NaN      0.685             0.360         0.311                0.458
       4000          227.067         CAB    30           0.100        0.033           0.149                0.033          0.1      0.817             0.426         0.103                1.345
       4000          227.067  CERT-RECAL    30           0.000        0.000           0.095                0.000          0.0        NaN               NaN         0.075                1.429
       4000          227.067 CLOSED-TEST    30           1.000        0.867           0.953                0.200     0.266667      0.809             0.543         0.251                0.738
       4000          227.067   FINE-TUNE    30           1.000        0.467           0.630                0.367          NaN      0.809             0.405         0.366                0.547
       4000          227.067  LABEL-FREE    30           1.000        1.000           1.000                0.000          NaN      0.786             0.542         0.246                0.736
       4000          227.067 RECALIBRATE    30           1.000        1.000           1.000                0.067          NaN      0.815             0.600         0.207                0.820
       4000          227.067     RETRAIN    30           1.000        0.700           0.834                0.533          NaN      0.800             0.412         0.341                0.546
      12000          679.500       AS-IS    30           1.000        1.000           1.000                1.000          NaN      0.693             0.361         0.314                0.460
      12000          679.500         CAB    30           1.000        0.033           0.149                0.033          1.0      0.852             0.423         0.406                0.575
      12000          679.500  CERT-RECAL    30           0.000        0.000           0.095                0.000          0.0        NaN               NaN         0.060                1.434
      12000          679.500 CLOSED-TEST    30           1.000        0.567           0.721                0.500     0.933333      0.803             0.346         0.410                0.478
      12000          679.500   FINE-TUNE    30           1.000        0.500           0.661                0.500          NaN      0.802             0.330         0.425                0.456
      12000          679.500  LABEL-FREE    30           1.000        1.000           1.000                0.000          NaN      0.799             0.542         0.246                0.740
      12000          679.500 RECALIBRATE    30           1.000        1.000           1.000                0.000          NaN      0.826             0.600         0.213                0.826
      12000          679.500     RETRAIN    30           1.000        0.367           0.533                0.367          NaN      0.805             0.333         0.426                0.452
```

CAB decisions (share of runs):

```
direction  s_star  margin  n_labelled  ADAPT  BLOCK
     A->B     0.8    0.05        1000  0.033  0.967
     A->B     0.8    0.05        4000  0.100  0.900
     A->B     0.8    0.05       12000  1.000  0.000
```

## Primary criterion, B->A (s* = 0.8, margin = 0.05)

```
 n_labelled  septic_labelled      policy  reps  activated_rate  unsafe_rate  unsafe_upper95  silent_failure_rate correct_rate  sens_mean  false_alert_mean  utility_mean  alarms_per_day_mean
       1000           88.567       AS-IS    30             1.0          1.0           1.000                1.000          NaN      0.866             0.722         0.357                1.002
       1000           88.567         CAB    30             0.0          0.0           0.095                0.000          1.0        NaN               NaN         0.133                2.227
       1000           88.567  CERT-RECAL    30             0.0          0.0           0.095                0.000          1.0        NaN               NaN         0.133                2.227
       1000           88.567 CLOSED-TEST    30             1.0          1.0           1.000                0.000          0.0      0.804             0.629         0.371                0.871
       1000           88.567   FINE-TUNE    30             1.0          1.0           1.000                0.033          NaN      0.788             0.589         0.381                0.829
       1000           88.567  LABEL-FREE    30             1.0          1.0           1.000                0.000          NaN      0.687             0.396         0.351                0.558
       1000           88.567 RECALIBRATE    30             1.0          1.0           1.000                0.000          NaN      0.806             0.637         0.369                0.882
       1000           88.567     RETRAIN    30             1.0          1.0           1.000                0.067          NaN      0.776             0.687         0.283                0.905
       4000          357.567       AS-IS    30             1.0          1.0           1.000                1.000          NaN      0.864             0.722         0.352                1.001
       4000          357.567         CAB    30             0.0          0.0           0.095                0.000          1.0        NaN               NaN         0.131                2.225
       4000          357.567  CERT-RECAL    30             0.0          0.0           0.095                0.000          1.0        NaN               NaN         0.131                2.225
       4000          357.567 CLOSED-TEST    30             1.0          1.0           1.000                0.033          0.0      0.779             0.584         0.375                0.812
       4000          357.567   FINE-TUNE    30             1.0          1.0           1.000                0.067          NaN      0.776             0.491         0.413                0.711
       4000          357.567  LABEL-FREE    30             1.0          1.0           1.000                0.000          NaN      0.682             0.396         0.348                0.557
       4000          357.567 RECALIBRATE    30             1.0          1.0           1.000                0.000          NaN      0.783             0.614         0.365                0.846
       4000          357.567     RETRAIN    30             1.0          1.0           1.000                0.000          NaN      0.780             0.514         0.413                0.703
      12000         1052.933       AS-IS    30             1.0          1.0           1.000                1.000          NaN      0.867             0.718         0.354                0.996
      12000         1052.933         CAB    30             0.0          0.0           0.095                0.000          1.0        NaN               NaN         0.136                2.221
      12000         1052.933  CERT-RECAL    30             0.0          0.0           0.095                0.000          1.0        NaN               NaN         0.136                2.221
      12000         1052.933 CLOSED-TEST    30             1.0          1.0           1.000                0.000          0.0      0.787             0.443         0.443                0.661
      12000         1052.933   FINE-TUNE    30             1.0          1.0           1.000                0.000          NaN      0.786             0.429         0.449                0.646
      12000         1052.933  LABEL-FREE    30             1.0          1.0           1.000                0.000          NaN      0.676             0.394         0.350                0.555
      12000         1052.933 RECALIBRATE    30             1.0          1.0           1.000                0.000          NaN      0.794             0.628         0.370                0.865
      12000         1052.933     RETRAIN    30             1.0          1.0           1.000                0.033          NaN      0.788             0.422         0.461                0.604
```

CAB decisions (share of runs):

```
direction  s_star  margin  n_labelled  ADAPT  BLOCK
     B->A     0.8    0.05        1000    0.0    1.0
     B->A     0.8    0.05        4000    0.0    1.0
     B->A     0.8    0.05       12000    0.0    1.0
```

## CAB: share of runs choosing the oracle remedy, all criteria

```
n_labelled                  1000      4000      12000
direction s_star margin                              
A->B      0.75   0.00    0.033333       0.0  0.366667
                 0.05    0.066667  0.033333  0.866667
                 0.10    0.066667  0.133333  0.966667
          0.80   0.00         0.0  0.066667  0.566667
                 0.05    0.033333       0.1       1.0
                 0.10    0.033333  0.266667       1.0
          0.85   0.00         0.0       0.0       0.7
                 0.05    0.033333  0.066667  0.966667
                 0.10    0.033333  0.166667       1.0
B->A      0.75   0.00         1.0       1.0       1.0
                 0.05         1.0       1.0       1.0
                 0.10         0.0       0.0       0.1
          0.80   0.00         1.0       1.0       1.0
                 0.05         1.0       1.0       1.0
                 0.10         0.0       0.0       0.0
          0.85   0.00         1.0       1.0       1.0
                 0.05         0.0       0.0       0.0
                 0.10         0.0       0.0       0.0
```

## Labels needed by CAB (P(correct remedy) >= 0.9 and P(unsafe) <= 0.05)

```
direction  s_star  margin oracle labels_needed
     A->B    0.75    0.00  ADAPT  > max budget
     A->B    0.75    0.05  ADAPT  > max budget
     A->B    0.75    0.10  ADAPT         12000
     A->B    0.80    0.00  ADAPT  > max budget
     A->B    0.80    0.05  ADAPT         12000
     A->B    0.80    0.10  ADAPT         12000
     A->B    0.85    0.00  ADAPT  > max budget
     A->B    0.85    0.05  ADAPT         12000
     A->B    0.85    0.10  ADAPT         12000
     B->A    0.75    0.00  BLOCK          1000
     B->A    0.75    0.05  BLOCK          1000
     B->A    0.75    0.10  ADAPT  > max budget
     B->A    0.80    0.00  BLOCK          1000
     B->A    0.80    0.05  BLOCK          1000
     B->A    0.80    0.10  ADAPT  > max budget
     B->A    0.85    0.00  BLOCK          1000
     B->A    0.85    0.05  ADAPT  > max budget
     B->A    0.85    0.10  ADAPT  > max budget
```

## Unsafe activation across ALL criteria, budgets and directions

```
     policy  max_unsafe_rate  mean_unsafe_rate  mean_silent_failure_rate
      AS-IS            1.000             1.000                     1.000
        CAB            0.033             0.009                     0.009
 CERT-RECAL            0.000             0.000                     0.000
CLOSED-TEST            1.000             0.893                     0.194
  FINE-TUNE            1.000             0.814                     0.288
 LABEL-FREE            1.000             0.985                     0.000
RECALIBRATE            1.000             1.000                     0.049
    RETRAIN            1.000             0.840                     0.240
```

ADAPT model chosen when CAB switched on ADAPT:

```
adapt_variant
refit+boost    0.692
boost          0.308
```
