## 4 Results

Unless stated otherwise, results are for the primary requirements (s* = 0.80, m = 0.05) and the error level α = 0.05. "Correct" refers to the correct remedy of Section 3.7, an evaluation reference computed from the receiving hospital's full data that no policy could know at deployment.

### 4.1 Imported Models Failed Differently in Each Direction

Imported unchanged, with the vendor's threshold for 80% sensitivity, both models violated the receiving hospital's requirements, but in opposite ways (Fig. 2; Table 5).

Hospital A's model at hospital B (A→B) lost sensitivity. Hourly AUROC fell from 0.855 for the local model to 0.777 (difference −0.078, 95% CI −0.102 to −0.057), and only 63% of septic patients were detected, against 84% for the local model and a target of 80%.

Hospital B's model at hospital A (B→A) remained sensitive, detecting 86% of septic patients, but alerted far more patients who were not septic: 67%, against 34% for the local model (difference +0.33, 95% CI 0.31 to 0.35). Alarms per patient-day rose from 0.51 to 0.92.

**Table 5.** Imported and local models at each receiving hospital, on its test patients. Each model uses its own vendor threshold. The local model is the receiving hospital's own source model. Confidence intervals are paired percentile intervals from resampling patients with replacement (2,000 resamples; 200 for AUROC), with both models evaluated on the same resampled patients.

| At | Imported from | Measure | Local | Imported | Difference [95% CI] |
|---|---|---|---|---|---|
| Emory (B) | Beth Israel (A) | Hourly AUROC | 0.855 | 0.777 | −0.078 [−0.102, −0.057] |
| | | Sensitivity (patients) | 0.838 | 0.632 | −0.206 [−0.268, −0.143] |
| | | Non-septic patients alerted | 0.303 | 0.250 | −0.053 [−0.070, −0.036] |
| Beth Israel (A) | Emory (B) | Hourly AUROC | 0.810 | 0.761 | −0.049 [−0.064, −0.032] |
| | | Sensitivity (patients) | 0.771 | 0.858 | +0.087 [0.039, 0.134] |
| | | Non-septic patients alerted | 0.339 | 0.669 | +0.330 [0.312, 0.348] |

These failures determined the correct remedy in each direction. For A→B, recalibration could not restore both requirements but adaptation could, so the correct remedy was ADAPT for all nine pairs of requirements. For B→A, no option met the primary requirements, so the correct remedy was BLOCK; with the most tolerant false-alert limit (m = 0.10) an adapted model would have sufficed. In the same-hospital control the correct remedy at the primary requirements was KEEP.

No bedside score met both requirements in any of the 72 combinations of scenario and requirement pair (eight scenarios, including the two controls, and nine pairs), with each of the four scores evaluated at every cut-off on all eligible patients. A blocked model therefore leaves the hospital with its usual care, not with a certified alternative.

### 4.2 CAB Rarely Deployed an Unsafe Model; Conventional Updating Usually Did

Fig. 4 shows the share of runs in which each policy deployed an unsafe configuration at the primary requirements, by budget, in the whole-hospital transfers and the same-hospital control. Table 6 summarises the same outcome more broadly: averaged over the whole-hospital transfers and the same-hospital control, all nine requirement pairs and all budgets, the conventional policies were unsafe in most runs. AS-IS was a silent failure in every unsafe run, because the vendor's own figures always looked acceptable. For the updating policies, between a fifth and two fifths of runs were silent failures: the hospital's own labelled patients suggested the deployment was safe when it was not.

**Table 6.** Share of runs in which the conventional policies deployed an unsafe configuration, and in which they did so while appearing safe on their own labelled patients (silent failure), averaged over the whole-hospital transfers and the same-hospital control, all requirement pairs and all budgets. LABEL-FREE uses no labelled patients, so it has no apparent result.

| Policy | Unsafe | Silent failure |
|---|---|---|
| AS-IS | 77.4% | 77.4% |
| LABEL-FREE | 79.2% | – |
| FINE-TUNE | 82.3% | 39.9% |
| RECALIBRATE | 88.1% | 25.8% |
| RETRAIN | 91.9% | 18.2% |
| CLOSED-TEST | 80.9% | 32.4% |

On the same basis, CAB deployed an unsafe configuration in 0.7% of runs, with the same silent-failure rate; Table 7 breaks this down by group of settings, averaging over all requirement pairs and budgets within each group. In the ICU-type transfers, CLOSED-TEST was unsafe in 97% of runs.

**Table 7.** Share of runs in which CAB deployed an unsafe configuration, by group of settings (α = 0.05; a setting is one scenario, requirement pair and budget, with 100 runs).

