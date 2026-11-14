# Why the GCI Diffusion method does not pass the release gate

**To:** Product manager / Methodology owner · **From:** Tech team · **Date:** 12 Nov 2026

Covers: *GCI Diffusion Index Methodology* (webpage draft) and *GCI FAQ*, both 12 Nov 2026,
read against the release gates in `docs/review/GCI_Core_Release_Checklist.md` and the
promotion gate G-09 in `docs/PLAN_GCI_CORE.md`.

## Summary

Diffusion cannot enter the release gate today: it is not a registered method, so the gate
check refuses it before any gate runs. If it were registered as written, it would still fail
on the method itself:

- It pays a company **+49.4 points** for setting guidance below its own expectation.
- It gives the same **50** to a company that lands within 0.5 points of guidance and one
  that misses by 3 points in each direction.
- On our data it ranks **Infosys above Cipla** (59.0 against 49.1), the opposite of their
  delivery records.

Separately, **every** candidate method, including GCI Core and GCI Range, is blocked today
by open citations, Cipla's confidence tier and four unsigned sign-offs. Fixing diffusion
alone would not publish anything.

No published level has moved.

## How the gate is run

`GET /api/v1/index/core/{company}/readiness` (`validation_gates.core_release_gates`) checks:

| Gate | Checks | Who |
|---|---|---|
| G-01 | Methodology version approved (owner plus one independent reviewer) | code + sign-off |
| G-02 | Same inputs give the same level; snapshot replays; golden tests pass | code |
| G-03 | At least 60% of figures compute; tier established or deep | code |
| G-04 | No row awaiting review or a guidance citation | code |
| G-05 | Security, backups, restore test | person |
| G-06 | Legal: terminology, disclaimers, data licences | person |
| G-07 | API documentation with a worked example per method | person |
| G-08 | Data-correction support process | person |

G-09 (promotion) then needs: gate 8 impact table reviewed, calibration CAL-R2-01 run,
counsel memo on terminology (D-13), two-person approval, and same-day ledger rows and
changelog entries for every level that moves.

## Part A — problems with the diffusion method

### A1. It cannot be submitted to the gate (G-01, G-02, gate 8)

- `core_release_gates("infy", ruleset="diffusion")` returns
  `ValueError: unknown GCI Core ruleset 'diffusion'`.
- Diffusion exists only in the Workbench Method lab, as a research method. The lab stores
  nothing, has no snapshot, no replay, no ledger row and no `algorithm_id`.
- Gate 8, the impact table the reviewer signs, compares v4, Core, Range, Delivery and the
  v2.5 proposals. Diffusion is not in it.

**Needed:** a complete specification (A5 below), then a shadow ruleset with its own id. The
name "v2.5" already belongs to the team's change-control proposals (GCI Draft).

### A2. It rewards guiding low (fails the calibration test in G-09)

Method lab checks: a growth figure with 5% true expected growth and a 1.5-point spread.

| Method | Points gained by guiding 4 points below expectation | Same mean for 2%/8% and 5.5%/4.5% on 4–6% guidance |
|---|---|---|
| Diffusion, as in the note | **+49.4** | **50 and 50** |
| Diffusion with metric direction and a 5-point growth floor (Guidance Bias) | **+37.7** | **50 and 50** |
| GCI Classic (published) | +0.4 | 49.2 and 100 |
| Range-P (12 Nov scan) | 0.0 | 75.0 and 100 |

- A company that sandbags scores higher than one that guides honestly. This holds even with
  the team's fixes applied, so it is the formula, not a parameter.
- In the 12 Nov scan of 400 simulated companies, diffusion's level correlates **−0.41** with
  true reliability. It ranks companies backwards.
- CAL-R2-01, approved by the owner, tests whether a high level this year predicts reliable
  delivery next year. On a signed scale both 0 and 100 are poor records, so the test cannot
  pass by construction.

The FAQ's "un-gameable" and "Management cannot game their credibility index" claims are
not supportable.

### A3. Beats and misses cancel, so the ranking inverts on real data

Closed rows in the packaged dataset, opening guidance, lab roll-up:

| Company | Record | GCI Classic | Diffusion (note) | Range-P |
|---|---|---|---|---|
| Infosys | Revenue missed FY24 by 2.6 points below the range; beat by up to 5.7 points in other years | 73.2 | **59.0** | 85.7 |
| Cipla | Margins inside or within 2 points of the range every year | 85.2 | **49.1** | 93.0 |

(All closed rows, including those still awaiting a guidance citation. Published-row levels
differ; the order does not.)

- Infosys FY22 (guided 12–14%, reported 19.7%) reads **75.8**, a good score. The guidance
  told investors little: the result was as far from it as a 5.7-point miss would have been.
- Infosys FY26 (guided 0–3%, reported 3.1%) reads **100**, the largest possible beat, for a
  0.1-point overshoot.

### A4. In-range results read as misses; scores bunch near 50

- Cipla FY25 R&D spend: guided 5–6%, reported 5.0%, inside the range. Reads **45.5**, below 50.
- Infosys FY24 operating margin: guided 20–22%, reported 20.7%, inside. Reads **49.3**.
- Cipla's six rows all fall between 45.5 and 55.7. A Screener sorted on this column
  separates companies by fractions of a point.
- The webpage's legend ("51.0 to 100.0 Beat", "0.0 to 49.0 Miss") leaves 49–51 undefined and
  labels these in-range results as misses.

