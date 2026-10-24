# 03 — GCI Scoring

## Definition

Company GCI = scored closed outcomes aggregated to **0–100**. Higher = better historical delivery vs stated guidance.

## Scorer versions

| Flag | Algorithm |
|---|---|
| `INTELLENS_GCI_VERSION=v4` (**default**) | v3 engine with beats floored: beat = `60 + 40·exp(−α δ^β)`. In-band and misses identical to v3 |
| `INTELLENS_GCI_VERSION=v3` | Spec engine: band δ → exp(−α δ^β), γ miss asymmetry, exp recency λ, φ metric weights, audit deductions. Beats decay toward 0 |
| `INTELLENS_GCI_VERSION=v2` | Legacy confidence-weighted heuristic (beats floored ≥85; dropped → 35) |

`GET /api/meta` → `gci_algorithm` / `feature_flags.INTELLENS_GCI_VERSION`. Rebuild listing cache after switching versions (`python -m app.jobs.score_india_universe`).

### Methodology changelog

Public mirror: `/changelog` ← `GET /api/v1/index/changelog` (source `backend/app/data/score_changelog.json`, plus entries the daily guidance review appends under `INTELLENS_DATA_DIR` when that volume is set). Every moved number also has a row in `backend/app/data/score_ledger.jsonl` (`GET /api/v1/index/ledger?company_id=`; job `python -m app.jobs.snapshot_scores --write --reason … --by …`).