| Group | Settings | Mean | Worst setting |
|---|---|---|---|
| Whole-hospital transfers | 126 | 0.5% | 6% |
| Same-hospital control | 72 | 1.0% | 7% |
| ICU-type transfers | 162 | 0.3% | 5% |

CAB's decisions followed the correct remedy as the number of labels grew (Fig. 3). For B→A it blocked in every run at every budget from 250 to 12,000 labelled patients. For A→B it blocked while the evidence was insufficient, then certified the adapted model in 10% of runs at 4,000 labels, 70% at 8,000 and 97% at 12,000 (about 690 septic patients). In the same-hospital control it deployed a configuration in at most 25% of runs at 2,000 labels, and kept or recalibrated the unchanged model in at most 23%; Section 4.5 explains why. With 250 or 500 labelled patients (a median of 18 and 35 septic patients), CAB deployed a configuration in at most 2.1% of runs in any scenario, over all requirement pairs, including those in which a safe configuration existed.

The ablation without the adapt stage (CERT-RECAL) was almost never unsafe, but it also almost never deployed anything in the whole-hospital transfers, because recalibration alone could not repair either model. The adapt stage is therefore what allows CAB to deploy at all after a real shift.

### 4.3 Comparison with Practical Alternatives

Fig. 5 compares CAB with the alternatives a hospital is most likely to use instead.

*Prevalence correction did not help.* LABEL-SHIFT estimated the receiving hospital's share of septic patient-hours reasonably well, at 1.7% and 2.4% against true values of 1.4% and 2.2%, yet it was unsafe in 100% of runs in the whole-hospital transfers. The models failed because the relationship between measurements and sepsis differed between the hospitals, not because sepsis was more or less common.

*Point-estimate validation was often unsafe.* NAIVE-VAL was unsafe in 34.9% of runs in the whole-hospital transfers and 33.7% in the same-hospital control, and the typical 500-patient validation (NAIVE-500) in 20.4% and 30.4%. Point estimates often chose the correct remedy, in 64–66% of runs, but they also often accepted a configuration just short of the requirements. More labels did not remove this: for B→A with 12,000 labelled patients, NAIVE-VAL still deployed an unsafe configuration in 29% of runs. In the ICU-type transfers NAIVE-VAL was unsafe in 35.9% of runs on average and in up to 72% in the worst setting, against 0.3% for CAB.

*Learn-then-Test without CAB's order made the same decision as CAB in every run of the whole-hospital transfers.* In the same-hospital control it deployed a configuration less often than CAB, in 3.1% against 8.0% of runs, and chose the correct remedy less often, in 5.7% against 7.9%. CAB tests the unchanged model on all the labelled patients, whereas the unordered procedure spends half of them fitting an adapted model that was not needed. At hospital B with 2,000 labels, CAB chose the correct remedy in 9% of runs and the unordered procedure in none.

### 4.4 Empirical Unsafe-Deployment Rates Were Consistent with the Guarantee

The simulations cannot prove the guarantee, which follows from the proof in Section 3.5, but they can show whether the observed behaviour is consistent with it. Each setting was repeated 100 times with independent label samples, so its measured unsafe-deployment rate is a binomial proportion with its own exact confidence interval. Table 8 compares the measured rates with the nominal level for α = 0.01, 0.05 and 0.10. Given the fixed hospital data, each repetition draws its own labelled sample, fits its own adapted model and is judged on its own unlabelled patients, using a seed of its own; the 100 outcomes of a setting are therefore independent, and each per-setting interval describes the probability of an unsafe deployment under this repeated-sampling design for these hospitals' patients, not uncertainty about a wider population. Within a run, however, the nine requirement pairs share the same labelled sample, so runs pooled across settings are not independent; the group means in Table 8 are therefore descriptive, and inference rests on the per-setting intervals.

**Table 8.** CAB's measured unsafe-deployment rate against the nominal level α. Mean and worst setting are descriptive summaries over the settings of each group (100 runs each); the last column counts settings whose exact (Clopper–Pearson) 95% interval lies wholly above α.

| α | Group | Settings | Mean | Worst setting | Settings with interval above α |
|---|---|---|---|---|---|
| 0.01 | Whole hospital | 126 | 0.11% | 2% | 0 |
| 0.01 | Same hospital | 72 | 0.14% | 2% | 0 |
| 0.05 | Whole hospital | 126 | 0.51% | 6% | 0 |
| 0.05 | Same hospital | 72 | 0.97% | 7% | 0 |
| 0.05 | ICU type | 162 | 0.28% | 5% | 0 |
| 0.10 | Whole hospital | 126 | 0.91% | 13% | 0 |
| 0.10 | Same hospital | 72 | 2.06% | 12% | 0 |

