# Plan — India whitespace (extract → match → index)

**Status:** WS0–WS2, WS3.1–WS3.2, WS4 implemented 2026-10-24 · WS-C (8 established Sensex names) waits on stored filings · WS5 (every NSE/BSE main-board listing) WS5.0–5.1 done 2026-11-11, WS5.7 model comparison built and blocked on Gemini credit and Bedrock quota · **Owner:** product + `gci-engineer`
**Source:** pitch slide “Proven category abroad. Whitespace in India.” (`docs/PITCH_DECK.md` slide 4, `docs/COMPETITIVE_LANDSCAPE.md`).
**Runs alongside:** `docs/PLAN_WORLDCLASS_GCI.md` (W2.2–W2.4 are the review depth this plan consumes) and `docs/PLAN_CITEALPHA_ANALYST.md` (Commitment Record stays beside the GCI). Nothing here may score a commitment or publish a number without the ledger protocol.
**Execute with:** `citealpha-gci-dev` (WS0–WS2) · `citealpha-guidance-review` + `citealpha-labeling` (WS3) · `citealpha-index-integrity` on any moved number · `citealpha-expert-ux` (WS4). Before a new file, `citealpha-reuse-sources`.

---

## 0. Goal

Occupy the two empty India cells on the maturity map, then publish them as a Guidance Credibility Index.

| Stage | Global | India today | This plan |
|---|---|---|---|
| Guidance extract | Marvin, FinCatch | Empty as a desk product | Verbatim bands from stored NSE/BSE filings |
| Match vs actuals | Marvin, FinCatch | Empty as a desk product | Opening band, revisions, later actual, with unit and metric guards |
| Credibility index | Marvin (US) | CiteAlpha target | Ranked only after a person accepts a dual-cited thread at `established` |

**Done for the programme** when `python -m app.jobs.guidance_coverage` reports at least **8 Sensex names** with a published GCI (`hand_labeled` and a score), each with a dossier thread a desk can read: opening quote, revisions, actual quote, both links, label. Nifty 50 is the next cohort after that gate, using the same jobs.

A company with no quantified guidance keeps one `coverage_reason` sentence. Its delivery record, when it has one, is the Commitment Record.

---

## 1. Decisions

| # | Decision | Consequence |
|---|---|---|
| D1 | `disclosures.process_company` is the only writer of India guidance rows | `jobs/extract_india_guidance.py` calls that path. A paused or unconfigured model leaves filings unread |
| D2 | `disclosures.reconcile` is the only matcher of a promise to a later filing | `matching.match_actuals` stays the import join for a figure the caller already supplied |
| D3 | `reviewed_by = job:disclosure_reconcile` may set `extracted_verified` | It never promotes `hand_labeled`. Ranked Snapshot stays `established` / `deep` |
| D4 | W2.2–W2.4 in `PLAN_WORLDCLASS_GCI.md` are the accept path | This plan fills the queue those tasks review. It does not open a second labeling stack |
| D5 | Commitments stay out of the GCI | Quiet-drop for a **numeric** metric is a queue suggestion on the GCI row. The Commitment Record’s own quiet-drop is unchanged |
| D6 | The walk reads filed text | Audio and video are not transcribed in this programme |
| D7 | Fixture companies carry the unit tests | A published Sensex number moves only from a stored filing quote, with a ledger row and a changelog line the same day |

---

## 2. Owners (extend these)

| Job | Owner | Leave as-is |
|---|---|---|
| Read a filing | `services/disclosures.py` `read_documents`, `llm_extract` | Chunk keys in `disclosures/{id}.json`; 48k pieces |
| Match a later actual | `services/disclosures.py` `reconcile` | Opening band, revisions, 550-day result window. Hand-labeled dossiers are never replaced (`apply_rows`) |
| India walk | `services/india_coverage.py` `process_company` | Ingest stays `exchange_filings.ingest_company_urls` |
| Import join | `services/matching.py` `match_actuals` | AlphaHunter / supplied actuals only |
| Shell extractor | `services/extract_pipeline.py` `extract_company` | Ledger and `maybe_promote_extracted` stay. Production India coverage stops calling `extract_company` |
| Score | `services/gci_scoring.py`, `score_policy.py` | No new algorithm |
| Review queue | `services/labeling_queue.py` `enqueue` | New `kind` values only |
| Accept into the index | `services/labeling.py` | `label_accept`, two-person rule, `hand_labeled.py` for repo rows |
| Withdrawal flag | `services/guidance_flags.py` | −15 only after `set_by` |
| Scoreboard | `jobs/guidance_coverage.py` | Same command |
| Dossier thread | `frontend/src/components/ThreadTimeline.tsx`, `EvidenceTable.tsx`, `RecordSentence.tsx` | Guest anatomy in rule `frontend-ux`: header, delivery record, evidence, revisions, how-calculated, links |
| Workbench | `frontend/src/pages/DeskPage.tsx` `?tab=labeling` and `?tab=review` | Guests do not see Run extract |