| 2026-10-19 | methodology | **Filing walk start date moved to January 2024.** Production reads filings dated on or after 2024-01-01 (was 2022-01-01; set to 2025-01-01 for about 20 minutes the same day) to cut model cost. Rows already read from 2022–2023 filings stay and still reconcile; no new 2022–2023 filings are read. Most companies will have two closed fiscal years (India FY25 and FY26, US FY2024 and FY2025) plus quarters; automated scores stay provisional. Published (hand-labeled) levels unchanged. |
| 2026-10-24 | new_filing | **Infosys FY24 operating margin.** Guided 20%–22% (13 Apr 2023 results release), actual 20.7% (18 Apr 2024 results release), inside the band. One closed margin period, so the row is context and the composite stays **76.5**. Evidence breadth moves provisional → **deep**. Infosys can be ranked. |
| 2026-10-24 | methodology | **Reporting basis on the outcome.** A row now stores reporting basis, unit, and scope on the guidance and on the actual. When both sides are filled and they differ, the row stays outside the score. A blank side is unknown and still scores, so published levels are unchanged. Infosys FY24 constant-currency revenue (guided 4–7%, actual 1.4% CC; January band 1.5–2%) remains a miss. Reported INR growth of 4.7% cannot close that constant-currency row. |
| 2026-10-19 | methodology | **Filing reader model and piece size.** The filing walk now reads filings with Gemini 3.8 Flash (Flex tier, standard on the last retry) in 48,000-character pieces, in place of Gemini 3.5 Flash on 12,000-character pieces. Scoring, quote checks and matching are unchanged. On eight sample filings (Chambal Fertilisers, CG Power, AbbVie, 3M) the new reader found the same three guidance statements and 40 checked rows against 21, at about a quarter of the cost. Filings already fully read are not read again. Provisional numbers can move as more results are matched; each move is written to the ledger and changelog by `disclosures.log_moves`. Published (hand-labeled) levels unchanged. |
| 2026-10-18 | data_correction | **Ledger correction after the v4.2 deploy.** The startup step that logs a methodology release (`score_ledger.record_methodology_release`) read scores while `seed.get_data()` was still applying stored guidance citations, and booked Axis Bank, Adani Ports, Apollo Hospitals and HDFC Life as withdrawn (`gci: null`, by `job:methodology_release`). The site never withdrew them. `get_data()` now publishes the dataset only after citations are applied (lock), and `correct_release_withdrawals()` appends `data_correction` rows restoring Axis Bank 90.7 (v4.2), Adani Ports 58.7, Apollo Hospitals 60.4, HDFC Life 87.8. |
| 2026-10-18 | methodology | **Filing walk v2, India + US.** Extraction now reads results as well as guidance, takes the period from the filing (the old reader defaulted every row to FY26), requires the whole quote verbatim with the number and unit inside it, and matches each promise to the first result filed after the period ends (within 550 days). The earliest pre-period promise is the opening band; later bands are revisions. Universe: Nifty 500 and S&P 500 (SEC results 8-Ks, Ex 99.1, since Jan 2022). US metrics: revenue, GAAP and adjusted EPS, adjusted EBITDA, FCF, capex (US$). Rows matched by the job are `reviewed_by = job:disclosure_reconcile` → `extracted_verified`, provisional, never ranked. Companies with no number carry `coverage_reason` (one sentence) in place of "Open period" / "Listed only". Moves from each run are written to the ledger and changelog by `disclosures.log_moves`. Published levels unchanged at release. See [18-filing-walk](18-filing-walk.md). |
| 2026-10-18 | methodology (v4.2) | **Metric direction and width floor.** Each catalogue metric has a `direction`: `higher` (default), `lower` (`wc_days`: below the range is the beat) or `two_sided` (`capex_guidance`, `rd_spend_pct_of_revenue`: outside the range either way is a miss). Every band gets a minimum half-width before scoring and labelling: `max(2% of midpoint, 0.1 pp)` for percentage metrics, 2% of midpoint for levels. Previously only point guidance got a band (±2%, no absolute floor). Spec v2.0 proposed 0.5 pp for margins; rejected because it scores Axis Bank's 18 bp NIM beat as in-band. **Moved (production):** Axis Bank 83.8 → **90.7** (FY25 NIM point 3.80%, actual 3.98%). Infosys 76.5, Cipla 65.5, Adani Ports 58.7, Apollo Hospitals 60.4, HDFC Life 87.8 unchanged. Locally only Infosys and Cipla score; neither moved. Ledger: run `snapshot_scores --write --reason methodology --by analyst:<id>` on the production volume after deploy. Dossier gains `guidance_profile` (descriptive, not in GCI). `ALGORITHM_REVISION` = "v4.2 width floor + metric direction". |
| 2026-10-02 | methodology | **India coverage status + extracted_verified.** Every NSE/BSE listing returns `coverage_status` (`scored` / `open_period` / `filing_in_review` / `no_quantified_guidance` / `listed_only`). A number still requires dual citation. `extracted_verified` may publish a provisional GCI when both quotes verify in stored filings; it cannot be ranked. Exchange filing ingest (`python -m app.jobs.ingest_india_filings`) and extract/classify jobs walk Nifty → IN1000 → NSE → BSE. Lookback without a metric+number promise is a coverage finding, not a miss. Published levels unchanged (Infosys 76.5, Cipla 65.5, Axis Bank 83.8, Adani Ports 58.7, Apollo Hospitals 60.4, HDFC Life 87.8). |
| 2026-10-01 | new_filing | **India guidance citations filed from stored filings where the promise is distinct from the result.** Axis Bank none → **83.8 provisional** (FY25 NIM guided 3.80%, actual 3.98%). Adani Ports none → **58.7 provisional** (FY25 cargo band 460–480 MMT, actual 450). Apollo Hospitals none → **60.4 provisional** (FY24 ARPOB band 6–7%, actual 11%). HDFC Life none → **87.8 provisional** (operating RoEV bands across FY24–FY25). Rows whose guided figure is the same number as the reported actual stay unscored. Infosys 76.5 and Cipla 65.5 unchanged. Ledger reason `new_filing`, by `job:guidance_review`. |
| 2026-10-01 | display_fix | **Filing check is the gate.** A closed row counts when a fetch of the guidance filing and the results filing both contain the recorded quotes. The dossier stamp is the check date. A missing quote drops the row and is not queued for a person. The 31 March 2027 Sensex / Nifty 50 coverage date is withdrawn; the homepage shows the live verified set. Methodology gains a limitations section (short history, current listings, design-choice constants, ±2% single-point band, unscored relative guidance). Revision count, direction, and average move render from stored revisions and are not part of GCI. Published levels unchanged (Infosys 76.5, Cipla 65.5). |
| 2026-09-29 | display (W2.8) | **Filing-to-score SLA.** Target: reviewed score published within 5 India business days of the results filing (`as_of`), for filings dated on or after 29 Sep 2026. Refresh records `filing_seen`; `accept_draft` records review → publish. Methodology and Trust show the observed median from scored rows (today: historical batch, n=6, all reviewed 29 Sep 2026; live sample empty). Availability 99.x% struck from `COVERAGE_AND_SLA.md`. Published GCI levels unchanged. |
| 2026-09-29 | data (W2.7) | **Source-link verification job.** Every hand-labeled `source_url` / `guidance_source_url` is checked for quote presence (`python -m app.jobs.verify_sources`; live refresh at most once per 24h). Failures are not citeable and go to the labeling queue. Trust Center shows n of N verified. Four HTML press pages that do not contain a verifiable quote are excluded (HCLTech FY26 guidance, Maruti FY25 wholesale volume, JSW Steel FY25, Grasim FY25 UltraTech volumes). Published GCI levels unchanged (Infosys 76.5, Cipla 65.5). |
| 2026-09-29 | methodology (W2.6) | **Audit flags are analyst-set.** Withdrawal (−15), restatement (−15) and definition-shift (−10) apply only when a reviewer persists the flag with `set_by` and a source URL. Keyword heuristics still run, but they enqueue a labeling-queue suggestion and do not move GCI. Dropped rows stay excluded from the average; they no longer auto-apply the withdrawal deduction. Published levels unchanged (Infosys 76.5, Cipla 65.5). |
| 2026-09-29 | methodology (W2.1) | **Dual citation required to score.** A closed row enters the composite only when both the original guidance and the subsequent actual have `source` + quote + as-of. Rows with an actual citation but no promise citation are labelled `pending_guidance_cite` (shown on the dossier, not scored). 6 of 84 closed rows already had both cites. **Withdrawn (37):** every previously published name except Infosys and Cipla, including TRENT 89.9. **Moved:** INFY 76.5 deep → **76.5 provisional** (FY25 op-margin excluded; one dual-cited metric remains); CIPLA 85.2 established → **65.5 provisional** (only FY24 EBITDA-margin remains dual-cited). Public Snapshot ranks no company until W2.2/W2.3 restore Established names. Ledger `2026-09-29.2`. `reviewed_by`/`reviewed_at` added to the outcome schema (enforced in W2.5). |
| 2026-09-29 | tier rule (D-tier) | **Context metrics count toward tier breadth.** `metrics_scored` = metrics with ≥ 1 closed, analyst-reviewed result (composite **and** context-only). Composite weighting and every level unchanged. Tier moves: INFY provisional → **deep** (5 periods, revenue + op-margin), CIPLA provisional → **established** (3 periods, revenue + R&D-spend). HINDALCO / HDFCLIFE / APOLLOHOSP gain breadth but stay provisional (< 3 periods). Public Snapshot (Nifty 50) now ranks TRENT, CIPLA, INFY; Sensex view ranks INFY. Ledger `2026-09-29.1` (tier rows, `prior_gci == gci`). |
| 2026-09-28 | v4.1 methodology | **Evidence-weighted composite.** Metric weight = closed periods (cap 5); a metric with < 2 closed periods is *context-only* (`context_metrics`, shown, not in the composite) whenever a deeper metric exists; if every metric is single-period the composite is a flat mean (tier `provisional`). Moved: INFY 88.2 → **76.5** (FY25 op-margin single row → context), CIPLA 92.6 → **85.2**, HDFCLIFE 87.3 → **94.0**, APOLLOHOSP 63.7 → **54.6**. TRENT / HINDALCO unchanged. Sector shrinkage removed (D5). Confidence tiers introduced (`score_policy.confidence_tier`): provisional / established / deep; Public Snapshot ranks established + deep only (today: TRENT). `algorithm_id` stays `gci_scoring_v4`; `ALGORITHM_REVISION` = "v4.1 evidence-weighted composite". Ledger `2026-09-28.2`. |
| 2026-09-28 | display fix | Δ chips / horizon bars / PIT feed publish only `series_kind == "citeable_pit"` (≥ 4 reviewed as-of points); otherwise horizons are `null` with `note`. `demo_pit_extension`, `demo_multi_horizon`, `hybrid_pit*` removed from every public route and from the listing cache; `pit_warehouse` returns an empty series when there is no published score. `/analytics`, `/wordmap`, `/stocks/{id}/history` require `analytics_experimental` / `wordmap` (pilot, desk, enterprise, onestop). `sentiment` dropped from `CompanyGCIDetail`. |
| 2026-09-28 | flag_change (INFY) | **Logged retrospectively.** INFY 48.2 → **88.2**: in-year band revisions moved from separate rows onto the FY row's `revisions`; placeholder FY24 "dropped restatement sample" row removed; `definition_shift` now keyed by `(thread_id, period)`. Withdrawal −15 / restatement −15 / definition-shift −10 no longer fire. Ledger `2026-09-28.1`. |
| 2026-09-27 | display fix | GCI Screener list, Public Snapshot, entity search, listing cache and PIT history now apply audit deductions (`audited_company_gci`), so every surface shows the dossier number. Previously lists showed the pre-deduction score for the 22 audit-flagged names (e.g. INFY 73.2 list vs 48.2 dossier; COALINDIA 4.7 vs 0.0; HDFCLIFE, ONGC, HINDALCO, TRENT −10). Guarded by `tests/test_score_consistency.py`. Public Snapshot "citeable rows" column was always 0 (counted raw outcomes) — now counts enriched citeable outcomes. |
| 2026-09-27 | data (INFY) | Infosys revenue rows re-cited to SEC-filed results releases (Form 6-K Ex. 99.1): `guidance_*` = the April release that set the band, `source_url`/`quote_span`/`as_of` = the April release that reported the actual. Corrections: FY22 band 10–12% → **12–14%** (Apr 2021 release; IR summary table disagreed), FY26 `as_of` 2026-04-17 → **2026-04-23**. FY22 60.4 → 61.8 pts; INFY dossier 48.1 → 48.2. No label changed. |
| 2026-09-27 | v4 | Beats floored at `GCI_BEAT_FLOOR = 60`. A beat far above the band still means the guidance was off, so it decays with distance, but no longer toward 0. Misses, in-band, dropped, recency, audit deductions unchanged. Cohort impact at switch: 15 of 49 scored names rose (e.g. INFY dossier 40.7 → 48.1 after audit deductions, AXISBANK 59.6 → 83.8); none fell. INFY FY22 row (band 10–12%, actual 19.7%) 1.1 → 60.4 pts. |
| before 2026-09-27 | v3 | Default exp-δ engine; beats decayed toward 0 (INFY FY22 ≈ 1 pt). |