Some settings' measured rates exceeded α, which is expected from sampling variation in 100 runs. At α = 0.05, one whole-hospital setting and three same-hospital settings exceeded 5%, but no setting's exact confidence interval lay wholly above α, at any of the three levels. Had every setting's true rate been exactly 5%, about 48 of the 126 whole-hospital settings would have shown a measured rate above 5% by chance alone. The three same-hospital settings above 5% all used 2,000 labels, where only 110–180 septic patients remained unlabelled to judge safety; with so few, a configuration whose true sensitivity is exactly at the target is judged unsafe about half the time.

The error level trades safety against approval. For A→B, CAB certified the adapted model in 82%, 97% and 98% of runs at 12,000 labels for α = 0.01, 0.05 and 0.10, and in 35%, 70% and 81% at 8,000 labels. B→A was blocked in every run at every level.

### 4.5 How Many Labels Certification Needs

The labels needed fall steeply as the model's margin over the target grows (Fig. 6a). To certify sensitivity at s* = 0.80, the calculator requires about 5,800 septic patients when the true sensitivity is 2 points above the target, about 870 at 5 points and about 190 at 10 points.

We also applied the calculator to each scenario's actual operating curve and compared its estimate with a simulation of CAB's exact rule. The simulation held the imported model and an adapted model fitted on the receiving hospital's full training set fixed, drew labelled samples with replacement from the receiving hospital's patients (400 samples per budget), and recorded the smallest budget on a coarse grid at which CAB chose the correct remedy in at least 90% of samples. For A→B the calculator's estimates agreed with the simulated budgets to within 1–18%. Because the simulated samples are drawn with replacement, they may contain the same patient more than once, so this agreement is empirical evidence under that sampling design rather than a guarantee of the number of distinct patients a hospital would need. At the primary requirements it estimated 6,127 labelled patients, including the half set aside for fitting, against 6,000 (about 340 septic) in simulation. Because CALIBRATE and ADAPT choose their threshold from the data, this agreement is an empirical check of the calculator as a planning tool, not a guarantee. When the adapted model was instead refitted on the fit half of each sample, as CAB does, about twice as many were needed: 12,000 patients, about 690 of them septic. This is consistent with a model fitted on a few thousand local patients having a smaller margin over the requirements than one fitted on the hospital's full training set.

The same-hospital control shows why certification can be slow even when nothing is wrong. At hospital A, the vendor's threshold detected 81.6% of septic patients on the test patients, against a target of 80%. Certifying a margin of 1.6 points would require about 9,600 septic patients, roughly 109,000 admissions. This is why CAB rarely kept the unchanged model at home with up to 2,000 labels, although KEEP was the correct remedy: the model was not unsafe, but its safety could not be demonstrated with so few labels.

No single ICU type had enough patients to certify an adapted model reliably: in the ICU-type transfers of A's model, CAB certified ADAPT in only 7% (MICU) and 11% (SICU) of runs at 4,000 labels, the largest budget the units allowed.

### 4.6 What Blocking Costs

A blocked model does not leave the ward without monitoring; the hospital keeps its usual care, modelled here as a modified NEWS2 score of 5 or more. Per 100 admissions, this fallback missed about 1.1–1.2 septic patients, and falsely alerted about 71 non-septic patients at hospital A and 56 at hospital B, with 2.2 and 1.4 alarms per patient-day respectively.

The benefit of blocking is therefore avoiding an unsafe model, not avoiding alarms. For B→A with 12,000 labelled patients, every point-estimate policy deployed a configuration that violated a requirement in 99–100% of runs, while CAB never did. Those policies alerted 35–65 non-septic patients per 100 admissions, against 71 for CAB's bedside fallback; CAB's price for safety was the noisier fallback.

When CAB adapted the model (A→B with 12,000 labels), it deployed the adapted model in 97% of runs and an unsafe configuration in 2%. Averaged over all runs, it missed 0.87 septic patients and falsely alerted 37 non-septic patients per 100 admissions, with 0.55 alarms per patient-day.

### 4.7 The Hospital's Tolerance, Not the Vendor's Headroom, Decides the Labels Needed

