# Plan — GCI Core v2.4 (PRD v1.0 review → implementation)

Source documents: *CiteAlpha GCI Platform Implementation PRD v1.0* and *GCI Computation Methodology v2.4*.
Requirement-by-requirement review, decisions and status: `docs/review/CiteAlpha_GCI_PRD_v2.4_Requirement_Review_09_Nov_2026.xlsx`
(sheets *PM Actions*, *Requirements Review*, *Decisions*, *Methodology Gaps*, *Calculator*).

## Principle

Core v2.4 runs **in shadow** beside the published v4 scorer. No published level moves until
validation gate 8 is reviewed, a ledger snapshot is written, and a methodology changelog entry
says so (rule `index-integrity`). `scorer_version()` cannot return Core; promotion flips
`CORE_ENGINE_APPROVED` in `gci_scoring.py` in the same change as the ledger and changelog rows.

## Owner rulings (Corrective Action Plan v1.1, 09 Nov 2026)

The owner upheld every locked v2.4 rule. Core implements v2.4 as written; the team's
reworks are v2.5 change-control proposals and run only with `ruleset="v2.5-proposal"`
for impact analysis. The Qual branch and the 80/20 Composite are in scope; lead time is
a score modifier.

| Category (workbook) | Action taken |
|---|---|
| Implement (82) | Scoring core, routes, reason codes, snapshots, replay, change feed shipped; remaining workflow and API items scheduled by phase |
| Implement + Enhance (62) | Same, with the enhancement in the workbook's *Enhance / reduce detail* column |
| Reduce / Simplify (18) | Market-level accounting profile; Ind AS history first; three seats. Lead time and frequency follow v2.4 as written |
| Rework, then implement (13) | Formula reworks → v2.5 proposals (below). PRD defects fixed (below) |
| Defer (15) | Qual branch and 80/20 Composite implemented (owner ruling). Data feeds, OCR, regime bridges, taxonomy, crosswalk and sector policy deferred |
| Do not implement (2) | Blockchain anchoring and bespoke post-quantum signing not built; hashes carry the `sha256:` prefix for agility |

## Locked v2.4 in code (default ruleset)

| Rule | In code |
|---|---|
| Range reference `(abs(L) + abs(U))/2`; point `abs(g)`; percentages as stated | `core_vintage_z` |
| One-sided bounds symmetric around the bound | `core_vintage_z` |
| Zero amount against one presentation unit; zero percentage against `prior_value` | `_zero_reference` |
| Revision magnitude: mean endpoint move / opening scale, `M = r/(1+r)`; numerical sign | `core_revision_magnitude`, `core_weight_exponent` |
| Frequency penalty on every substantive revision inside the target period; FY ceiling 5, Q ceiling 2 | `core_frequency_penalty`, `core_family_detail` |
| Lead-time factor 0.8 / 0.9 / 1.0 / 1.1; `C_f = min(100, D_f(1 − P_f)L_f)` | `core_lead_time_factor`, `core_family_detail` |
| Equal family and parameter weights | `compute_core_detail` |
| Qual branch (§10, §15.2): accepted commitments, fulfilled by the deadline, unknown widens the range | `core_qual_branch`, `commitments.qual_family` |
| Composite `0.8 Quant + 0.2 Qual`; single branch labelled | `core_composite` |
| Golden tests §24.1–§24.10 (§24.10 per the v2.4.1 erratum) | `tests/test_gci_core.py` |

Interpretations the methodology leaves open (to confirm with the owner):

- **Family lead time** = lead time of the opening (earliest eligible) vintage.
- **Half-year guidance** uses the annual frequency curve (v2.4 names annual and quarterly only).
- **Quarterly beyond-ceiling slope** = 8 points per revision, as the annual table implies.
- **Vintages issued after period end** earn no weight and sit outside the frequency window.
- **Opening guidance after period end** is `GUIDANCE_AFTER_PERIOD_END`, not scored.
- **Erratum §24.10** reproduces with the revision issued 11/12 of the horizon after the original.

## PRD defects fixed

| Defect | Resolution |
|---|---|
| DM-11 / DM-12 cardinality | Snapshot *–* Vintage; Snapshot 1–* GCIResult (the snapshot payload holds every input row) |
| ID-02 horizon | Horizon = cadence of the period label (Q 90, H 180, FY 365 days) — `core_cadence` |
| LT-03 / FQ-03 | One formula: `C_f = min(100, D_f × (1 − P_f) × L_f)` |
| API namespace | Extend `/api/v1/index`; no second tree |