Map: `docs/kb/19-reuse-and-source-once.md`. Filing walk behaviour: `docs/kb/18-filing-walk.md`.

---

## 3. Where the cells are still empty

Measured 2026-10-03 by `guidance_coverage`: **2 of 50** Nifty names and **1 of 30** Sensex names had a guidance-side citation. The filing walk (2026-10-18) can write provisional `extracted_verified` rows. Production reads filings dated on or after 2024-01-01, so most names have two closed years and stay `provisional`.

Three holes:

1. **Two writers.** `india_coverage.process_company` calls `disclosures.process_company` when the model is on, and `extract_pipeline.extract_company` otherwise. The fallback writes guidance shells (12k chunks, default period) and does not match a later filing. `jobs/extract_india_guidance.py` calls `run_extract_cohort`, which is that fallback.
2. **Match is exact on `(period, metric)`.** Reported growth can be paired with constant-currency growth. A crore can be paired with a million when the bare number appears in the quote. Numeric guidance that disappears from later guidance filings is not proposed as `dropped`.
3. **The ranked index is a person.** Job-stamped rows are provisional. Publishing the Sensex names that guide is W2.2–W2.4: promise citations, ≥ 3 closed periods × ≥ 2 metrics, revision trails.

`ThreadTimeline` shows band direction and the latest guided text. It does not yet show the promise link and the actual quote side by side as the thing a desk cites.

---

## 4. Workstreams

### WS0 — Scoreboard

Extend `jobs/guidance_coverage.py` `measure`. One run, Sensex and Nifty 50, prints:

| Count | Definition |
|---|---|
| `with_cited_guidance` | ≥ 1 outcome with `guidance_quote` and `guidance_source_url` |
| `with_matched_actual` | ≥ 1 of those rows also has `actual_value`, `quote_span`, and `source_url` |
| `with_published_gci` | `data_quality == hand_labeled` and a score |
| `with_accepted_commitments` | Accepted Commitment Record rows (already counted) |
| `provisional_only` | `extracted_verified` with a matched actual, not `hand_labeled` |

Print the company ids in `provisional_only` and in `with_matched_actual` that are still below `established`. That list is the WS3 queue.

| ID | Task | Files | Done when |
|---|---|---|---|
| WS0.1 | Add the counts above. Keep the CLI (`--index`, `--json`) | `jobs/guidance_coverage.py` | `python -m app.jobs.guidance_coverage --index SENSEX` and `--index NIFTY50` print all five counts |
| WS0.2 | Unit test on fixture outcomes. No network, no model | `tests/test_guidance_coverage.py` | A dual-cited closed row counts as matched; a promise without an actual does not; a commitment does not count as guidance |

Reprint the two indexes into §8 at the start of execution and again at WS-C.

### WS1 — One extractor

| ID | Task | Files | Done when |
|---|---|---|---|
| WS1.1 | In `india_coverage.process_company`, call `disclosures.process_company` when `disclosures.enabled()`. When the model is paused or not configured, return `budget_out` / `model_unavailable` and do not call `extract_company` | `india_coverage.py` | `tests/test_coverage_india.py` covers both branches. A second call does not re-read a stored chunk |
| WS1.2 | `jobs/extract_india_guidance.py` walks the disclosure path (same as the coverage job). `extract_pipeline.extract_company` remains for tests of the ledger and for `maybe_promote_extracted` | `jobs/extract_india_guidance.py` | The job’s module docstring names `disclosures` as the writer. A test shows the job function does not call `extract_company` |
| WS1.3 | Golden extract cases: fixture company text in `tests/golden/whitespace_cases.json`. Each case has metric id, canonical period, low, high, and a quote that is a substring of the fixture. Include one reported-growth case, one constant-currency case, one margin, one point band (`±`), one qualitative sentence that must be dropped, one unknown metric that must be dropped | `tests/golden/whitespace_cases.json`, `tests/test_disclosures.py` | All cases pass `quote_verbatim` and `_check_item`. Qualitative and unknown-metric cases increment the drop counters. No case uses a real ticker’s published actual |
| WS1.4 | Point kb 04 stages 2 and 5 at `disclosures` for the filing walk, and at `matching.match_actuals` for the import join | `docs/kb/04-pipeline.md` | An agent reading kb 04 does not add a third extractor |

