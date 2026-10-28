# 05 — API Map

Base: FastAPI `backend/app/api/routes.py`. Public OpenAPI (`/docs`, `/openapi.json`) is the W8.5 allowlist — 40 paths or fewer. Other routes stay callable and are omitted from the spec.

## Core GCI

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | Liveness |
| GET | `/api/meta` | Version, gaps, `gci_algorithm`, `pending_depth`, flags; `gci_scored_count` (scoreable quality with a score), `gci_listing_unscored_count`, `sensex_scored_count` / `sensex_count`; `gci_coverage` tallies; `filing_to_score` (W2.8 target + observed median); `published_gci_count` / `published_ranked_count` from `repository.list_published_companies()` (the one count every public page states) |

**Score policy:** only `hand_labeled` companies carry a public `gci_score`. Listings and demo companies return `score: null` with status `not_yet_scored` (see `services/score_policy.py`). Outcome rows may include `revisions[]`, `revision_direction` (raised/cut/unchanged), `final_guided_low/high` and a context-only `final_label`; the score always uses the opening band.
| GET | `/api/ops/pending-depth` | Depth backlog + optional `?bootstrap=true` |
| POST | `/api/ops/pending-depth/bootstrap` | Nifty M2 enqueue + PIT warehouse ensure |
| GET | `/api/ops/corpus-coverage` | Sensex hand_labeled Tier-1 gate rollup |
| GET | `/api/public/seo-dossiers` | Hand-labeled dossier titles/descriptions for prerender + sitemap (W5.2) |
| GET | `/api/og/{id}.png` · `/api/og/{id}.svg` | OG share card (W5.3) |
| GET | `/api/v1/companies` · `/{id}/gci` · `/{id}/gci/history` · `/api/v1/rankings` | Public-read aliases (W8.5) |
| GET | `/api/v1/index/files` · `/files/{name}` | Frozen daily GCI CSV + Parquet + checksum (W9.2). S3 when `INTELLENS_INDEX_S3_BUCKET` is set |
| GET | `/api/v1/index/digest` | Weekly ledger-move email preview (W9.6). Send via `python -m app.jobs.ledger_digest` |
| GET | `/api/companies/count` | Pagination |
| GET | `/api/entitlements/me` | Plan × role intersection (`features`, `limits`). Guest: `tracker` only |
| GET | `/api/companies/{id}/gci` | Full dossier payload; guest sessions cap at 15 opens (`403` `guest_dossier_cap` — paywall modal, not GCI change). Carries `coverage_status`, `coverage_reason` (plain sentence when there is no number, e.g. "First guided year (FY27) closes Mar 2027"), `confidence_tier`, `closed_periods`, `metrics_scored`, `as_of`, `algorithm_id`, `by_metric` (composite) + `context_metrics` (< 2 closed periods). No `sentiment`. |
| GET | `/api/companies/{id}/gci/history` | PIT points + Δ (citeable outcome as-of only) |
| GET | `/api/companies/{id}/changes` | WoW/MoM/QoQ/YoY — numeric only when `series_kind == "citeable_pit"` (≥ 4 reviewed dates); else `null` + `note` |
| GET | `/api/companies/{id}/analytics` · `/api/stocks/{id}/history` | **Seat-only** (`analytics_experimental`). Experimental — synthetic inputs; `401`/`403` for guests |
| GET | `/api/companies/{id}/wordmap` | **Seat-only** (`wordmap`) |
| GET | `/api/alerts` | Misses / dropped |
| GET | `/api/products` | Portfolio SKU catalog (Score / Cite / Radar / Ledger / Data / Sights / Holdings) |
| POST | `/api/holdings/lookthrough` | Dated holdings file → covered published GCI, gaps, residual, delivery tilt, and scheme change from values in the file. Feature `holdings`: paid desk, or an admin-approved pilot inside 30/45/60 days. An approved term that has ended closes the pilot desk. |
| GET | `/api/holdings/latest` | Last holdings file for the caller's org, plus `last_opened_at` and `since_last_open` (accepted filings ingested since that time, open guidance, published misses; three filings per name) |
| POST | `/api/ninja/worksheets/{template}` | Valuation worksheet from numbers the desk enters. Saved on the organisation when `company_id` is set. Feature `ninja`. Not a published GCI. |
| GET | `/api/ninja/worksheets` | Latest saved worksheet and recent history for `company_id` and optional `template` |
| POST | `/api/ninja/observations` | Cited note on accounting, causality, conduct, or execution |
| DELETE | `/api/ninja/observations/{obs_id}` | Remove one cited note from this organisation |
| POST | `/api/ninja/ratings` | One 0–4 desk rating on a named question. Requires a quote and a source. Not a published GCI. |
| GET | `/api/ninja/indices` | Universe stock listing plus the specification delivery worksheet, score heatmap, and filing chronology for every company with a closed, cited guidance row. Feature `ninja`. Not a published GCI. |
| GET | `/api/ninja/indices/{company_id}` | Note share (blank under three cited notes), desk layer sheet, delivery worksheet, and filing chronology. Optional `period`. |
| GET | `/api/ninja/profile/{company_id}` | Cited layer text for the dossier. No index level and no rating score. Empty for a guest |
| GET | `/api/ninja/tests` | Counts on the published delivery record, with the rows behind each count. A thin comparison withholds the miss share. |
| GET | `/api/ninja/taxonomy` | Sectors already stored on companies |
| POST | `/api/analyst/projects/{project_id}/models` | Analyst-owned model figure on a project |
| GET | `/api/radar/feed` | CiteAlpha Radar change feed |
| GET | `/api/ledger/{company_id}` | CiteAlpha Ledger promise dossier |
| GET | `/api/data/catalog` | CiteAlpha Data export contracts |
| GET | `/api/sights/meta` | CiteAlpha Sights catalog + flags + refuse list |
| GET | `/api/sights/search` | Deprecated alias of `/api/research/search?expand=true` (`superseded_by`) |
| POST | `/api/sights/ask` | Deprecated alias of `/api/research/chat` with `expand` (`superseded_by`) |
| GET | `/api/sights/themes` | Delivery Themes |
| GET | `/api/sights/street/{id}` | Street Context (not broker notes) |
| GET | `/api/sights/field/{id}` | Field Evidence |
| POST | `/api/sights/grid` | Compare Grid (`SIGHTS_GRID`) |
| POST | `/api/sights/deep-dive` | Deep Dive (`SIGHTS_DEEP_DIVE`) |
| GET | `/api/sights/fundamentals/{id}` | Fundamentals Strip |
| GET | `/api/sights/agents` · POST `/api/sights/agents/run` | `410`, `moved_to` `/api/analyst/skills` · `/api/analyst/run` |
| GET | `/api/sights/hooks` | `410`, `moved_to` `/api/analyst/destinations` |
| GET | `/api/sights/export/{id}` | `410`, `moved_to` `/api/analyst/runs/{run_id}/export` |
| GET | `/api/sights/enterprise` | Trust / SSO / billing deep-links |
| GET | `/api/radar/diff/{company_id}` | QoQ guidance diff brief |
| GET | `/api/radar/calendar` | Open promise / result windows |
| GET · POST | `/api/radar/digest/preview` · `/digest/send` | `410`, `moved_to` `/api/analyst/digest` |
| POST | `/api/radar/webhooks` | `410`, `moved_to` `/api/analyst/destinations` |
| GET | `/api/ledger/{company_id}/pdf` | Ledger PDF (API key) |
| GET | `/api/ledger/mirror/{company_id}` | IR Mirror (`IR_MIRROR=1`) |
| GET | `/api/cite/tiers` · `/api/cite/usage` | Cite API commercial tiers |
| GET | `/api/data/export/outcomes` | Bulk outcomes JSON/CSV/Parquet |
| GET | `/api/digest/vernacular/{company_id}` | Factual vernacular digest |
| GET | `/api/data/kpi-dictionary` | Metric ontology |
| GET | `/api/score/narrative-consistency/{id}` | NCI beta |
| GET | `/api/channel/trust-badge/{ticker}` | Broker badge channel |
| GET | `/api/workbench/extraction` | Ops workbench stub |
| GET | `/api/peers/{sector}` | Sector benchmark |

