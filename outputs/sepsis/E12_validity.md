# E12: measured unsafe rates against the nominal alpha

One setting = direction x labelled patients x s* x margin, repeated `reps` times. above_alpha: settings whose measured rate exceeds alpha. expected_above_if_at_alpha: how many would, by chance, if every setting's true rate were exactly alpha (the worst case the guarantee allows). exceeds: settings whose exact 95% interval lies wholly above alpha. pooled: all runs of the group together, with its 95% interval.

## By group

```
       tag  alpha     policy          group  settings  reps  mean_rate  max_rate  above_alpha  expected_above_if_at_alpha  exceeds  pooled_rate  pooled_lo  pooled_hi  min_judging_septic
  E3mac100   0.05        CAB cross-hospital       126   100     0.0051      0.06            1                     48.3841        0       0.0051     0.0039     0.0065              459.10
  E3mac100   0.05        CAB           home        72   100     0.0097      0.07            3                     27.6481        0       0.0097     0.0076     0.0123              112.31
  E3mac100   0.05 CERT-RECAL cross-hospital       126   100     0.0000      0.00            0                     48.3841        0       0.0000     0.0000     0.0003              459.10
  E3mac100   0.05 CERT-RECAL           home        72   100     0.0065      0.06            1                     27.6481        0       0.0065     0.0048     0.0087              112.31
   E6units   0.05        CAB       ICU unit       162   100     0.0028      0.05            0                     62.2081        0       0.0028     0.0021     0.0038              135.59
   E6units   0.05 CERT-RECAL       ICU unit       162   100     0.0000      0.00            0                     62.2081        0       0.0000     0.0000     0.0002              135.59
E12alpha01   0.01        CAB cross-hospital       126   100     0.0011      0.02            4                     33.2940        0       0.0011     0.0006     0.0019              459.10
E12alpha01   0.01        CAB           home        72   100     0.0014      0.02            3                     19.0251        0       0.0014     0.0007     0.0026              112.31
E12alpha01   0.01 CERT-RECAL cross-hospital       126   100     0.0000      0.00            0                     33.2940        0       0.0000     0.0000     0.0003              459.10
E12alpha01   0.01 CERT-RECAL           home        72   100     0.0008      0.01            0                     19.0251        0       0.0008     0.0003     0.0018              112.31
E12alpha10   0.10        CAB cross-hospital       126   100     0.0091      0.13            1                     52.5224        0       0.0091     0.0075     0.0109              459.10
E12alpha10   0.10        CAB           home        72   100     0.0206      0.12            1                     30.0128        0       0.0206     0.0174     0.0241              112.31
E12alpha10   0.10 CERT-RECAL cross-hospital       126   100     0.0001      0.01            0                     52.5224        0       0.0001     0.0000     0.0004              459.10
E12alpha10   0.10 CERT-RECAL           home        72   100     0.0150      0.10            0                     30.0128        0       0.0150     0.0123     0.0181              112.31
```

## E3mac100: the ten CAB settings with the highest measured rate

```
direction  n_labelled  s_star  margin  unsafe  reps  rate  ci_lo  ci_hi  exceeds  judging_septic
     B->B        2000    0.75    0.00       7   100  0.07  0.029  0.139    False          112.31
     B->B        2000    0.80    0.00       6   100  0.06  0.022  0.126    False          112.31
     A->A        2000    0.80    0.10       6   100  0.06  0.022  0.126    False          181.17
     B->A       12000    0.75    0.10       6   100  0.06  0.022  0.126    False          732.13
     A->A        1000    0.85    0.10       5   100  0.05  0.016  0.113    False          269.13
     B->A       12000    0.80    0.10       5   100  0.05  0.016  0.113    False          732.13
     A->A        2000    0.85    0.05       4   100  0.04  0.011  0.099    False          181.17
     A->B       12000    0.85    0.00       4   100  0.04  0.011  0.099    False          459.10
     A->A        2000    0.80    0.05       4   100  0.04  0.011  0.099    False          181.17
     A->A        1000    0.85    0.05       4   100  0.04  0.011  0.099    False          269.13
```

## E6units: the ten CAB settings with the highest measured rate

```
direction  n_labelled  s_star  margin  unsafe  reps  rate  ci_lo  ci_hi  exceeds  judging_septic
A->B:SICU        4000    0.75    0.05       5   100  0.05  0.016  0.113    False          179.41
A->B:SICU        4000    0.75    0.10       5   100  0.05  0.016  0.113    False          179.41
A->B:SICU        4000    0.80    0.05       4   100  0.04  0.011  0.099    False          179.41
A->B:SICU        4000    0.80    0.00       4   100  0.04  0.011  0.099    False          179.41
A->B:SICU        4000    0.80    0.10       4   100  0.04  0.011  0.099    False          179.41
A->B:SICU        2000    0.75    0.10       1   100  0.01  0.000  0.054    False          300.89
A->B:SICU        2000    0.75    0.05       1   100  0.01  0.000  0.054    False          300.89
A->B:SICU        1000    0.75    0.10       1   100  0.01  0.000  0.054    False          365.44
A->B:MICU        1000    0.85    0.10       1   100  0.01  0.000  0.054    False          331.75
A->B:MICU        2000    0.75    0.05       1   100  0.01  0.000  0.054    False          272.20
```

