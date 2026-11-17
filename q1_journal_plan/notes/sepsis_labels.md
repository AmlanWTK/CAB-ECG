# Sepsis-3 labels from MIMIC-IV and eICU (WP1)

Draft, 2026-10-30. Shared rules in `code/sepsis3.py` (Challenge 2019 style); extractors in
`code/mimiciv_sepsis.py` (done for MIMIC-IV) and an eICU extractor (to do).

## Rules (Challenge 2019, checked against Reyna et al., Crit Care Med 2020;48:210-217, Methods)

- Suspected infection: blood culture and IV antibiotics given for at least 72 consecutive hours.
  Culture first: antibiotic within 72 h. Antibiotic first: culture within 24 h. Time = the earlier.
- SOFA rise: 2 or more within a 24-hour period (above the lowest SOFA in the previous 24 h).
- Onset: earlier of suspicion and SOFA rise, with the rise no more than 24 h before or 12 h after
  suspicion. SepsisLabel = 1 from 6 h before onset.
- Cohort: at least 8 hourly windows; onset less than 4 h after ICU admission excluded; truncated
  at 2 weeks.

Fixed on 2026-10-30. The first version of `sepsis3.py` had the pairing windows reversed (culture
first: antibiotic within 24 h), used Seymour et al.'s 48/24 h window and a rise against the lowest
SOFA in the whole stay, and had no cohort rules. The first demo run used that version: 31% septic,
median onset 1.6 h, 50% of hours labelled.

## MIMIC-IV extraction choices

- Cultures: specimens with "BLOOD CULTURE" in the type; charttime, else chartdate.
- Antibiotics: IV prescriptions (route starting "IV") with a systemic antibacterial in the drug
  name (list in the code). Overlapping prescriptions, or ones less than 24 h apart, form one course;
  only courses of at least 72 h count; time = course start. The 24 h gap allowance is our choice
  (the Challenge does not say how "consecutive" was judged).
- PaO2/FiO2: arterial pO2 with the latest FiO2 in the previous 4 h; ventilation from
  procedureevents 225792.
- GCS: eye + verbal + motor charted together; not scored when verbal is "No Response-ETT".
- MAP: lowest of 220052, 220181, 225312 in the hour. Vasopressors in mcg/kg/min.
- Urine: 24 h sum from hour 23. Events up to 24 h before ICU admission count towards hour 0.

## Check on the open demo (MIMIC-IV demo v2.2: 100 patients, 140 ICU stays)

- Suspected infection in 25 stays (18%); Sepsis-3 before cohort rules in 12.
- Excluded: 7 with onset under 4 h, 4 with under 8 h of data. Cohort: 129 stays.
- Septic: 5 of 129 (4%); median onset 21 h after admission (IQR 4-118). SepsisLabel = 1 in 5.8% of
  hours. The same order as the Challenge data, but five septic stays are too few to judge more
  closely; the full database will.
- Hours with each SOFA component measured: cardio 94%, renal 76%, CNS 16%, coag 7%, resp 4%,
  liver 3% (labs are daily; the 24 h rolling worst fills the gaps).

## Open questions before the full databases

1. How "72 consecutive hours" of antibiotics was judged in the Challenge (gap allowance).
2. GCS under sedation and intubation: not scored here (counts as normal in SOFA). Compare with
   mimic-code's SOFA concept once full access is available.
3. Check the septic share on full MIMIC-IV against the Challenge's per-system shares
   (Supplemental Table 1 of Reyna et al.).

## eICU (demo v2.0.1: 2,520 stays, 186 hospitals), 2026-10-30

`code/eicu_sepsis.py`; same shared rules and scoring as MIMIC-IV (`sepsis3.score_and_label`).

- Under the Challenge rules, only 9 of 2,520 stays have suspected infection (0.4%) and none is
  septic after the cohort rules. Cultures and antibiotics are recorded unevenly: microLab is filled
  at 12 of 186 hospitals; adding culture orders from the treatment table gives blood cultures in 130
  stays; IV antibiotic courses of at least 72 h are found in 141 stays, and the two rarely coincide.
  Only 107 hospitals record any antibiotic in medication, 101 any culture.
