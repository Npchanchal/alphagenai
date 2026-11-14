# Response to the GCI v2.4 rulings (Corrective Action Plan v1.1)

**To:** Product owner / Methodology owner · **From:** Tech team · **Date:** 10 Nov 2026

## Summary

We accept the rulings and have implemented locked v2.4 as written. That covers the
Qual branch, the 80/20 Composite, the lead-time modifier, the four PRD defect fixes and
golden tests for every worked example (§24.1–§24.10). Our formula reworks are now
v2.5 proposals. They run only on request, for impact analysis.

Before the first publication we ask the owner to look again at **four items**. Each is
backed by our own data. We are not re-opening the rest. A rule changed after launch
moves every published level, needs a ledger row and a public changelog entry, and has
to be re-explained to every licensee. The same change costs nothing today.

## What is built (shadow; no published level moves)

- **Locked v2.4 default.** Percentages scored as stated; range reference `(|L|+|U|)/2`;
  symmetric bounds; zero amount against one presentation unit; numerical revision
  sign; frequency penalty on every revision inside the target period; lead-time
  factor; equal weights; `C_f = min(100, D_f × (1 − P_f) × L_f)`.
- **Qual branch** from reviewed commitments. A commitment fulfilled by its deadline
  scores 1. An outcome with no evidence yet widens the range; it is never scored zero.
- **Composite** = 0.8 Quant + 0.2 Qual. With one branch, the composite equals that
  branch and is labelled.
- **Erratum §24.10 reproduces exactly:** D_f 84.7492, C_f 67.7993, when the revision is
  issued 11/12 of the horizon after the original. Please confirm that was the setting.
- **Impact table (gate 8).** Published v4 level, Core v2.4 and the v2.5 proposals, side by side.

| Company | Published (v4) | Core v2.4 (locked) | v2.5 proposals |
|---|---|---|---|
| Infosys | 76.5 | 70.8 | 93.0 |
| Cipla | 65.5 | 80.4 | 91.3 |

## The four asks

### 1. Do not penalise routine guidance updates (frequency penalty, D-05/D-06)

**What the data shows.**
- Infosys updates its annual revenue guidance every quarter, as Indian IT majors do.
  Locked v2.4 takes 35% off each year for three revisions.
- Infosys revenue guidance therefore scores **41.7**. FY25 (guided 1–3%, raised to
  4.5–5%, reported 4.2%) scores 34.3. FY26 (guided 0–3%, raised to 3–3.5%, reported 3.1%)
  scores 26.7.
- Three in-year updates cap a guidance line at 71.5, even when every figure is delivered exactly.
- In a simple test, an honest raise that is then delivered scores **77.8**. Staying
  silent and missing scores **88.0**. Cipla raised its margin guidance once, beat both
  figures, and loses 20%.

**Why it matters.**
- **GCI basic nature:** the index measures whether management delivers what it
  promised. How often it talks to the market is a different thing.
- **Customer usability:** a desk that knows Infosys as a reliable guider will not trust
  a 41.7. An IR officer will ask why updating the market cost points.
- **Practice:** SEBI LODR Regulation 30 pushes companies to disclose material changes
  promptly. Japan's exchange makes companies revise forecasts when revenue is off by
  10% or profit by 30%. The rule penalises disclosure that regulators require, and US
  quarterly updates will be hit harder still.
- **Cost:** none to change now. After launch, every Indian IT score moves.

**Ask.** Choose one before publication:
- (a) count only revisions toward a weaker figure (v2.5 D-05/D-06); or
- (b) at minimum, do not count a revision that narrows the range inside the previous range.

### 2. Range reference for ranges that touch zero (D-03)

**What the data shows.** Infosys, one of our two published companies, guided 0–3% for
FY26 and reported 3.1%. Under v2.4 the opening guidance scores **0**, because the
reference for a 0–3 range is 1.5 and the result is 1.6 away from the midpoint.

**Why it matters.**
- **Customer usability:** "reported just above the top of guidance, scored zero"
  cannot be defended to a journalist or an IR officer.
- **GCI basic nature:** a result inside or at the edge of the range should score close to full credit.
- **Cost:** low. 3 of 155 closed rows move. Worked examples §24.1 and §24.2 are
  unchanged; §24.3 moves from 99.1009 to 99.5504.

