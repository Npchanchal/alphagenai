# 15 — Platform Admin Portal

Multi-tenant **platform** administration at `/admin` — separate from **org seat admin** on Desk (`OrgAdminPanel`).

## Two admin layers

| Layer | Who | Where | Scope |
|---|---|---|---|
| **Org admin** | `owner` / `admin` org role | Desk → Seat administration | One tenant: invites, revoke, API keys, OIDC |
| **Platform admin** | `platform_admin_role` on user or API key | `/admin` | Cross-tenant: orgs, users, legal, billing, feedback |

Org `admin` alone does **not** unlock `/admin`. User must have `platform_admin_role` set.

## Platform roles

| Role | Typical owner | Key permissions |
|---|---|---|
| `super` | Engineering lead | All — assign platform roles, system ops |
| `ops` | Customer success / ops | Orgs, pilot provision, feedback, audit |
| `compliance` | Counsel / compliance | Legal attestations, audit |
| `billing` | Finance / RevOps | Invoices, MSA, audit |
| `support` | Support desk | Feedback, users/orgs read, audit |

Permissions are enforced server-side per route (`backend/app/services/admin_portal.py`).

## APIs

Base: `/api/admin/portal/*` · Auth: session Bearer **or** `X-API-Key` with `platform_admin_role`.

| Method | Path | Permission |
|---|---|---|
| GET | `/me` | portal (any platform role) |
| GET | `/orgs` | `orgs.read`. Includes seat holders |
| DELETE | `/orgs/{id}` | `orgs.write`. Empty orgs only. Standing desks stay |
| POST | `/orgs/{id}/owner-invite` | `pilot.manage`. Emails the recorded owner a link to join as desk admin |
| GET | `/users` | `users.read` |
| PATCH | `/users/{id}/platform-role` | `users.write` (super) |
| DELETE | `/users/{id}` | `users.write` (super). Standing team accounts stay |
| DELETE | `/pilot-requests/{id}` | `pilot.manage`. Request row only; the organisation stays |
| GET/PATCH | `/feedback`, `/feedback/{id}` | `feedback.read` / `feedback.write` |
| GET/POST | `/legal`, `/legal/attest` | `legal.read` / `legal.write` |
| GET | `/billing` | `billing.read` |
| GET | `/audit` | `audit.read` |
| GET | `/board` | portal. Counts only for sections the role can open |
| GET | `/labeling` | `audit.read` |
| GET | `/commitments` | `audit.read` |
| GET | `/system` | `system.ops`. Guidance review stamp, monitors, coverage roll, flags |
| GET | `/reports` | catalog filtered by permission |
| GET | `/reports/{id}` | `index` `coverage` `sla` `audit-events` need `audit.read`. `usage` needs `billing.read`. `trust` needs `legal.read`. `audit-events?format=csv` is the same page |
| POST | `/billing/invoices` | `billing.write`. MSA invoice. Optional `signer_email` records the signature |
| POST | `/pilot` | `pilot.manage` |
| POST | `/cleanup-test-tenants` | `system.ops`. Body `{"dry_run": true}` lists e2e tenants and guests; `false` removes them. Approved pilot orgs and CiteAlpha accounts stay |

## Bootstrap

Demo super admin: `X-API-Key: intellens-admin` (seed `platform_admin_role: super`) — local only. When `INTELLENS_API_KEY` is set (production), seeded platform-admin keys are rejected; the rotated key resolves as `super`.

Grant a user:
```bash
curl -X PATCH "$API/api/admin/portal/users/{user_id}/platform-role" \
  -H "X-API-Key: intellens-admin" \
  -H "Content-Type: application/json" \
  -d '{"platform_admin_role":"ops"}'
```

Revoke: `"platform_admin_role": null`.

## Code

- Service: `backend/app/services/admin_portal.py`
- Routes: `backend/app/api/routes.py` (`/api/admin/portal/*`)
- UI: `frontend/src/pages/AdminPortalPage.tsx`
- Tests: `backend/tests/test_admin_portal.py`

## Operator board

`docs/PLAN_SUPER_ADMIN.md` (SA0–SA3, 2026-10-24). The portal reads the existing stores. It does not accept a label, a commitment, or a score, and it does not offer demo reset.

## Full runbook

`docs/ADMIN_PORTAL.md`
