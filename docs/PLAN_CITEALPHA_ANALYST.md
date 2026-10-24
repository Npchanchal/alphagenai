# Plan — CiteAlpha Analyst (always-on cited research agent) + Commitment Record

**Status:** approved 2026-10-03 · A0 + A1 core shipped (see §11) · **Created:** 2026-10-03 · **Owner:** product + `architect`
**Benchmark:** AlphaSense SuperAnalyst (platform page, Oct 2026).
**Runs alongside:** `docs/PLAN_WORLDCLASS_GCI.md` (Round-3). Nothing here may move a published GCI.
**Rules:** `citealpha-core`, `index-integrity`, `public-copy-voice`, `compliance-sebi`.

---

## 0. Why

Most Indian listed companies do not publish numeric guidance. A GCI that only scores explicit guidance therefore covers a thin slice of the market, and many companies will never get a score.

**Measured (A0, 2026-10-03, `python -m app.jobs.guidance_coverage`):** 2 of the 50 Nifty 50 companies (1 of the Sensex 30) have a guidance row carrying the guidance-side citation in CiteAlpha's data. This is a lower bound set by labelling (Round-3 finding R3-07), not a count of companies that guide.

They do, however, make **dated, checkable commitments** in concalls, annual reports, investor presentations and exchange filings, for example:

- "Plant 2 commissions in Q3 FY26."
- "Capex of ₹4,000 cr over two years."
- "Net-debt free by FY27."
- "Order book of ₹X cr executable in 24 months."
- "Launch 12 products in the US this year."
- "Scheme of amalgamation to close by March."

Two answers, built together:

1. **Commitment Record**: extract those commitments and track each one to the filing that proves it, disproves it, or shows it was quietly dropped. This gives a delivery record for every company, not just the guiders.
2. **CiteAlpha Analyst**: an always-on agent that watches Indian disclosures, runs the workflows desks actually perform (results prep, concall questions, board scorecard, peer read-across, DRHP and open-offer briefs), and returns cited, auditable outputs.

**Positioning.** AlphaSense says *find anything, cite it*. CiteAlpha says *did management deliver? Prove it*, and now does it for every company and every workflow around a result.

---

## 1. Decisions (recorded 2026-10-03)

| # | Decision | Consequence |
|---|---|---|
| D1 | The agent is part of the **core product**, not a separate SKU | Overrides the "SuperAnalyst OS" non-goal in `GAPS_VS_ALPHASENSE_BLOOMBERG.md`. Entitlements still apply per feature (guests get no agent runs) |
| D2 | Commitments go into a **separate Commitment Record**; the GCI stays explicit-guidance only | No GCI methodology change, no ledger entries from this programme. Commitment Record has its own methodology page and changelog |
| D3 | Content is **public Indian disclosures plus the user's own uploads** | No broker research, no expert-call network, no unlicensed transcripts. Licensed content stays a later, separate decision |
| D4 | First deliverable is this plan | Code starts at Phase A0 after approval |

Working names (display), subject to the copy rule: **CiteAlpha Analyst** (`/analyst`), **Commitment Record** (shown inside the dossier and Ledger), **Skills**, **Monitors**, **Projects**. Avoid "OS", "signal" and "alpha" as a common noun.

---

## 2. Feature map: SuperAnalyst → CiteAlpha

Legend for "Build on": existing code we extend. **Phase** refers to §5.

### 2.1 Platform pillars