## Write / pipeline (session or API key; `require_feature`)

Writes are gated by **plan × role intersection**. Guest Bearer cannot piggyback `intellens-demo`. CSV/Parquet EM export needs `em_export` (Enterprise / One-Stop). Research chat / Sights Ask need `research_chat` / `sights_ask`.

| Method | Path |
|---|---|
| POST | `/api/extract`, `/api/extract/commit`, `/api/extract/pending` |
| POST | `/api/match` |
| POST | `/api/review` · GET `/api/reviews` | Accept, edit, reject: `reviewer`, `admin`, `owner` only (`403` otherwise, row unchanged). Each decision writes `review_accept` / `review_edit` / `review_reject` to `/api/audit` with the person; a bare key is recorded as `api_key:<hash>` |
| POST | `/api/labeling/drafts` · submit/accept/reject · `/api/labeling/import` |
| GET | `/api/labeling/companies` · `/api/labeling/drafts` |
| POST | `/api/companies/{id}/audit-flags` · DELETE `…/audit-flags/{flag}` (analyst-set; labeling) |
| POST | `/api/feedback` · GET `/api/feedback` (does not mutate GCI; quality kinds enqueue labeling-queue) |
| POST | `/api/activity/cite-copy` | Habit ping (no quote text); guests allowed |
| POST | `/api/orgs/{id}/partner-invite` · `/members/{user_id}/role` | Body `role`, optional `company_scope` (IR only; ids must be covered companies, else `400`). Writes `seat_change` to `/api/audit`. `/api/audit` reads with feature `org_audit` (oversight, reviewer, admin, owner) |
| POST | `/api/import/alphahunter` |
| POST | `/api/ingest/paste`, `/text`, `/url`, `/bootstrap`, `/media` |
| POST | `/api/ingest/crawl` · GET `/api/ingest/crawl/status` |
| POST | `/api/ingest/refresh` | live 6h job: crawl + extract queue + FMP warm |
| POST | `/api/actuals/import`, `/api/consensus/import` |
| POST | `/api/admin/reset-demo` | platform `system.ops` only — wipes JSON store **and** persisted tenant state |

