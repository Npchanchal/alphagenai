# User Stories — CiteAlpha GCI MVP

## US-001 — List companies
**As a** buy-side analyst  
**I want** to see covered companies with their GCI scores  
**So that** I can spot weak guidance track records quickly.

**Acceptance**
- Given the API is running with seed data  
- When I open the home page or `GET /api/companies`  
- Then I see multiple companies each with `id`, `name`, `ticker`, and `gci_score`

## US-002 — View company GCI detail
**As a** buy-side analyst  
**I want** to open a company and see score breakdown and evidence  
**So that** I can trust and audit the number.

**Acceptance**
- Given a valid company id  
- When I open its detail page or `GET /api/companies/{id}/gci`  
- Then I see overall score, metric breakdown, and a list of outcomes with guided vs actual

## US-003 — Evidence trail
**As a** sell-side associate  
**I want** each outcome to show guidance text and delta  
**So that** I can cite it in research.

**Acceptance**
- Given a company with ≥1 outcome  
- When I view the evidence table  
- Then each row includes period, metric, guided_value, actual_value, delta_pct, and guided_text

## US-004 — Deterministic scoring
**As a** product engineer  
**I want** GCI scoring to be pure and tested  
**So that** scores do not drift silently.

**Acceptance**
- Given fixed outcome fixtures  
- When `compute_company_gci` runs (default **v4**; `INTELLENS_GCI_VERSION=v3` or legacy `v2`)  
- Then the score matches the golden expected value in unit tests (`test_gci_scoring*.py`)

## US-005 — Health / deploy readiness
**As an** operator  
**I want** a health endpoint and containerized deploy  
**So that** I can run the stack locally and in CI.

**Acceptance**
- Given containers are up  
- When I `GET /health`  
- Then I receive `{"status":"ok"}` and the UI loads

## US-006 — Empty / edge company
**As a** system  
**I want** companies with no outcomes to return a clear empty state  
**So that** the UI does not crash.

**Acceptance**
- Given a company with zero outcomes  
- When GCI is requested  
- Then score is `null` or explicit `insufficient_data` and UI shows an empty message

---

## Portfolio SKUs (parallel products)

## US-P01 — Product catalog
**As a** prospect or desk lead  
**I want** to see CiteAlpha’s parallel product lines  
**So that** I can buy the job I need (not only GCI seats).

**Acceptance**
- Given the API is running  
- When I `GET /api/products` or open `/products`  
- Then I see Score, Cite, Radar, Ledger, and Data with status and endpoints

## US-P02 — Radar feed
**As a** portfolio manager  
**I want** a guidance change / miss / drop feed  
**So that** I catch accountability events without rereading every transcript.

**Acceptance**
- Given seeded outcomes and alerts  
- When I `GET /api/radar/feed`  
- Then I receive severity-ranked items with company, kind, and message (no trading signals)

## US-P03 — Promise ledger
**As a** compliance or credit analyst  
**I want** a company promise ledger  
**So that** I can audit what was promised vs delivered with sources.

**Acceptance**
- Given a valid company id  
- When I `GET /api/ledger/{id}`  
- Then I see closed outcomes and open promises with source fields and a factual disclaimer

## US-P04 — Data catalog
**As a** quant buyer  
**I want** a discoverable export catalog  
**So that** I know which PIT / factor endpoints to license.

**Acceptance**
- Given the API is running  
- When I `GET /api/data/catalog`  
- Then I see export ids, paths, and formats without invented actuals

## US-P05 — Guidance diff brief
**As a** portfolio manager  
**I want** QoQ guided band deltas on a company  
**So that** I see language/range changes without rereading transcripts.

**Acceptance**
- Given a valid company id  
- When I `GET /api/radar/diff/{id}`  
- Then I receive diffs with metric, periods, and band_delta when applicable

## US-P06 — Radar calendar & digest
**As a** desk lead  
**I want** a calendar of open promises and a weekly digest of guidance changes  
**So that** the team can follow changes without opening Tracker.

**Acceptance**
- When I `GET /api/radar/calendar` then I see companies with open promises  
- Given my org's Monitors cover a company, when its guidance is raised, cut, dropped or withdrawn, then the next CiteAlpha Analyst weekly digest lists the change once with its source link (`/api/analyst/digest`)  
- The old `/api/radar/digest/*` and `/api/radar/webhooks` return `410` with `moved_to`