| SuperAnalyst capability | CiteAlpha version (what is different) | Build on | Phase |
|---|---|---|---|
| 500M+ premium documents | **India disclosure corpus**: NSE/BSE announcements (all categories), concall transcripts and audio-derived text published by issuers, annual reports, investor decks, credit-rating rationales (CRISIL/ICRA/CARE/India Ratings), SEBI orders, DRHP/RHP, open-offer letters, NCLT scheme documents, USFDA public records for Indian pharma. Depth over breadth; each document dated and hashed | `exchange_filings.py`, `doc_store.py`, `ir_discovery.py` | A0, A5 |
| Pre-indexed, normalized, connected data | **India entity graph**: scrip ↔ ISIN ↔ group ↔ promoter ↔ subsidiaries ↔ plants/projects ↔ peers ↔ rating agency. Built at ingest, not at query time. Commitments attach to graph nodes (for example "Plant 2, Dahej") so later filings link back automatically | `india_listings.py`, `universe.py` | A0, A1 |
| Operates like a power user | Agent tool registry over our own services: Filing Search, GCI, Commitment Record, peers, PIT, consensus import, fundamentals, Disclosure Explorer Deep Dive | `research.py`, `sights.py` | A0 |
| Monitors what matters, acts on events | **Event-triggered Monitors**: each new filing is classified, then resolved to affected commitments, watchlists and Projects. The relevant Skill runs only for those. No fixed cadence and no re-reading of unchanged documents | `refresh.py`, `exchange_filings.classify_*`, Radar | A2 |
| Decision-ready outputs (briefs, models, memos, decks) | Cited Markdown/PDF memo, **Excel workbook with a citation per cell** (comment + hyperlink to `/c/{id}`), **PowerPoint deck with source footers**. Every output carries an **Evidence Receipt** (list of every source, quote span and retrieval time) | `reports.py`, `audit_dossier.py`, `citations.py` | A4 |
| Reasons with context and memory | **Projects**: coverage universe, thesis notes, prior outputs, uploaded models, house style. Memory is explicit and editable (the user can see and delete what the agent remembers) | `analyst_notes.py`, preferences | A3 |
| Executes your workflows (Skills) | **Skills** = versioned, declarative workflow specs (YAML): inputs, steps, tools, output template, acceptance checks. Ship pre-built India Skills; desks fork and codify their own method | Sights Desk Agents (`earnings_prep`, `promise_brief`, `peer_delivery`, `ic_footnote`) become the first four Skills | A2 |
| Enterprise security: sandboxed, isolated, never trains | Per-org tenancy on every table, uploads encrypted at rest and scoped per org, no customer content in prompts of other orgs, LLM provider zero-retention settings, processor named in Privacy. Agent cannot write to the GCI or Commitment Record (read-only tools for those) | `orgs.py`, `rbac.py`, `entitlements.py` | A0, A3 |
| Accurate, auditable | **Verifier pass**: after drafting, a second step checks every factual sentence against a citation span. Unsupported sentences are removed or marked "not found in sources". Outputs fail closed | `llm_client.rewrite_cite_only_answer` | A0 |
| Efficient token architecture | Retrieval over stored embeddings (pgvector) plus section-level chunking; per-run token budget; cached document summaries keyed by content hash | `doc_store` content hashes | A0 |
| Multi-LLM | Provider-agnostic `llm_client` (OpenAI-compatible, Gemini); route per step (cheap model for classification, stronger model for synthesis); log model id per output | `llm_client.py` | A0 |
| PowerPoint and Excel add-ins | Phase A4 ships exports; a true Office add-in is A6 (optional) | — | A4, A6 |
| Connectors | Delivery to email (exists), webhooks (registered, not delivered), Slack/Teams. **CiteAlpha MCP server and API** so customers' own agents can call Filing Search, GCI and Commitment Record with citations | `mailer.py`, `/api/radar/webhooks` | A6 |

### 2.2 Workflows, adapted to Indian desks

SuperAnalyst sells about 25 workflows across six personas. We take the ones that fit public Indian disclosures, rework them, and drop those that need licensed content or advice.