### Labels

| Label | Meaning | v4 score | v3 score | v2 score |
|---|---|---|---|---|
| `met` | Actual in band | 100 | 100 | 100 |
| `exceeded` | Beat above band | 60 + 40·exp(−α δ^β) | exp(−α δ^β), γ=1.0 | ≥85 |
| `missed` | Below band | exp + γ=1.4 | exp + γ=1.4 | linear shortfall → 0 at ≥50% |
| `dropped` | Stopped reiterating | excluded; **−15** only if an analyst sets `guidance_withdrawal` | excluded; **−15** if analyst-set | ≈ **35** |
| `pending` | Period open | **Excluded** | **Excluded** | **Excluded** |
| `pending_guidance_cite` | Closed actual cited, original guidance not yet cited | **Excluded** | **Excluded** | **Excluded** |
| `unmapped` | Qualitative / NLP fail | **Excluded** | **Excluded** | **Excluded** |

### v3 / v4 highlights

- **Width floor (v4.2):** `W* = max(W, floor)`, floor = `max(0.02·|G_mid|, RATE_FLOOR_PP=0.1)` for `unit: pct` metrics, `0.02·|G_mid|` for levels. Applies to point guidance and to narrow ranges. The label tolerance in `classify_outcome` widens to the same floor so label and score agree.
- **Direction (v4.2):** `metric_catalog` `direction` = `higher` | `lower` | `two_sided`. Beat/miss, the beat floor and `normalized_surprise` (s* = σ·(A − M)/W*) all follow it. Unknown metrics default to `higher`.
- Miss below band: γ = 1.4; beat / in-band: γ = 1.0.
- v4 scores **promise-keeping**: a small beat scores near 100, a large beat decays toward 60 and never below it. A beat always outscores a miss of equal distance (beat − miss = 100 − S ≥ 0). Public copy names this as a design choice (promise-keeping discipline, separate from forecast accuracy) and states the δ = 1 points: a miss scores about 59, a beat about 88. Cross-metric comparability is half-width of each range; there is no sector adjustment. A wide range reaches 100 more easily than a tight one.
- Recency: `w_t = e^{-0.15(t-1)}` (t=1 most recent).
- Optional `definition_shift` audit flag → **−10**, only when an analyst sets it (`set_by` + source). Keyword heuristics enqueue a review suggestion (W2.6).
- `N < 4` periods → `low_confidence` (informational). Sector shrinkage removed 2026-09-28 (D5); `sector_mean` is accepted and ignored.
- **Composite (v4.1):** weight per metric = `min(closed periods, 5)`; metrics with < 2 closed periods are `context_metrics` (not in the composite) when a deeper metric exists. `score_meta()` in `guidance_flags.py` returns `confidence_tier`, `closed_periods`, `metrics_scored`, `as_of`, `algorithm_id`, `composite_weights`.
- Forensic “shenanigans engines” remain out of scope — only analyst-set audit flags.

