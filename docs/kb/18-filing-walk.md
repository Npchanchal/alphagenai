# 18 — Filing walk: India and US, from January 2024 (production)

Every listed company in the Nifty 500 and S&P 500 is checked for numeric guidance since January 2022. A company either gets a GCI (provisional until a reviewer signs it) or one plain sentence saying why it has none. No number is ever shown without both quotes.

## Universe

| Market | List | Source | Refresh |
|---|---|---|---|
| India | Nifty 500 (`NIFTY500` index tag, cohort `nifty500`) | `archives.nseindia.com/content/indices/ind_nifty500list.csv` → `backend/app/data/listings/nifty500.json` | `python -m app.jobs.refresh_index_lists --nifty500` |
| US | S&P 500 (`SPX`, ids `us_<ticker>`) | Wikipedia constituents table (ticker, GICS sector, CIK) → `backend/app/data/listings/us_equity.json` | `python -m app.jobs.refresh_index_lists --us` |

Both refreshes refuse a short list (India < 400, US < 450 rows). Walk order: names whose filings have not been read back to `INTELLENS_FILING_DISCOVERY_SINCE` (default `2022-01-01`) go first.

## Sources

- **India:** exchange filings (NSE/BSE) and filed call transcripts, best documents per fiscal year (`INTELLENS_FILING_DISCOVERY_DOCS_PER_YEAR`, default 6). Audio and video are not transcribed.
- **US:** SEC results 8-Ks (item 2.02) from the EDGAR submissions API; Ex 99.1 plus one CFO commentary or supplement exhibit per filing (`services/sec_filings.py`). `INTELLENS_SEC_USER_AGENT` must carry a contact address; requests are spaced 0.15 s.

## Reading (`services/disclosures.py`)

1. Filings are cut into 48,000-character pieces (`READ_CHUNK_CHARS`, 1,000 overlap); a filing already fully read in the earlier 12,000-character pieces is not read again. Each unread piece with at least three figures goes to the model under the shared daily budget. The model returns `guidance` (metric, period, low, high, quote, optional `pm_pct`) and `results` (metric, period, value, quote). Extracts are cached per company in `{INTELLENS_DATA_DIR}/disclosures/{id}.json`; a chunk is read once.
2. Three model failures in a row pause the model for the day. The walk continues: US releases fall back to the rule reader (`services/us_release_rules.py`, company revenue and EPS only, rejects table text and prior-year baselines); India filings wait for the next read.
3. Every statement is checked: known metric for the market, canonical period (India `FY25` / `Q3 FY25`, April–March; US `FY2025` / `Q3 FY2025` from the SEC fiscal year end), whole quote verbatim in the filing, and the number with its unit inside the quote. Drops are counted by reason.

## Reconciling

- The earliest promise made before the period ends is the opening band. Later different bands are revisions. Promises more than five years ahead are ignored.
- `$X, plus or minus N%` becomes a band only when the quote says so.
- The actual is the first result filed after the period end, within 550 days. Interim figures filed before the period ends never count.
- A matched row is `reviewed_by = job:disclosure_reconcile`; the company becomes `extracted_verified` (provisional, never ranked). Hand-labeled companies are never touched.
- Every number gained, moved or lost gets a ledger row and a public changelog line at the end of the run (`disclosures.log_moves`).

## What a company with no number shows (`coverage.coverage_reason`)

| Status | Example sentence |
|---|---|
| `open_period` | First guided year (FY27) closes Mar 2027 · FY26 result not yet matched to a filing |
| `filing_in_review` | Guidance found, being checked against results · SEC results releases since Jan 2022 held, being read |
| `no_quantified_guidance` | No numeric guidance in exchange filings since Jan 2022 · No numeric guidance in SEC results releases since Jan 2022 |
| `listed_only` | Filings since Jan 2022 not yet read |

The sentence is returned as `coverage_reason` on `/api/companies` and `/api/companies/{id}/gci`. US names are marked `no_quantified_guidance` only after a full model read; the rule reader alone is too narrow to say a company never guides.

## Running

```bash
python -m app.jobs.refresh_index_lists                    # both lists
python -m app.jobs.classify_india_coverage --live --cohort nifty50,nifty500
python -m app.jobs.us_coverage --limit 50                 # or --company us_nvda
```

Production (`deploy/aws/main.tf`): `INTELLENS_INDIA_COVERAGE_COHORT=nifty50,nifty500`, `INTELLENS_US_COVERAGE=1`, `INTELLENS_SEC_USER_AGENT`, `INTELLENS_FILING_DISCOVERY_SINCE=2024-01-01` (was 2022-01-01 until 2026-10-19, briefly 2025-01-01 that day; filings before the start date are not sent to the model, extracts already read from them still reconcile). The daily jobs (`gci_refresh`, `guidance_review`) run both walks; in the `guidance_review` thread the India and US walks run side by side and the day's filing review starts once both finish. Shared stores (documents, coverage, extracted rows, ledger, dataset saves) are guarded by one process-wide lock (`app/data/store_lock.py`); network and model calls stay outside it (`tests/test_store_lock.py`). Progress: `GET /api/ops/coverage-progress` (`india`, `us`).

Model budget at 48k pieces: about 40 calls per Indian company (35–40 filings) and 20–40 per US company, roughly 20k calls for the Nifty 500 back to FY22 and 14k for the S&P 500; most filings fit in one piece. AI Studio project spend caps apply: a capped project returns 429 "exceeded its monthly spending cap" and the walk pauses the model for the day. On a 38k-character SEC release, one 48k call cost 28% less than four 12k calls and found the same guidance. Free-tier keys run out in minutes; a paid key is needed for full coverage. Production model: Gemini 3.8 Flash (`gemini_chat_model`), filing reads on the Flex tier (`INTELLENS_DISCLOSURE_SERVICE_TIER=flex`, half price, 10-minute timeout, last retry on standard). Introductory price $0.75 / $3.75 per 1M tokens (Flex $0.375 / $1.875) until 31 Dec 2026, doubling on 1 Jan 2027. Production pace: each walk sends `INTELLENS_DISCLOSURE_READ_WORKERS=16` pieces at once under `INTELLENS_LLM_RATE_PER_MIN=200` and `INTELLENS_EXTRACT_LLM_DAILY_CAP=100000`; India filing fetches are capped at 40,000 a day. A 429 or 503 from the model is retried after 5 s and 20 s before it counts as a failure.

## Tests

`tests/test_disclosures.py`, `tests/test_sec_filings.py`, `tests/test_us_release_rules.py`, `tests/test_coverage_india.py`.

## Whitespace programme

Making this walk the only India extractor, guarding matches, and reviewing threads into the ranked index is `docs/PLAN_WHITESPACE.md` (WS0–WS4). The walk’s reconcile rules stay here.
