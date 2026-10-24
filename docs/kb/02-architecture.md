# 02 — Architecture

**Detailed design (diagrams):** [`docs/ARCHITECTURE_AND_DESIGN.md`](../ARCHITECTURE_AND_DESIGN.md) · Internal only — not published on the site

## Layout

```
backend/app/
  api/routes.py          # thin HTTP
  models/                # Pydantic
  services/              # pure scoring, extract, match, research, auth
  data/                  # seed, hand_labeled, store.json
frontend/src/
  lib/api.ts             # sole HTTP client
  pages/                 # route surfaces
  components/            # EvidenceTable, TabBar, ChangeChip, …
  i18n/                  # vernacular UI strings
e2e/                     # Playwright
deploy/aws/              # Terraform / ECS
scripts/                 # verify-all, aws-deploy, idle/wake
```

## Layering rules

| Layer | May | Must not |
|---|---|---|
| `services/gci_scoring.py` | Pure math on outcomes | DB, HTTP, time.now side effects |
| `services/repository.py` | Read/write store | Scoring policy |
| `api/routes.py` | Auth, validation, HTTPException | Business formulas |
| `frontend/lib/api.ts` | Typed fetch | Inline fetch in random components |

## Data flow (GCI)

```
IR / transcript / import
  → extract (structured statements, pending)
  → analyst Accept/Edit/Reject → commit
  → match (company_id, period, metric) ↔ actuals
  → compute_company_gci → CompanyGCIDetail
  → UI evidence trail + PIT history
```

## Persistence

Demo/MVP store: JSON under `backend/app/data/` (`store.json`). After hand-label edits, delete `store.json` and rebuild via app/tests.

`store.json` is rebuilt on every container start. With SQL auth (`USE_DB_AUTH` / Postgres), customer collections listed in `seed.TENANT_KEYS` (orgs, org API keys, labeling queue, notes, pilot data, …) are mirrored to `intellens_tenant_state` on each `save_data()` and restored on load. GCI data (companies, outcomes, reviews, pending extracts) is not mirrored. On startup `orgs.restore_missing_orgs()` recreates orgs for users whose org record was lost (B2B → pilot, retail → retail).

## Feature flags

See `services/feature_flags.py` — research LLM, consensus import, SSO stubs.

## Price history (context only)

- Optional **Financial Modeling Prep** EOD via `INTELLENS_FMP_API_KEY` / `FMP_API_KEY` (`services/fmp_client.py`).
- Wired into market/index/stock history APIs; **never** into GCI math.
- Free FMP tiers often block India NSE (`.NS`) with HTTP 402 → automatic demo fallback.
- See `.env.example` and `docs/AWS_DEPLOYMENT.md`.

## Related

| Topic | Doc / route |
|---|---|
| Full architecture & design | `docs/ARCHITECTURE_AND_DESIGN.md` |
| Pipeline | [04-pipeline](04-pipeline.md) |
| Reuse owners; read a source once | [19-reuse-and-source-once](19-reuse-and-source-once.md) |
| Scoring | [03-scoring](03-scoring.md) |
| AWS | [11-deploy-aws](11-deploy-aws.md) |
| UX | [06-frontend-ux](06-frontend-ux.md) |