## Platform admin portal

Requires `platform_admin_role` on session user or API key. See `docs/ADMIN_PORTAL.md`.

| Method | Path | Permission |
|---|---|---|
| GET | `/api/admin/portal/me` | any platform role |
| GET | `/api/admin/portal/orgs` | `orgs.read`. Each org includes `members` (seat logins), `deletable`, and `delete_block` |
| DELETE | `/api/admin/portal/orgs/{id}` | `orgs.write`. Empty organisations only. Standing desks (`demo`, `retail`, `onestop-demo`, `citealpha-team`, `protected`) return 400. Occupied seats return 409 |
| GET | `/api/admin/portal/users` | `users.read` |
| PATCH | `/api/admin/portal/users/{id}/platform-role` | `users.write` (super) |
| DELETE | `/api/admin/portal/users/{id}` | `users.write` (super). Frees the seat. Standing team accounts and the signed-in account return 400 |
| GET/PATCH | `/api/admin/portal/feedback` | `feedback.read` / `feedback.write` |
| GET/POST | `/api/admin/portal/legal` · `/legal/attest` | `legal.read` / `legal.write` |
| GET | `/api/admin/portal/billing` | `billing.read` |
| GET | `/api/admin/portal/audit` | `audit.read` |
| GET | `/api/admin/portal/board` | any platform role. Queue counts the role can open |
| GET | `/api/admin/portal/labeling` | `audit.read`. Open queue, pending extracts, source-check failures |
| GET | `/api/admin/portal/commitments` | `audit.read`. Unreviewed commitments |
| GET | `/api/admin/portal/system` | `system.ops` |
| GET | `/api/admin/portal/reports` | catalog for the caller's permissions |
| GET | `/api/admin/portal/reports/{id}` | `index`, `coverage`, `sla`, `audit-events` (`audit.read`); `usage` (`billing.read`); `trust` (`legal.read`). `?format=csv` on `audit-events` |
| POST | `/api/admin/portal/billing/invoices` | `billing.write` |
| POST | `/api/admin/portal/pilot` | `pilot.manage` |

## Research

`/api/research/search`, `chat`, `snapshot/{id}`, `estimates/{id}`, `brief/{id}`, `news`, `watchlist`, `transcripts`

`GET /api/research/search?q=&company_id=&expand=` — a research seat may omit `company_id` to search all covered companies. `expand=true` adds India IR synonyms and returns `original_query` / `expanded_query`. A caller without that seat searches one company with a published GCI (`GET /api/companies?scored=true`) and is counted to 8 on the account or the `citealpha_reading` cookie. `GET /api/research/reading-room` reports the count and does not increment it. `GET /api/filings/recent` returns the newest accepted filing per source URL, with no filing text. `POST /api/research/chat` takes the same `expand` flag.