Catalog ids stay in `data/metric_catalog.py`. A new India metric is a catalog row plus a golden case, in the same change. The model prompt is `disclosures.build_prompt`.

### WS2 — Match a desk can defend

All guards live in `disclosures.reconcile` (or a pure helper it calls in the same file). They run before `review_status` becomes `accepted`.

| ID | Task | Files | Done when |
|---|---|---|---|
| WS2.1 | Refuse a pair whose metric ids differ. Record it on the reconcile result as `conflicts` (period, promise metric, result metric, both doc ids). Do not write `actual_value` | `disclosures.py` | Golden case: FY guidance on `revenue_growth_cc_pct` is not filled from a `revenue_growth_pct` result |
| WS2.2 | Refuse a pair whose units disagree (percent vs basis points, crore vs million) even when the bare number sits inside the quote. `_numbers_fit` stays the “number is in the quote” check; this is a separate scale check | `disclosures.py`, `metric_catalog.py` (read `unit` only) | Golden case: a margin quoted in basis points does not match a percent actual of the same digits |
| WS2.3 | Numeric quiet-drop proposal. After reconcile, if a guided metric is absent from the next `QUIET_DROP_CYCLES` (2) guidance filings that do contain other guidance for that company, enqueue `kind=guidance_drop_suggestion` with the two silent doc ids in `note`. Do not set `dropped` and do not apply −15 | `disclosures.py` (detect), `labeling_queue.py` (enqueue). Cycle count matches `commitments.QUIET_DROP_CYCLES` | Test: one silent filing does nothing; two silent guidance filings enqueue one open item; a reiteration clears the proposal; GCI is unchanged until a reviewer sets `guidance_withdrawal` |
| WS2.4 | Enqueue `kind=match_conflict` for each WS2.1 / WS2.2 refusal, once per open `(company, period, metric)` | `labeling_queue.py` | Duplicate runs do not stack a second open item |

`apply_rows` still skips `hand_labeled` companies. Conflicts on a hand-labeled name are queue items only.

### WS3 — Review into the ranked index

This is W2.2–W2.4, fed by WS1–WS2. Continue `labeling.py` and `hand_labeled.py`. The job reviewer never promotes.

| ID | Task | Files | Done when |
|---|---|---|---|
| WS3.1 | Workbench labeling queue shows `match_conflict` and `guidance_drop_suggestion` with company, period, metric, and the note. Accept / dismiss uses the existing queue status API | `DeskPage.tsx`, `lib/api.ts` if the queue payload is missing a field | A seated user can open the item, read both quotes, and mark it done or cancelled. Guest routes do not list the queue |
| WS3.2 | Accepting a matched `extracted_verified` row goes through the existing draft → submit → second reviewer. Promotion to `hand_labeled` still requires dual citation and `reviewed_by` / `reviewed_at` | `labeling.py` | `tests/test_labeling_governance.py` gains a case: `job:disclosure_reconcile` alone does not promote |
| WS3.3 | First cohort, in order: Infosys, then the other Sensex names that already have a stored guidance filing and a later results filing (TCS, HCLTech, Wipro, and the bank / industrial names the scoreboard lists). Each name needs ≥ 3 closed periods and ≥ 2 metrics before it counts toward the gate | `hand_labeled.py` or workbench accepts, `docs/LABELING_PLAYBOOK.md` checklist only if a step is missing | 8 Sensex names at `established`. Every moved number has a ledger row and a `/changelog` line (`new_filing` or `data_correction`) |
| WS3.4 | Reprint `guidance_coverage` for SENSEX and NIFTY50 into §8 | this file | Counts are from the command, not estimated |

A row whose quote is not in the stored filing stays unscored (`source_verify`). Do not invent a quote to clear the gate.

### WS4 — Thread on the dossier

Extend the panels the guest dossier already has. Do not add a seventh panel.

