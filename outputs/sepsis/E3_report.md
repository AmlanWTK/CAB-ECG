# E3: Calibrate, Adapt, or Block?

Each row: one source->target direction, one label budget n (patients labelled at the target),
one policy; averaged over repeated random label samples. Judged on the target's unlabelled patients.
unsafe = switched on something that fails sensitivity >= s* or false-alert <= f* on those patients.

## Oracle remedy for each criterion

```
direction  s_star  margin  f_star oracle_remedy  keep_sens  keep_fa  calibrate_fa_at_s_star  adapt_fa_at_s_star  local_model_fa_at_s_star
     A->B    0.75    0.00   0.261         ADAPT      0.569    0.195                   0.441               0.191                     0.208
     A->B    0.75    0.05   0.311         ADAPT      0.569    0.195                   0.441               0.191                     0.208
     A->B    0.75    0.10   0.361         ADAPT      0.569    0.195                   0.441               0.191                     0.208
     A->B    0.80    0.00   0.331         ADAPT      0.620    0.247                   0.531               0.247                     0.263
     A->B    0.80    0.05   0.381         ADAPT      0.620    0.247                   0.531               0.247                     0.263
     A->B    0.80    0.10   0.431         ADAPT      0.620    0.247                   0.531               0.247                     0.263
     A->B    0.85    0.00   0.418         ADAPT      0.687    0.331                   0.633               0.318                     0.340
     A->B    0.85    0.05   0.468         ADAPT      0.687    0.331                   0.633               0.318                     0.340
     A->B    0.85    0.10   0.518         ADAPT      0.687    0.331                   0.633               0.318                     0.340
     B->A    0.75    0.00   0.233         BLOCK      0.779    0.572                   0.537               0.338                     0.299
     B->A    0.75    0.05   0.283         BLOCK      0.779    0.572                   0.537               0.338                     0.299
     B->A    0.75    0.10   0.333         BLOCK      0.779    0.572                   0.537               0.338                     0.299
     B->A    0.80    0.00   0.298         BLOCK      0.862    0.674                   0.601               0.401                     0.371
     B->A    0.80    0.05   0.348         BLOCK      0.862    0.674                   0.601               0.401                     0.371
     B->A    0.80    0.10   0.398         BLOCK      0.862    0.674                   0.601               0.401                     0.371
     B->A    0.85    0.00   0.329         BLOCK      0.890    0.718                   0.656               0.452                     0.450
     B->A    0.85    0.05   0.379         BLOCK      0.890    0.718                   0.656               0.452                     0.450
     B->A    0.85    0.10   0.429         BLOCK      0.890    0.718                   0.656               0.452                     0.450
```

## Primary criterion, A->B (s* = 0.8, margin = 0.05)

