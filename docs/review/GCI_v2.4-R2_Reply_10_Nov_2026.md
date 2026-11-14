# Response to the GCI v2.4-R2 specification

**To:** Product owner / Methodology owner · **From:** Tech team · **Date:** 10 Nov 2026

## Summary

R2 settles all four of our asks, and we accept its structure. We have built it as a
shadow ruleset, `v2.4-R2`, beside locked v2.4. Locked v2.4 stays the default. No
published level moves.

Before the owner signs the release note, we ask for five amendments. Two of them
change scores. As written, R2 removes the two zeros we reported (Infosys FY25 and
FY26) but creates new ones. Cipla beat its EBITDA margin guidance by 2 points and
would score **19.0**, down from 80.4 under v2.4. With the amendments it scores 93.8.
The other three amendments define terms that R2 leaves open.

We do not recommend implementing the *GCI Range Scoring Matrix* workbook. It
describes the midpoint rule that R2 retires (see the section on the workbook below).

## What we accept and have built (shadow)

- **§2 Revision weights.** A walk-down counts 1.0, a raise 0.3, a mixed revision 0.5, a
  wider band 0.7, and a narrower band or a no-op 0. The weighted count N_eff runs on the
  existing penalty curve: three raises take 18% off, three walk-downs take 35%.
- **§3 Ranges.** A result inside the guided range scores 100.
- **§4 Lead time.** One continuous curve, 0.80 + 0.30 × min(lead days / horizon days, 1).
  The horizon is in actual calendar days, so FY24 counts 366. Guidance given before the
  period begins is capped at 1.10 and flagged.
- **§5 Headline.** Quant is the headline until Qual has at least 3 evidenced commitments
  covering at least half of those due. The Composite is computed and shown either way.
- **§6 Growth floor.** A growth-percentage miss is read against at least 5 points. A
  flag shows wherever the floor applies.
- **§8–§12.**
  - Calibration parameters are listed (protocol CAL-R2-01, below).
  - The cross-market limitation is stated on every R2 response.
  - Each vintage carries:
    - target type and endpoints;
    - whether the target was met;
    - deviation and side;
    - natural and effective scale.
  - The §11 properties run as tests.
  - R2 has its own algorithm id, `gci_core_v2_4_r2`, and the v2.4 fixtures are untouched.

## Five amendments we ask the owner to accept

### A1. Scale a miss by the larger of range width and midpoint (§3, §6)

**The problem.** R2 divides a miss by the width of the range. A narrow range is a
precise promise, yet it is punished hardest for a small miss. Paired with "inside the
range scores 100", the rule rewards guiding wide, which no index should do.

**What it does to our data.** Opening guidance, as written:

| Company, figure | Guided | Reported | v2.4 | R2 as written | R2 with A1 |
|---|---|---|---|---|---|
| Infosys FY26 revenue growth | 0–3% | 3.1% | 0 | 98 | 98 |
| Infosys FY25 revenue growth | 1–3% | 4.2% | 0 | 76 | 76 |
| Cipla FY24 EBITDA margin | 21.5–22.5% | 24.5% | 88.6 | **0** | 90.9 |
| Infosys FY22 revenue growth | 12–14% | 19.7% | 48.5 | **0** | 56.2 |

**Point and range disagree too.** Under §6, point guidance of 41% growth reported at
45% scores 90. A range of 40–42% reported at 45% scores 40. Issuers would learn to
give points instead of ranges.

**Ask.** Use scale = max(range width, |midpoint|, floor). The floor is 5 points for
growth percentages and none for other metrics. A point is then a range of zero width,
so the point and range rules become one rule. The scale never depends on the reported
figure.

**Effect on the §3 worked examples.** 0–3% reported at 3.1% stays at 96.67. 4–6%
reported at 6.5% moves from 75 to 90.

R2's own worked examples also need a metric type. If 0–3% is growth guidance, §6 gives
98, not 96.67.

