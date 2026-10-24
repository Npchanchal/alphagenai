# 17 — CiteAlpha Analyst

Cited research agent for seat users at `/analyst`. Plan: `docs/PLAN_CITEALPHA_ANALYST.md`.

## Flow

Skill spec → read-only tools (`profile`, `guidance_record`, `open_guidance`, `commitments`, `filing_search`, `peers`, `recent_filings`, `document_passages`) → claims with numbered citations → verifier → disproof pass → output + Evidence Receipt.

| Piece | File |
|---|---|
| Runtime + builders | `backend/app/services/agent/runtime.py` |
| Tools (read-only) | `backend/app/services/agent/tools.py` |
| Verifier (pure) | `backend/app/services/agent/verifier.py` |
| Skill loader / validation | `backend/app/services/agent/skills.py` |
| Skill specs | `backend/app/skills/*.json` — `results_prep`, `company_ramp`, `concall_questions`, `board_scorecard`, `coverage_monitor`, `peer_delivery_grid`, `diligence_room`†, `weekly_driver_review`† (†`requires_project`); India event Skills `corporate_action_brief`, `drhp_reader`, `usfda_watch`, `rating_tracker`, `debate_map` |
| Event filings (open offer, delisting, scheme, DRHP, USFDA, rating rationale) | `backend/app/services/event_filings.py` (`ANALYST_EVENT_FILINGS`) |
| Weekly digest | `backend/app/services/agent/digest.py` (`analyst_digest.json`) |
| Org API keys · public API v1 · MCP server | `services/agent/org_keys.py`, `services/agent/public_api.py`, `api/connector_routes.py` |
| Delivery destinations (webhook, Slack, Teams) | `services/agent/delivery.py` (`analyst_destinations.json`) |
| House style for exports | `services/agent/house_style.py` (`analyst_house_style.json` + `analyst_house_style/`) |
| Projects + memory | `backend/app/services/agent/projects.py` (`analyst_projects.json`) |
| Exports (Excel, PowerPoint, PDF, Markdown) | `backend/app/services/agent/exports.py` |
| Uploads (parse, store, search) | `backend/app/services/agent/uploads.py` (`analyst_uploads/<org hash>/`) |
| Run history (org-scoped) | `backend/app/services/agent/run_store.py` |
| Monitors + new-filing processor | `backend/app/services/agent/monitors.py` · job `python -m app.jobs.analyst_monitors [--status] [--no-email]` |
| UI | `frontend/src/pages/AnalystPage.tsx` (`/analyst?run=<id>` opens a saved run); settings panels in `frontend/src/pages/analyst/AnalystSettings.tsx` |
| Tests | `backend/tests/test_analyst_*.py` (agent, monitors, projects, exports, a2 follow-ups, a5 Skills + `golden/a5_cases.json`, connectors, house style, compliance sign-off) |
| Compliance sign-off record | `docs/compliance/ANALYST_SKILLS_SIGNOFF.md` (Skill versions + export layout version; human approver still pending) |

## Monitors

An org's standing instruction: when a company files something new, run a Skill and deliver it. Scope is one company, the creator's watchlist (`preferences.watchlist`, read at run time), or a Project's company list (project-only Skills can only be monitored this way). The processor compares the document store with the document IDs it has already seen (`analyst_monitors.json`).

- **First run = baseline.** Existing documents are recorded and nothing runs, so a new deployment does not flood feeds.
- **What counts as a new filing:** sources from an ingestion path only (`exchange_filing`, `ir_catalog`, `paste`, `plain_text`, `html_fetch`, `ingest`) with a URL. Documents CiteAlpha generates itself (corpus packs, outcome excerpts, demo transcripts) are marked seen and never trigger.
- **Each new filing:** (1) commitment proposals queued as `unreviewed` with `proposed_by = auto:commitment_extract` (a reviewer must accept); (2) each matching Monitor runs its Skill with a first section "What the new filing says", quoting forward-looking sentences from that filing only; (3) the run is saved to the org's history (the feed) and emailed if the Monitor has an address (`mailer.send_mail`, SES or SMTP; stubbed when neither is set; link `/analyst?run=`).
- A failing Monitor or email does not stop the batch. Nothing here writes to the GCI or accepts a commitment.
- Runs after every GCI refresh when `ANALYST_MONITORS` is on (default on; tests set it off in `conftest.py`).
- Results also go to the org's delivery destinations subscribed to `monitor.run`.

## Weekly digest

Per org, at most once every seven days from the refresh loop, to up to 10 email recipients and destinations subscribed to `digest.weekly`. Covers the companies the org's Monitors cover: new filings in the window, Skill runs saved, guidance changes from the Radar feed not sent before (`seen_changes`), and reviewed commitments due in 30 days or past due. Nothing is sent in a week with nothing new. This replaced the Radar digest and the Radar webhook stub (`/api/radar/digest/*` and `/api/radar/webhooks` now return `410` with `moved_to`).

## Connectors