| SuperAnalyst workflow | CiteAlpha Skill | Output | Phase |
|---|---|---|---|
| Pre-Print Consensus Check | **Results Prep Pack**: open commitments due this quarter, delivery record, what management said last call, peer read-across from companies that already reported, user-imported consensus (never sourced by us) | Cited brief; "commitments at stake this print" table | A2 |
| Weekly Model Recalibration | **Weekly Driver Review**: maps each new filing, rating action or peer result to the drivers in the user's uploaded model; flags drivers whose evidence changed | Dated change log per driver, cited; no price target | A3 |
| Single-Session Company Ramp | **Company Ramp**: 24-month story from filings, the 2–4 open debates in management's own words, delivery record, governance events, then a **disproof pass** that searches for evidence against each conclusion | Memo, debate map, "what we could not find" list | A2 |
| Conference / meeting prep | **Concall and Analyst-Meet Question Pack**: questions built from unmet or quietly dropped commitments, changes in language versus last call, peer contradictions. Front page across all meetings ranks where the sharpest questions sit | Question pack with a citation per question | A2 |
| Continuous Board Prep ("scores management against last quarter's commitments") | **Board Scorecard**: this is our wedge. Commitment Record + GCI + governance events for an independent director, promoter or IR team | Scorecard, cited follow-up questions | A2 |
| Same-Day Arb Package | **Open Offer / Delisting / Scheme Brief**: SEBI SAST open-offer letter terms, offer price rule, timelines, scheme of arrangement steps, NCLT and exchange approvals, closing-risk checklist. Facts only; **no recommended spread** | Event brief, timeline, conditions checklist | A5 |
| Pre-IPO Model Build | **DRHP Reader**: segment breakdown, objects of the issue, risk factors diffed against listed peers, KPIs disclosed versus peers, promoter history | Cited DRHP brief, peer KPI table (Excel) | A5 |
| Opportunity Underwriting / Deal Diligence | **Diligence Room**: user uploads data-room files; agent lists what is missing, cross-checks seller claims against public filings | Gap list, cross-check table, draft request list | A3 |
| Always-on Coverage Monitoring / Pipeline Screening | **Coverage Monitor**: per-company feed of material filings, management changes, rating actions, pledge changes, regulatory orders; weekly digest | Digest, cited | A2 |
| Battle-Ready / Client-Ready Competitive Set | **Peer Delivery Grid**: who delivers on what they promise, by metric and commitment type, across a sector | Grid + per-company profile | A2 |
| Roadmap Stress-Testing | **Debate Map**: sector questions split by who is saying it (company, rating agency, regulator) | Debate map with both sides cited | A5 |
| Continuous Trial Monitoring / Asset Diligence (life sciences) | **USFDA Watch for Indian pharma**: Form 483s, warning letters, import alerts, EIRs, ANDA approvals, mapped to the plants named in company commitments | Event brief + affected-commitments list | A5 |
| Strategic Pathways / Disruption map / Buyer universe / Pitch build / Live deal tracking | Out of scope: these need private CRM data, transaction databases or advisory judgement | — | — |

### 2.3 India-native innovations (not in SuperAnalyst)

1. **Commitment Record**: extracts promises beyond numeric guidance and tracks them to a proof filing (see §3).
2. **Quiet-drop detector**: flags a commitment that disappears from subsequent calls and decks without a stated reason. "Last mentioned Q2 FY25 concall; not in Q3 or Q4 FY25 materials."
3. **Say-versus-file contradiction finder**: compares concall statements with the numbers in the subsequent results filing or annual report.
4. **Disproof pass in every Skill**: the agent tries to refute its own conclusion and reports what it found and what it could not find.
5. **Evidence Receipt**: a machine-readable list of sources attached to every output (also exported in Excel and PPT), so a compliance team can audit any line.
6. **Methodology as a Skill**: a desk writes its research method once (YAML); runs are versioned, so an output can be reproduced against the Skill version and data as of that date.
7. **Rating-rationale tracker**: credit-rating agency rationales are public and cite management commitments (capex, deleveraging). We link them to the Commitment Record.
8. **Vernacular delivery**: digests in Hindi and other languages using the existing vernacular path.

