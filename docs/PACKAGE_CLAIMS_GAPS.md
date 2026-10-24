# Package Plans — claims vs product (audit + implementation plan)

**Audited:** 2026-08-07 · **Implemented:** 2026-08-07 (P0–P3 product gaps).

## Status (post-implementation)

| Area | Status |
|---|---|
| GCI + evidence + review | **Shipped** |
| Tier 1 corpus / citations | **Shipped** |
| Wordmap | **Shipped** — corpus themes + seed fallback (`source` / `citeable`) |
| MoM / QoQ / YoY | **Shipped** — prefers citeable PIT; warehouse labeled |
| Granger analytics | **Shipped** — prefers citeable ≥12; else `demo_pit_extension` |
| EM factor export | **Shipped** — JSON + CSV (+ Parquet/TSV fallback) |
| Facts / AlphaHunter import | **Shipped** — `/api/import/facts` + `/alphahunter` |
| Org seats / plan entitlements | **Shipped** — Pilot 5 / Desk 25 / One-Stop 40 |
| Soft API rate limits | **Shipped** — `RATE_LIMIT_RPM` (default 300, per visitor IP or API key) |
| SSO OIDC | **Shipped** — authorize → token → session when `OIDC_*` set; HTML bridge for browser; see `docs/OIDC.md` |
| Labeling priority queue | **Shipped** — Desk tab + `/api/labeling/queue` |
| Research estimates | **Shipped** — no silent demo street (`ALLOW_DEMO_STREET`) |
| Charts / market tape | **Honest** — FMP when `INTELLENS_FMP_API_KEY` set on ECS; else demo |
| Live AlphaHunter | **Shipped** — `ALPHAHUNTER_API_URL` live pull + paste fallback |
| Nifty deep GCI | **Milestone-gated** — M0–M4 API + Desk enqueue; no invented hand_labels |
| HTTPS custom domain | **Ready** — Route53/ACM; Hostinger NS cutover required |
| CSM / SLA / VPC | **Shipped surfaces** — Desk CSM + `/api/csm` `/api/sla` `/api/vpc/posture`; MSA terms still commercial |
| Git | **Remote** — https://github.com/Npchanchal/alphagenai |

## Tests

`backend/tests/test_package_gaps.py` · `backend/tests/test_production_gaps.py`

## Ops flags

| Env | Default | Meaning |
|---|---|---|
| `RATE_LIMIT_RPM` | 300 | Soft API rate limit |
| `SSO` | false | Enable SSO endpoints |
| `OIDC_CLIENT_ID` / `ISSUER` / `REDIRECT_URI` / `CLIENT_SECRET` | — | Real OIDC |
| `OIDC_DEMO_ASSERT` | false | Test-only email → session |
| `ALPHAHUNTER_API_URL` / `ALPHAHUNTER_API_KEY` | — | Live facts connector |
| `CSM_EMAIL` | csm@citealpha.com | Desk CSM contact |
| `ALLOW_DEMO_STREET` | false | Fabricated street consensus |
