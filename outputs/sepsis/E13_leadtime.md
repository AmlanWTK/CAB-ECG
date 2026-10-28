# E13: lead time before sepsis onset (A->B, 12,000 labels, primary criterion)

Lead time = onset hour - first alert within onset -12 h to +3 h, among detected septic patients (median and quartiles, averaged over runs). share_6h_early: share of ALL septic patients alerted at least 6 h before onset. CAB rows: runs where CAB switched something on. References are on the target's test patients.

```
                 policy  runs  detected  lead_median  lead_q1  lead_q3  share_6h_early
Local model (reference)     1     0.803        7.000    5.000     12.0           0.579
 NEWS2 >= 5 (reference)     1     0.789        8.000    3.750     12.0           0.487
                  AS-IS    20     0.680       11.925    3.712     12.0           0.440
            RECALIBRATE    20     0.824       11.400    5.050     12.0           0.587
              FINE-TUNE    20     0.800        9.675    5.175     12.0           0.579
                    CAB    20     0.850       10.700    5.650     12.0           0.644
```