```
 n_labelled      policy  reps  activated_rate  unsafe_rate  unsafe_upper95 correct_rate  sens_mean  false_alert_mean  utility_mean  alarms_per_day_mean
        250       AS-IS    30             1.0        1.000           1.000          NaN      0.620             0.247         0.275                0.310
        250         CAB    30             0.0        0.000           0.095          0.0        NaN               NaN         0.066                1.427
        250   FINE-TUNE    30             1.0        1.000           1.000          NaN      0.735             0.505         0.187                0.646
        250  LABEL-FREE    30             1.0        1.000           1.000          NaN      0.725             0.399         0.267                0.511
        250 RECALIBRATE    30             1.0        1.000           1.000          NaN      0.765             0.501         0.201                0.670
        250     RETRAIN    30             1.0        1.000           1.000          NaN      0.789             0.781        -0.247                0.812
        500       AS-IS    30             1.0        1.000           1.000          NaN      0.620             0.247         0.274                0.310
        500         CAB    30             0.0        0.000           0.095          0.0        NaN               NaN         0.066                1.427
        500   FINE-TUNE    30             1.0        1.000           1.000          NaN      0.760             0.508         0.221                0.654
        500  LABEL-FREE    30             1.0        1.000           1.000          NaN      0.725             0.399         0.267                0.511
        500 RECALIBRATE    30             1.0        1.000           1.000          NaN      0.800             0.557         0.188                0.750
        500     RETRAIN    30             1.0        1.000           1.000          NaN      0.767             0.698         0.023                0.797
       1000       AS-IS    30             1.0        1.000           1.000          NaN      0.620             0.247         0.274                0.311
       1000         CAB    30             0.0        0.000           0.095          0.0        NaN               NaN         0.066                1.427
       1000   FINE-TUNE    30             1.0        1.000           1.000          NaN      0.786             0.495         0.248                0.651
       1000  LABEL-FREE    30             1.0        1.000           1.000          NaN      0.725             0.399         0.266                0.512
       1000 RECALIBRATE    30             1.0        1.000           1.000          NaN      0.801             0.540         0.204                0.730
       1000     RETRAIN    30             1.0        1.000           1.000          NaN      0.800             0.651         0.134                0.820
       2000       AS-IS    30             1.0        1.000           1.000          NaN      0.620             0.247         0.274                0.311
       2000         CAB    30             0.0        0.000           0.095          0.0        NaN               NaN         0.067                1.426
       2000   FINE-TUNE    30             1.0        0.967           0.998          NaN      0.776             0.392         0.299                0.516
       2000  LABEL-FREE    30             1.0        1.000           1.000          NaN      0.725             0.398         0.267                0.511
       2000 RECALIBRATE    30             1.0        1.000           1.000          NaN      0.806             0.545         0.208                0.739
       2000     RETRAIN    30             1.0        1.000           1.000          NaN      0.788             0.478         0.198                0.582
       4000       AS-IS    30             1.0        1.000           1.000          NaN      0.621             0.248         0.274                0.311
       4000         CAB    30             0.0        0.000           0.095          0.0        NaN               NaN         0.066                1.429
       4000   FINE-TUNE    30             1.0        0.767           0.885          NaN      0.804             0.373         0.322                0.507
       4000  LABEL-FREE    30             1.0        1.000           1.000          NaN      0.727             0.399         0.268                0.513
       4000 RECALIBRATE    30             1.0        1.000           1.000          NaN      0.816             0.557         0.206                0.759
       4000     RETRAIN    30             1.0        0.867           0.953          NaN      0.802             0.385         0.306                0.509
       8000       AS-IS    30             1.0        1.000           1.000          NaN      0.621             0.248         0.272                0.312
       8000         CAB    30             0.1        0.000           0.095          0.1      0.822             0.356         0.090                1.332
       8000   FINE-TUNE    30             1.0        0.600           0.750          NaN      0.793             0.307         0.358                0.422
       8000  LABEL-FREE    30             1.0        1.000           1.000          NaN      0.727             0.398         0.266                0.512
       8000 RECALIBRATE    30             1.0        1.000           1.000          NaN      0.817             0.552         0.208                0.754
       8000     RETRAIN    30             1.0        0.667           0.807          NaN      0.794             0.327         0.344                0.432
```

CAB decisions (share of runs):

```
direction  s_star  margin  n_labelled  ADAPT  BLOCK
     A->B     0.8    0.05         250    0.0    1.0
     A->B     0.8    0.05         500    0.0    1.0
     A->B     0.8    0.05        1000    0.0    1.0
     A->B     0.8    0.05        2000    0.0    1.0
     A->B     0.8    0.05        4000    0.0    1.0
     A->B     0.8    0.05        8000    0.1    0.9
```

## Primary criterion, B->A (s* = 0.8, margin = 0.05)