## US-P07 — Ledger PDF & IR Mirror
**As a** compliance analyst  
**I want** a downloadable ledger PDF and optional IR Mirror view  
**So that** I can ship board packs without the Score UI.

**Acceptance**
- With API key, `GET /api/ledger/{id}/pdf` returns application/pdf  
- With `IR_MIRROR=1`, mirror endpoint returns peer context and mirror copy

## US-P08 — Bulk data export & vernacular digest
**As a** quant / distributor  
**I want** bulk outcomes export and factual vernacular digests  
**So that** I can license Data and Cite SKUs separately.

**Acceptance**
- CSV export requires API key  
- Vernacular digest includes hi + en text and source links when available

## US-A01 … US-A08 — CiteAlpha Analyst and Commitment Record
Full Given/When/Then text: `docs/PLAN_CITEALPHA_ANALYST.md` §7. Tests: `backend/tests/test_commitments.py`, `backend/tests/test_analyst_*.py`.

| ID | Story | Status |
|---|---|---|
| US-A01 | Commitment extraction lands unreviewed, quote verbatim | Shipped |
| US-A02 | Quiet drop proposed after two silent cycles | Shipped (proposal only) |
| US-A03 | Results Prep Pack, every sentence cited | Shipped |
| US-A04 | New filing triggers a Skill run | Shipped (company, watchlist or Project Monitors; feed, email, Slack/Teams/webhook) |
| US-A05 | Verifier removes unsupported sentences | Shipped |
| US-A06 | Tenant isolation | Shipped (run history, Monitors, Projects, uploads) |
| US-A07 | Excel export with per-cell citations | Shipped (plus PowerPoint, PDF, Markdown) |
| US-A08 | Board Scorecard in plain counts, no advice wording | Shipped |
| US-A09 | Weekly digest of filings, runs, guidance changes and commitments due for the companies my Monitors cover | Shipped (`/analyst` → Weekly digest) |
| US-A10 | India event Skills (open offer / delisting / scheme, DRHP, USFDA, rating rationale, Debate Map), three golden cases each | Shipped |
| US-A11 | Org admin issues API keys; our systems call the public API or MCP server, rate-limited per key | Shipped (`/analyst` → API keys) |
| US-A12 | Exports in our house style (colours, font, logo, PowerPoint template) without losing the disclaimer, data date, source footers or Evidence Receipt | Shipped; human compliance approver pending |

## US-ADM-01 … US-ADM-08 — Administration menu

Full acceptance criteria: `docs/PRD_ADMIN.md` §11. Implemented 2026-10-25: admin bar, organisation sections, and the platform menu groups.

| ID | Story |
|---|---|
| US-ADM-01 | Admin bar appears only for an org owner, org admin, or platform role, with items that role can open |
| US-ADM-02 | Org owner appoints admin; org admin manages working seats only |
| US-ADM-03 | Analyst keys, desk key, destinations, and export style sit on the Organisation menu |
| US-ADM-04 | Org owner or admin saves issuer, client id, and email domain for this desk |
| US-ADM-05 | Billing and audit show this organisation only |
| US-ADM-06 | Platform super sees the full platform menu; labeling and commitments stay read-only |
| US-ADM-07 | Platform billing, ops, compliance, and support see only their permission set |
| US-ADM-08 | A user who is both org owner and platform ops sees both menus, unmerged |

## US-M01 — One place for each job (2026-10-17 merge)
**As a** desk user  
**I want** each job to live in one place  
**So that** I don't learn two tools for the same thing.

**Acceptance**
- Search and cite-only questions across all covered companies are in Filing Search (`/research?scope=all`, India IR synonyms on); `/sights/search`, `/sights/ask` and `/sights/boards` redirect there  
- Saved searches sit on the Filing Search tab and sync with `preferences.saved_queries`  
- Desk Agents, Cite Export and Notify Hooks are replaced by CiteAlpha Analyst Skills, exports and destinations; `/sights/agents` and `/sights/export` redirect to `/analyst`  
- Sector averages appear only in the GCI Screener Sectors tab (`/tracker?tab=sectors`); `/research?tab=sectors` redirects there and the Workbench no longer draws its own sector heatmap  
- Products, Package and Tier features are one page (`/products`)
