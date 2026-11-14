# Response to the GCI v2.5 Diffusion note and the PRD resolutions

**To:** Product owner / Methodology owner · **From:** Tech team · **Date:** 11 Nov 2026

Replies to: *Comprehensive Alignment Note: GCI v2.5 (Diffusion Architecture)* and
*PRD: Resolution of Tech Team Queries & Red Flags for GCI v2.5*, both 11 Nov 2026.

## Summary

We accept the goal: a reader should see at once whether a company beat or missed its
guidance. We accept the rulings on A3, A4 and A5, and CAL-R2-01. They confirm what is
already built in the `v2.4-R2` shadow ruleset.

We ask the owner not to make the 50-centred diffusion score the GCI headline. It
measures direction, not delivery. On our own data it ranks the less reliable guider
above the more reliable one, and it scores Infosys's 0.1-point overshoot of its
FY26 range as the largest possible beat.

We propose the same transparency without that cost:

- The headline stays an accuracy level, where higher means more reliable delivery.
- Each figure carries a *beat / in line / miss* tag.
- The signed 50-centred deviation is published beside the headline as a companion
  **Guidance Bias** index. That is what a PMI-style reading measures, and the PMI
  analogy fits it there.

Nothing is built yet. No published level moves.

## What the diffusion score does to our data

Opening guidance on every closed, dual-cited row in the packaged dataset:

| Company, figure | Guided | Reported | v2.4 | Diffusion |
|---|---|---|---|---|
| Infosys FY22 revenue growth (cc) | 12–14% | 19.7% | 48.5 | 75.8 |
| Infosys FY23 revenue growth (cc) | 13–15% | 15.4% | 90.0 | 55.0 |
| Infosys FY24 revenue growth (cc) | 4–7% | 1.4% | 25.5 | 12.7 |
| Infosys FY24 operating margin | 20–22% | 20.7% | 98.6 | 49.3 |
| Infosys FY25 revenue growth (cc) | 1–3% | 4.2% | 0 | **100** |
| Infosys FY25 operating margin | 20–22% | 21.1% | 99.5 | 50.2 |
| Infosys FY26 revenue growth (cc) | 0–3% | 3.1% | 0 | **100** |
| Cipla FY23 EBITDA margin | 21.5–22.5% | 22.1% | 99.5 | 50.2 |
| Cipla FY24 EBITDA margin | 21.5–22.5% | 24.5% | 88.6 | 55.7 |
| Cipla FY25 EBITDA margin | 24.5–25.5% | 25.9% | 96.4 | 51.8 |
| Cipla FY25 R&D spend (% of revenue) | 5–6% | 5.0% | 90.9 | 45.5 |

The simple mean of row scores is 63.3 for Infosys and 51.1 for Cipla. Today's levels,
for comparison:

| Company | Published (v4) | Core v2.4 | GCI Range (v2.4-R2 with A1–A5) |
|---|---|---|---|
| Infosys | 76.5 | 70.8 | 87.6 |
| Cipla | 65.5 | 80.4 | 93.8 |

## Why the diffusion score cannot be the headline

### 1. Beats and misses cancel

The note does not say how row scores combine into a company level. Any average of a
signed score lets a beat offset a miss.

- A company that misses by 40% one year and beats by 40% the next averages exactly
  **50**. The note reads 50 as "surgical precision".
- Infosys reported FY24 revenue growth 2.6 points below the floor of its range and
  finished above the range in the other four years. It averages 63.3. Cipla lands
  inside or close above its range every year and averages 51.1.
- Ranked by diffusion, the erratic record sits above the steady one. The GCI promises
  the opposite: management that delivers what it said ranks higher.

PMI and ISM readings are diffusion indexes because they measure direction across
respondents. Nobody reads a PMI of 50 as "accurate". The analogy supports a direction
index beside the GCI, not a change to what the GCI measures.

### 2. The low-growth problem changes sign; it does not go away

Infosys guided 0–3% for FY26 and reported 3.1%, just above the top of the range.

- v2.4 scored it **0**.
- Diffusion scores it **100**, the same as a 100% beat.

Both come from dividing by a small midpoint (1.5). The fix is a floor on the scale for
growth percentages, which our amendment A1 supplies (5 points). Rejecting A1 removes
that floor. CAL-R2-01, approved in the same note, still lists the 5-point growth floor
as a parameter to test.

### 3. The penalties no longer read correctly

The note keeps the revision-frequency penalty, revision weights and lead time. It does
not say how they apply to a 50-centred score. Applied as v2.4 applies them:

- An exact hit with three in-year revisions scores 50 × (1 − 0.35) = **32.5**. That
  reads as a miss.
- The same hit with the 1.1 lead-time factor scores **55**. That reads as a beat.

A penalty has to pull a score toward "worse". On a signed scale, worse is not a
direction.

### 4. Beat and miss depend on the metric

`e = (x − m) / |m|` treats every figure above the midpoint as a beat.

- For costs, capex ceilings, working-capital days and credit cost, above the midpoint
  is a miss. The tag `EXPANSION_BEAT` would sit on a cost overrun.
- Cipla's R&D spend was guided 5–6% and reported 5.0%, inside the range. Diffusion
  scores it 45.5, a miss. R&D spend has no better direction.

The metric catalogue already holds each metric's direction (`higher`, `lower`,
`two_sided`). The formula needs it, and two-sided metrics cannot carry a beat or miss
tag at all.

### 5. Scores bunch near 50

Most guidance lands within ±10% of the midpoint, which maps to 45–55.