## Decisions adopted from the team review

| ID | Decision | In code |
|---|---|---|
| D-12 | Two lanes: machine-verified is provisional and never ranked; human-approved publishes | `score_policy` + Core `SHADOW` |
| D-15 | Extend `/api/v1/index` | `routes.py` |
| D-16 | Decimal strings beside floats (`quant_gci_exact`, `composite_exact`, `score_exact`) | Core responses |
| D-17 | Ind AS era first (India `history_from` FY2017) | `GCI_CORE_PROFILES` |
| D-18 | Three seats + two-person rule | scheduled |
| D-20 | Shadow one results season, `algorithm_id` `gci_core_v2_4` | `CORE_ALGORITHM_ID` |
| D-21 | Horizon = cadence | `core_cadence` |
| D-22 | One snapshot per calculation event | `score_ledger.snapshot_payload` |
| D-24 | Raw bytes kept by hash | `doc_store._keep_raw` |
| D-25 | Score as-reported actual; keep restated value | `restated_actual_value` |
| D-13, D-14, D-27 | **Open — counsel** (terminology, index scope, data rights) | — |

Analyst plan D2 still holds for the published GCI: commitments never feed it. They feed
only the Core Qual branch, which stays in shadow until promotion.

## v2.5 change-control backlog (proposals — not in use)

Each needs a version, rationale, impact analysis (gate 8 `proposal_gci` column and
`/api/v1/index/core/{id}?ruleset=v2.5-proposal`), updated tests, independent review and an effective date.

| Proposal | Rationale | In code (proposal ruleset only) |
|---|---|---|
| D-01 beaten bound costs half | Beating a floor is not missing it | `PROPOSAL_FAVOURABLE_BOUND_RATE` |
| D-02 growth on implied level | Removes the framing artefact. **Too lenient as built** (Infosys FY24 guided 4–7%, reported 1.4%: opening vintage 96.1); needs a percentage-point-aware alternative | `_core_level` |
| D-03 reference `max(abs(m), U − L)` | Infosys FY26 guided 0–3%, reported 3.1%: opening vintage scores 0 under v2.4 | `core_vintage_z` |
| D-04 zero amount scale reference | Unit choice should not move a score | `_zero_reference` |
| D-05/06 direction-aware frequency | Honest raise 77.8 < silence 88.0 under v2.4; three in-year updates cap a family at 71.5 | `core_family_detail` |
| D-07 lead-time smoothing | Step cliffs; flat 1.1 for April annual guidance | — |
| D-08 window first issuance → results | Closes the pre-period and post-period windows | `PROPOSAL_FREQUENCY_CURVES` |
| D-10 ≥ 2 families per parameter | Thin evidence should not swing deep records | `PROPOSAL_MIN_FAMILIES_PER_PARAMETER` |
| D-31 economic revision sign | A cost cut is not a walk-down | `_econ_sign` |
| Composite calibration (D-09/D-28) | 80/20 is uncalibrated | — |

Response to the owner: `docs/review/GCI_v2.4_Ruling_Response_10_Nov_2026.md`.

## Delivery ruleset and companion indexes

Where a v2.4 element measures something other than delivery, it is moved to its own index
instead of being blended into the level. `ruleset=delivery` (`gci_core_delivery_v1`) is locked
v2.4 measurement without those elements. Locked v2.4 stays the default: `CORE_DEFAULT_RULESET`
in `gci_scoring.py` is the one line to switch after the owner rules.

| v2.4 element | Why it misleads inside GCI | Delivery ruleset | Companion index (`guidance_profile.py`) |
|---|---|---|---|
| §14 revision-frequency penalty | Penalises honest raises; three updates cap a family at 71.5 | `P_f = 0`; revisions still counted and shown | Revision Discipline: share of figures never walked toward a weaker figure before results |
| §13.3 lead-time factor | Step cliffs; flat 1.1 for April annual guidance; a timing question, not delivery | `L_f = 1`; undated guidance still scores | Guidance Visibility: lead days ÷ period days, capped at 100 |
| §17 Qual 20% | Uncalibrated blend of a different question | Headline is the Quant branch; Qual shown beside it | Commitment Delivery: `core_qual_branch` standalone |
| §9 relative deviation on growth | A 1.2-point beat on 1–3% guidance scores 0 | Growth reference at least 10 points (`DELIVERY_GROWTH_FLOOR_PP`) | Growth Accuracy: points outside the opening range, 10 index points per point |
| Not in v2.4 (GAP-18) | A wide range or a low floor scores as met | — | Guidance Setting: ranges over twice the median width for the metric, results beaten by more than the range width |

