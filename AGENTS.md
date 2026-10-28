# AGENTS.md — CiteAlpha

Instructions for Cursor agents working in this repository.

## Mission

Ship a credible **Guidance Credibility Index (GCI)** for Indian equity desks under **CiteAlpha** (Ocotillo Innovation Private Limited): factual, evidence-linked management delivery scores — not sentiment, not Buy/Hold.

## Always

1. Read `docs/kb/00-overview.md` when context is cold.
2. Follow always-on rules `.cursor/rules/citealpha-core.mdc` and `.cursor/rules/index-integrity.mdc`.
3. Pick a specialist from `.cursor/agents/` using `docs/kb/AGENT_ROUTING.md`.
4. Load the matching `.cursor/skills/*/SKILL.md` before multi-step work.
5. Prefer small, tested changes; never invent financial actuals **or score history**.
6. Any change that moves a published GCI follows `citealpha-index-integrity` (ledger + changelog).
7. Public copy is for domain experts: rule `public-copy-voice`; canonical names GCI Screener · Analyst Workbench · Filing Search · Disclosure Explorer · Public Snapshot.
8. Do not duplicate a shipped owner or refetch a stored source. Rules `reuse-before-add` and `source-once`; skill `citealpha-reuse-sources`; map `docs/kb/19-reuse-and-source-once.md`.

## Current programme

`docs/PLAN_WORLDCLASS_GCI.md` — Round-3 review remediation (findings `R3-nn`, workstreams `W1–W9`, gates G-A…G-E). Execute with skill `citealpha-worldclass-remediation`.

`docs/PLAN_WHITESPACE.md` — India guidance extract, match vs actuals, and the ranked index (WS0–WS4). Extend `disclosures.py`. Execute on request with `citealpha-gci-dev`.

## Specialist agents

| Agent file | Use for |
|---|---|
| [index-steward](.cursor/agents/index-steward.md) | Score policy, confidence tiers, ledger, changelog, labeling governance, index governance |
| [gci-engineer](.cursor/agents/gci-engineer.md) | Scoring, APIs, pipeline, Screener/dossier backend |
| [frontend-designer](.cursor/agents/frontend-designer.md) | Expert-grade UI/UX: homepage, dossier, Screener, Snapshot, Workbench chrome |
| [research-terminal](.cursor/agents/research-terminal.md) | Search, cite-only chat, snapshots |
| [labeling-analyst](.cursor/agents/labeling-analyst.md) | Hand-labeled Sensex outcomes |
| [guidance-reviewer](.cursor/agents/guidance-reviewer.md) | Daily guidance-quote and later-filing review, one market per day |
| [product-strategist](.cursor/agents/product-strategist.md) | Scope, GTM, user stories, pitch |
| [qa-release](.cursor/agents/qa-release.md) | pytest, Playwright, docker verify |
| [devops-aws](.cursor/agents/devops-aws.md) | ECS deploy, idle/wake, health checks |
| [compliance-reviewer](.cursor/agents/compliance-reviewer.md) | SEBI disclaimer, claim hygiene |
| [architect](.cursor/agents/architect.md) | Layering, refactors, system map |
| [sights-engineer](.cursor/agents/sights-engineer.md) | Sights SKU (`/sights/*`, `/api/sights/*`) |
| [platform-engineer](.cursor/agents/platform-engineer.md) | Auth, billing, entitlements, Postgres |
| [portfolio-engineer](.cursor/agents/portfolio-engineer.md) | Score, Cite, Radar, Ledger, Data SKUs |

## Knowledge base

Canonical memory: [`docs/kb/README.md`](docs/kb/README.md).

## Demo write key

`X-API-Key: intellens-demo` (local demo org, seat `reviewer`)