## Layers

Evidence (stored filings, quotes, hashes, `ingested_at`) → measurement (band, floor, direction, s*) → GCI composite → delivery (dossier, Screener, ledger, index files). The **guidance profile** sits beside the GCI and reads only from measurement. Nothing in the profile, the Commitment Record or any pilot construct feeds the GCI (`test_profile_does_not_move_gci`, `test_commitments_do_not_change_gci`).

## Guidance profile (`services/guidance_profile.py`)

Descriptive, on `CompanyGCIDetail.guidance_profile`. Uses only rows the GCI could use (dual-cited, reviewed, closed).

| Part | Always | Label from 6 closed figures |
|---|---|---|
| Results vs range | Counts above / within / below, one sentence | `bias_index = 100·(above − below)/n`; ≥ 20 `usually_above`, ≤ −20 `usually_below`, else `balanced` |
| In-year revisions | Revised count, toward weaker / stronger (direction-aware) | `mixed` (both ≥ 25%), `walk_down` / `walk_up` (≥ 30%), `stable` (< 20% revised) |
| Divergences | Same-period revenue vs EBITDA/operating/net margin on opposite sides of their ranges, both sources | n/a |

Label text is neutral ("Results tend to land above the guided range"). Not used: spec v2.0's "over-promising", "financial engineering", "working capital strain". `surprise_spread` (1.4826 × MAD of s*) is computed for pilots and the gates job; it is not in the public payload.