- Relaxing the rules (suspected infection in stays):

  | Rules | Stays |
  |---|---|
  | Challenge (blood culture, IV antibiotic >= 72 h) | 9 (0.4%) |
  | any culture site | 20 (0.8%) |
  | no 72 h antibiotic rule | 24 (1.0%) |
  | both | 49 (1.9%) |
  | both, plus antibiotics from the treatment table | 209 (8.3%) |

  MIMIC-IV demo under the Challenge rules: 25 of 140 (18%).
- Decision needed for WP3: in eICU, labels under any rule depend on how well each hospital records
  cultures and antibiotics. Options: one relaxed definition for both databases with a
  data-completeness filter on eICU hospitals (Challenge rules as a sensitivity analysis on
  MIMIC-IV), or Challenge rules on MIMIC-IV only with eICU on a separate definition.

## Decision (2026-10-30): one relaxed definition for both databases

Primary labels for the transfer study use the "relaxed" suspected-infection rule in both
databases: any non-screening culture and any systemic antibiotic order (in eICU also culture and
antibacterial entries in the treatment table), with no minimum antibiotic duration. The SOFA rise,
onset window, 6 h label lead and cohort rules stay exactly as in the Challenge. The Challenge's own
rule (blood culture, IV antibiotic course >= 72 h) is run on MIMIC-IV as a sensitivity analysis.
Reason: in eICU, recording of cultures and antibiotics differs by hospital, so labels must not
depend on the strictest recording, and the same rule must hold at every hospital.

eICU hospital recording check (provisional, to be fixed in the analysis plan before the full run):
a hospital is kept if antibiotics are recorded in at least 20% of its stays and cultures in at
least 10%. These are recording rates, not outcomes.

Demo results (`--definition relaxed` / `challenge`):

| | MIMIC-IV relaxed | MIMIC-IV challenge | eICU relaxed, adequate hospitals | eICU challenge, all |
|---|---|---|---|---|
| Suspected infection | 72 of 140 (51%) | 25 of 140 (18%) | 170 of 736 (23%) | 9 of 2,520 (0.4%) |
| Excluded (onset < 4 h / < 8 h of data) | 22 / 4 | 7 / 4 | 33 / 38 | 3 / 238 |
| Cohort, septic | 114, 8 (7.0%) | 129, 5 (3.9%) | 665, 16 (2.4%) | 2,279, 0 |
| Onset, median (IQR) h | 6.7 (5.0-14.8) | 21 (4-118) | 13.2 (10.0-23.5) | - |
| Hours with SepsisLabel = 1 | 16.7% | 5.8% | 5.1% | 0% |

- 60 of 186 eICU demo hospitals pass the recording check (736 stays). In the demo each hospital has
  only about 14 stays, so the check is noisy there; on the full database it will rest on hundreds
  of stays per hospital.
- eICU's septic share is lower than MIMIC-IV's under the same rule (2.4% vs 7.0%). Possible reasons:
  sparser SOFA inputs in eICU (PaO2 2%, bilirubin 3%, GCS 15% of hours) or case mix. To check on the
  full data: SOFA component coverage by hospital, and whether a coverage requirement belongs in the
  recording check.
- The onset-under-4-h rule excludes many septic stays (22 of 30 in MIMIC-IV, 33 of 51 in eICU),
  as in the Challenge: early-warning models are for sepsis that develops in the ICU.

## Full MIMIC-IV v3.1, first extraction (2026-11-17)

Run on the remote PC; aggregate output only (PhysioNet data use agreement).

| | Challenge definition |
|---|---|
| ICU stays | 94,458; 14 dropped (no admission or discharge time, new in v3.1), 94,444 used |
| Suspected infection | 14,951 (16%) |
| Sepsis-3 before cohort rules | 7,357; onset hour median 2.0 |
| Excluded (onset < 4 h / < 8 h of data) | 4,497 / 1,539 |
| Cohort, septic | 88,408, 2,857 (3.2%); onset median 33.0 h (IQR 8.2-103.7) |
| SOFA component coverage (hours) | resp 4%, coag 7%, liver 2%, cardio 89%, cns 19%, renal 74% |
| Hours with SepsisLabel = 1 | 7.2% |

**Check 1 fails**: 3.2% septic against the range of 5-13% fixed in advance (`label_check.md`).
Following the rule there, the extraction is investigated before anything else is run, and the
range is not changed. First diagnostics: `code/label_diagnostics.py` on the per-stay tables
(timing of suspected infection, suspected infection without a SOFA rise, what sets early onsets).
Cause and fix to be recorded here.