- **Org API keys:** owners/admins create up to the per-org limit; role `analyst` (run + read) or `viewer` (read). Shown once, stored as SHA-256. Rate limit `PUBLIC_API_RPM` per key (default 60).
- **Public API v1:** `/api/v1/analyst/skills`, `…/companies/{id}/commitments`, `…/companies/{id}/search`, `…/runs`, `…/runs/{id}`, `…/runs/{id}/export`. Org keys cannot reach operator routes.
- **MCP server:** `POST /api/mcp` (protocol `2025-06-18`); tools `list_skills`, `get_gci` (published numbers only), `get_commitments`, `search_filings`, `run_skill`, `get_run`.
- **Destinations:** Slack (`hooks.slack.com`), Teams (`*.webhook.office.com`, Logic Apps, Power Platform) and HTTPS webhooks (HMAC-signed, private hosts refused). Test button sends a one-line message.

## House style

Owners/admins set firm name, two colours, font, footer, classification, a logo (PNG/JPEG ≤ 500 KB) and optionally a PowerPoint template (.pptx/.potx ≤ 5 MB; its slide master is used). Every export keeps the disclaimer, "Data as of", run id, source footers and the Evidence Receipt regardless of style (`test_analyst_compliance_signoff.py`). Export layout version is `exports.LAYOUT_VERSION`; changing it requires a new sign-off row.

## Projects and uploads

- A Project belongs to one org: name, company list, memory items, model figures, files. Another org gets `404` on every Project route and its files never enter retrieval (`project_uploads` filters by org and Project).
- A model is a figure the analyst enters, with assumptions, sources, and what was not found. It is not a published GCI.
- Memory is plain text the user sees and deletes. It steers the optional model summary as "Analyst focus (not a source)" and is never cited.
- Files are parsed once into passages with a location; the original bytes are not kept. Cites read `file (location) — your upload` with `source_url = upload://<id>#<loc>` (shown as text, not a link).
- A run with `project_id` requires the company to be in the Project (`422`). Skills with `requires_project` refuse without one and cannot be Monitors.
- Weekly Driver Review reads driver names from the first column of uploaded sheets (matched to `DRIVER_TERMS`) and lists filings from the last 7 days that mention each driver. Diligence Room cross-checks figures and forward statements in uploads against the closest filing passage and lists checklist items no file covers.

## Exports

Rendered from the saved run (`run_store`), so the Evidence Receipt in each file is the run log. Links are absolute via `INTELLENS_PUBLIC_URL`.

- **Excel:** Brief (section, statement, sources), one sheet per section whose claims carry a `row` (Peer Delivery Grid, delivery record), Sources, Evidence receipt (fields, quote SHA-256 per source, tool calls). Every sourced cell has a comment with the quote(s) and a hyperlink to `/c/{id}`, else the public source. Strings starting with `=` are written as text.
- **PowerPoint:** 16:9, six bullets per slide, a "Sources:" footer with linked titles on every content slide, then Sources and receipt slides.
- **PDF memo / Markdown:** same content as text; PDF is ASCII-only (`pdf_minimal`).
- Quotes are the stored spans only (≤ 400 characters); upload cites read "your upload" and carry no link.
- Adding a table to an export: pass `row={...}` to `_claim` with cells that restate the sentence's own figures.

## Verifier rules

- Claim kinds: `quoted` (model or filing text — every number must appear in a cited quote, plus one shared content word), `record` (reviewed dataset row) and `computed` (counts derived by code) — both need citations, skip the number check.
- Advice wording is removed even with a citation.
- Output with zero kept claims is `refused`.

## Access

Feature `analyst_agent` on plans pilot / desk / enterprise / onestop, roles analyst / reviewer / admin / owner. Guests `401`, retail `403`. `include_unreviewed` only honoured with `labeling`.

## Flags

`ANALYST_LLM` (default off) adds a model-written summary; every sentence still goes through the verifier. Model id is logged in the receipt.

`ANALYST_MONITORS` (default on) processes new filings for Monitors at the end of each refresh.

`ANALYST_EVENT_FILINGS` (default off) pulls NSE event announcements (open offers, delisting, schemes, DRHP, USFDA, rating rationales) for the event Skills during refresh.

`PUBLIC_API_RPM` (default 60, minimum 5) per-key limit on `/api/v1` and `/api/mcp`.

## What moved here from other surfaces (2026-10-17)

| Was | Now |
|---|---|
| Disclosure Explorer Desk Agents (`/sights/agents`, `/api/sights/agents*`) | Analyst Skills |
| Disclosure Explorer Cite Export + Notify Hooks (`/sights/export`, `/api/sights/export/*`, `/api/sights/hooks`) | Analyst exports + destinations |
| Radar digest + webhook stub (`/api/radar/digest/*`, `/api/radar/webhooks`) | Analyst weekly digest + destinations |

Old API paths return `410` with `moved_to`; old pages redirect to `/analyst`.

## Adding a Skill

Drop a JSON spec in `backend/app/skills/` using known builders (`skills.KNOWN_BUILDERS`). `test_all_skill_specs_valid_and_use_known_builders` and `test_skill_copy_is_factual` must pass.