- Cipla beat its FY24 margin guidance by 2 points, a beat a desk would notice. It
  scores **55.7**.
- Infosys delivered its FY24 margin guidance and scores 49.3, labelled a miss.

A screener sorted on this column separates companies by fractions of a point.

### 6. The specification is incomplete

- **Zero-midpoint fallback.** "The most recent non-zero observation B(t−k)" is not
  defined: the earlier guided midpoint, the earlier actual, or the earlier reference.
  The sample code passes the zero midpoint into its own fallback, so it cannot return
  anything.
- **Roll-up** from vintage to family, parameter and company is not given.
- **One-sided guidance (A2).** A met floor maps to 50 or above. A met ceiling on a cost
  needs the metric's direction to come out the same way. The ruling does not say how.
- **Ranges inside the promise.** 7% delivered against 0–10% guidance scores 70, a
  "beat", although it is inside the range. This is the midpoint rule from the *Range
  Scoring Matrix* workbook, which R2 retired on 10 Nov.
- **Worked examples.** The §24.1–§24.10 golden tests are v2.4 examples. A new method
  needs its own worked examples before it can be tested.
- **Labels.** `EXPANSION_BEAT` / `CONTRACTION_MISS` are PMI terms for the economy.
  For guidance, "beat", "in line" and "miss" say the same in plain finance English.

## What we propose instead

| Need in the note | How we meet it |
|---|---|
| Beat or miss visible at once | Every vintage and family carries a tag: **beat / in line / miss**, set by the metric's direction. Two-sided metrics show *in range* or *outside range*. The headline reads, for example, "87.6 · revenue above range 4 of 5 years, below in FY24" |
| A 50-centred reading like PMI | Companion index **Guidance Bias** (`guidance_profile.companion_indexes`): 50 + 50 × clamp(signed deviation), with the metric's direction and the growth floor. Preview, `rankable: false`, `part_of_gci: false`, like the five companion indexes already shipped |
| No reward for wide ranges | Already in place: R2 with A1 scales a miss by the larger of width and midpoint, and the *Guidance Setting* companion flags ranges over twice the median width and results beaten by more than the range width |
| Sandbagging visible | Guidance Bias persistently above 50, plus the Guidance Setting flag |
| Headline | GCI Range (`v2.4-R2` with A1–A5): Infosys 87.6, Cipla 93.8 |

Each vintage already carries `deviation_side` and `met` under `v2.4-R2`, so the tag
needs no new data.

## On the other rulings

- **A2 (met floor or ceiling).** Accepted in principle. We read it in the headline as
  "a met bound scores full credit", which is A2 as built; Guidance Bias shows by how
  much the bound was beaten.
- **A3 (raise, walk-down, mixed, no direction).** Accepted. Built as specified.
- **A4 (curves for quarterly and half-year guidance).** Accepted. Built as specified.
- **A5 (unevidenced commitments stay in).** Accepted. Built as specified.
- **CAL-R2-01.** Accepted. Its test asks whether a high level this year predicts
  delivery next year. That works for an accuracy level. It cannot work for a signed
  score, where both 0 and 100 are poor records.
- **"Locked and approved for production".** Under the promotion gate (G-09), a method
  publishes only after the following, in this order:
  1. Gate 8 has been run and reviewed.
  2. CAL-R2-01 has run.
  3. The counsel memo on terminology (D-13) is in.
  4. Two people approve the publication.
  5. Same day: ledger rows and a changelog entry for every level that moves.

  Until then any new method runs in shadow. If diffusion is kept, it needs its own
  ruleset id. "v2.5" already names the team's change-control proposals (GCI Draft).

## Questions the notes leave open

1. Does the headline keep the revision-frequency penalty and the lead-time factor? Our
   10 Nov asks on both are not answered.
2. Is the headline Quant or the 80/20 Composite while reviewed commitments are zero?
3. When commitment coverage passes 50% but some are unresolved, which level publishes?
4. Does `v2.4-R2` with A2–A5 become the default, and does A1 stand for the headline?

## Decisions we need

1. Keep an accuracy level as the GCI headline (GCI Range, `v2.4-R2` with A1–A5) and
   publish direction as the Guidance Bias companion with beat / in line / miss tags.
   Or, if the owner keeps diffusion as the headline, supply the roll-up, the penalty
   combination, metric direction, the growth floor, the zero-midpoint fallback and
   worked examples. We then build it in shadow under its own ruleset id for gate 8.
2. Answer the four open questions above.
3. Sign the release note that makes the chosen method the default. The switch writes
   a ledger row and a changelog entry for every level that moves.

## Method note

Three method versions have come in three days: locked v2.4 on 9 Nov, R2 on 10 Nov and
diffusion on 11 Nov. Before launch a change costs nothing. After launch, each would move
every published level and need re-explaining to every licensee. We suggest freezing the
headline method once decision 1 is taken, and routing later ideas through change
control with an impact table.

## How to check

- Gate 8 table: `/api/v1/index/core` (`v4_gci`, `core_gci`, `r2_gci`, `delivery_gci`, `proposal_gci`).
- Per vintage, with `deviation_side` and `met`: `/api/v1/index/core/{company}?ruleset=v2.4-R2`.
- Companion indexes: `/api/v1/index/companions/{company}`.
- The diffusion figures above are 50 + 50 × clamp((x − m) / |m|, −1, 1) on the opening
  guidance of each row, with m the arithmetic midpoint. Applied penalties and lead time
  would move them further, as section 3 shows.
