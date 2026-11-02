# Springer chapter: status and checks before submission

## Section status

| Section | Status |
|---|---|
| Front matter (title, authors, affiliation, e-mails, keywords) | Draft; confirm names and affiliation |
| Abstract | Final (2026-11-02), 290 words, figures verified |
| 1 Introduction | Final (2026-11-01), claims verified (`verification_introduction.md`) |
| 2 Background and Related Work | Final (2026-11-02), shared α/4 lemma reviewed (`verification_section2.md`) |
| 3 Materials and Methods | Final (2026-11-02); three review rounds plus cross-check corrections (`response_section3.md`, `audit_sections3_4.md`) |
| 4 Results | Final (2026-11-02); review response and cross-check (`response_section4.md`, `audit_sections3_4.md`) |
| 5 Application | Final (2026-11-02); review response (`response_section5.md`) |
| 6 Discussion | Final (2026-11-02); three review rounds (`response_section6.md`) |
| 7 Conclusion | Final (2026-11-02), reviewer score 9.5/10 |
| Back matter (competing interests, data and code availability) | Written 2026-11-02: no competing interests (confirmed by the authors), data, code and figure statements |

## Carried forward

- Section 3.5 must state the guarantee with: i.i.d. patient-level sampling (A1), counts of patients
  not alerts, threshold chosen from septic patients and false alerts tested on non-septic
  patients, the shared α/4 lemma for the imported model's two false-alert tests, separate fit and
  certification halves for the adapted model, and the union bound over four events. It must match
  Section 2.3's summary.
- Table numbers: Table 1 is in Section 2; the old chapter's Tables 1–8 become Tables 2–9.

## Before submission

- [ ] Recheck the regulatory facts against the official texts: FDA PCCP guidance (current
      version), EU AI Act Article 43(4) and post-market monitoring, Regulation (EU) 2026/1744 and
      the 2 August 2028 date for Annex I devices.
- [ ] EU AI Act: decide whether to cite the consolidated text in force at submission rather than Regulation (EU) 2024/1689 plus its 2026 amendment.
- [ ] Check every reference's metadata and URL, and that each citation supports its claim.
- [ ] Open the Word file in Word, check page count (at least 20), fonts, equations and figures;
      save the PDF from Word.
- [ ] Check the PDF's extracted text for technical names (Learn-then-Test, Distribution-Free,
      Risk-Controlling Prediction Sets).
- [ ] Abstract, Results, Discussion and Conclusion: a detection may come up to 3 h after onset; never imply every detection is a warning before onset.
- [ ] "Correct remedy" is an evaluation reference: say so wherever Section 4 reports it.
- [x] Data figures redrawn at Springer's 117 mm text width (`code/sepsis_figures.py --springer`, written to `outputs/sepsis/figures_springer/`); Fig. 1 redesigned for the narrow page.
- [ ] Final manuscript-wide pass: Abstract, Introduction, Discussion, Conclusion and limitations match the revised results (empirical vs theoretical, detections after onset, with-replacement simulations, correct remedy as reference).
- [x] Figs. 7 and 8 retaken in a 1,100-pixel window and cropped to their key panels (`scripts/app_screenshots.py --springer`); the gate's evidence table now wraps so every column shows.
- [ ] Commit the app wording change ("switch on" → "deploy", "proves" → "certifies", bound column headers) with the chapter.
- [ ] Keep three kinds of evidence distinct everywhere: the theoretical guarantee (theorem, under A1–A3), the certification decision (the exact tests on one local sample), and the retrospective evaluation (performance on patients excluded from the gate's decisions).
- [ ] Turnitin similarity below 18%.
- [ ] Tag a release (or note the commit) of the repository that produced the results, and cite it in Section 3.9.
- [x] Competing-interests statement from both authors (none).
- [ ] Name the final file after the corresponding author (sarkar.docx) with its PDF.