---

## 3. Commitment Record (separate from GCI)

### 3.1 What counts as a commitment

A forward-looking statement by the company that has **(a)** a subject, **(b)** a checkable outcome, **(c)** a due date or period, **(d)** a source quote and link.

| Type | Example outcome check |
|---|---|
| `capacity` | Plant/line commissioning date, capacity in units |
| `capex` | Amount spent by period (cash-flow statement, annual report) |
| `balance_sheet` | Net debt, leverage, rating target |
| `order_book` | Order inflow / execution |
| `launch` | Product, store, branch, market entry count |
| `corporate_action` | Merger, demerger, scheme, divestment closing date |
| `operational` | Utilisation, volume, cost-saving programme |
| `esg` | Renewable share, emissions target |
| `numeric_guidance` | Already handled by the GCI; linked, not duplicated |

### 3.2 States

`open` → `delivered` | `delivered_late` | `partially_delivered` | `missed` | `withdrawn_with_reason` | `quietly_dropped` | `superseded`

Each transition needs a **proof citation** (filing, quote span, date). `quietly_dropped` needs two consecutive disclosure cycles without mention, and states that in plain words.

### 3.3 Governance

- LLM proposes the extraction and the state change; a reviewer accepts it. This reuses the review queue and labeling governance (reviewer id + date).
- Public surfaces show only reviewed rows. Unreviewed rows are visible to seat users and labelled "Unreviewed".
- A company-level summary is a **plain count**, not an index level: "Delivered 7 of 10 dated commitments due by FY25; 2 late; 1 quietly dropped". No composite 0–100 number until a separate methodology is written and approved. This keeps it outside the index-integrity scope for published GCI levels.
- Own methodology page and changelog (`docs/kb/16-commitments.md`, public `/methodology#commitments`).

---

## 4. Architecture

```text
 Ingest (NSE/BSE/IR/ratings/SEBI/USFDA)
        │  dated, hashed docs + section chunks + embeddings (pgvector)
        ▼
 Event bus (doc.ingested, doc.classified, commitment.due, schedule.tick)
        │
        ├──► Commitment extractor ──► review queue ──► Commitment Record (read-only to agent)
        │
        ▼
 Monitor router: which watchlists / Projects / commitments does this event touch?
        │
        ▼
 Agent runtime
   planner (Skill spec)  →  tools (read-only services)  →  draft
   →  verifier (every sentence ↔ citation span)  →  disproof pass  →  output + Evidence Receipt
        │
        ▼
 Delivery: in-app Project feed · email · webhook · Slack/Teams · Excel/PPT/PDF · API/MCP
```

**Key components (new):**

| Component | Location | Notes |
|---|---|---|
| `agent_runtime.py` | `backend/app/services/agent/` | Step executor, token budget, per-step model routing, run log |
| `tools.py` | same | Typed, read-only wrappers over research/sights/gci/commitments; every tool returns citations |
| `verifier.py` | same | Pure function: (draft, citations) → (kept, removed, unsupported). Unit-tested without an LLM |
| `skills/*.yaml` + `skill_loader.py` | `backend/app/skills/` | Versioned specs; the four Desk Agents ported first |
| `events.py` | `backend/app/services/` | Simple table-backed queue (Postgres) first; no new infra |
| `commitments.py` | `backend/app/services/` | Pure state machine + extraction schema; unit-tested |
| `projects.py`, `uploads.py` | `backend/app/services/` | Org-scoped, Postgres |
| `exports.py` | `backend/app/services/agent/` | `openpyxl`, `python-pptx`, `pdf_minimal`; cell comments carry citations |

**Persistence (Postgres, org-scoped):** `documents_chunks` (+ pgvector), `events`, `commitments`, `commitment_transitions`, `projects`, `project_memory`, `uploads`, `skills`, `skill_versions`, `agent_runs`, `agent_outputs`, `evidence_receipts`, `monitors`, `deliveries`. JSON files remain for the GCI path until the Round-3 plan migrates them.