### A2. A met floor or ceiling scores 100 (§6 against §11)

**The problem.** §6 measures distance from the bound in both directions, so "at least
10%" delivered at 15% scores 50. §11 requires every member of a closed set to score 100.
Both cannot hold.

**Ask.** Meeting the bound scores 100, and a miss is scored by its distance from the
bound. This reads "range = promise" the same way for one-sided guidance. Sandbagging,
meaning beating a bound by a wide margin, is already measured by the Guidance Setting
companion index.

### A3. What counts as a raise, and what "mixed" means (§2)

**Raise.** A raise must mean a move in the direction that is better for the company. A
higher working-capital-days target or a higher capex ceiling is a walk-down. The metric
catalogue already holds each metric's direction. For one-sided guidance the bound sets
it: a higher floor or a lower ceiling is a raise.

**Mixed.** As written, mixed cannot occur: a midpoint moves up, moves down, or stays.
We define it as a better midpoint with the weaker bound moved against the company, for
example 4–6% revised to 3.5–7%.

**No direction.** For metrics with no better direction (two-sided, no bound) we weight
a midpoint move 1.0. This is the conservative choice.

**Ask.** Confirm these three definitions.

### A4. Which penalty curve applies to quarterly and half-year guidance (§2)

R2 gives only the annual curve. We apply the existing per-cadence curves to N_eff,
with 0.2 × N_eff below one revision:

| Cadence | Curve |
|---|---|
| Annual | 0.20 + 0.075 per revision up to 5 (0.50), then 0.08 per revision |
| Quarterly | 0.20, 0.50 at 2, then 0.08 per revision |
| Half-year | Annual curve |

Whole-number counts give exactly the v2.4 penalties.

**Ask.** Confirm, or name the curves.

### A5. A commitment past its deadline without evidence stays in (§7)

**The problem.** Indian companies announce completed projects but rarely file the ones
that slipped. If unevidenced commitments are dropped, mostly the delivered ones remain,
and Qual drifts toward 100.

**Ask.**
- **Before the deadline:** the commitment is `PENDING` and excluded.
- **After the deadline without evidence:** the commitment is `UNAVAILABLE`. It stays in
  as an unresolved range, as v2.4 does: never scored zero, never dropped.
- **Coverage for §5:** evidenced commitments divided by commitments due. This also
  supplies the definition of "expected families" that §5 leaves open.

## Impact (packaged dataset, shadow)

| Company | Published (v4) | Core v2.4 | R2 as written | R2 with A1–A5 |
|---|---|---|---|---|
| Infosys | 76.5 | 70.8 | 83.3 | 87.6 |
| Cipla | 65.5 | 80.4 | **19.0** | 93.8 |

Neither company has reviewed commitments, so the headline is Quant under every column.

**Infosys by year, R2 with amendments:**

| Year | Guided | Reported | Score |
|---|---|---|---|
| FY22 | 12–14% | 19.7% | 65.5 |
| FY23 | 13–15% | 15.4% | 87.9 |
| FY24 | 4–7% | 1.4% | 57.1 |
| FY25 | 1–3% | 4.2% | 77.9 |
| FY26 | 0–3% | 3.1% | 87.5 |

FY24 also has operating margin guided 20–22%, reported 20.7%, which scores 100.

FY24 stays the weakest year. The miss is clear, and the only weighted revisions that
year were walk-downs.

## The Range Scoring Matrix workbook

It scores every shape by distance from the midpoint, z = |x − m| / |m|. R2 retires
that rule, and the workbook breaks R2's own properties:

- **Values inside the range lose points.** 7% inside 0–10% scores 60 (R2 says 100).
  6% inside −10% to +10% scores 80.
- **Met floors and ceilings lose points.** "At least 10%" delivered at 12% scores 80.
  "Below 10%" delivered at 5% scores 50.
- **Strict and inclusive bounds score the same**, against §11.
- **The "≠ k" row is inverted.** It scores being far from k as worse.
- **The log row depends on units.** In $M it scores 91.2; the same figures in dollars
  score 97.8, against §11.
