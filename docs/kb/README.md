# CiteAlpha Knowledge Base

Canonical project memory for humans and Cursor agents. Prefer these pages over reinventing conventions from chat history.

## How to use

| Audience | Start here |
|---|---|
| Any agent / new session | [00-overview](00-overview.md) → [AGENT_ROUTING](AGENT_ROUTING.md) |
| Product / GTM | [01-product-gci](01-product-gci.md) · [13-commercial](13-commercial.md) |
| Backend / scoring | [03-scoring](03-scoring.md) · [04-pipeline](04-pipeline.md) · [05-api-map](05-api-map.md) |
| Frontend / UX | [06-frontend-ux](06-frontend-ux.md) |
| Research Terminal | [07-research-terminal](07-research-terminal.md) |
| Labeling / data | [08-data-labeling](08-data-labeling.md) |
| Auth / i18n / markets | [09-i18n-auth-markets](09-i18n-auth-markets.md) |
| QA / release | [10-testing](10-testing.md) |
| AWS / ops | [11-deploy-aws](11-deploy-aws.md) |
| Compliance | [12-compliance](12-compliance.md) |
| Architecture | [02-architecture](02-architecture.md) · [ARCHITECTURE_AND_DESIGN](../ARCHITECTURE_AND_DESIGN.md) |
| Sights SKU | [14-sights](14-sights.md) |
| Platform admin portal | [15-admin-portal](15-admin-portal.md) |
| Commitment Record | [16-commitments](16-commitments.md) |
| CiteAlpha Analyst (cited agent) | [17-analyst-agent](17-analyst-agent.md) |
| Filing walk (India + US, FY22 →) | [18-filing-walk](18-filing-walk.md) |
| Reuse owners; read a source once | [19-reuse-and-source-once](19-reuse-and-source-once.md) |

## Source-of-truth docs (outside kb/)

| Topic | Doc |
|---|---|
| **Current programme (Round-3 remediation)** | `docs/PLAN_WORLDCLASS_GCI.md` |
| India whitespace (extract → match → index) | `docs/PLAN_WHITESPACE.md` |
| CiteAlpha Analyst agent + Commitment Record (draft) | `docs/PLAN_CITEALPHA_ANALYST.md` |
| MVP scope | `docs/PRODUCT_DEFINITION.md` |
| Portfolio SKUs | `docs/PRODUCT_PORTFOLIO.md` · `docs/PORTFOLIO_ROADMAP.md` |
| Stories | `docs/USER_STORIES.md` |
| Product requirements, one job per file | `docs/prd/README.md` · administration: `docs/PRD_ADMIN.md` |
| Gaps G01–G23 | `docs/GAPS_AND_ROADMAP.md` |
| Phases 0–8 | `docs/IMPLEMENTATION_PLAN.md` |
| Labeling | `docs/LABELING_PLAYBOOK.md` |
| Parameters | `docs/GCI_PARAMETERS_AND_SOURCES.md` |
| Research | `docs/RESEARCH_TERMINAL.md` |
| Customer pack | `docs/customer/` · `docs/customer/skus/` |
| B2B/B2C production | `docs/PRODUCTION_B2B_B2C.md` · `docs/INFRA_PRODUCTION.md` |
| Platform admin portal | `docs/ADMIN_PORTAL.md` |
| Admin menu PRD (super and org admin) | `docs/PRD_ADMIN.md` |
| Super admin board, workflows, reports | `docs/PLAN_SUPER_ADMIN.md` |
| Pitch | `docs/PITCH_DECK.md` |

## Cursor assets

| Kind | Path |
|---|---|
| Always-on + scoped rules | `.cursor/rules/*.mdc` |
| Workflow skills | `.cursor/skills/*/SKILL.md` |
| Specialist agents | `.cursor/agents/*.md` + root `AGENTS.md` |

## Maintenance rule

When you change scoring, API contracts, routes, deploy, or product scope: update the matching kb page in the same PR/change set. Do not invent financial actuals in docs or code.