Companion indexes are preview: `rankable: false`, `part_of_gci: false`, no value below three closed figures.
Gate 8 reports `delivery_gci` beside the v4, locked and proposal levels.

## Markets — what the data supports

| Market | Core status | Why |
|---|---|---|
| India | publish after review | Hand-labelled dual-cited rows; Ind AS from FY2016-17; numeric guidance sparse outside IT, banks, autos, cement |
| US | shadow | Quarterly raise/cut of annual ranges is routine (the v2.4 frequency penalty bites hardest here); GAAP vs non-GAAP basis |
| UK, Eurozone | shadow | Half-yearly; "in line with expectations" is `RELATIVE_TO_CONSENSUS`; directional wording unscorable |
| Japan | shadow for IFRS / US GAAP; J-GAAP not eligible | Kessan Tanshin forecasts near-universal; mandated revisions at 10% revenue / 30% profit; no J-GAAP adapter |
| Singapore | shadow | Half-yearly; banks only guide numerically |
| Australia | shadow (next to publish) | Guidance common; July–June year; miners' quarterly production updates are revisions |
| Korea, Brazil, Canada | shadow | Fair-disclosure targets; reference-form projections compared each quarter; MD&A outlook comparison |
| Hong Kong | diagnostics only | Forward numeric guidance rare; profit warnings come after period end |
| China | diagnostics only | Performance forecasts cover a closed period; CAS has no adapter |

`markets.core_publication_status(market, regime)` applies this per company.

## Promotion gate (G-09)

1. Gate 8 (`python -m app.jobs.validation_gates`) deterministic for every company.
2. A person reviews the v4 vs Core table (today Infosys 76.5 v4 vs 70.8 Core vs 93.0 under the proposals; Cipla 65.5 vs 80.4 vs 91.3).
3. Calibration on established-tier names (O-01) and counsel memo on terminology (D-13).
4. Same-day: `snapshot_scores --write --reason methodology`, changelog row in `docs/kb/03-scoring.md` and `score_changelog.json`, flip `CORE_ENGINE_APPROVED`.

## Progress log

- **2026-11-09** — Core engine (shadow), canonical routes and 25 reason codes, market profiles for 12 markets, half-year period ends, calculation snapshots + replay, `/api/v1/index/{methodology,markets,updates,snapshots,core,cdi}`, Commitment Delivery Index (preview), lead-time diagnostic, gate 8, raw-byte hash + public-availability time on filings, model/prompt provenance on extracts, Workbench *GCI Core (shadow)* tab. Tests: `test_gci_core.py`, `test_core_api_and_cdi.py`. Published levels unchanged.
- **2026-11-10** — Owner ruling applied. Core default is locked v2.4: percentages as stated, `(abs(L)+abs(U))/2`, symmetric bounds, presentation-unit zero, every in-period revision, numerical sign, lead-time factor, equal weights. Qual branch (`core_qual_branch`, `commitments.qual_family`) and the 80/20 Composite added; the separate Commitment Delivery Index and `/api/v1/index/cdi/{id}` removed (one owner). Reworks kept behind `ruleset=v2.5-proposal`; gate 8 shows the v4, Core and proposal levels. Golden tests for §24.1–§24.10, including the erratum. Tests: `test_gci_core.py`, `test_core_api.py`. Published levels unchanged.

- **2026-11-10 (r2)** — Delivery ruleset and five companion indexes (`/api/v1/index/companions/{id}`). Core output carries `family_id` / `vintage_id` (a basis switch is a new family), vintage time from the stored `public_available_at`, units and currency, coverage, uncertainty, record state (HC-03), `BASIS_SWITCH`, `SAME_DAY_CONFLICT`, `THIN_HISTORY`. A re-run cannot add a revision. Same-day statements follow a source hierarchy in `disclosures.statement_precedence` (GAP-17) and are queued for review. Diagnostics for withdrawal, reinstatement, deadline extension and basis switch (GAP-19/20/21). Drill-down routes (parameter, family with stored evidence, vintage), bulk headline route, release gates G-01…G-08 (`validation_gates.core_release_gates`), two-person publication requests and admin sign-offs on the audit log, recalculation and ledger writes audited, route changes snapshot (RT-06). One place gathers Core inputs: `validation_gates.core_inputs`. Non-code items: `docs/review/GCI_Core_Release_Checklist.md`. Published levels unchanged.