- **Zero-midpoint shapes fall back on a prior-year actual.** That replaces both the
  v2.4 zero-amount rule and the 5-point floor R2 adopts.
- **The examples are US $M metrics**, several of which are never guided (TAM, legal
  contingency, rebates).

We will keep its 20 shapes as a test inventory, scored under R2, for the guidance
parser and the regression suite.

## Interpretations we implemented

| Point | Implemented |
|---|---|
| Revisions that count toward N_eff | The v2.4 window: inside the target period, before the result |
| Vintage weights (§12.1) | Unchanged from v2.4; R2 is silent |
| Horizon days H | Calendar days from period start to period end, inclusive |
| Lead time L | From the opening guidance's public-availability date to period end, both days counted, so guidance on the first day of the period gives L = H and anything earlier is flagged `PRE_PERIOD_GUIDANCE` |
| Strict bounds (> rather than ≥) | Not captured by extraction yet; any unrecognised bound fails closed |
| Missing actual past the results deadline | `ACTUAL_UNAVAILABLE`, not scored (60 days after year end, 45 after a quarter) |
| Headline when coverage passes 50% but a due commitment is unresolved | Quant stays the headline. Under A5 the unresolved commitment keeps the Composite a range, and a range is not a level. Without this, adding evidence could remove the headline altogether |
| Level as of a past date | Only what was public by that date: later guidance is not scored, later revisions earn no weight, a later result counts as not yet reported |

## Calibration protocol CAL-R2-01 (to pre-register, §8)

Proposed for the owner's approval before any parameter is tuned:

- **Parameters under test.**
  - Raise weight 0.3 (tested from 0 to 0.5).
  - Lead-time slope 0.30 (0 to 0.30).
  - Growth floor 5 points (3 to 10).
  - Composite 80/20.
  - Headline gate (3 commitments, 50% coverage).
- **Question.** Does the R2 level at a year end separate companies by whether their
  next-year guidance is met?
- **Sample.** Nifty 50 rows, FY22–FY26, hand-labelled and dual-cited, held out by year.
- **Threshold.** Rank correlation of at least 0.3 between level and next-year delivery,
  on at least 30 companies over two seasons.
- **Trigger.** A parameter is changed only if the threshold fails, through change
  control, with a ledger row and a changelog entry.
- **Freeze.** The thresholds are fixed before anyone looks at outcome data.

## Decisions we need

1. Accept A1 (scale) and A2 (met bounds). These two change scores.
2. Confirm the A3 definitions and the A4 curves.
3. Accept A5 for Qual evidence and coverage.
4. Rule on the headline when coverage passes 50% but some due commitments are
   unresolved. We keep Quant as the headline. The alternative is to publish the low
   end of the Composite range, which counts every unresolved commitment as missed.
   Under our reading the 50% test never decides, because the Composite is a single
   level only when coverage is 100%.
5. Approve CAL-R2-01, or set other thresholds.
6. After 1–5, sign the release note that makes `v2.4-R2` the default. The switch
   writes a ledger row and a changelog entry for every moved level.

## How to check

- Reviewer API: `/api/v1/index/core/{company}?ruleset=v2.4-R2`. Each vintage shows its
  target type, scale and revision kind.
- Gate 8 table: `/api/v1/index/core`, which now has an `r2_gci` column.
- Methodology: `/api/v1/index/methodology` → `r2` (weights, floor, scale rule, calibration).
- Workbench: Analyst Workbench → GCI methods → *GCI Range v2.4-R2*. R2 is named **GCI Range**
  (code `range`); locked v2.4 is **GCI Core**, and the published v4 is **GCI Classic**.
- As-written comparison: set `R2_SCALE_INCLUDES_MIDPOINT` and `R2_MET_BOUND_SCORES_FULL`
  to `False` in `backend/app/services/gci_scoring.py`. The tests pin both variants.
