# Extended abstract: Advanced Computing Applications (Springer), Health Informatics

Submit by Fri 13 November 2026 to Dr Abeer Alsadoon (alsadoon.abeer@ieee.org).
Required: structured as Background, Objective, Methodology, Results, Conclusion; at least 5 keywords; focus on practical application and implementation.
Version 4: final numbers from the 100-repeat runs on one machine (E3mac100, E6units), E5 and E2.

## Submitted version (in the call's template: CAB_Sepsis_Abstract.docx)

Written by Amlan Sarkar from version 4, with one reordering in Results ("With as few as 250 labelled patients, CAB blocked…") to avoid a misreading. About 320 words, one paragraph with inline labels as in the template.

**Calibrate, Adapt, or Block: A Statistically Certified Deployment Gate for Imported Sepsis Early-Warning Models**

Amlan Sarkar¹* and Md Tobibul Islam¹
¹ Department of Biomedical Engineering, Military Institute of Science and Technology (MIST), Dhaka, Bangladesh
amlansarkar738@gmail.com, tobibul.islam@bme.mist.ac.bd

**Background:** Clinical prediction models often lose performance when transferred to new hospitals or clinical units, yet receiving institutions lack a statistically grounded approach to determining whether an imported model can be deployed safely, requires updating, or should be rejected. **Objective:** This study proposes CAB (Calibrate, Adapt, or Block), a statistically certified deployment gate that uses locally labelled patient data to select the least invasive acceptable intervention for an imported sepsis early-warning model while controlling the risk of activating a model that fails prespecified safety requirements. **Methodology:** Using data from 40,336 intensive care patients across two US hospitals in the PhysioNet/CinC Challenge 2019 dataset, gradient-boosted sepsis prediction models were transferred between hospitals and into individual intensive care units across six scenarios. CAB evaluates model retention, recalibration, and adaptation in order of increasing intervention, permitting activation only when exact binomial tests certify that prespecified sensitivity and false-alert-rate requirements are satisfied; otherwise, deployment is blocked. CAB was compared with direct deployment, recalibration, fine-tuning, retraining, and classical statistical updating using 250–12,000 labelled patients, with 100 repetitions per setting. A prototype deployment and ward-monitoring application was also implemented. **Results:** Imported models exhibited direction-dependent safety failures, with sensitivity falling to 63% against an 80% target or false-alert rates doubling. Conventional and classical updating methods activated models that failed the prespecified safety requirements in 77–100% of runs, whereas CAB did so in fewer than 1%. With as few as 250 labelled patients, CAB blocked models that could not be safely repaired, and it certified the adapted model in 97% of runs with 12,000 labelled patients, including approximately 690 septic cases. A closed-form calculator estimated the required number of labelled patients to within 20%. **Conclusion:** CAB provides a systematic approach to evaluating and updating imported clinical prediction models before deployment. The findings highlight that deployment rejection is a legitimate safety decision and that local data collection should be planned according to the statistical evidence required for certification.

**Keywords:** Sepsis Early Warning; Clinical Decision Support; Dataset Shift; Model Updating; Local Validation; Statistical Certification; Health Informatics.

## Version 4 (longer working draft, kept for the chapter)

---

**Title:** Calibrate, Adapt, or Block? A Certified Deployment Gate for Imported Sepsis Early-Warning Models

**Authors:** [names, affiliations, corresponding email]

**Background.** Hospitals increasingly deploy clinical prediction models developed at other institutions. Performance often degrades after transfer because patient populations, measurement practices and outcome rates differ between sites. A recent review of 78 model-updating studies found no guidance on how a receiving hospital should choose between recalibrating, adapting or abandoning an imported model, and in practice the choice is often made on a small local validation sample.

**Objective.** To develop and evaluate a practical deployment gate that uses a limited number of locally labelled patients to select the least invasive safe remedy for an imported sepsis early-warning model, while controlling the probability of switching on a model that is unsafe at the new hospital, and to give hospitals a way to plan how many labels this requires.

**Methodology.** We used the open PhysioNet/CinC Challenge 2019 ICU data (40,336 patients from two US hospitals). At each hospital, we trained a gradient-boosted (LightGBM) model on hourly vital-sign and laboratory features, then imported it unchanged into the other hospital as a whole and into its medical and surgical ICUs separately (six import scenarios). The proposed procedure, CAB, tests four options in order of cost: keep the model, recalibrate its alert threshold, adapt it to local data, or block it. An option is activated only if exact binomial tests certify patient-level sensitivity and false-alert rate against pre-specified targets, which bounds the probability of unsafe activation at 5%. We compared CAB with deploying the model as is, label-free threshold adjustment, recalibration, fine-tuning, local retraining and classical significance-test-based model updating. The comparison covered label budgets of 250 to 12,000 patients, nine safety criteria, a same-hospital positive control and 100 repeated samples per setting. We derived a closed-form calculator for the labels certification requires, and implemented the procedure in a prototype application with a deployment gate and an hour-by-hour ward monitor.

**Results.** Imported unchanged, the model failed differently in each direction. At one hospital, hourly AUROC fell from 0.855 to 0.777 and only 63% of septic patients were detected against a target of 80%. At the other, 67% of non-septic patients were alerted, twice the local model's rate. Across scenarios, conventional remedies were unsafe in 77–100% of runs, including classical statistical updating (81–97%), often while appearing safe on the hospital's own data. CAB was unsafe in 0.5% of cross-hospital runs and 0.3% of ICU-level runs. It blocked models that no remedy could make safe from 250 labelled patients, and certified the adapted model in 97% of runs at 12,000 patients (about 690 septic cases), half of which served to refit the model. The calculator predicted simulated label requirements to within about 20%, and showed that a vendor threshold set 1.6 points above the target would need about 9,600 septic patients to certify. No single ICU had enough patients to certify adaptation.