| Method | Path | Notes |
|---|---|---|
| GET | `/api/citations?company_id=` | Citeable outcome records + bibliographic / markdown / IC footnote |
| GET | `/api/citations/{citation_id}` | Lookup `cite_*` (outcomes) or document fingerprint; includes `document_text`, span offsets, `highlight_url` |
| GET | `/api/documents` | Indexed corpus list. `?url=` returns the stored filing for that URL (`find_by_url`), or `count: 0` |
| GET | `/api/documents/{doc_id}` | One filing/transcript body for in-app highlight |
| POST | `/api/research/chat` | Cite-only; numbered `[1]` markers bound to citation objects |
| GET | `/api/research/watchlist` | Optional `ids=` or Bearer `preferences.watchlist`; else default slice |
| GET | `/api/trust` | Public Trust Center (security + CSP, residency, SSO, citations, source-link verification n of N, filing-to-score SLA, labeling governance, counsel, subprocessors) |

## Product extras

| Path | Purpose |
|---|---|
| `/api/vernacular/{id}` | Lang blurbs |
| `/api/badge/{ticker}` (+ `/svg`) | Embed **GCI** badge (`data-citealpha-badge`; ticker, score, tier, as-of). Not a Trust Score. |
| `/api/compliance/sebi-note` | Disclaimer text + Ocotillo entity |
| `/api/legal/meta` · `/terms` · `/privacy` | Copyright, Terms, Privacy (counsel_status, contact_email) |
| `/api/export/em-factor/{id}` | Factor export · honest `series_kind` |
| `/api/v1/pit/contract` · `/companies/{id}/history` · `/bulk` | Design-partner PIT contract (`series_kind_enum`: citeable_pit · citeable_pit_short · hand_labeled_incomplete_citations · not_yet_scored) |
| `GET /api/v1/index/ledger?company_id=&limit=&as_of=` | Append-only score ledger (`score_ledger.jsonl`); one row per published level; `as_of` drops later rows |
| `GET /api/v1/index/levels?as_of=` | Level per company as published on a date, rebuilt from the ledger |
| `GET /api/v1/index/evidence?checksum=` | Stored filing metadata for a SHA-256 content hash (no text) |
| `GET /api/v1/index/changelog?company_id=` | Public changelog (`score_changelog.json`), feeds `/changelog` |
| `/api/reports/generate` | IC audit dossier markdown/json/pdf |
| `/api/public/gci-rankings` | Citeable-only public rankings |
| `/api/ops/throughput` | Extract→review citeable backlog |
| `/api/orgs/pilot` · `/orgs/{id}/pilot-checklist` | Pilot template + conversion checklist (`activity.dossier_opens` / `citations_copied`) |
| `/api/csm/{org_id}` | CSM dashboard + `labeling_audit` (submitter/reviewer ids) |
| `/api/metrics` | Parameter catalog |
| `/api/auth/*` | Register (B2B desk + terms; retail 403 until `sebi_retail`), login, guest, verify-email, password-reset, accept-invite, SSO |
| POST | `/api/pilot-request` | Public pilot intake (abuse challenge; stored as pending). Mails `PILOT_REQUEST_TO` via `mailer.send_mail` (SES or SMTP). A mail failure still stores the request |
| GET/PATCH/DELETE | `/api/admin/portal/pilot-requests` | List / approve / reject / delete inbound pilot requests (`pilot.manage`). Approve requires `term_days` of 30, 45, or 60 and that choice starts the evaluation clock. Reject leaves the request closed. A mail failure still approves. Delete removes the request. A provisioned organisation stays |
| POST | `/api/admin/portal/orgs/{id}/owner-invite` | `pilot.manage`. Send that link again to the recorded owner. 400 without an email, 409 if that email already has a login |
| POST | `/api/admin/portal/cleanup-test-tenants` | `system.ops`. Drops `e2e-*` orgs, `@ocotillo.test` users, and guests. `dry_run` defaults on. Approved pilot orgs and `@citealpha.com` accounts stay |
| `/api/orgs/{id}/invites` · `/revoke` · `/members` · `/api-keys` · `/oidc` | B2B seat admin. Owner appoints `admin`; an admin cannot. Another organisation returns `403` Org mismatch |
| `/api/infra/postgres` | DB readiness |
| `/api/markets`, indexes, history | Multi-market scaffold |