| ID | Task | Files | Done when |
|---|---|---|---|
| WS4.1 | Each metric thread shows the opening quote, date, and guidance link; each revision (date, band, link); the actual quote, date, and results link; the label via `formatOutcomeLabel` | `ThreadTimeline.tsx`, `EvidenceTable.tsx` | Dossier for a golden matched company shows both quotes. A period with no actual says the period is still open |
| WS4.2 | Header sentence stays `RecordSentence`. A name with no quantified guidance shows `coverage_reason` and no GCI | `RecordSentence.tsx`, `CompanyDetailPage.tsx` | Guest dossier still ≤ 6 panels. Run extract and the review queue stay on the Workbench |
| WS4.3 | Copy hygiene: no metric ids, no `extracted_verified` string, no Buy/Hold | `tests/test_public_copy_hygiene.py` if a new string needs a ban | Existing hygiene test stays green |

Public Snapshot continues to rank `established` and `deep` only. Provisional rows appear on the company page with the tier, unranked.

### WS5 — Every NSE and BSE main-board listing

Bring the walk from the Nifty 500 to every active main-board equity (SME boards out) at the lowest model and fetch cost. Everything lands provisional (`extracted_verified` at most). Nothing here publishes or moves a number. Extend `refresh_index_lists`, `india_listings`, `exchange_filings`, `india_coverage` and `disclosures`; no second client, store or extractor.

Spike, 11 Nov 2026:

| Source | Result |
|---|---|
| NSE announcements by date, no symbol | Works. One call returns the day for every company (10 Nov 2026: 307 filings, 210 companies) with ISIN, dissemination time `exchdisstime` and `hasXbrl` |
| NSE `EQUITY_L.csv`, Nifty 50 and Nifty Bank CSVs | Work |
| NSE financial-results list by date | Returns `[]` for a one-day query; parameters still to find |
| BSE announcements, scrip list, bhavcopy | Refused: 403 to scripts, and a browser session is sent to BSE's data "show interest" page. BSE data is a licensed product |
| AMFI six-month average market cap | Works. 5,427 companies with ISIN, BSE and NSE symbols and rank (`portal.amfiindia.com`) |

| ID | Task | Files | Done when |
|---|---|---|---|
| WS5.0 | India lists: NSE master, Nifty 50 / Bank from NSE's files, AMFI rank. A renamed NSE symbol keeps its company id (same ISIN). BSE SME groups, non-`INE` ISINs and BSE-only scrips AMFI does not rank are left out. Walk and `IN1000` in AMFI rank order | `jobs/refresh_index_lists.py` (`--india`), `data/india_listings.py` | Done 2026-11-11 |
| WS5.1 | `doc_store` lookups by `url_key`, hash and (hash, company) instead of a scan per call; ingest asks `stored_preview` per URL | `data/doc_store.py`, `exchange_filings.py` | Done 2026-11-11 |
| WS5.2 | Announcement index by day: `exchange_filings.discover_by_date`, one file per day under `announcements/nse/`; a past day is fetched once. `discover_nse_filings(payload=…)` ranks each company's slice unchanged. `exchdisstime` becomes `public_available_at`. `roll_daily` walks names with a new guidance-bearing filing; per-symbol discovery stays for one name on demand | `exchange_filings.py`, `india_coverage.py`, kb 19 row | A second run for a past day does not fetch. Nifty 500 discovery calls a day fall from about 1,000 to under 10 |
| WS5.3 | BSE-only names (1,722 in the universe; AMFI ranks about 2,950, of which 656 are missing from the August BSE file). No free exchange source | Decision: BSE data licence, or web-search and issuer-site leads (60 a day each), or AMFI-only rows without scrip code | Owner decision recorded here |
| WS5.4 | Results from XBRL: candidate actual for `reconcile`, quote bound by text search in the stored results PDF (no model), cross-check of model-read actuals. Results PDFs go to the model only for metrics XBRL does not carry | `exchange_filings.py` (fetch, parse), `disclosures.reconcile` | Golden case: XBRL figure and PDF quote agree; disagreement enqueues `match_conflict` |
| WS5.5 | Model backfill since Jan 2024, finished before 31 Dec 2026 (Flex price doubles 1 Jan 2027). Separate Fargate Spot task, not the API task. AMFI order. No guidance-bearing filing → no model call and its own coverage sentence; else probe the latest two transcripts or presentations; full lookback where the probe finds guidance. A forward-language chunk gate only after it keeps ≥ 99% of guidance in chunks already read | `india_coverage.py`, `disclosures.py`, `coverage.py`, deploy task | 200 names (AMFI rank 501–700) measured first; calls per company recorded in §8 |
| WS5.6 | Steady state: one NSE sweep a day; fetch and read only new filings | `india_coverage.run_daily_from_env` | Daily discovery calls ≈ days swept, not companies |
| WS5.7 | Reading model. `llm_client` reads through Amazon Bedrock (Converse API, task IAM role) when `INTELLENS_LLM_PROVIDER=bedrock`; Gemini stays the default. Choose the backfill model by `jobs/extract_model_compare` on the same stored pieces: accepted items under `_check_item`, recall against Gemini 3.8 Flash, drops by reason, seconds and tokens per piece. Switch only if a candidate keeps ≥ 95% of Gemini's accepted guidance items at lower cost per piece | `services/llm_client.py`, `jobs/extract_model_compare.py`, deploy task env | Comparison table reprinted below. Bedrock path built 2026-11-11; run blocked (see below) |