- **2026-11-10 (r3)** — Owner's v2.4-R2 specification built as `ruleset=v2.4-R2` (`gci_core_v2_4_r2`, shadow) with tech amendments A1–A5: range miss scaled by `max(width, abs(m), 5 pp growth floor)`, met floor/ceiling = 100, economic revision kinds and `mixed` defined, per-cadence curves on `N_eff`, Qual evidence status with coverage over due commitments. Continuous lead time, Quant headline until Qual coverage, calibration protocol CAL-R2-01 listed. `R2_SCALE_INCLUDES_MIDPOINT` / `R2_MET_BOUND_SCORES_FULL` reproduce R2 as written. Gate 8 adds `r2_gci`; readiness uses `headline_gci`. The *Range Scoring Matrix* workbook is not implemented (midpoint rule R2 retires). Reply to the owner: `docs/review/GCI_v2.4-R2_Reply_10_Nov_2026.md` (+ PDF). Missing actual past the results deadline is `ACTUAL_UNAVAILABLE`. Published levels unchanged.
- **2026-11-10 (r4, reconciliation review)**:
  - **R2 fixes:**
    - Lead time L is counted inclusively like H, so guidance on the first day of the period has r = 1 and anything earlier is flagged.
    - The R2 headline stays Quant while any due commitment is unresolved, so more evidence never removes the headline (owner to confirm).
    - The coverage test uses the raw fraction.
  - **Every Core ruleset:**
    - `as_of` is a point-in-time cutoff.
    - `input_digest` covers the market calendar, audit flags and R2 constants, and ignores row order.
    - Snapshots carry the market calendar, so non-March and non-IN companies replay.
    - G-02 replays a serialised snapshot.
  - **Publication:**
    - Publication and replay use `headline_gci` / `headline_exact`.
    - Approval needs a reviewer or admin, checks the requested level against current data (`STALE_REQUEST`), and writes a same-day changelog entry.
    - The Core reviewer routes and the publication list stay inside the desk's markets.
  - Published levels unchanged.
- **2026-11-11 (r5, method names)**:
  - Every method has a stable display name in `gci_scoring.GCI_METHODS`: GCI Classic (v4, published), GCI Core (v2.4), GCI Range (v2.4-R2), GCI Delivery (v1) and GCI Draft (v2.5).
  - Desk seats pick a method by name in Analyst Workbench → GCI methods, and the choice is remembered. API callers pass the code as `ruleset`.
  - The dossier footer names its method.
  - No number moves.
