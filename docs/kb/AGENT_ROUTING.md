# Agent routing

Use this map to pick the right **rule set**, **skill**, and **agent** for a task.

| User intent | Agent (`.cursor/agents/`) | Skill | Rules (also) | KB |
|---|---|---|---|---|
| Implement / continue Round-3 plan (R3-nn, W1–W9) | per workstream owner | `citealpha-worldclass-remediation` | index-integrity, public-copy-voice | `docs/PLAN_WORLDCLASS_GCI.md` |
| India whitespace: guidance extract, match vs actuals, ranked index (WS0–WS4) | `gci-engineer` (WS0–WS2) · `guidance-reviewer` / `labeling-analyst` (WS3) · `frontend-designer` (WS4) | `citealpha-gci-dev`, `citealpha-guidance-review`, `citealpha-expert-ux` | index-integrity, reuse-before-add, source-once | `docs/PLAN_WHITESPACE.md`, 18 |
| A published score moved / scorer constant / ledger / changelog / tiers | `index-steward` | `citealpha-index-integrity` | index-integrity, gci-scoring | 03 |
| Score / GCI API / Screener backend | `gci-engineer` | `citealpha-gci-dev` | gci-scoring, python-backend, api-contracts, index-integrity | 03, 05 |
| Close gaps G01–G23 / pipeline | `gci-engineer` | `citealpha-close-gaps` | gci-pipeline | 04, GAPS doc |
| Public pages: homepage, dossier, Screener, Snapshot, Package, copy voice | `frontend-designer` | `citealpha-expert-ux` | frontend-ux, public-copy-voice, compliance-sebi | 06 |
| Seat roles and role UX (`BRD_ROLES`, `PRD_ROLES`, `TRD_ROLES`) | `platform-engineer` (seats) · `frontend-designer` (screens) | `citealpha-production`, `citealpha-expert-ux` | production-monetization, public-copy-voice, index-integrity | 09, 06, those three docs |
| Workbench / Filing Search chrome, tabs, toasts | `frontend-designer` | `citealpha-frontend-ux` | frontend, frontend-ux | 06 |
| Research search/chat | `research-terminal` | `citealpha-research` | research-terminal | 07 |
| Hand-label Sensex | `labeling-analyst` | `citealpha-labeling` / phase0 | data-quality | 08 |
| Guidance quote vs later filing, daily market rotation | `guidance-reviewer` | `citealpha-guidance-review` | index-integrity, data-quality | 08 |
| Product / GTM / stories | `product-strategist` | `citealpha-product` | citealpha-core, seo-marketing | 01, 13 |
| Tests / docker release | `qa-release` | `citealpha-test-deploy` | testing-deploy | 10 |
| AWS / ECS | `devops-aws` | `citealpha-aws` | aws-deploy | 11 |
| SEBI / disclaimer / claims | `compliance-reviewer` | `citealpha-compliance` | compliance-sebi | 12 |
| Auth / i18n / markets | `platform-engineer` or frontend | `citealpha-production` | i18n-auth, production-monetization | 09 |
| Billing / paywall / legal attest | `platform-engineer` | `citealpha-production` | production-monetization, compliance-sebi | 09, 13 |
| Sights SKU | `sights-engineer` | `citealpha-sights` | sights, compliance-sebi | 14 |
| Portfolio SKUs (Score/Cite/Radar/Ledger/Data) | `portfolio-engineer` | `citealpha-portfolio` | portfolio, api-contracts | 13, PRODUCT_PORTFOLIO |
| Platform admin portal / super board, workflows, reports / org admin menu | `platform-engineer` | `citealpha-production` | production-monetization, reuse-before-add | 15, `docs/PRD_ADMIN.md`, ADMIN_PORTAL, `docs/PLAN_SUPER_ADMIN.md` |
| CiteAlpha Analyst (skills, verifier, runs) / Commitment Record | `gci-engineer` (agent) · `index-steward` (commitment governance) | `citealpha-gci-dev` | index-integrity, public-copy-voice, compliance-sebi | 16, 17, `docs/PLAN_CITEALPHA_ANALYST.md` |
| Architecture map | `architect` | `citealpha-architecture` | python-backend, frontend | 02 |
| New feature, route, page, job, or external fetch (NSE, BSE, EDGAR, model) | `architect` | `citealpha-reuse-sources` | reuse-before-add, source-once | 19 |
| Update this kb | any | `citealpha-kb` | docs-kb | README |

## Default session

1. Read `docs/kb/00-overview.md` if unfamiliar.
2. Apply always-on `citealpha-core` and `index-integrity`.
3. Load the matching skill before coding.
4. Keep changes small and tested.
5. If a published GCI number changes, finish with the ledger + changelog protocol (`citealpha-index-integrity`).
6. Before a new module or a source fetch, follow `citealpha-reuse-sources` and `docs/kb/19-reuse-and-source-once.md`. Extend the owner. Read the store before NSE, BSE, EDGAR, or the model.