Model comparison, 11 Nov 2026 (not run):

| Item | State |
|---|---|
| Sample | 34 pieces from 15 Nifty 500 companies' stored filings since 2024: the opening 48k piece of the latest call and of the latest deck or results, plus outlook pieces from 5 annual reports. 1.27M characters, about 9,000–10,000 input tokens a piece. Saved by `extract_model_compare sample`, so every model reads the same text |
| Gemini 3.8 Flash (baseline) | Production key refused: HTTP 402, prepaid credit used up. Production reads on this key fail the same way until the credit is topped up |
| Bedrock, ap-south-1 | Account `884686184601` has 0 requests and 0 tokens a minute for every candidate. gpt-oss-120b / 20b and Nova Lite quotas are not adjustable from Service Quotas; Claude Haiku 4.5 and Nova Lite cross-region tokens are. Raising them needs an AWS Support case |
| Candidates | gpt-oss-120b ($0.155 / $0.618 per 1M in/out, Flex and Batch half), gpt-oss-20b, Nova Lite (apac), Nova 2 Lite (global), Claude Haiku 4.5 (`in.`), DeepSeek V3.2. Qwen3-235B: quota 0 and not adjustable |
| Known limits | Bedrock has no web-search tool: `web_search_links` returns nothing on that path and issuer-site leads come from the IR crawl only. Embeddings move to Titan v2 (`amazon.titan-embed-text-v2:0`). Bedrock Flex needs a `boto3` newer than the pinned 1.35.90 (no `serviceTier` on Converse); Batch needs an S3 prefix and a Bedrock service role |
| Price check at list | About 9,500 in and 1,500 out a piece: Gemini 3.8 Flash Flex ≈ $0.0064 (≈ $0.013 from 1 Jan 2027); gpt-oss-120b standard ≈ $0.0024, Flex or Batch ≈ $0.0012. Output tokens to be replaced by the measured figure |

Estimates (to replace with the WS5.5 measurement): 35,000–50,000 model calls since Jan 2024, about $0.007 each on Flex now (about $0.014 from 1 Jan 2027), so $250–350; on gpt-oss-120b Batch about $40–60 if it passes WS5.7. XBRL actuals avoid about 60,000 results-PDF reads; 40,000–50,000 filing fetches; about 100 GB of raw files (`doc_raw/`), EFS Infrequent Access after 30 days; about 20,000 calls a year in steady state.

Open: Tata Motors demerger (seeded `tatamotors` predates it; NSE lists `TMPV`, now in the Nifty 50, as `nse_tmpv`), a methodology question. Sensex membership stays in code because BSE's list is refused. Gemini prepaid credit (blocks production reads and the WS5.7 baseline) and the Bedrock Support case are owner actions.

---

## 5. Gates

| Gate | After | Pass |
|---|---|---|
| **WS-A** | WS0 + WS1 | One writer. Golden extract file green. Coverage command prints the five counts |
| **WS-B** | WS2 | Golden match file: opening band, revision, later actual. Zero wrong-metric and wrong-unit accepts. Quiet-drop enqueues and does not move GCI |
| **WS-C** | WS3 | ≥ 8 Sensex names `established`. Ledger and changelog current. Scoreboard reprinted in §8 |
| **WS-D** | WS4 | Dossier thread has both quotes and both links. Guest walk has no extract controls |
| **WS-E** | WS5 | India lists refreshed within 7 days and AMFI on its latest half-year. Every main-board listing has a coverage sentence. Backfill read before 1 Jan 2027. No published level moved |

