# 19 — Reuse what exists; read a source once

Standing rule for every change. Owners below are the only implementation. A stored filing, extract, listing, or score is reused. The network or the model runs only for a URL or chunk the store does not have.

Rules: `reuse-before-add`, `source-once`. Skill: `citealpha-reuse-sources`.

## Before adding a module, route, page, or fetch

1. Search this table and the progress logs in `docs/PLAN_WORLDCLASS_GCI.md` §7, `docs/PLAN_CITEALPHA_ANALYST.md` §11, and `docs/PLAN_WHITESPACE.md` §8.
2. Extend the owner. Add a new file only when the owner cannot express the case, and add a row here in the same change.
3. Call the lookup. Do not open a second client for NSE, BSE, EDGAR, issuer sites, FMP, or Gemini.

The browser does not call those hosts. UI goes through `frontend/src/lib/api.ts`.

## Owners

| Job | Owner | Store / skip |
|---|---|---|
| Filing bytes, any market | `app/data/doc_store.py` | `find_by_url` (`url_key`), `find_by_hash`, `upsert_document` (same hash + company returns the row). Body over 4,000 chars in `doc_text/<hash>.txt` |
| India exchange + issuer filings | `services/exchange_filings.py` | `ingest_company_urls` records `already_stored` and does not GET |
| SEC results releases | `services/sec_filings.py` | `ingest_company` skips exhibit URLs already stored |
| Disclosure model read (48k) | `services/disclosures.py` | `{INTELLENS_DATA_DIR}/disclosures/{id}.json`. `read_documents` skips known chunk keys; a file fully read at 12k is not read again |
| Guidance extract (12k) | `services/extract_pipeline.py` | `llm_extract_ledger.json` `seen` map. Failed calls are retried; successes are not |
| Match, score | `services/matching.py`, `services/gci_scoring.py` | Pure. No HTTP. Lists read `data/gci_score_cache.py` `load_cache` |
| Coverage sentence | `services/coverage.py`, `india_coverage.py`, `us_coverage.py` | `coverage_status.json`. One status per scrip |
| India / US lists | `data/india_listings.py`, `data/us_listings.py`, `jobs/refresh_index_lists.py` | `data/listings/nifty500.json`, `data/listings/us_equity.json`. Refresh refuses a short file |
| Quote check | `services/source_verify.py` | Reads stored text. At most once per 24h when `INTELLENS_VERIFY_SOURCES=1` |
| Commitments (not GCI) | `services/commitments.py`, `commitment_store.py`, `commitment_extract.py`, `commitment_monitor.py` | `commitments.json` |
| Holdings look-through | `services/holdings.py` | Org file under `holdings/`. Reads `gci_score_cache` and the Commitment Record. Does not write a score. The saved file keeps the delivery tilt and the scheme change, and the page reloads that file. |
| Financial Ninja | `services/ninja.py`, `api/ninja_routes.py` | Worksheets from desk inputs, saved on the organisation file. Org-scoped layer notes and a five-question desk sheet per layer. Counts of the published delivery record. The company page shows cited quotes only, with no sheet level. Does not write a GCI. |
| Analyst model on a project | `services/agent/projects.py` | The analyst's figure, assumptions, sources, and what was not found. Does not write a GCI. |
| Analyst skills, runs, exports | `services/agent/*`, `app/skills/*.json`, `api/analyst_routes.py` | Runs, projects, monitors, uploads, house style, destinations under the data dir |
| Event filings | `services/event_filings.py` | Flag `ANALYST_EVENT_FILINGS` |
| Filing Search / chat | Research terminal (`/research`) | Not a second search stack |
| Sights pages that remain | `services/sights.py` | Themes, street, field, grid, deep dive, fundamentals. Flags: `SIGHTS`, `SIGHTS_DEEP_DIVE`, `SIGHTS_GRID`, `SIGHTS_WEB_ASSIST` |
| Prices (never in the GCI) | `services/fmp_client.py` | Optional EOD only |
| Shared JSON writes | `app/data/store_lock.py` | Documents, coverage, extracts, ledger, dataset saves. Network and model calls stay outside the lock |
| Product mail | `services/mailer.py` | SMTP if `SMTP_HOST` is set, otherwise SES when `INTELLENS_MAIL_TRANSPORT=ses`. Pilot intake notifies from `services/pilot_request.py`. The recorded-owner invite is `orgs.invite_recorded_owner` (same `create_invite` token) |

## Ledgers that already throttle a refetch

| File | Window |
|---|---|
| `filing_fetch_budget.json` | Daily filing fetch and discovery caps |
| `web_search_ledger.json` | Per company, every 30 days |
| `ir_crawl_ledger.json` | Per company, every 30 days |
| `llm_extract_ledger.json` | Chunk seen, plus the UTC-day model cap |
| `disclosures/{id}.json` | Chunk of that filing already read |

## Already shipped — do not add a second copy

From `docs/PLAN_CITEALPHA_ANALYST.md` §11 (through 2026-10-17): verifier, skills, monitors, projects, uploads, exports, digest, event skills, org API keys, public API, MCP, destinations, house style. UI is `/analyst` and `/analyst` settings.

Merged the same day, redirects or `410` + `moved_to`:

| Retired | Use |
|---|---|
| `/sights/search`, `/sights/ask`, `/sights/boards` | `/research` |
| `/sights/agents`, `/sights/export` | `/analyst` |
| `/api/radar/digest/*`, `/api/radar/webhooks` | Analyst digest and destinations |
| Desk Agents, Cite Export, Notify Hooks | `services/agent/` |

From `docs/PLAN_WORLDCLASS_GCI.md` §7: W1 (citeable PIT only, tiers, ledger, changelog) is done. Later rows shipped dual citation, labeling governance, source verify, copy sweep, OpenAPI allowlist, and the index files. Read §7 before starting a workstream id.

Filing walk (India Nifty 500, US S&P 500, FY22 extracts kept): `docs/kb/18-filing-walk.md`.

## Planned leftovers — extend the owner

| Leftover | Extend |
|---|---|
| Postgres + pgvector for analyst stores | `services/agent/run_store.py` and the JSON stores named in kb 17. Not a second runtime |
| Commitment panel on the dossier | `commitment_store` readers. The panel does not enter `gci_scoring` |
| Office add-in | `api/connector_routes.py` and `services/agent/public_api.py` |
| Sensex commitment review (A1 exit) | Reviewer actions on `api/analyst_routes.py`. Not a new extractor |
| W2 labeling depth | `citealpha-guidance-review` on stored filings. Do not refetch a `url_key` hit |

## When a second read is the right call

- No `url_key` and no content hash in `doc_store`.
- Chunk key missing from the disclosure file and from `llm_extract_ledger.json`.
- The matching ledger says the refresh window has elapsed (web search, IR crawl, nightly verify, index-list job).
- Tests pass `fixture_text` or a stub `fetch` and never hit the network.