Rejected from spec v2.0 (2026-10-18 review): 2-adic period distance (measures divisibility, not nesting; no time decay), cyclotomic phase vectors (no timing input; zero for steady delivery), market-calibrated loss L(δ) (sign error; turns GCI into a price model), bias-normalised revision lift, Loughran-McDonald hedging density, the long version's gate thresholds and ARR model.

## Validation gates (`python -m app.jobs.validation_gates`)

| Gate | Test | Pass |
|---|---|---|
| 2 Label stability | Drop the latest period; profile labels must not change | < 5% of labelled companies flip |
| 3 Floor sensitivity | Levels under rate floors 0.05–0.5 pp × level floors 1–2% | Reviewed by a person; any adopted change → ledger |
| 4 Extraction audit | Double review of ≥ 200 stratified rows in `app/data/extraction_audit.json` (`guided_match`, `actual_match`) | ≥ 95% exact |
| 7 Point in time | Promise dated before result; revisions in between; review after result; no document ingested before its filing date | Zero violations (`--strict` exits 1) |

Gates 5 (event study) and 6 (out-of-sample lift for any advanced construct) wait for enough established-tier companies. An advanced construct ships only if it beats the plain measurement on gate 6.

## Evidence hashes and point in time

- Each `OutcomeView` carries `evidence_hashes`: SHA-256 of the guidance quote and results quote (exact UTF-8, same as Analyst citations), the stored filing's `content_hash`, and its `ingested_at`.
- `GET /api/v1/index/evidence?checksum=<sha256>` → filing metadata (no text).
- `GET /api/v1/index/ledger?as_of=YYYY-MM-DD` and `GET /api/v1/index/levels?as_of=YYYY-MM-DD` rebuild what was published on a date from the append-only ledger.
- Documents ingested before 2026-10-18 have no `ingested_at`; gate 7 skips them.