**Frontend:** `/analyst` (Projects, Monitors, Skill runs, outputs), Commitment Record panel in the dossier (counts the panel budget), "Run Skill" from dossier and Screener for seat users.

---

## 5. Phases and gates

| Phase | Scope | Exit gate |
|---|---|---|
| **A0 Foundations** | Measure explicit-guidance coverage across Nifty 50 (real count, replaces the qualitative claim in §0); Postgres tables; chunking + pgvector; tool registry; verifier; agent run log; model routing | Verifier unit tests green; a run without citations fails closed; coverage number written into §0 |
| **A1 Commitment Record** | Extraction schema, LLM extractor on concalls/decks/annual reports, review queue reuse, state machine, entity-graph links (plants/projects), dossier panel for seat users | 10 Sensex companies reviewed end-to-end; every row has quote + link + date + reviewer; public panel shows reviewed rows only |
| **A2 Monitors + Skills v1** | Event bus, monitor router, Skill spec + loader; ship Results Prep Pack, Company Ramp, Concall Question Pack, Board Scorecard, Coverage Monitor, Peer Delivery Grid (four ported from Desk Agents); quiet-drop + contradiction checks; email delivery | A new filing for a watchlist company produces a cited brief within one refresh cycle; zero unsupported sentences in the evaluation set |
| **A3 Projects, memory, uploads** | Projects, editable memory, file uploads (PDF/XLSX/DOCX) org-scoped; Weekly Driver Review; Diligence Room | Tenant-isolation tests; uploaded content never appears in another org's retrieval |
| **A4 Exports** | Excel with per-cell citations, PPT with source footers, PDF memo; Evidence Receipt on all | Opening the workbook shows a citation on every sourced cell; receipt matches the run log |
| **A5 India event Skills** | Open offer / delisting / scheme brief, DRHP Reader, USFDA Watch, rating-rationale tracker, Debate Map | Each Skill has three golden cases with expected citations |
| **A6 Connectors** | Webhook delivery, Slack/Teams, public API + CiteAlpha MCP server, optional Office add-in | Contract tests; rate limits; per-org keys |

Compliance gate (applies from A2): `compliance-reviewer` signs off Skill output templates. No price targets, ratings, spread recommendations or Buy/Hold/Sell. Bull/base/bear wording only as **scenarios on disclosed drivers**, for seat users, after the SEBI RA memo (R3-31).

---

## 6. Guardrails

1. **The agent never writes a GCI number or a Commitment Record state.** Its tools for those are read-only; changes go through the review queue.
2. **No synthetic content on public surfaces.** Agent outputs are seat-only; nothing generated appears on guest pages.
3. **Cite or refuse.** The verifier removes any unsupported sentence. If too little remains, the output says what was not found instead of filling gaps.
4. **No advice.** Copy rule `public-copy-voice` banned list applies to Skill templates; extend `test_public_copy_hygiene.py` to scan `backend/app/skills/**`.
5. **Consensus and models come from the user.** We never fabricate estimates; imported numbers are labelled with their source.
6. **Reproducibility.** Every output stores Skill version, model ids, document hashes and as-of time.
7. **Licensing.** Only sources cleared under R3-35 (IR/transcript redistribution) are quoted verbatim in exports.

---

## 7. User stories (Given / When / Then)

**US-A01 — Commitment extraction.** *Given* a concall transcript for a Sensex company, *when* the extractor runs, *then* each proposed commitment has type, subject, outcome, due period, quote span and link, and lands in the review queue as "Unreviewed".

**US-A02 — Quiet drop.** *Given* a reviewed open commitment not mentioned in two consecutive disclosure cycles, *when* the monitor runs, *then* it proposes `quietly_dropped` with the last-mentioned citation and the two cycles checked.

