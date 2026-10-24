# Portfolio Implementation Roadmap

Stepwise plan to productize parallel SKUs on top of the shared CiteAlpha spine.  
Canonical catalog: [`PRODUCT_PORTFOLIO.md`](PRODUCT_PORTFOLIO.md).

**Rule:** ship Score depth first; each phase must leave GCI tests green and claims honest (`data_quality` badges).

---

## Phase P0 — Freeze portfolio & claims (docs) ✅

| Step | Work | Exit |
|---|---|---|
| P0.1 | Portfolio catalog + 5 bundle one-pagers | `PRODUCT_PORTFOLIO.md` + `customer/skus/` |
| P0.2 | Sync business plan, pricing, kb commercial | No conflicting SKU lists |
| P0.3 | User stories US-P01… for Radar / Ledger / Cite / Data | Acceptance criteria written |
| P0.4 | `GET /api/products` catalog (status + endpoints) | Meta discoverable |

**Exit:** Sales and eng share one SKU vocabulary.

---

## Phase P1 — Productize what already ships ✅

| Step | Work | Exit |
|---|---|---|
| P1.1 | **Radar:** `GET /api/radar/feed` | pytest + Products UI |
| P1.2 | **Ledger:** `GET /api/ledger/{company_id}` | pytest |
| P1.3 | Cite SKU + Package cards | One-pagers match `/api/products` |
| P1.4 | **Data:** `GET /api/data/catalog` | Contract test |
| P1.5 | Frontend `/products` | Products page live |

---

## Phase P2 — Radar habit ✅

| Step | Work | Exit |
|---|---|---|
| P2.1 | Diff brief: `GET /api/radar/diff/{company_id}` | Company dossier card |
| P2.2 | Digest stub: `GET /api/radar/digest/preview`, `POST /api/radar/digest/send` (`RADAR_DIGEST=1`) | Flag off by default |
| P2.3 | Calendar: `GET /api/radar/calendar` | Products + Radar UI |
| P2.4 | Webhook stub: `POST /api/radar/webhooks` | Registered when flag on |

**Exit:** Pilot desk can preview weekly Radar digest without opening Tracker.

---

## Phase P3 — Ledger depth ✅

| Step | Work | Exit |
|---|---|---|
| P3.1 | PDF: `GET /api/ledger/{company_id}/pdf` | Downloadable; cite rows |
| P3.2 | IR Mirror: `GET /api/ledger/mirror/{company_id}` (`IR_MIRROR=1`) | Separate copy + peer context |
| P3.3 | Credit filter: `?credit_only=true` on ledger | Capex / margin / FCF metrics |

**Exit:** Board-brief deliverable from Ledger API, not Score UI alone.

---

## Phase P4 — Cite & Data licensing ✅

| Step | Work | Exit |
|---|---|---|
| P4.1 | Cite tiers + usage: `GET /api/cite/tiers`, `/api/cite/usage` | Documented in PRICING |
| P4.2 | Bulk export: `GET /api/data/export/outcomes` (json/csv/parquet) | Sample + schema |
| P4.3 | Vernacular digest: `GET /api/digest/vernacular/{company_id}` | hi + en factual templates |

**Exit:** Data / Cite quotes reference portfolio SKUs independently of One-Stop.

---

## Phase P5 — Stretch lines ✅ (beta / gated)

| Line | Endpoint | Gate |
|---|---|---|
| Narrative Consistency Index | `GET /api/score/narrative-consistency/{id}` | `PORTFOLIO_STRETCH=1` (default on) |
| KPI Dictionary | `GET /api/data/kpi-dictionary` | Live |
| Broker Trust Badge channel | `GET /api/channel/trust-badge/{ticker}` | SEBI MSA before retail embed |
| Extraction Workbench | `GET /api/workbench/extraction` | API key; ops preview |

---

## Feature flags

| Env | Default | Purpose |
|---|---|---|
| `RADAR_DIGEST` | off | Email / webhook digest delivery |
| `IR_MIRROR` | off | Corporate IR Mirror ledger |
| `PORTFOLIO_STRETCH` | on | NCI + workbench endpoints |
| `SIGHTS` | on | CiteAlpha Sights shell |
| `SIGHTS_DEEP_DIVE` | on | Deep Dive synthesis |
| `SIGHTS_GRID` | on | Compare Grid |
| `SIGHTS_WEB_ASSIST` | off | Open-web assist beside IR (quality gate) |

---

## Phase S0–S6 — CiteAlpha Sights

| Phase | Work | Exit |
|---|---|---|
| S0 | Docs, brand map, refuse list, `/api/products` entry | `SIGHTS.md` + catalog |
| S1 | `/sights` shell + Search / Ask / Boards | Meta + research compose |
| S2 | Lexicon, Delivery Themes, Street Context, Field Evidence | Honest empty states |
| S3 | Compare Grid, Deep Dive, Fundamentals Strip | Cite-only refuse tests |
| S4 | Desk Agents, Notify Hooks, Cite Export | Superseded 2026-10-17 by CiteAlpha Analyst Skills, exports and destinations |
| S5 | Enterprise links (Trust / SSO / billing / seats) | Settings deep-links |
| S6 | Counsel-gated licensed content / Office add-ins | Budget + counsel only |

---

## Tests

- `backend/tests/test_portfolio_products.py` — P0/P1
- `backend/tests/test_portfolio_phases.py` — P2–P5
- `backend/tests/test_sights.py` — Sights SKU

## Owner skills

| Phase | Skill / agent |
|---|---|
| P0 | `citealpha-product` |
| P1–P2 | `citealpha-portfolio` · `citealpha-api` · `citealpha-gci-dev` |
| P3 | `citealpha-frontend-ux` · compliance-reviewer |
| P4 | `citealpha-aws` · qa-release |
| P5 | `portfolio-engineer` · architect + compliance-reviewer |
| S0–S5 | `citealpha-sights` · `citealpha-api` · `citealpha-frontend-ux` |