**Ask.** Adopt reference = max(|midpoint|, range width) before publication.

### 3. Lead-time factor: run it in shadow for one results season, or cap it at 1.0 (D-07)

**What the data shows.** Every closed row with a guidance date (7 of 7) earns **1.1**.
Indian companies give annual guidance in April, so the factor is a flat +10% that tells
a desk nothing.

**Why it matters.**
- **Practice:** Indian filings carry a date, not a time. NSE and BSE dissemination
  times differ, and board meetings often end after market hours. A one-day shift
  across the 30-, 90- or 180-day line moves a score by 10%.
- **GCI basic nature (comparability):** quarterly guidance has less than 90 days of
  lead time, so a US quarterly guider usually gets 0.9. An Indian annual guider gets
  1.1. The same delivery record differs by 22% between markets.
- **Customer usability:** "10% lower because guidance came 29 days before period end,
  not 31" is a hard conversation with an issuer.
- **Cost:** none. The factor is built and can be switched on after one season of evidence.

**Ask.** Keep the factor computed and shown, but publish with it capped at 1.0 until
one results season shows it separates good guiders from weak ones.

### 4. Composite as the headline: sequence it after calibration (D-09/D-11)

The Qual branch is built, as ruled. The question is only whether the 80/20 Composite
is the published headline from day one.

**What the data shows.** The packaged dataset holds **0** reviewed commitments today.

**Why it matters.**
- **Practice, and the exchange filing process:** in India, qualitative promises sit
  mostly in earnings-call transcripts (filed only since 2021–22), investor
  presentations and press releases. No structured or XBRL field exists for a
  commitment. Proof of completion (a plant commissioned, debt cut to a stated level)
  is often never filed at all. Making this routine would need a change in how
  companies file with the exchanges, which we do not control.
- **Cost:** every commitment needs a reviewer to split it into components, set
  weights, define the acceptance test and judge the evidence, every season. There is
  no automation path today, and labelling capacity is already the constraint on Quant
  coverage.
- **Customer usability:** a company with commitments gets a blend; one without gets
  pure Quant. Two companies with the same delivery record are not comparable. While
  any commitment is unresolved, the headline becomes a range.
- **GCI basic nature:** the Quant branch compares a published figure with a reported
  figure. The Qual branch rests on reviewer judgement. Putting judgement into the
  headline moves the product toward a rating, which is the open counsel question
  (D-13). The 80/20 weight itself is uncalibrated, as the ruling notes.

**Ask.** Show Qual beside Quant and compute the Composite, but keep Quant as the
published headline until the weights are calibrated and enough companies carry
reviewed commitments.

## What we are not asking

D-01 (beaten bound), D-04 (zero amount), D-08 (counting window), D-10 (weights) and
D-31 (revision sign) have little effect on today's India data. They stay logged as v2.5
proposals.

We are **withdrawing D-02 as built.** Scoring growth on the implied level is too
lenient: Infosys FY24 (guided 4–7%, reported 1.4%) scores 96.1 on its opening guidance,
which hides a clear miss. Low-growth guidance still needs work, because v2.4 scores a
beat of 1–3% guidance with 4.2% at 0. We will bring a percentage-point-based proposal
with an impact analysis under change control.

## Interpretations to confirm

v2.4 leaves these open. We implemented the reading on the left.

| Point | Implemented |
|---|---|
| Family-level effective lead time | Lead time of the opening (earliest eligible) guidance |
| Half-year guidance frequency curve | Annual curve |
| Quarterly penalty beyond 2 revisions | +8 points per revision, as the annual table implies |
| Revisions issued after period end | No weight; outside the counting window |
| Opening guidance issued after period end | Not scored (`GUIDANCE_AFTER_PERIOD_END`) |
| §24.10 elapsed time | 11/12 of the horizon |

## How to check

- Reviewer API: `/api/v1/index/core/{company}` (locked) and
  `/api/v1/index/core/{company}?ruleset=v2.5-proposal`.
- Gate 8 table: `/api/v1/index/core`.
- Workbook: `docs/review/CiteAlpha_GCI_PRD_v2.4_Requirement_Review_09_Nov_2026.xlsx`,
  sheet *PM Actions* (status counts and the v2.5 backlog with evidence).