**Diagnostics, round 1** (`label_diagnostics.py`, Challenge definition):

- Our rules match the Challenge paper's text (Reyna et al. 2020, PMC6964870): stays with fewer than
  8 hourly windows and stays with onset less than 4 h after ICU admission are not included;
  truncation at 2 weeks; suspicion and SOFA windows as coded. So the shortfall is not a rule error.
- Before the cohort rules, 7.9% of stays of 8 h or more meet Sepsis-3 (7,354 of 92,905), inside the
  5-13% range. The cohort rule removes 4,500 of them (61%) for onset under 4 h: 2,682 because
  suspected infection (cultures and antibiotics) came before or soon after ICU admission, 1,818
  because the SOFA rise did.
- Suspected infection is often before ICU admission: 11.3% more than 24 h before, 18.4% in the
  24 h before, 36.4% in the first 4 h.
- Half of suspected infections (7,594 of 14,951) have no qualifying SOFA rise, although 56% of
  those reach a SOFA of 6 or more. A rise must fall from 24 h before to 12 h after suspicion, and
  SOFA exists only from ICU admission (earlier values are folded into hour 0), so a suspicion
  more than 12 h before admission can never be followed by a rise, and a patient whose organ
  dysfunction is already present on arrival shows none. These stays stay in the cohort as
  non-septic; under the Challenge's intent they would be septic before the ICU and excluded.

Open questions: whether the Challenge took cultures and antibiotics from before ICU admission
(the paper does not say), and whether hospital A's cohort differs in unit mix or period.
Round 2 adds the septic share by first ICU unit and by MIMIC-IV anchor year group (`--root`).

**Diagnostics, round 2** (2026-11-17):

- Unit mix does not explain it. Every large unit is below 5%: MICU 3.3% (18,548 stays), SICU 3.7%,
  TSICU 4.1%, CCU 2.8%, MICU/SICU 2.5%, CVICU 2.0% (14,420 stays). Only the Neuro SICU (7.2%) and a
  small intermediate unit reach the range.
- Period does not explain it either. The septic share rises over time, from 2.8% in 2008-2010 (the
  years closest to the Challenge's hospital A) to 4.3% in 2020-2022.
- Compared with the open Challenge data (computed here from `outputs/sepsis/rows.pkl`), **the onset
  timing matches**. Hospital A's onset median is 34.5 h (IQR 13-78) against our 33.0 h (8.2-103.7).
  Neither has onsets under 4 h. 20% of A's stays are shorter than 24 h, against 18% of ours. Only
  the rate differs: 8.8% at A against 3.2% here.
- **New finding: the Challenge truncates septic stays.** In A and B, every septic stay ends 8 to
  10 hours after its first SepsisLabel = 1 (median 10), that is, at about onset + 3 h. So 2.2% of
  A's hours are labelled, against 7.2% in our MIMIC-IV table, which runs to discharge. This does
  not change the septic share. But the Challenge-format export (WP2) must truncate septic stays at
  onset + 3 h, or the hourly prevalence and the evaluation differ from the chapter's. To fix in
  `challenge_format.py` before WP3.

Next: the relaxed definition, to see whether the strict suspicion rule is the bottleneck
(blood cultures plus IV antibiotic courses of 72 h or more taken from prescription orders).

**Relaxed definition, full MIMIC-IV** (2026-11-17):

| | Challenge definition | Relaxed definition |
|---|---|---|
| Suspected infection | 14,951 (15.8%) | 42,853 (45.4%) |
| Sepsis-3 before cohort rules | 7,357 (7.8%) | 16,769 (17.8%) |
| Excluded (onset < 4 h / < 8 h) | 4,497 / 1,539 | 11,319 / 1,539 |
| Cohort, septic | 88,408, 2,857 (3.2%) | 81,586, 5,439 (6.7%) |
| Onset median (IQR), h | 33.0 (8.2-103.7) | 16.0 (6.2-46.0) |
| Hours with SepsisLabel = 1 | 7.2% | 13.5% |

- Check 2, first part, **passes**: the relaxed share (6.7%) is at least the Challenge share (3.2%).
- Check 2, second part, **fails**: only 2,017 of the 2,857 stays septic under the Challenge definition
  (70.6%) are septic under the relaxed one, against at least 80%. A likely mechanism is the "first
  pair" rule. Under the relaxed definition, an earlier culture-antibiotic pair (any culture, any
  order) can move suspicion earlier. That either puts onset under 4 h (excluded) or moves the SOFA
  window away from the rise. Not yet verified.
