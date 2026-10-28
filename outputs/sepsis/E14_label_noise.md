# E14: imperfect sepsis labels (primary criterion)

noise: share of labelled septic patients recorded as non-septic in the data CAB sees. Safety is judged with the true labels on the unlabelled patients. 20 repeats per cell, same samples as E3mac100.

```
direction      policy  noise  runs  switched_on  unsafe  sens  false_alert
     A->B         CAB   0.00    20         1.00    0.05 0.850        0.388
     A->B         CAB   0.05    20         0.90    0.00 0.844        0.384
     A->B         CAB   0.10    20         0.95    0.05 0.847        0.389
     A->B         CAB   0.20    20         0.65    0.05 0.834        0.380
     A->B RECALIBRATE   0.00    20         1.00    1.00 0.824        0.552
     A->B RECALIBRATE   0.05    20         1.00    1.00 0.823        0.552
     A->B RECALIBRATE   0.10    20         1.00    1.00 0.822        0.550
     A->B RECALIBRATE   0.20    20         1.00    1.00 0.822        0.550
     B->A         CAB   0.00    20         0.00    0.00   NaN          NaN
     B->A         CAB   0.05    20         0.00    0.00   NaN          NaN
     B->A         CAB   0.10    20         0.00    0.00   NaN          NaN
     B->A         CAB   0.20    20         0.00    0.00   NaN          NaN
     B->A RECALIBRATE   0.00    20         1.00    1.00 0.787        0.587
     B->A RECALIBRATE   0.05    20         1.00    1.00 0.786        0.586
     B->A RECALIBRATE   0.10    20         1.00    1.00 0.788        0.587
     B->A RECALIBRATE   0.20    20         1.00    1.00 0.787        0.587
```

CAB decisions:

```
remedy           ADAPT  BLOCK
direction noise              
A->B      0.00    1.00   0.00
          0.05    0.90   0.10
          0.10    0.95   0.05
          0.20    0.65   0.35
B->A      0.00    0.00   1.00
          0.05    0.00   1.00
          0.10    0.00   1.00
          0.20    0.00   1.00
```
