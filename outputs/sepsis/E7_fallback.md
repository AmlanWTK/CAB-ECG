# E7_fallback: can a bedside score replace a blocked model?

Each row: the bedside score and cut-off that reaches the sensitivity target with the
fewest false alerts on the target's eligible patients (large-sample check, no labels).
Criteria where some bedside score meets both targets: 0 of 72.

```
direction  s_star  margin  f_star oracle_remedy  any_score_meets_both best_score  best_cutoff  best_sens  best_false_alert  excess_false_alert
     A->B    0.75    0.00   0.310         ADAPT                 False  NEWS2_mod            5      0.784             0.597               0.287
     A->B    0.75    0.05   0.360         ADAPT                 False  NEWS2_mod            5      0.784             0.597               0.237
     A->B    0.75    0.10   0.410         ADAPT                 False  NEWS2_mod            5      0.784             0.597               0.187
     A->B    0.80    0.00   0.401         ADAPT                 False   SIRS_mod            2      0.813             0.670               0.269
     A->B    0.80    0.05   0.451         ADAPT                 False   SIRS_mod            2      0.813             0.670               0.219
     A->B    0.80    0.10   0.501         ADAPT                 False   SIRS_mod            2      0.813             0.670               0.169
     A->B    0.85    0.00   0.484         ADAPT                 False  NEWS2_mod            4      0.886             0.758               0.274
     A->B    0.85    0.05   0.534         ADAPT                 False  NEWS2_mod            4      0.886             0.758               0.224
     A->B    0.85    0.10   0.584         ADAPT                 False  NEWS2_mod            4      0.886             0.758               0.174
     B->A    0.75    0.00   0.285         BLOCK                 False  NEWS2_mod            6      0.755             0.643               0.358
     B->A    0.75    0.05   0.335         BLOCK                 False  NEWS2_mod            6      0.755             0.643               0.308
     B->A    0.75    0.10   0.385         ADAPT                 False  NEWS2_mod            6      0.755             0.643               0.258
     B->A    0.80    0.00   0.329         BLOCK                 False  NEWS2_mod            5      0.867             0.783               0.454
     B->A    0.80    0.05   0.379         BLOCK                 False  NEWS2_mod            5      0.867             0.783               0.404
     B->A    0.80    0.10   0.429         ADAPT                 False  NEWS2_mod            5      0.867             0.783               0.354
     B->A    0.85    0.00   0.399         BLOCK                 False  NEWS2_mod            5      0.867             0.783               0.384
     B->A    0.85    0.05   0.449         BLOCK                 False  NEWS2_mod            5      0.867             0.783               0.334
     B->A    0.85    0.10   0.499         ADAPT                 False  NEWS2_mod            5      0.867             0.783               0.284
     A->A    0.75    0.00   0.310   ADAPT|BLOCK                 False   MEWS_mod            3      0.768             0.713               0.403
     A->A    0.75    0.05   0.360          KEEP                 False   MEWS_mod            3      0.768             0.713               0.353
     A->A    0.75    0.10   0.410          KEEP                 False   MEWS_mod            3      0.768             0.713               0.303
     A->A    0.80    0.00   0.401     CALIBRATE                 False  NEWS2_mod            5      0.872             0.786               0.385
     A->A    0.80    0.05   0.451          KEEP                 False  NEWS2_mod            5      0.872             0.786               0.335
     A->A    0.80    0.10   0.501          KEEP                 False  NEWS2_mod            5      0.872             0.786               0.285
     A->A    0.85    0.00   0.484          KEEP                 False  NEWS2_mod            5      0.872             0.786               0.302
     A->A    0.85    0.05   0.534          KEEP                 False  NEWS2_mod            5      0.872             0.786               0.252
     A->A    0.85    0.10   0.584          KEEP                 False  NEWS2_mod            5      0.872             0.786               0.202
     B->B    0.75    0.00   0.285     CALIBRATE                 False  NEWS2_mod            5      0.789             0.604               0.319
     B->B    0.75    0.05   0.335          KEEP                 False  NEWS2_mod            5      0.789             0.604               0.269
     B->B    0.75    0.10   0.385          KEEP                 False  NEWS2_mod            5      0.789             0.604               0.219
     B->B    0.80    0.00   0.329     CALIBRATE                 False   SIRS_mod            2      0.807             0.672               0.343
     B->B    0.80    0.05   0.379          KEEP                 False   SIRS_mod            2      0.807             0.672               0.293
     B->B    0.80    0.10   0.429          KEEP                 False   SIRS_mod            2      0.807             0.672               0.243
     B->B    0.85    0.00   0.399     CALIBRATE                 False  NEWS2_mod            4      0.873             0.764               0.365
     B->B    0.85    0.05   0.449          KEEP                 False  NEWS2_mod            4      0.873             0.764               0.315
     B->B    0.85    0.10   0.499          KEEP                 False  NEWS2_mod            4      0.873             0.764               0.265
A->B:MICU    0.75    0.00   0.310         ADAPT                 False  NEWS2_mod            5      0.808             0.633               0.324
A->B:MICU    0.75    0.05   0.360         ADAPT                 False  NEWS2_mod            5      0.808             0.633               0.274
A->B:MICU    0.75    0.10   0.410         ADAPT                 False  NEWS2_mod            5      0.808             0.633               0.224
A->B:MICU    0.80    0.00   0.401         ADAPT                 False  NEWS2_mod            5      0.808             0.633               0.233
A->B:MICU    0.80    0.05   0.451         ADAPT                 False  NEWS2_mod            5      0.808             0.633               0.183
A->B:MICU    0.80    0.10   0.501         ADAPT                 False  NEWS2_mod            5      0.808             0.633               0.133
A->B:MICU    0.85    0.00   0.484         ADAPT                 False  NEWS2_mod            4      0.903             0.797               0.313
A->B:MICU    0.85    0.05   0.534         ADAPT                 False  NEWS2_mod            4      0.903             0.797               0.263
A->B:MICU    0.85    0.10   0.584         ADAPT                 False  NEWS2_mod            4      0.903             0.797               0.213
A->B:SICU    0.75    0.00   0.310         ADAPT                 False   MEWS_mod            3      0.764             0.693               0.383
A->B:SICU    0.75    0.05   0.360         ADAPT                 False   MEWS_mod            3      0.764             0.693               0.333
A->B:SICU    0.75    0.10   0.410         ADAPT                 False   MEWS_mod            3      0.764             0.693               0.283
A->B:SICU    0.80    0.00   0.401         ADAPT                 False  NEWS2_mod            5      0.841             0.731               0.331
A->B:SICU    0.80    0.05   0.451         ADAPT                 False  NEWS2_mod            5      0.841             0.731               0.281
A->B:SICU    0.80    0.10   0.501         ADAPT                 False  NEWS2_mod            5      0.841             0.731               0.231
A->B:SICU    0.85    0.00   0.484         ADAPT                 False  NEWS2_mod            4      0.918             0.875               0.391
A->B:SICU    0.85    0.05   0.534         ADAPT                 False  NEWS2_mod            4      0.918             0.875               0.341
A->B:SICU    0.85    0.10   0.584         ADAPT                 False  NEWS2_mod            4      0.918             0.875               0.291
B->A:MICU    0.75    0.00   0.285         BLOCK                 False  NEWS2_mod            6      0.766             0.601               0.316
B->A:MICU    0.75    0.05   0.335         BLOCK                 False  NEWS2_mod            6      0.766             0.601               0.266
B->A:MICU    0.75    0.10   0.385         BLOCK                 False  NEWS2_mod            6      0.766             0.601               0.216
B->A:MICU    0.80    0.00   0.329         BLOCK                 False  NEWS2_mod            5      0.852             0.746               0.417
B->A:MICU    0.80    0.05   0.379         BLOCK                 False  NEWS2_mod            5      0.852             0.746               0.367
B->A:MICU    0.80    0.10   0.429         BLOCK                 False  NEWS2_mod            5      0.852             0.746               0.317
B->A:MICU    0.85    0.00   0.399         BLOCK                 False  NEWS2_mod            5      0.852             0.746               0.347
B->A:MICU    0.85    0.05   0.449         BLOCK                 False  NEWS2_mod            5      0.852             0.746               0.297
B->A:MICU    0.85    0.10   0.499         BLOCK                 False  NEWS2_mod            5      0.852             0.746               0.247
B->A:SICU    0.75    0.00   0.285         ADAPT                 False  NEWS2_mod            6      0.797             0.823               0.538
B->A:SICU    0.75    0.05   0.335         ADAPT                 False  NEWS2_mod            6      0.797             0.823               0.488
B->A:SICU    0.75    0.10   0.385         ADAPT                 False  NEWS2_mod            6      0.797             0.823               0.438
B->A:SICU    0.80    0.00   0.329         BLOCK                 False   SIRS_mod            2      0.838             0.857               0.528
B->A:SICU    0.80    0.05   0.379         BLOCK                 False   SIRS_mod            2      0.838             0.857               0.478
B->A:SICU    0.80    0.10   0.429         ADAPT                 False   SIRS_mod            2      0.838             0.857               0.428
B->A:SICU    0.85    0.00   0.399         BLOCK                 False  NEWS2_mod            5      0.914             0.928               0.529
B->A:SICU    0.85    0.05   0.449         BLOCK                 False  NEWS2_mod            5      0.914             0.928               0.479
B->A:SICU    0.85    0.10   0.499         ADAPT                 False  NEWS2_mod            5      0.914             0.928               0.429
```

## Primary criterion (s* = 0.80, margin = 0.05)

```
direction oracle_remedy  f_star best_score  best_cutoff  best_sens  best_false_alert  excess_false_alert
     A->B         ADAPT   0.451   SIRS_mod            2      0.813             0.670               0.219
     B->A         BLOCK   0.379  NEWS2_mod            5      0.867             0.783               0.404
     A->A          KEEP   0.451  NEWS2_mod            5      0.872             0.786               0.335
     B->B          KEEP   0.379   SIRS_mod            2      0.807             0.672               0.293
A->B:MICU         ADAPT   0.451  NEWS2_mod            5      0.808             0.633               0.183
A->B:SICU         ADAPT   0.451  NEWS2_mod            5      0.841             0.731               0.281
B->A:MICU         BLOCK   0.379  NEWS2_mod            5      0.852             0.746               0.367
B->A:SICU         BLOCK   0.379   SIRS_mod            2      0.838             0.857               0.478
```