Order: WS0 → WS1 → WS2 → WS3 → WS4, then WS0 again. WS4 can start once one matched Sensex dossier exists; it does not wait for all eight names.

---

## 6. Tests

| Area | Where |
|---|---|
| Extract drops and verbatim quotes | `tests/test_disclosures.py` + `tests/golden/whitespace_cases.json` |
| Metric and unit conflicts | same |
| Quiet-drop suggestion, GCI unchanged | `tests/test_disclosures.py` and `tests/test_gci_scoring_v3.py` or `tests/test_guidance_flags.py` |
| Coverage counts | `tests/test_guidance_coverage.py` |
| Job does not call `extract_company` | `tests/test_coverage_india.py` |
| Job reviewer does not promote | `tests/test_labeling_governance.py` |
| Published number moved | `tests/test_score_consistency.py` plus ledger protocol in `citealpha-index-integrity` |
| Guest dossier | existing dossier Playwright spec; add a thread assertion when WS4 lands |

No test fetches NSE, BSE, EDGAR, or a model. Pass `fixture_text` or a stored document.

---

## 7. Out of scope

- A new extractor, matcher, score, page, or HTTP client for NSE, BSE, or EDGAR.
- Transcription of concall audio or video.
- Scoring the Commitment Record, or copying a commitment into an outcome row.
- Auto-promotion from `job:disclosure_reconcile` to `hand_labeled`.
- Sentiment, word map, price overlay, Buy / Hold / Sell.
- US coverage. The SEC walk already uses `disclosures` and `sec_filings.py`. This programme’s gate is Sensex, then Nifty 50.
- Moving `INTELLENS_FILING_DISCOVERY_SINCE` earlier to manufacture a third closed year. Depth comes from filings the store already has, or from a dated methodology change with a changelog line.

---

## 8. Progress log

| Date | What | Tests | Score impact |
|---|---|---|---|
| 2026-10-23 | Plan written. No code. Baseline remains the 2026-10-03 coverage measure (2/50 Nifty, 1/30 Sensex with a guidance-side citation) until WS0.1 is run. | — | none |
| 2026-11-11 | WS5 planned and spiked; WS5.0–WS5.1 built. `refresh_index_lists --india`: NSE 2,645 (was 2,364), 6 renamed symbols keep their ids, Nifty 50 / Nifty Bank (14) from NSE, AMFI 30 Jun 2026 (5,427). Universe 4,374 main-board rows (was 5,557 with SME and unranked BSE scrips); `IN1000` is now the top 1,000 by AMFI rank. `doc_store` lookups indexed. Nifty 50 filter follows NSE: UltraTech, BSE Ltd and TMPV in; Wipro, Hero MotoCorp, Tata Motors out | `test_refresh_index_lists`, `test_india_listings`, `test_doc_store_external_text`, `test_citation_universe_audit` | none |
| 2026-11-11 | WS5.7 Bedrock path in `llm_client` (Converse, `last_usage` tokens for both providers, Titan embeddings, no web search) and `jobs/extract_model_compare` (34-piece sample saved). Comparison not run: Gemini key HTTP 402 (prepaid credit used up, production reads affected) and Bedrock on-demand quotas 0 in ap-south-1 | `test_llm_rate_limit` (Bedrock request, cut-off, throttle → 429, no web search) | none |
| 2026-10-24 | WS0–WS2, WS3.1–WS3.2, WS4. `disclosures.process_company` is the only India writer. Reconcile refuses a lookalike metric and a basis-point / million scale clash, and proposes a numeric quiet-drop without setting `dropped`. The job reviewer does not promote. Dossier evidence panel shows the promise, revisions, and the later actual. | `test_disclosures`, `test_guidance_coverage`, `test_labeling_governance`, `test_coverage_india` (writer branches), `test_public_copy_hygiene` | none |

```text
SENSEX: cited 1 / 30 · matched 1 · published 1 · provisional-only 0
NIFTY50: cited 2 / 50 · matched 2 · published 2 · provisional-only 0
```

Matched below established: Infosys, Cipla. WS-C needs 8 Sensex names at `established`. Those rows are not in the stored hand-labeled set. They are not invented here. The accept path is `labeling._maybe_promote_quality` once a person dual-cites them.

Reprint format for later rows:

```text
SENSEX: cited __ / 30 · matched __ · published __ · provisional-only __
NIFTY50: cited __ / 50 · matched __ · published __ · provisional-only __
```