**US-A03 — Results Prep Pack.** *Given* a seat user with a company on their watchlist and results due within 10 days, *when* they run the Skill, *then* they get open commitments due this quarter, last-call statements and peer read-across, each sentence cited, plus a "not found" list.

**US-A04 — Event trigger.** *Given* a Monitor on a company, *when* a new NSE announcement is ingested and classified as material, *then* the affected Skill runs once and the user receives a cited brief by email or in the Project feed.

**US-A05 — Verifier fails closed.** *Given* a draft with a sentence that has no supporting span, *when* the verifier runs, *then* the sentence is removed and recorded in the run log as unsupported.

**US-A06 — Tenant isolation.** *Given* org A uploads a model, *when* a user in org B runs any Skill, *then* no chunk from org A's upload is retrieved or cited.

**US-A07 — Excel citations.** *Given* a Peer Delivery Grid export, *when* opened in Excel, *then* every sourced cell has a comment with the quote and a link to `/c/{id}`.

**US-A08 — Board Scorecard.** *Given* a company with reviewed commitments and a GCI, *when* an independent director runs Board Scorecard, *then* the output states the delivery record in one plain sentence and lists cited follow-up questions, with no advice wording.

---

## 8. Success measures

| Measure | Target by end of A2 |
|---|---|
| Companies with a delivery record (GCI or Commitment Record) in Nifty 50 | Measured in A0; aim ≥ 2× the explicit-guidance-only count |
| Unsupported sentences in shipped outputs (evaluation set) | 0 |
| Time from material filing to cited brief | ≤ one refresh cycle |
| Seat-user Skill runs per week | Tracked from A2 launch |

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| Commitment extraction noise | Reviewer-gated; precision measured on a golden set before public display |
| Agent reads as investment advice | Compliance gate on templates; banned-word test; seat-only |
| Transcript / IR redistribution rights | Quote spans only until R3-35 clears; link out otherwise |
| LLM cost | Event-triggered runs, cached summaries, per-org budgets |
| Scope creep toward "find anything" | Every Skill must touch delivery, disclosure or governance; others are rejected |
| Round-3 still open | A0–A1 can start in parallel; public Commitment Record panel waits for W3 dossier rework |

---

## 10. Docs and assets to update when execution starts

- `docs/GAPS_VS_ALPHASENSE_BLOOMBERG.md`: non-goal list updated (done with this plan).
- `docs/kb/16-commitments.md` and `docs/kb/17-analyst-agent.md` (new), `docs/kb/README.md`, `docs/kb/AGENT_ROUTING.md`.
- `docs/PRODUCT_PORTFOLIO.md`: Ledger SKU absorbs Commitment Record; Sights Desk Agents migrate to Skills.
- `docs/USER_STORIES.md`: add US-A01…A08.
- New skill `citealpha-analyst-agent` and agent file `.cursor/agents/analyst-agent-engineer.md` at A0.
- `public-copy-voice` canonical names: add CiteAlpha Analyst once the name is approved.

---

## 11. Progress log

**2026-10-03 — A0 + A1 core.** Name "CiteAlpha Analyst" approved.

| Item | Status | Where |
|---|---|---|
| Coverage measure | Done (2/50 Nifty, 1/30 Sensex) | `backend/app/jobs/guidance_coverage.py` |
| Verifier (pure, fails closed) | Done | `services/agent/verifier.py` |
| Read-only tool registry, runtime, disproof pass, Evidence Receipt | Done | `services/agent/` |
| Skills v1: Results Prep Pack, Company Ramp, Earnings-Call Question Pack, Board Scorecard | Done (JSON specs) | `backend/app/skills/` |
| Org-scoped run history | Done (JSON store) | `services/agent/run_store.py` |
| Optional model summary behind `ANALYST_LLM` | Done (verified per sentence) | `runtime._llm_summary` |
| Commitment rules, store, extractors, quiet-drop scan, review/transition routes | Done | `services/commitment*.py`, `api/analyst_routes.py` |
| `/analyst` page (seat-only) | Done | `frontend/src/pages/AnalystPage.tsx` |
| Tests | 38 new; full backend suite 569 passed, frontend 19 passed | `tests/test_commitments.py`, `tests/test_analyst_agent.py` |