## CiteAlpha Analyst + Commitment Record (`backend/app/api/analyst_routes.py`)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/analyst/skills` | Skill specs (`backend/app/skills/*.json`) + tool list. Feature `analyst_agent` |
| POST | `/api/analyst/run` | `{skill_id, company_id, include_unreviewed?, project_id?}` → cited sections, `not_found`, `citations`, `verifier`, `evidence_receipt`, `markdown`. Run saved per org |
| GET | `/api/analyst/runs` · `/runs/{run_id}` | Org-scoped history; another org gets `404` |
| GET | `/api/analyst/runs/{run_id}/export?format=` | `xlsx` (comment + `/c/{id}` link on every sourced cell) · `pptx` (source footers) · `pdf` · `md`; each ends with the Evidence Receipt. Own org only (`404`); bad format `422`. An `ir` seat exports the board pack (`pack_export`) for companies in its `company_scope` only; empty scope `403` with a sentence; each export writes `pack_export` to `/api/audit` |
| GET | `/api/analyst/feed` | Org's Monitor-triggered runs only, each with `trigger` (new filing title/date) |
| GET · POST | `/api/analyst/monitors` | List / create `{skill_id, scope: company\|watchlist\|project, company_id?, project_id?, email?}`; 25 per org (`409` over); same target+Skill returns the existing Monitor. Watchlist needs a signed-in user |
| GET · PUT | `/api/analyst/digest` | Weekly digest settings `{enabled, emails}` (≤ 10) + this week's preview text |
| POST | `/api/ops/analyst/digest/send?force=` | Write key. Send due digests now |
| GET · POST · DELETE | `/api/analyst/keys` · `/keys/{key_id}` | Org owner/admin. Create returns the key once |
| GET · POST · DELETE | `/api/analyst/destinations` · `/{id}` · POST `/{id}/test` | Org owner/admin. `{kind: webhook\|slack\|teams, url, events, label?}`; webhook secret returned once |
| GET · PUT · DELETE | `/api/analyst/house-style` | Read: any analyst seat. Write/reset: owner/admin |
| POST · DELETE | `/api/analyst/house-style/template` · `/house-style/{template\|logo}` | `{filename, content_base64}` .pptx/.potx ≤ 5 MB (nginx 15 MB on this path) |
| GET | `/api/analyst/house-style/preview` | Sample deck in the org's style, no company data |
| GET · POST | `/api/v1/analyst/skills` · `/companies/{id}/commitments` · `/companies/{id}/search` · `/runs` · `/runs/{id}` · `/runs/{id}/export` | Org API key (`Authorization: Bearer ca_…`); `PUBLIC_API_RPM` per key |
| GET · POST | `/api/mcp` | MCP server (JSON-RPC, protocol `2025-06-18`) with an org key |
| DELETE | `/api/analyst/monitors/{monitor_id}` | Own org only (`404` otherwise) |
| GET · POST | `/api/analyst/projects` | List / create `{name, company_ids}`; 50 per org |
| GET · PATCH · DELETE | `/api/analyst/projects/{project_id}` | Own org only (`404` otherwise); delete removes its files |
| POST · DELETE | `/api/analyst/projects/{project_id}/memory` · `…/memory/{memory_id}` | `{text}` up to 500 chars, 100 items |
| POST | `/api/analyst/projects/{project_id}/uploads` | `{filename, content_base64}`; PDF/DOCX/XLSX/CSV/TXT/MD, 10 MB, 20 per Project; `422` on unreadable files. nginx allows 15 MB on this path only |
| DELETE | `/api/analyst/projects/{project_id}/uploads/{upload_id}` | Own org only |
| GET | `/api/ops/analyst/monitors/status` | Write key. Baseline date, seen documents, Monitor count |
| POST | `/api/ops/analyst/monitors/process?limit=` | Write key. Process new filings now (first call = baseline only). Also runs after each refresh (`ANALYST_MONITORS`) |
| GET | `/api/commitments/meta` | Types, states, quiet-drop rule |
| GET | `/api/companies/{id}/commitments` | Accepted rows + plain-count summary. `?include_unreviewed=true` only for seats with `desk` |
| POST | `/api/commitments/propose` · `/extract` | Feature `labeling`; rows land `unreviewed`. Extract quotes must be verbatim |
| POST | `/api/commitments/{id}/review` · `/transition` | Reviewer / admin / owner only; transitions need a proof citation |
| POST | `/api/companies/{id}/commitments/quiet-drop-scan` | Proposals only |

## Frontend contract

All UI calls go through `frontend/src/lib/api.ts`. Do not add ad-hoc `fetch` in pages without updating that module + types.