## E12alpha01: the ten CAB settings with the highest measured rate

```
direction  n_labelled  s_star  margin  unsafe  reps  rate  ci_lo  ci_hi  exceeds  judging_septic
     A->B       12000    0.85    0.05       2   100  0.02  0.002  0.070    False          459.10
     A->A        1000    0.80    0.10       2   100  0.02  0.002  0.070    False          269.13
     B->A       12000    0.75    0.10       2   100  0.02  0.002  0.070    False          732.13
     A->A        2000    0.80    0.10       2   100  0.02  0.002  0.070    False          181.17
     A->B       12000    0.85    0.00       2   100  0.02  0.002  0.070    False          459.10
     A->A        2000    0.75    0.10       2   100  0.02  0.002  0.070    False          181.17
     A->B       12000    0.85    0.10       2   100  0.02  0.002  0.070    False          459.10
     A->B        8000    0.75    0.10       1   100  0.01  0.000  0.054    False          684.46
     A->B       12000    0.80    0.00       1   100  0.01  0.000  0.054    False          459.10
     A->B       12000    0.80    0.05       1   100  0.01  0.000  0.054    False          459.10
```

## E12alpha10: the ten CAB settings with the highest measured rate

```
direction  n_labelled  s_star  margin  unsafe  reps  rate  ci_lo  ci_hi  exceeds  judging_septic
     B->A       12000    0.75    0.10      13   100  0.13  0.071  0.212    False          732.13
     B->B        2000    0.75    0.00      12   100  0.12  0.064  0.200    False          112.31
     A->A        2000    0.80    0.10      10   100  0.10  0.049  0.176    False          181.17
     B->B        2000    0.80    0.00      10   100  0.10  0.049  0.176    False          112.31
     A->A        2000    0.85    0.05       8   100  0.08  0.035  0.152    False          181.17
     A->A        2000    0.80    0.05       8   100  0.08  0.035  0.152    False          181.17
     A->A        2000    0.75    0.10       7   100  0.07  0.029  0.139    False          181.17
     B->A       12000    0.80    0.10       7   100  0.07  0.029  0.139    False          732.13
     A->A        1000    0.80    0.05       7   100  0.07  0.029  0.139    False          269.13
     A->A        1000    0.80    0.10       6   100  0.06  0.022  0.126    False          269.13
```

## Alpha sensitivity, CAB, primary criterion (s* = 0.8, margin = 0.05)

Unsafe rate:

```
n_labelled       250    500    1000   2000   4000   8000   12000
direction alpha                                                 
A->A      0.01     0.0   0.00   0.01   0.01    NaN    NaN    NaN
          0.05     0.0   0.00   0.03   0.04    NaN    NaN    NaN
          0.10     0.0   0.00   0.07   0.08    NaN    NaN    NaN
A->B      0.01     0.0   0.00   0.00   0.00   0.00   0.00   0.01
          0.05     0.0   0.00   0.00   0.01   0.01   0.03   0.02
          0.10     0.0   0.00   0.01   0.01   0.01   0.03   0.04
B->A      0.01     0.0   0.00   0.00   0.00   0.00   0.00   0.00
          0.05     0.0   0.00   0.00   0.00   0.00   0.00   0.00
          0.10     0.0   0.00   0.00   0.00   0.00   0.00   0.00
B->B      0.01     0.0   0.00   0.00   0.01    NaN    NaN    NaN
          0.05     0.0   0.00   0.02   0.02    NaN    NaN    NaN
          0.10     0.0   0.01   0.02   0.03    NaN    NaN    NaN
```

Share of runs switched on:

```
n_labelled       250    500    1000   2000   4000   8000   12000
direction alpha                                                 
A->A      0.01    0.00   0.00   0.01   0.01    NaN    NaN    NaN
          0.05    0.00   0.00   0.03   0.05    NaN    NaN    NaN
          0.10    0.01   0.00   0.09   0.09    NaN    NaN    NaN
A->B      0.01    0.00   0.00   0.00   0.00   0.01   0.35   0.82
          0.05    0.00   0.00   0.01   0.02   0.10   0.70   0.97
          0.10    0.00   0.00   0.02   0.03   0.16   0.81   0.98
B->A      0.01    0.00   0.00   0.00   0.00   0.00   0.00   0.00
          0.05    0.00   0.00   0.00   0.00   0.00   0.00   0.00
          0.10    0.00   0.00   0.00   0.00   0.00   0.00   0.00
B->B      0.01    0.00   0.00   0.00   0.03    NaN    NaN    NaN
          0.05    0.00   0.02   0.05   0.25    NaN    NaN    NaN
          0.10    0.01   0.04   0.16   0.45    NaN    NaN    NaN
```
