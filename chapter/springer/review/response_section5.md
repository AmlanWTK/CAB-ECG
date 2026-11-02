# Response to the review of Section 5

2026-11-02. Checked against the application (`app/sepsis_monitor.py`) and its gate module
(`code/cabsepsis/deploy.py`). "Changed" means Section 5 now says this.

1. **The 12,000 labelled patients and the 8,000 checked.** Checked: `draw_labels` samples from
   hospital B's training and validation patients (the same pool as the experiments), then splits
   the sample 50/50 within septic and non-septic patients into fit and certification halves, as
   in `one_run`. The adapted model is fitted only on the fit half (`split_patients(fit)`,
   `fit_adapt`). The retrospective check uses `eligible & ~lab`: the 8,000 patients not labelled,
   namely the 4,000 remaining training and validation patients and all 4,000 test patients. The
   gate uses only the labelled patients, so these 8,000 take no part in any of its decisions.
   Changed: 5.1 states the pool, the split, the composition of the 8,000 and that they take no
   part in the gate's decisions; it also says the quoted figures are the application's own
   output for this sample (they are read from the Fig. 7 screenshot, retaken on 2026-11-02).
2. **Which patients the ward monitor replays.** Checked (`page_ward`): a ward of 16 patients drawn
   from hospital B's test patients with at least 12 hours in the ICU, 4 septic and 12 non-septic.
   Test patients are never in the labelling pool, so they are a subset of the 8,000 above.
   Changed: 5.2 says so.
3. **What certification means.** Changed: 5.2 says the gate certifies against the hospital's
   configured requirements and that this is not a demonstration of clinical safety or benefit.
   The interface already says "certified by the gate"; it never says "safe" or "clinically
   certified", so no further code change was made.
4. **Enriched samples.** Checked: the application samples septic and non-septic patients at random
   within their class. Changed: 5.1 states this condition and that a convenience sample enriched
   for sepsis would not meet it.
5. **Scope of the 3,000-case test.** Changed: 5.3 says it covers the decision function, not the
   whole interface.
6. **Vendor counts as reported.** Changed: "the home validation counts the vendor reports".
7. **Local operation.** Changed: it adds that local operation alone does not establish compliance
   with any data-protection or regulatory requirement.
8. **NEWS2 fallback.** Unchanged: modified NEWS2 with a cut-off of 5, as in Sections 3.7 and 4.6.
