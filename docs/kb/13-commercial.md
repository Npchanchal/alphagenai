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
