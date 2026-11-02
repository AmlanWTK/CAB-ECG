# Reference and regulatory check

2026-11-02. All 30 references cited in the chapter (none in `references.md` is uncited), checked
for bibliographic details and for whether each supports the sentence that cites it. Numbers are the
chapter's order of first citation.

## Checked against an online source in this session

| # | Reference | Details | Supports its claim |
|---|---|---|---|
| 2 | Rudd et al., Lancet 2020;395(10219):200–211 | Confirmed (doi 10.1016/S0140-6736(19)32989-7) | 48.9 M cases, 11.0 M deaths, 19.7% of deaths in 2017: yes |
| 3 | Seymour et al., NEJM 2017;376(23):2235–2244 | Confirmed (doi 10.1056/NEJMoa1703058) | Each hour to bundle completion associated with higher mortality: yes |
| 6 | Wong et al., JAMA Intern Med 2021;181(8):1065–1070 | Confirmed | AUROC 0.63 vs developer's 0.76–0.83; 67% of septic patients missed: yes |
| 11 | Angelopoulos et al., Ann Appl Stat 2025;19(2):1641–1662 | Confirmed (journal table of contents) | Learn-then-Test, multiple risks, fixed-sequence testing: yes |
| 13 | Reyna et al., Crit Care Med 2020;48(2):210–217 | Confirmed | Hidden third hospital; lower performance for algorithms that learned site habits: yes |
| 15 | Churpek et al., AJRCCM 2017;195(7):906–911 | Confirmed (doi 10.1164/rccm.201604-0854OC) | No score combined high sensitivity and specificity; NEWS/MEWS outperformed qSOFA: yes |
| 17 | Wong et al., JAMA Netw Open 2026;9(2):e260181 | Confirmed (doi 10.1001/jamanetworkopen.2026.0181; PMC12949446) | Four US health systems; institutional variability, low PPV, high alert burden; authors advise internal evaluation before deployment: yes. **Corrected**: "good discrimination overall" → "improved discrimination" (the paper's own wording) |
| 18 | Kamran et al., NEJM AI 2024;1(3) | Confirmed (doi 10.1056/AIoa2300032) | Performance falls when predictions after treatment starts are excluded: yes |
| 19 | Moor et al., eClinicalMedicine 2023;62:102124 | Confirmed (doi 10.1016/j.eclinm.2023.102124) | Three countries (US, Netherlands, Switzerland); AUROC 0.846 within site, 0.761 across sites, 0.807 after fine-tuning on 10%: yes |
| 23 | Shimodaira, J Stat Plan Inference 2000;90(2):227–244 | Confirmed (doi 10.1016/S0378-3758(00)00115-4) | Importance weighting under covariate shift: yes |
| 24 | FDA PCCP guidance for AI-enabled device software functions | Confirmed on fda.gov: final guidance (December 2024), page current as of 18 August 2025, docket FDA-2022-D-2628 | Pre-authorised modifications with methods and impact assessment: yes |
| 25 | Regulation (EU) 2024/1689 (AI Act) | High-risk status of AI that is, or is a safety component of, a medical device requiring third-party assessment (Art. 6(1)); Art. 43(4) | **Corrected**: Art. 43(4) applies to high-risk systems *that continue to learn after being placed on the market*; Section 2.5 now says so |
| 26 | Regulation (EU) 2026/1744 (Digital Omnibus on AI) | Published in the Official Journal 24 July 2026, in force 27 July 2026; Annex I high-risk obligations moved to 2 August 2028 (several independent summaries agree) | Yes |
| — | PhysioNet Challenge 2019 data licence | Creative Commons Attribution 4.0 International, on PhysioNet's dataset page | Data availability statement: yes |

## Standard references, details checked against the published record

Singer et al. JAMA 2016;315(8):801–810 (1); Finlayson et al. NEJM 2021;385(3):283–286 (4);
Subbaswamy and Saria, Biostatistics 2020;21(2):345–352 (5); Steyerberg, Clinical Prediction
Models, 2nd ed., Springer 2019 (7); Van Calster et al., BMC Med 2019;17:230 (8); Vergouwe et al.,
Stat Med 2017;36(28):4529–4539 (9); Riley et al., Stat Med 2021;40(19):4230–4251 (10); Bates et
al., J ACM 2021;68(6):43 (12); Royal College of Physicians, NEWS2, 2017 (14); Adams et al., Nat Med
2022;28:1455–1460 (16); Angelopoulos et al., Conformal Risk Control, ICLR 2024 (20); Saerens et al.,
Neural Comput 2002;14(1):21–41 (21); Lipton et al., ICML 2018, PMLR 80:3122–3130 (22); Goldberger
et al., Circulation 2000;101(23):e215–e220 (27); Ke et al., NeurIPS 30, 2017, pp. 3146–3154 (28);
Pollard et al., Sci Data 2018;5:180178 (29); Angelopoulos et al., Science 2023;382(6671):669–674
(30). Each is cited for what it is known for (definitions, updating hierarchy, calibration, closed
testing, sample size, risk-controlling sets, bedside scores, TREWS association, conformal risk
control, label shift, PhysioNet, LightGBM, eICU, prediction-powered inference).

## Decision on the EU AI Act citation

Keep the original regulation (2024/1689) with its amending regulation (2026/1744). The chapter
states the 2028 date from the amendment, so citing both is exact; a consolidated text is a
convenience version without legal force of its own.