- Suspected infection is 45% under the relaxed definition, the same as Moor et al.'s 45% on
  MIMIC-III, against 16% under the Challenge definition. So most of the difference lies in the
  strict suspicion rule: blood cultures only, and IV courses of at least 72 h built from
  prescription orders. The Challenge counted antibiotics *administered* for 72 consecutive hours.
  MIMIC-IV records administrations in `hosp/emar`, which we do not use yet.
- Not yet run: check 4's onset-concentration part, check 5 (`challenge_b.py` inputs against
  hospital A), and eICU (check 3).

**Diagnostics, round 3** (built 2026-11-17, to run on the full data):

- `label_diagnostics.py` with both per-stay tables now breaks down the stays that are septic under
  the Challenge definition but not under the relaxed one: excluded for early onset, excluded as
  short, no suspicion, or suspicion without a SOFA rise. It also reports whether relaxed suspicion
  came earlier (the "first pair" mechanism).
- `abx_diagnostics.py --root <MIMIC-IV>` compares 72-h IV antibiotic courses built from orders
  (`prescriptions`, as the extractor does now) with courses built from recorded doses (`emar`).
  It counts only doses given, IV by the route of the linked prescription, with the same 24-h
  joining rule. `emar` does not cover every admission, so the comparison is limited to admissions
  with any `emar` record.
- On the demo (too small to judge), `emar` covers 37 of 57 blood-culture admissions. Within them,
  administrations give **fewer** 72-h courses than orders (18 against 26), not more. If the full
  data agree, order-based courses do not undercount the Challenge's rule, and the antibiotic
  source does not explain check 1.

**Round 3 results, full MIMIC-IV** (2026-11-17):

- **Antibiotic source: ruled out.** `emar` covers 21,467 of 35,947 blood-culture ICU admissions
  (59.7%). Within those, orders give a 72-h IV course in 64.9% and administrations in 47.1%.
  Almost every administration course is also an order course (10,117 both, 3,807 orders only,
  fewer than 10 administrations only). Suspected infection falls from 16.2% to 11.5% with
  administrations, and where both find it the timing agrees (median difference 0.0 h). So
  administrations would *lower* the septic share. The order-based courses stay, and
  administration-based courses are a possible sensitivity analysis.
- **Overlap failure (check 2): explained, and it exposes an extraction choice.** All 840
  Challenge-septic stays that are not septic under the relaxed definition have an *earlier*
  relaxed suspicion (median 75.8 h earlier). 389 then fall under the 4-h exclusion, and for 451
  the SOFA window (24 h before to 12 h after suspicion) no longer covers the rise. The cause is
  our rule that only the **first** culture-antibiotic pair of a stay counts. An earlier, unrelated
  suspicion, often days before the ICU, then hides a later episode that does meet Sepsis-3. The
  same rule affects the Challenge definition: suspicion more than 12 h before ICU admission can
  never be followed by a rise we can see.
- Proposed fix, written down before running it: evaluate every suspicion episode (every
  qualifying culture-antibiotic pair) and set onset from the earliest episode with a qualifying
  SOFA rise, keeping all other rules and every threshold. The Challenge paper's text ("clinical
  suspicion of infection identified as the earlier timestamp of IV antibiotics and blood
  cultures") does not say "first pair only". The result is reported whatever it is, against the
  same ranges.

**Implemented 2026-11-17** (`sepsis3.py`, both extractors):

- `suspicion_episodes` returns every qualifying culture-antibiotic pair time per stay. `onset_times`
  finds, for each episode, the first SOFA rise from 24 h before to 12 h after it (one
  `merge_asof`), and the earliest episode with a rise sets the onset. Both extractors take
  `--episodes all` (default) or `--episodes first` (the earlier rule). The per-stay table keeps
  `t_suspicion` (the first episode) and adds `t_suspicion_used` (the episode that set the onset).