**2026-10-03 — A2 Monitors + remaining Skills.**

| Item | Status | Where |
|---|---|---|
| New-filing processor (baseline on first run; ingested sources only; derived/demo documents never trigger) | Done | `services/agent/monitors.py` |
| Auto commitment proposals from each new filing (`unreviewed`, `auto:commitment_extract`) | Done | `monitors._queue_commitments` |
| Org Monitors (create / list / delete, 25 per org), feed, ops process + status | Done | `api/analyst_routes.py` |
| "What the new filing says" section, trigger in run + Evidence Receipt | Done | `runtime._trigger_section` |
| Email delivery with `/analyst?run=` link | Done (stub without SMTP) | `monitors._deliver` |
| Refresh hook (`ANALYST_MONITORS`, default on) + CLI job | Done | `services/refresh.py`, `jobs/analyst_monitors.py` |
| Skills: Coverage Monitor, Peer Delivery Grid | Done | `backend/app/skills/` |
| Monitors panel + New filings feed on `/analyst` | Done | `AnalystPage.tsx` |
| Tests | 11 new; full backend suite 581 passed, frontend 19 passed | `tests/test_analyst_monitors.py` |

Corpus check (packaged, 205 docs): the heuristic extractor found two candidates in Sensex filings — one is numeric guidance already in the GCI, the other is vague with no source link — so nothing was queued from the existing corpus. Proposals will come from newly ingested transcripts and annual reports.

**2026-10-03 — A3 Projects, memory, uploads.**

| Item | Status | Where |
|---|---|---|
| Projects (50 per org, 30 companies each), explicit editable memory (100 items, shown in full, never cited) | Done | `services/agent/projects.py` |
| Org-scoped uploads: PDF, DOCX, XLSX, CSV, TXT, MD; 10 MB, 20 per Project; parsed to passages with a location (`p.3`, `Sheet!A12`, `para 4`); dedupe by hash; DOCTYPE/entity and zip-bomb rejects | Done | `services/agent/uploads.py` |
| `project_uploads` tool; upload cites shown as "file (location) — your upload", never as a public source | Done | `services/agent/tools.py` |
| Skills: Diligence Room (claims cross-checked against filings, checklist gaps, record), Weekly Driver Review (model drivers × last 7 days of filings) — both require a Project | Done | `backend/app/skills/` |
| Routes: Projects CRUD, memory, uploads (base64 JSON; nginx 15 MB on the upload path only); run checks the company is in the Project | Done | `api/analyst_routes.py`, `frontend/nginx*.conf` |
| Projects panel on `/analyst` (choose/create, memory, files); project-only Skills disabled without a Project | Done | `AnalystPage.tsx` |
| Tests | 17 new incl. cross-org isolation; full backend suite 607 passed, frontend 19 passed | `tests/test_analyst_projects.py` |

Uploads are stored as parsed text under the data volume (EFS in production), not encrypted at the application layer; EFS encryption at rest covers them. Model prompts only include the requesting org's Project memory.

**2026-10-03 — A4 Exports.**

