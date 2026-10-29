# 13 — Commercial

## Access tiers (how you buy)

| Plan | Role |
|---|---|
| Retail (B2C) | **Not offered** until counsel memo (`sebi_retail`). Plan still exists in entitlements for a future attest. |
| Pilot | Complimentary evaluation (B2B), 30, 45, or 60 days, set when an admin approves. When that term ends, the desk closes and Tracker remains |
| Desk | Seat ARR for research teams |
| Desk | Seat ARR for research teams |
| Enterprise API | PIT / factor embed |
| One-Stop | Desk + API + AlphaHunter + Wordmap bundle |

## Job SKUs (what you buy)

| SKU | Role |
|---|---|
| Score | GCI + peers |
| Cite | Citations + Research |
| Radar | Change feed |
| Ledger | Promise dossier |
| Data | PIT / factor license |
| Sights | India disclosure research OS (`/sights`) |
| Holdings | Holdings-weighted published GCI (`/holdings`), plus delivery tilt and the scheme change from values in the file. Open on an approved pilot term and on Desk / Enterprise / One-Stop |
| Financial Ninja | Desk module at `/ninja`: valuation worksheets, layer indices, and delivery counts. Not a separate price and not a published GCI |

Effective access is plan **intersect** role (never union). Tracker read is on every plan including guest. Research chat / Desk writes start at Pilot. Label workbench: One-Stop, or Desk/Enterprise **reviewer+**, or Pilot when `labeling_granted`. EM/Data file export: Enterprise / One-Stop. Partner feedback: Pilot+.

See `backend/app/services/entitlements.py` and `/package`.

## Markets and exchanges (priced separately)

A desk buys market scope on top of its plan: all markets (`*`), a whole market (`IN`, `US`), or one Indian exchange (`IN:NSE`, `IN:BSE`). The US is one unit for now. A company is in scope when any of its listings is purchased, so NSE+BSE listings count under either exchange.

Published GCI (Screener, dossier, Snapshot) stays open for every market. Seat tools — Filing Search, chat, Workbench, Analyst, Ninja, Holdings, alerts, exports, API — answer 403 `market_not_in_plan` outside scope; Holdings marks those lines `not_in_plan`. Desk, Enterprise and One-Stop default to all markets; Pilot and others default to India. Only platform billing sets scope (`PUT /api/admin/portal/orgs/{id}/coverage`, history kept); signing an order form does not. Owner: `backend/app/services/market_scope.py`; frontend helpers `lib/marketScope.ts` and `useEntitlements().inPlan / marketAccess`. Matrix: `docs/prd/PRD_COMMERCIAL.md` §3.2.
Details: `docs/PRODUCT_PORTFOLIO.md`, `docs/customer/skus/`, `docs/customer/PRICING.md`, Package UI `/package`.
Multi-tenant + production gates: `docs/PRODUCTION_B2B_B2C.md`.

## Legal entity

CiteAlpha is a product of **Ocotillo Innovation Private Limited**.

## GTM

India PMS / AIF / sell-side / EM quant desks first; retail B2C is not sold until counsel attests. See `docs/BUSINESS_PLAN.md` and `docs/MARKETING_PLAN.md` (SEO, blog, outbound).

## Do not

- Over-claim accuracy vs hand-labeled cohort size.
- Promise live exchange feeds or OMS in commercial copy.
- Sell Buy/Hold or sentiment dashboards as CiteAlpha SKUs.