**Conclusion.** A certified deployment gate prevents nearly all the unsafe activations of imported sepsis models that conventional and classical updating allow. Certification has a measurable cost: typical local validation samples are too small, so blocking should be a planned outcome, vendors should ship thresholds with headroom above the target, and hospitals should plan label collection with a calculator before deployment. The code, calculator and prototype application are openly available.

**Keywords:** sepsis early warning; clinical decision support; model transportability; dataset shift; model updating; local validation; health informatics

---

## Where each number comes from

| Claim | Source |
|---|---|
| AUROC 0.855 → 0.777 (−0.078, 95% CI −0.102 to −0.057); sensitivity 0.838 → 0.632 | E2_ci.md (desktop), target B, imported from A |
| False alerts 0.339 → 0.669 (+0.330, CI 0.312 to 0.348) | E2_ci.md, target A, imported from B |
| Six import scenarios | E3mac100 (A->B, B->A) + E6units (A->B:MICU, A->B:SICU, B->A:MICU, B->A:SICU) |
| Conventional remedies unsafe 77–100% | E3mac100 mean unsafe: AS-IS 0.774, LABEL-FREE 0.792, FINE-TUNE 0.823, RECALIBRATE 0.881, RETRAIN 0.919; E6units 0.93–1.00 |
| Classical updating 81–97% | CLOSED-TEST mean unsafe: E3mac100 0.809, E6units 0.974 |
| "Appearing safe on their own data" | silent-failure rates, E3mac100: AS-IS 77%, FINE-TUNE 40%, CLOSED-TEST 32%, RECALIBRATE 26%, RETRAIN 18% |
| CAB 0.5% cross-hospital, 0.3% ICU-level | E3mac100 A->B and B->A mean 0.0051 (max 0.06, 1 of 126 settings above 5%); E6units mean 0.003 (max 0.05) |
| Blocked from 250 labels | E3mac100 primary B->A, CAB correct 1.00 at every budget; E6units B->A:MICU all criteria |
| 97% at 12,000 (about 690 septic) | E3mac100 primary A->B, CAB correct 0.97 at 12,000 (0.70 at 8,000); pool prevalence 5.7% |
| "Half of which served to refit" | E5: certification alone (models fixed) reached 90% at 6,000 patients (343 septic) |
| Calculator within about 20% | E5_needed.csv, plan_patients vs sim_patients (e.g. 6,127 vs 6,000; 14,650 vs 16,000) |
| 1.6 points → about 9,600 septic | E5, A->A primary: home sensitivity 0.816 vs target 0.80, plan_septic 9,595 |
| No single ICU had enough patients | E6units A->B:MICU / SICU: oracle ADAPT, labels needed > the 4,000 that the pools allow (CAB certified in 7–11% of runs at 4,000) |

## Caveats to keep in mind for the full chapter

- **Home-hospital control.** CAB was unsafe in 1.0% of home runs on average. In 3 of 72 home settings it was above 5% (worst 7%), all at the largest home budgets, where the patients left to judge safety are fewest (about 175 septic), so the measured sensitivity varies by about ±3 points by chance.
- **Cost of blocking.** When CAB blocks, the hospital keeps modified NEWS2 ≥ 5. That alerts about 71 non-septic patients per 100 admissions and raises 2.2 alarms per patient-day, against 28–56 per 100 admissions for the AI policies (E3mac100_impact.md). The chapter must say this. Decide whether the fallback should be a stricter NEWS2 cut-off or "no automated alert".
- **Vendor headroom (E11) corrects the v4 conclusion.** Raising the shipped threshold's headroom does not raise the chance that CAB approves the model, because CAB's calibrate step picks its own threshold from the same labels (approval at home stayed at 45–47% for A->A and 64–67% for B->B, from 0 to 10 points of headroom). Headroom only changes whether the approval is labelled KEEP or CALIBRATE. What does move approval is the hospital's false-alert tolerance: at home with 8,000 labels, approval rose from 4% to 54% to 98% (A->A) as the tolerance went from 0 to 5 to 10 points. In the chapter, replace "vendors should ship thresholds with headroom" with: hospitals should fix the false-alert tolerance before labelling, and vendors should publish the home operating curve so that hospitals can plan labels with the calculator. The submitted abstract does not contain the headroom claim.
- **Ablation.** CAB without the adapt step (CERT-RECAL) was almost never unsafe but almost never switched anything on in the cross-hospital scenarios. So the adapt step is what lets CAB activate at all.
- **E2 numbers** (AUROC, sensitivity, false alerts after import) come from the desktop run. Everything else in Results comes from the Mac runs. If needed, rerun E2 on the Mac for full consistency.
- **Enrichment** (E4) is not in this version of the abstract. It allowed earlier activation but did not reduce the labels needed to reach 90% correct.
- **Before submitting,** check the citation for the "review of 78 studies" (Meijerink et al., J Clin Epidemiol 2025).
- **Similarity must be below 18% on Turnitin.** Write the chapter fresh, not pasted from the Stage 2 report or the README.