| Item | Status | Where |
|---|---|---|
| `/c/{id}` permalinks on guidance, actual and filing evidence (all resolve on the citation page) | Done | `services/agent/tools.py` |
| Table rows on Peer Delivery Grid and delivery-record claims (same facts as the sentence, as cells) | Done | `runtime._claim(row=)` |
| Excel: Brief, one sheet per table, Sources, Evidence receipt. Every sourced cell has a comment with the quote(s) and a link to `/c/{id}` (or the public source); formulas never written from quotes | Done | `services/agent/exports.py` (`openpyxl`) |
| PowerPoint: title, one slide per section (6 bullets), source footer with links on each slide, What we could not find, Sources, Evidence receipt + quote hashes | Done | `exports.to_pptx` (`python-pptx`) |
| PDF memo (no-dependency writer, ASCII-safe: ₹ → Rs) and Markdown, both ending with the receipt | Done | `exports.to_pdf`, `pdf_minimal.py` |
| `GET /api/analyst/runs/{id}/export?format=` (`xlsx`, `pptx`, `pdf`, `md`) (org-scoped) + export buttons on `/analyst` | Done | `api/analyst_routes.py`, `AnalystPage.tsx` |
| Tests | 8 new (every sourced cell, receipt = saved run, footers, upload cites unlinked, formula guard, non-ASCII PDF); full backend suite 615 passed, frontend 19 passed | `tests/test_analyst_exports.py` |

Exports carry only the stored quote spans (≤ 400 characters) and links, never full documents (R3-35 still open). Upload cites appear as "your upload" with no link. Exports render from the saved run, so the receipt in every file is the run log.

**Not yet:** Postgres tables + pgvector (stores are JSON); reviewing the first 10 Sensex companies' commitments (A1 exit gate — needs a reviewer and ingested full transcripts / annual reports); contradiction check (language versus last call); weekly digest; Monitors on watchlists and Projects (per-company only today); compliance sign-off on Skill templates and export layouts; Commitment panel on the public dossier (waits for W3); house-style templates for decks.

**2026-10-17 — A2 leftovers, A5, A6, compliance sign-off, house style.**

| Item | Status | Where |
|---|---|---|
| "What changed since the last call" (language shift against the previous call) in Results Prep, Concall Questions, Debate Map | Done | `language_shift` builder |
| Weekly digest per org (filings, runs, commitments due, guidance changes once each); email + destinations | Done | `services/agent/digest.py` |
| Monitors on a watchlist or a Project's companies | Done | `services/agent/monitors.py` |
| A5 India event Skills: Corporate Action Brief (open offer / delisting / scheme), DRHP Reader, USFDA Watch, Rating Tracker, Debate Map; NSE event filings behind `ANALYST_EVENT_FILINGS` | Done; three golden cases each | `backend/app/skills/`, `services/event_filings.py`, `tests/golden/a5_cases.json` |
| A6: org API keys, public API v1, MCP server, per-key rate limit (`PUBLIC_API_RPM`), webhook/Slack/Teams destinations with test + log | Done (Office add-in not built) | `api/connector_routes.py`, `services/agent/{org_keys,public_api,delivery}.py` |
| House style (firm, colours, font, footer, classification, logo, PowerPoint template); export layout 1.1 | Done | `services/agent/house_style.py`, `exports.py` |
| Compliance sign-off record for 13 Skills + layout 1.1, with tests that every export keeps the disclaimer, data date, run id and Evidence Receipt | Recorded; human approver pending | `docs/compliance/ANALYST_SKILLS_SIGNOFF.md`, `tests/test_analyst_compliance_signoff.py` |
| `/analyst` settings screens: Monitor scope picker, weekly digest, house style (template upload + sample deck), destinations, API keys | Done | `frontend/src/pages/analyst/AnalystSettings.tsx` |
| Duplicates merged: Desk Agents, Cite Export, Notify Hooks and the Radar digest/webhook stub into Analyst; Disclosure Explorer Search/Ask/Boards into Filing Search; one sector leaderboard (Screener) | Done; old paths redirect or return `410` with `moved_to` | see `docs/kb/14-sights.md`, `docs/kb/17-analyst-agent.md` |

**Still not done:** Postgres + pgvector; A1 exit gate (10 Sensex companies' commitments reviewed); Commitment panel on the public dossier (W3); Office add-in; a named human approver on the sign-off record.
