# E5: labels needed for certified deployment

## Part A: labels needed for certification (exact tests, alpha = 0.05)

Each test at level alpha/4 = 0.0125, power sqrt(0.9) so that both pass with probability >= 0.9. gap = how far the model's true rate is on the safe side of the target.

### Septic patients needed (sensitivity test); columns = target s*

```
target  0.75  0.80  0.85
gap                     
0.020   6850  5792  4533
0.030   3010  2526  1964
0.050   1055   873   657
0.075    452   367   268
0.100    241   193   136
```

### Non-septic patients needed (false-alert test); columns = target f*

```
target   0.3   0.4   0.5
gap                     
0.020   7749  8933  9405
0.030   3404  3951  4172
0.050   1203  1409  1500
0.075    519   622   665
0.100    286   345   377
```

### Total patients, random labelling, KEEP/CALIBRATE (same gap on both rates); columns = septic prevalence

```
target   0.030   0.057  0.088  0.150
gap                                 
0.020   193067  101615  65819  38614
0.030    84200   44316  28705  16840
0.050    29100   15316   9921   5820
0.075    12234    6439   4171   2447
0.100     6434    3386   2194   1287
```

### Total patients, random labelling, ADAPT (half fit, half certify); columns = prevalence

```
target   0.030   0.057   0.088  0.150
gap                                  
0.020   386134  203229  131637  77227
0.030   168400   88632   57410  33680
0.050    58200   30632   19841  11640
0.075    24467   12878    8341   4894
0.100    12867    6772    4387   2574
```