- Checks: with `--episodes first`, all four demo runs (MIMIC-IV and eICU, both definitions)
  reproduce the earlier per-stay labels exactly. Synthetic cases behave as intended. An episode
  40 h before admission plus one at hour 20 with a rise at hour 22 gives onset 20 (first-only: not
  septic). A rise 8 h before suspicion is kept, and a rise 17 h after suspicion is not.
- Demo results with every episode (orientation only): MIMIC-IV Challenge definition 7 of 128
  (5.5%, was 3.9%), relaxed 14 of 109 (12.8%, was 7.0%); eICU hospitals passing the recording
  check, relaxed, 49 of 663 (7.4%, was 2.4%). In the MIMIC-IV relaxed demo, a later episode set
  the onset in 11 of 41 Sepsis-3 stays.

**Full MIMIC-IV with every episode** (2026-11-17):

| | Challenge, first episode | Challenge, every episode | Relaxed, first episode | Relaxed, every episode |
|---|---|---|---|---|
| Sepsis-3 before cohort rules | 7,357 (7.8%) | 8,059 (8.5%) | 16,769 (17.8%) | 25,348 (26.8%) |
| Onset set by a later episode | - | 702 | - | 8,579 |
| Excluded, onset < 4 h | 4,497 | 4,707 | 11,319 | 14,655 |
| Cohort, septic | 88,408, 2,857 (3.2%) | 88,198, 3,349 (3.8%) | 81,586, 5,439 (6.7%) | 78,250, 10,675 (13.6%) |
| Onset median (IQR), h | 33.0 (8.2-103.7) | 40.0 (9.9-119.0) | 16.0 (6.2-46.0) | 20.0 (9.0-49.0) |

Checks against the ranges fixed on 2026-10-31 (every-episode rule):

1. Challenge definition within 5-13%: **fails**, 3.8%. The causes investigated were unit mix,
   period, antibiotic source (orders against administrations) and the first-episode rule. Only
   the last was an extraction issue, and fixing it raised the share from 3.2% to 3.8%. Per
   `label_check.md`, this is reported as it stands. It does not affect the main analysis, which
   uses the relaxed definition (decided 2026-10-30). The Challenge definition is the
   sensitivity analysis.
2. Relaxed at least the Challenge share (13.6% against 3.8%): **passes**. At least 80% of
   Challenge-septic stays also septic under relaxed: **passes**, 84.2% (2,820 of 3,349; was
   70.6%). All 529 that are not were excluded under relaxed for onset under 4 h, because an
   earlier relaxed suspicion (median 64 h earlier) set the onset.
3. eICU: not yet run.
4. SOFA coverage close to the demo: passes. Onsets are not concentrated at the earliest allowed
   hour (Challenge definition: onset median 40 h; relaxed: 20 h, IQR 9-49).
5. Inputs against hospital A (`challenge_b.py`): not yet run on the full data. The script still
   reads the demo tables and needs the Challenge files on the remote PC.

The every-episode rule was adopted after checks 1 and 2 had failed, for the reason recorded above
(an earlier, unrelated suspicion hid later episodes). The first-episode results are kept in this
table, and the paper reports both.

The relaxed definition labels 13.6% of cohort stays septic, and 27.2% of hours because stays are
not truncated after onset. Before WP3, the Challenge-format export must truncate septic stays at
onset + 3 h, as the Challenge does (round 2 finding).

**Septic stays end at onset + 3 h** (2026-11-17). `sepsis3.challenge_cohort` now drops the hours
after onset + 3 h (`AFTER_ONSET = 3`), so the hourly table and the Challenge-format export end
where the Challenge files do. Patient-level counts (cohort, septic share) do not change. On the
MIMIC-IV demo (Challenge definition), the 7 septic stays now have 8, 8, 8, 9, 10, 10 and 10
labelled hours, the same 8-10 as sets A and B, and labelled hours fall from 5.8% to 0.7%. The
full tables must be re-extracted (from cache) to apply this.

**Check 5 on the full data.** `challenge_b.py` now takes `--mimic <pkl> --no-eicu --no-dry-run
--name full` and writes `B_harmonisation_full.md`. The output is aggregate (share measured and
quartiles per variable). It needs the open Challenge files on the remote PC
(`scripts/download_sepsis2019.py`, about 42 MB, CC BY 4.0). The model dry run is skipped on the
full data, because it would train a model and so belongs to WP3.
