---
name: citealpha-reuse-sources
description: >-
  Finds the existing CiteAlpha owner and the stored copy before adding a
  service, route, page, job, or external fetch. Use when adding features,
  fetching filings, listings, scores, or documents, calling NSE, BSE, EDGAR,
  SEC, or a model, or when a plan item might already be shipped.
---

# Reuse the owner, read the source once

## When

Any new module, route, page, job, or outbound fetch. Also when a task sounds like search, ask, export, monitors, filings, coverage, commitments, or a second GCI.

## Steps

1. Read [docs/kb/19-reuse-and-source-once.md](../../../docs/kb/19-reuse-and-source-once.md).
2. Search the plan progress log before writing code:
   - `docs/PLAN_WORLDCLASS_GCI.md` §7
   - `docs/PLAN_CITEALPHA_ANALYST.md` §11
   - `docs/PLAN_WHITESPACE.md` §8
3. Search for the noun (`rg` the module names in the kb table). Hit means extend that file.
4. For a URL or filing body, call `doc_store.find_by_url` first. For a model read, call `disclosures.load_extracts` and skip chunk keys already present.
5. Wire the new behavior through the owner. Add a test that a second call does not fetch: `already_stored`, `chunks_already_read`, or an unchanged ledger count.
6. If the owner truly cannot express the case, add a function in that module and one row to kb 19 in the same change. Do not create `*_v2.py` or a second page.

## Decide

| You were about to… | Do this instead |
|---|---|
| Fetch an NSE, BSE, or issuer PDF | `exchange_filings.ingest_company_urls` (skips `url_key` hits) |
| Fetch an SEC 8-K exhibit | `sec_filings.ingest_company` (skips stored exhibit URLs) |
| Send filing text to a model | `disclosures.read_documents` (India guidance writer: `docs/PLAN_WHITESPACE.md`). `extract_pipeline.extract_company` is the ledger/fallback helper, not a second writer |
| Score a company | `gci_scoring` via repository; read `gci_score_cache.load_cache` for lists |
| Add numeric guidance | Outcome row on the GCI path. Commitments are not guidance |
| Add a non-numeric promise | `services/commitments.py` + `commitment_store.py` |
| Add a research skill or export | `backend/app/skills/*.json` and `services/agent/` |
| Add search or cite-only chat | `/research` and `services` behind `lib/api.ts` |
| Refresh Nifty 500 or S&P 500 | `python -m app.jobs.refresh_index_lists` |

## A second fetch is allowed only when

- The store has no row for that `url_key` or content hash.
- The chunk key is absent from the disclosure cache and from `llm_extract_ledger.json`.
- A scheduled refresh is inside its own ledger window (`web_search_ledger.json` 30 days, `ir_crawl_ledger.json` 30 days, index-list job, nightly source verify at most once per 24h).
- A test passes `fixture_text` or a fake `fetch` and does not touch the network.

## Do not rebuild

Shipped and merged: see the "Already shipped" section of kb 19. Analyst leftovers (Postgres, dossier commitment panel, Office add-in) extend `services/agent/` and `services/commitment*.py`. They are not a new product.