One might expect a vendor to make certification easier by shipping a threshold with extra sensitivity above the target. We examined this in a separate simulation of the same-hospital control. The vendor's threshold was set to reach a home sensitivity of s* + h, for headroom h from 0 to 10 points, while f* stayed as in the main experiment. With the models held fixed and no adaptation, CAB's rule was applied to labelled samples drawn with replacement from the hospital's test patients (200 samples per cell). Because sampling is with replacement, budgets could extend beyond the main experiment's 2,000 labels, to 32,000 (Fig. 6b, c). The larger budgets therefore contain repeated patients and represent repeated sampling from the test patients' empirical distribution; they show how approval responds to headroom and tolerance, and should not be read as the evidence that labelling the same number of distinct patients would provide. Approval of the unchanged model at home, KEEP or CALIBRATE, hardly changed: averaged over budgets of 1,000 to 32,000 labels, it stayed at about 46% at hospital A and 66% at hospital B, varying by at most 3 points. CAB's calibration step chooses its own threshold from the hospital's labelled patients, so headroom only changes whether an approval is recorded as KEEP or CALIBRATE. Large headroom (8–10 points) also raised the vendor's own false-alert rate by 6–15 points.

The hospital's false-alert tolerance m did change approval. With 8,000 labels, approval at hospital A was 4% with no additional tolerance, 54% with 5 points and 98% with 10 points; the pattern at hospital B was similar. A hospital should therefore set its tolerance deliberately before labelling, and a vendor should publish its full operating curve rather than a single threshold, so that the hospital can plan its labels with the calculator.

### 4.8 Lead Time and Robustness

*Lead time.* Because detection counts alerts up to 3 h after onset, we examined how early the alerts came (Table 9). In A→B with 12,000 labels, the configurations CAB deployed detected 85% of septic patients and alerted 64% of all septic patients at least 6 h before onset, the highest share of any policy. Recalibration and fine-tuning alerted 58–59% that early, and the imported model as supplied 44%. The imported model's longer median lead time reflects the fewer patients it detected, not earlier alerts; lead times are capped at 12 h by the detection window. The imported model's sensitivity here (68%) differs from Table 5 (63%) because the patient sets differ: Table 5 uses hospital B's 4,000 test patients, on which the 95% interval is 57–69%, whereas Table 9 averages over the unlabelled patients of each run; over all of hospital B's patients the figure is 67%. For the same reason, and because it is a different model with a different threshold, Table 9's local model is not the local model of Table 5.

**Table 9.** Lead time before sepsis onset, A→B, 12,000 labels, primary requirements. The first four rows average 20 runs, each judged on the about 8,000 patients of hospital B not labelled in that run; CAB deployed the adapted model in all 20. The two reference rows are single evaluations on hospital B's test patients: its own local model (trained on its training set, threshold set to 80% sensitivity on those patients) and the bedside score. Lead times are among detected patients; the last column is the share of all septic patients.

| Alerting system | Septic patients detected | Median lead time, h (IQR) | Alerted ≥ 6 h before onset |
|---|---|---|---|
| CAB (adapted model) | 85% | 10.7 (5.7–12) | 64% |
| Recalibration | 82% | 11.4 (5.1–12) | 59% |
| Fine-tuning | 80% | 9.7 (5.2–12) | 58% |
| Imported model, as supplied | 68% | 11.9 (3.7–12) | 44% |
| Hospital's own local model | 80% | 7.0 (5.0–12) | 58% |
| Modified NEWS2 ≥ 5 | 79% | 8.0 (3.8–12) | 49% |

*A shorter detection window.* We repeated the whole-hospital experiment counting a septic patient as detected only from 6 h, rather than 12 h, before onset, applying the shorter window throughout (the vendor's threshold, CAB's tests and the judging), with 30 runs per setting and budgets of 1,000, 4,000 and 12,000 labels. The correct remedies at the primary requirements were unchanged (ADAPT for A→B, BLOCK for B→A), and so were the conclusions. CAB was unsafe in 0.9% of runs on average (worst setting 3.3%); the conventional policies were unsafe in 81–100%; and at 12,000 labels CAB certified the adapted A→B model in every run.

*Imperfect labels.* The guarantee assumes that the labels are correct. We relaxed this by recording 5%, 10% or 20% of the labelled septic patients as non-septic in the data CAB sees, while still judging safety with the true labels (20 runs each). Under this one-sided noise, CAB remained conservative in these simulations. Its unsafe-deployment rate stayed between 0% and 5% of runs (at most 1 of 20), as with correct labels; for A→B it deployed the adapted model in 65% of runs at 20% noise, against 100% with correct labels; and for B→A it blocked in every run at every noise level. A septic patient recorded as non-septic leaves the sensitivity test, which then has fewer patients, and joins the false-alert test, where, if alerted, it adds a false alert; in these runs the net effect was fewer deployments, although it need not be in every case. Point-estimate recalibration remained unsafe in every run at every noise level. With 20 runs per condition, and without over-calling of sepsis or errors in onset times, this is a limited robustness check rather than a guarantee under imperfect labels.