```
 n_labelled      policy  reps  activated_rate  unsafe_rate  unsafe_upper95 correct_rate  sens_mean  false_alert_mean  utility_mean  alarms_per_day_mean
        250       AS-IS    30             1.0          1.0           1.000          NaN      0.862             0.674         0.320                0.937
        250         CAB    30             0.0          0.0           0.095          1.0        NaN               NaN         0.116                2.226
        250   FINE-TUNE    30             1.0          1.0           1.000          NaN      0.772             0.562         0.277                0.797
        250  LABEL-FREE    30             1.0          1.0           1.000          NaN      0.671             0.351         0.284                0.493
        250 RECALIBRATE    30             1.0          1.0           1.000          NaN      0.807             0.601         0.298                0.825
        250     RETRAIN    30             1.0          1.0           1.000          NaN      0.747             0.703         0.128                0.852
        500       AS-IS    30             1.0          1.0           1.000          NaN      0.862             0.674         0.319                0.937
        500         CAB    30             0.0          0.0           0.095          1.0        NaN               NaN         0.116                2.226
        500   FINE-TUNE    30             1.0          1.0           1.000          NaN      0.800             0.578         0.311                0.807
        500  LABEL-FREE    30             1.0          1.0           1.000          NaN      0.670             0.351         0.284                0.493
        500 RECALIBRATE    30             1.0          1.0           1.000          NaN      0.799             0.585         0.313                0.806
        500     RETRAIN    30             1.0          1.0           1.000          NaN      0.772             0.710         0.215                0.830
       1000       AS-IS    30             1.0          1.0           1.000          NaN      0.862             0.674         0.320                0.937
       1000         CAB    30             0.0          0.0           0.095          1.0        NaN               NaN         0.116                2.227
       1000   FINE-TUNE    30             1.0          1.0           1.000          NaN      0.799             0.561         0.326                0.792
       1000  LABEL-FREE    30             1.0          1.0           1.000          NaN      0.671             0.351         0.285                0.493
       1000 RECALIBRATE    30             1.0          1.0           1.000          NaN      0.809             0.606         0.320                0.834
       1000     RETRAIN    30             1.0          1.0           1.000          NaN      0.779             0.630         0.271                0.820
       2000       AS-IS    30             1.0          1.0           1.000          NaN      0.861             0.674         0.320                0.937
       2000         CAB    30             0.0          0.0           0.095          1.0        NaN               NaN         0.117                2.226
       2000   FINE-TUNE    30             1.0          1.0           1.000          NaN      0.794             0.523         0.337                0.748
       2000  LABEL-FREE    30             1.0          1.0           1.000          NaN      0.670             0.350         0.284                0.493
       2000 RECALIBRATE    30             1.0          1.0           1.000          NaN      0.795             0.594         0.318                0.813
       2000     RETRAIN    30             1.0          1.0           1.000          NaN      0.787             0.552         0.328                0.719
       4000       AS-IS    30             1.0          1.0           1.000          NaN      0.860             0.674         0.316                0.936
       4000         CAB    30             0.0          0.0           0.095          1.0        NaN               NaN         0.114                2.225
       4000   FINE-TUNE    30             1.0          1.0           1.000          NaN      0.783             0.460         0.351                0.665
       4000  LABEL-FREE    30             1.0          1.0           1.000          NaN      0.668             0.351         0.282                0.492
       4000 RECALIBRATE    30             1.0          1.0           1.000          NaN      0.788             0.587         0.315                0.803
       4000     RETRAIN    30             1.0          1.0           1.000          NaN      0.784             0.471         0.360                0.640
       8000       AS-IS    30             1.0          1.0           1.000          NaN      0.862             0.674         0.317                0.935
       8000         CAB    30             0.0          0.0           0.095          1.0        NaN               NaN         0.113                2.226
       8000   FINE-TUNE    30             1.0          1.0           1.000          NaN      0.798             0.420         0.376                0.629
       8000  LABEL-FREE    30             1.0          1.0           1.000          NaN      0.671             0.351         0.285                0.492
       8000 RECALIBRATE    30             1.0          1.0           1.000          NaN      0.802             0.602         0.318                0.825
       8000     RETRAIN    30             1.0          1.0           1.000          NaN      0.799             0.415         0.390                0.578
```

CAB decisions (share of runs):

```
direction  s_star  margin  n_labelled  ADAPT  BLOCK
     B->A     0.8    0.05         250    0.0    1.0
     B->A     0.8    0.05         500    0.0    1.0
     B->A     0.8    0.05        1000    0.0    1.0
     B->A     0.8    0.05        2000    0.0    1.0
     B->A     0.8    0.05        4000    0.0    1.0
     B->A     0.8    0.05        8000    0.0    1.0
```

## Labels needed by CAB (P(correct remedy) >= 0.9 and P(unsafe) <= 0.05)

```
direction  s_star  margin oracle labels_needed
     A->B    0.75    0.00  ADAPT  > max budget
     A->B    0.75    0.05  ADAPT  > max budget
     A->B    0.75    0.10  ADAPT  > max budget
     A->B    0.80    0.00  ADAPT  > max budget
     A->B    0.80    0.05  ADAPT  > max budget
     A->B    0.80    0.10  ADAPT  > max budget
     A->B    0.85    0.00  ADAPT  > max budget
     A->B    0.85    0.05  ADAPT  > max budget
     A->B    0.85    0.10  ADAPT  > max budget
     B->A    0.75    0.00  BLOCK           250
     B->A    0.75    0.05  BLOCK           250
     B->A    0.75    0.10  BLOCK           250
     B->A    0.80    0.00  BLOCK           250
     B->A    0.80    0.05  BLOCK           250
     B->A    0.80    0.10  BLOCK           250
     B->A    0.85    0.00  BLOCK           250
     B->A    0.85    0.05  BLOCK           250
     B->A    0.85    0.10  BLOCK           250
```

## Unsafe activation across ALL criteria, budgets and directions

```
     policy  max_unsafe_rate  mean_unsafe_rate
      AS-IS            1.000             1.000
        CAB            0.067             0.002
  FINE-TUNE            1.000             0.947
 LABEL-FREE            1.000             1.000
RECALIBRATE            1.000             1.000
    RETRAIN            1.000             0.959
```