- **2026-11-11 (r6, owner's v2.5 Diffusion note)**:
  - The owner proposes a 50-centred signed score, `50 + 50 × clamp((x − m)/|m|, −1, 1)`. The owner rejects A1, accepts A2–A5 and approves CAL-R2-01.
  - Tech reply: `docs/review/GCI_v2.5_Diffusion_Reply_11_Nov_2026.md`. It accepts A3–A5 and CAL-R2-01. It asks to keep an accuracy level as the headline and to publish direction as a **Guidance Bias** companion with beat / in line / miss tags.
  - Evidence:
    - Beats offset misses: Infosys averages 63.3, Cipla 51.1.
    - Infosys FY26 (0–3% guided, 3.1% reported) scores 100.
    - Penalties flip an exact hit to a "miss".
    - Metric direction is ignored.
  - Nothing built; no number moves.
- **2026-11-12 (r7, method lab)**:
  - Analyst Workbench → Method lab: every proposed method (GCI Classic, Core, Range, Delivery, Draft, and the scan's Range-P, Interval score, Midpoint error in points, Relative error, Hit rate, Diffusion, Conversation rubric) with adjustable settings, presets and roll-up, compared on up to 8 configurations. Role views for methodology owner / PM, analyst, PM, quant and IR.
  - Owner: `gci_scoring` lab section; `GET /api/v1/index/lab`, `POST /api/v1/index/lab/run`. Classic defaults reproduce published v4 (Infosys 66.5 after the 10-point audit flag, Cipla 65.5). Behaviour checks reproduce the 12 Nov scan (Diffusion +49.4 from guiding low).
  - Research only: nothing stored, ranked or published; no ledger row. The base column stays GCI Classic until the owner rules on a headline. Tests: `test_gci_method_lab.py`.
  - No number moves.
- **2026-11-12 (r8, diffusion webpage and FAQ drafts)**:
  - Reviewed the owner's *GCI Diffusion Index Methodology* webpage draft and *GCI FAQ*, both 12 Nov.
  - The webpage draft is not published. It describes the GCI as 50-centred, width-invariant and ungameable. The published level (GCI Classic) scores a result inside the range at 100, floors beats at 60 and lets a wide range reach 100 more easily. The 12 Nov scan measures +49.4 points from guiding low under diffusion.
  - Guidance Bias companion built (`guidance_profile.guidance_bias`, preview, unranked, not part of the GCI). It reuses the method lab's diffusion rule with the `guidance_bias` preset and tags each figure beat / in line / miss / outside range. Infosys reads 55.1 (4 beat, 1 in line, 1 missed).
  - Release-gate findings for the PM: `docs/review/GCI_Diffusion_Release_Gate_Findings_12_Nov_2026.md`. Diffusion is not a registered ruleset, so readiness refuses it. As a method it fails calibration (+49.4 points from guiding low) and inverts Infosys and Cipla. G-03, G-04 and G-05 to G-08 block every method today.
  - Citation review fix (`guidance_review.bind_from_documents`): stored excerpts are our labelling note plus the filing quote, so the job could confirm a row from its own label. It now matches and copies only the filing sentence, refuses a promise dated after the period's midpoint or a result dated before period end, and binds one promise per period and metric. India dry run: 24 binds → 3. Cipla FY25 EBITDA margin: two half-rows merged into one (guidance May 2024, result May 2025), held as `source_unverified` because the result quote does not state 25.9%. No published level moved (53 companies). Open: the 1 Oct production binds for Axis Bank, Adani Ports, Apollo Hospitals and HDFC Life rest on rows the new rules refuse and need a `data_correction` on the production store.
  - `/answers` FAQ: eight answers adapted from the owner's FAQ and checked against the Methodology page. Dropped: terminal-vendor feeds (not built), "alpha factor" (banned voice), confidential weights (the method is published), the `institutional@` address (not in use), and the claim that wider ranges do not help (untrue for the published method).
  - No number moves.
- **2026-11-13 (r9, owner's 40-case workbook)**:
  - Review: `docs/review/GCI_40_Case_Workbook_Review_13_Nov_2026.md`. Corrected copy generated from the method lab by `docs/review/assets/gci_algorithm/repro/case_workbook.py`.
  - The sheet's R2 column omits A2 (11 of 80 rows understate the proposal). Range-P scores one-sided guides as points and $M in raw dollars. Legacy v4 differs from the published scorer in 74 rows. Diffusion is undefined at a zero midpoint, and the sheet fills those 12 rows inconsistently.
  - Diffusion scores 16 in-promise results 0 or 100. 19 of the sheet's BEAT / MISS tags are wrong. Added sheets: cases to add, method properties, and a roll-up on Infosys and Cipla.
  - Open: `lab_tag` takes direction from the catalog only, so a breached ceiling on a higher-is-better metric tags as a beat. No scored row is bounded today. Settle this with A2.
  - No number moves.

## Next (scheduled in the workbook)

- Owner decision on the v2.5 Diffusion reply: accuracy headline with a Guidance Bias companion, or diffusion in shadow under its own ruleset id once roll-up, penalty combination, metric direction, growth floor and zero fallback are specified.
- Owner ruling on R2 amendment A1 and the four open questions in the Diffusion reply. Then the release note, ledger rows and changelog that make `v2.4-R2` the default (`CORE_DEFAULT_RULESET`).

- Issuer-year accounting profile (S-02 reduced field set).
- Three-seat review roles (D-18); adjudication by the methodology owner.
- Calibrate the companion constants (growth points per point, wide-range multiple) on established-tier names.
- Backfill FY2017–FY2023 India filings with source-once ingest.
- Regime adapters (J-GAAP, CAS, Indian GAAP) before those markets move off `NOT_ELIGIBLE`.
