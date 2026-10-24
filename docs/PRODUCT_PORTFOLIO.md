# CiteAlpha Product Portfolio

Parallel product lines that reuse the same India disclosure corpus (filings, concalls, guidance↔actuals, citations) but sell as **different jobs**. GCI remains the brand wedge; these are not tabs pretending to be products.

**Legal entity:** Ocotillo Innovation Private Limited · **Compliance:** factual research tooling — not investment advice; no Buy/Hold/Sell.

## Selection filter

Every SKU must:

1. Use **primary disclosure + evidence**, not news sentiment.
2. Stay **factual** (SEBI-safe posture).
3. Be sellable **without** GCI if the buyer only wants that job.
4. Prefer reuse of: extract → match → cite → review.

## Five commercial bundles

| Bundle | Hero job | Primary buyer | Status |
|---|---|---|---|
| **CiteAlpha Score** | GCI 0–100 + peer delivery benchmarks | Buy-side / sell-side | Live (core) |
| **CiteAlpha Cite** | Mandatory primary citations + Research Terminal | Research ops / AI copilots | Live (core) · API packaging |
| **CiteAlpha Radar** | Guidance change / miss / drop / withdrawal feed | PMs, risk, IR-watch | Live alerts · productize |
| **CiteAlpha Ledger** | Promise ledger / accountability dossier | Compliance, credit, IR, board | Partial (`promise_brief`) · expand |
| **CiteAlpha Data** | PIT guidance-outcome dataset + factor export | Quant / alt-data | Live PIT · license packaging |
| **CiteAlpha Sights** | India disclosure research OS (search, cite GenAI, grids, agents) | India equity desks | Live · `/sights` |
| **CiteAlpha Holdings** | Holdings-weighted published GCI, coverage, residual assets | MF, PMS, AIF, pension | Live · `/holdings` · admin-approved 30/45/60 day pilot, then a paid seat |

One-pagers: [`docs/customer/skus/`](customer/skus/).

Implementation phases: [`PORTFOLIO_ROADMAP.md`](PORTFOLIO_ROADMAP.md).

---

## Catalog (15 lines → 5 SKUs + Sights)

### Inside Score

| # | Line | One-line |
|---|---|---|
| 1 | Guidance Credibility Index | Credit score for management delivery |
| 2 | Peer Delivery Benchmarks | Sector/index percentiles for met / miss / drop rates |

### Inside Cite

| # | Line | One-line |
|---|---|---|
| 3 | Citation-as-a-Service | Answer APIs with mandatory primary citations |
| 4 | Research Terminal | Search, cite-only chat, snapshot, watchlist |
| 5 | Vernacular Earnings Digest | Regional factual digests with source links |

### Inside Radar

| # | Line | One-line |
|---|---|---|
| 6 | Guidance Change Radar | Alert when ranges revise, drop, or soften |
| 7 | Concall / Filing Diff Brief | QoQ “what changed in guided language/numbers” |
| 8 | Event Calendar + Evidence Hooks | Guidance windows → dossier deep links |

### Inside Ledger

| # | Line | One-line |
|---|---|---|
| 9 | Promise Ledger | What was promised, by whom, when, status |
| 10 | IR Credibility Mirror | How the street would score *your* IR history |
| 11 | Board / Independent Director Brief | Open / missed / dropped promises pack |
| 12 | Credit / Covenant Adjacent Watch | Capex, leverage, margin-floor commitments vs delivery |
| 13 | Narrative Consistency Index | Cross-doc story conflict flags (later) |

### Inside Data

| # | Line | One-line |
|---|---|---|
| 14 | PIT Guidance Outcome Dataset | Guided band, actual, label, confidence — backtestable |
| 15 | KPI Dictionary / Metric Normalizer | India sector metric ontology (infrastructure, later) |

### Inside Sights

| # | Line | One-line |
|---|---|---|
| 16 | Sights Search + Business Lexicon | India IR search with synonym expand |
| 17 | Sights Ask / Deep Dive / Compare Grid | Cite-only GenAI over disclosure corpus |
| 18 | Street Context + Field Evidence | Public street vs guidance; labeled outcomes trail |
| 19 | Desk Agents + Cite Export + Notify Hooks | Templated briefs, MD/CSV export, Radar hooks |

### Channel (not standalone consumer)

| # | Line | Notes |
|---|---|---|
| — | Broker Trust Badge | White-label factual badge + evidence link (Year-2 channel) |
| — | Extraction + Review Workbench | Sell ops tooling to captive research factories (later) |

---

## Positioning matrix

| | Score | Cite | Radar | Ledger | Data | Sights |
|---|---|---|---|---|---|---|
| Time horizon | Multi-quarter history | Any ask | Near-term change | Open + closed promises | Historical series | Interactive research session |
| Output | Score + evidence | Cited answer | Alert / brief | Dossier / PDF | Tables / Parquet | Search / Ask / Grid / Agents |
| Habit | Screen weekly | Write notes daily | Inbox / Slack | Audit quarterly | Batch / API | Desk research daily |
| Competing with | Sentiment dashboards | Generic LLM copilots | News alerts | Manual Excel ledgers | US-only guidance datasets | Generic market-intel OS (we stay India IR) |

---

## Shared spine (do not rebuild per SKU)

```
IR / filings / concalls
        ↓
   ingest + extract
        ↓
  match guidance ↔ actual
        ↓
  outcomes + citations + review
        ↓
   ┌────┴────┬────────┬─────────┬────────┬────────┐
 Score    Cite     Radar    Ledger    Data    Sights
```

---

## Explicit non-goals (portfolio-wide)

- Retail Buy / Hold / Sell or tips.
- Live quotes, OMS, or competitor clone positioning / trademarks in UI.
- Sentiment-only dashboards.
- Invented financial actuals.
- Unlicensed sell-side PDF redistribution or expert-call brokerage (Sights refuse list).

## Related

- [`PRODUCT_DEFINITION.md`](PRODUCT_DEFINITION.md) — GCI MVP scope
- [`BUSINESS_PLAN.md`](BUSINESS_PLAN.md) — GTM + monetization
- [`customer/PRICING.md`](customer/PRICING.md) — seat + API tiers
- [`customer/COMPLIANCE.md`](customer/COMPLIANCE.md) — SEBI posture
- [`customer/skus/SIGHTS.md`](customer/skus/SIGHTS.md) — Sights one-pager
- [`kb/14-sights.md`](kb/14-sights.md) — Sights kb