## Bands

Prefer `guided_low`–`guided_high`. Midpoint-only guidance is weaker; vague text → lower **confidence weight** (0.5–1.0), not silent zero.

## Invariants

- **Index integrity:** any change that moves a published number → score ledger row + changelog row the same day (rule `index-integrity`, skill `citealpha-index-integrity`). Public surfaces never show synthetic history or Δ (`demo_pit_extension`, `demo_multi_horizon`, `hybrid_pit`). Remediation plan: `docs/PLAN_WORLDCLASS_GCI.md` (W1).
- A row scores only with both citations (promise `guidance_*` + actual `source_*`) **and** `reviewed_by` / `reviewed_at`. Rows missing the promise citation are `pending_guidance_cite` and are excluded. Companies carry a `confidence_tier` (`provisional` / `established` / `deep`).
- Deterministic: same inputs → same score.
- Pure function in `backend/app/services/gci_scoring.py` — no I/O.
- Outcomes should carry `source_url` / `source_ref` / `quote_span` when available.
- Threads: `thread_id` groups raise/lower/reiterate history.

## Tests

Edge cases in `backend/tests/test_gci_scoring.py` (v2 golden), `test_gci_scoring_v3.py` (v3) and `test_gci_scoring_v4.py` (v4 floor, v3 parity for misses). Gap tests `test_g06`… in `test_gaps.py`. Source-link verification: `test_source_verify.py`. Filing-to-score: `test_score_sla.py`.

## Do not

- Treat beats as misses: v2 floors beats ≥85; v4 floors beats ≥60; v3 lets large beats decay toward 0. All versions apply γ=1.4 only to misses.
- Score pending / unmapped into the average.
- Invent actuals to “fill” a demo.

## Multi-horizon GCI Δ (WoW / MoM / QoQ / YoY)

- Engine: `services/changes.py` → `change_bundle` (calendar-aligned day windows + FY/quarter labels).
- Company chips: `gci_change_bundle_for` — **citeable PIT only** (`MIN_CITEABLE_PIT_FOR_DELTAS = 4`); otherwise all horizons `null` + `note`. Synthetic paths (`demo_multi_horizon`, `demo_pit_extension`, `hybrid_pit*`) are Workbench analytics scaffolding only and never appear on public routes (`tests/test_index_integrity.py`).
- India listings cache: `python -m app.jobs.score_india_universe` writes horizons only for `citeable_pit` rows plus `confidence_tier` / `closed_periods` / `metrics_scored` / `as_of` / `algorithm_id`.
- Citations: hand_labeled only for external cite; `citation_index.json` holds comprehensive outcome packs (guided/actual/label/evidence_summary).

## Red alerts & revision trail

- `services/guidance_flags.py` — analyst-set audit flags (`guidance_withdrawal`, `restatement`, `definition_shift`) with `set_by` + source → GCI v3/v4 deductions + UI badges. Keyword hits enqueue `/api/labeling/queue` (`kind=audit_flag_suggestion`) and do not deduct.
- GCI Screener `/api/alerts` includes applied audit kinds, misses, drops, revisions, drift, stale threads.
- Dossier: `audit_badges`, `red_alerts`, `revision_timeline` on `CompanyGCIDetail`.
- Not a Beneish / forensic shenanigans engine — evidence-linked guidance events only.