### A5. The specification is incomplete (G-01 cannot be signed)

An independent reviewer cannot approve a method that is not fully written down. Open:

1. **Roll-up** from figure to metric to company.
2. **Penalties.** If the revision-frequency penalty and lead-time factor apply as in v2.4, an
   exact hit with three revisions scores 50 × 0.65 = **32.5** (reads as a miss) and an exact
   hit with the 1.1 lead-time factor scores **55** (reads as a beat). On a signed scale,
   "worse" is not a direction.
3. **Metric direction.** The note treats any result above the midpoint as a beat; a cost
   overrun would be tagged a beat. The catalogue already holds direction per metric.
4. **Growth floor.** The owner rejected amendment A1, which supplies it. Without it, a
   0.1-point overshoot on 0–3% guidance scores 100.
5. **Zero-midpoint fallback.** "The most recent non-zero observation" is undefined, and the
   sample code passes the zero midpoint into its own fallback.
6. **One-sided guidance** (floors and ceilings) under a signed scale.
7. **Worked examples.** G-02 requires golden tests. §24.1–§24.10 are v2.4 examples; diffusion
   has none.

### A6. The public copy conflicts with the published method (G-06, index integrity)

The live Methodology page says a result inside the range scores 100, beats floor at 60, and
"a wide range reaches 100 more easily than a tight one". The webpage draft says 50 is "met"
and that widening a range has "zero impact". Publishing it would describe today's levels
(Infosys 76.5, Cipla 65.5) as upside surprises, which they are not.

FAQ items that a legal or compliance reviewer would stop:

| FAQ text | Problem |
|---|---|
| "alpha factor alongside Quality, Momentum, and Value" | Investment-advice wording; banned on public surfaces |
| "Terminal Integrations (Bloomberg / LSEG / FactSet data feeds)" | Not built; competitor names barred from product copy |
| "proprietary weights … shared exclusively … under confidentiality" | The method and constants are public; a citable index must be recomputable |
| "institutional@citealpha.com" | Address not in use |
| "minimize cost of capital and reduce post-earnings stock volatility" | Outcome claim with no evidence |
| "Expansion / Contraction", PMI and ISM framing | Terminology memo (D-13) still open with counsel |
| "Historical time-series datasets are fully point-in-time compliant" | History is citeable point-in-time only with at least four reviewed as-of dates; other companies return a short or incomplete series |

The corrected FAQ is live on `/answers`. The webpage draft is not published.

### A7. Switching the headline moves every published level (G-09)

Every published level would change, and the scale would change meaning: 76.5 today means
"close to fully delivered"; under diffusion, 76.5 would mean "a large beat". Each licensee
and each company page would need re-explaining. The ledger and changelog rows are
mechanical; the re-explanation is not.

## Part B — problems that block any method today

Readiness run on 12 Nov 2026 (default ruleset `v2.4` and `v2.4-R2`; same result for both):

| Gate | Infosys | Cipla | What clears it |
|---|---|---|---|
| G-01 Methodology approved | fail | fail | Owner ruling on the headline method, plus an independent reviewer |
| G-02 Replay | pass | pass | — |
| G-03 Coverage and tier | pass (deep) | **fail (provisional)** | More closed Cipla periods and metrics with dual citations |
| G-04 Rows reviewed and cited | **fail: 1 row awaiting guidance citation** | **fail: 5 rows awaiting guidance citation** | Guidance quotes bound by the daily guidance review |
| G-05 Security | not signed | not signed | Backups and restore test (go-live B8) |
| G-06 Legal | not signed | not signed | Counsel memo D-13; FAQ and companion wording approved |
| G-07 API docs | not signed | not signed | Worked example per method in the API map |
| G-08 Support | not signed | not signed | Named contact and response time for corrections |

## What would let a direction reading ship now

The owner's goal, seeing at once whether a company beat or missed, does not need the
headline to change:

- **Guidance Bias** (built 12 Nov, Workbench preview): the 50-centred reading with metric
  direction and a 5-point growth floor, and a beat / in line / miss tag on every figure.
  Infosys reads 55.1 (4 beat, 1 in line, 1 missed). It is not ranked and not part of the GCI.
- To show it publicly next to the GCI it needs only G-06 wording approval. It never moves a
  published level, so it needs no ledger row.

## Decisions we need from the PM

1. **Headline.** Keep an accuracy level (GCI Classic now; GCI Range or Range-P after
   calibration) with Guidance Bias beside it. Or, to keep diffusion as the headline, supply
   items 1–7 in A5. We will then register it as a shadow ruleset with its own id, add it to
   gate 8, and report A2–A4 again on the full specification.
2. **Public wording.** Approve the Guidance Bias description for G-06, or keep it
   Workbench-only.
3. **Data gates.** Prioritise the six open guidance citations (G-04) and Cipla coverage
   (G-03). These block any method.
4. **Sign-off owners** for G-05 to G-08.

## How to check

- Gate run: `GET /api/v1/index/core/infy/readiness?ruleset=v2.4` (and `cipla`).
- Diffusion behaviour: Analyst Workbench → Method lab → Diffusion, presets *As in the owner's
  note* and *Guidance Bias*; or `POST /api/v1/index/lab/run`.
- Guidance Bias: `GET /api/v1/index/companions/infy`.
- Earlier replies: `GCI_v2.5_Diffusion_Reply_11_Nov_2026.md`,
  `GCI_Best_Algorithm_and_Market_Scan_12_Nov_2026.md`.
