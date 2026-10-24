# CiteAlpha Platform Admin Portal

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited

Operator guide for the platform admin portal — cross-tenant operations, role-based access, and API usage.

---

## Overview

The admin portal is a **platform-level** console for CiteAlpha operators. It is intentionally separate from **org seat administration** (inviting analysts, revoking seats, minting org API keys), which remains on **Desk** under *Seat administration*.

| Surface | URL | Audience |
|---|---|---|
| Platform admin portal | `/admin` | Users with `platform_admin_role` |
| Org seat admin | `/desk` (admin tab) | Org `owner` or `admin` |
| Legal attest (legacy API key) | `POST /api/legal/attest` | Admin API key (still supported) |

---

## Access model

### Platform admin vs org admin

```
┌─────────────────────────────────────────────────────────────┐
│  User session (Bearer token) or API key (X-API-Key)         │
└───────────────────────────┬─────────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
   platform_admin_role set?          org role owner/admin?
            │                               │
            ▼                               ▼
   /admin + /api/admin/portal/*     Desk seat admin only
   (cross-tenant)                    (single org_id)
```

- **Org role** (`viewer`, `analyst`, `admin`, `owner`, …) gates product features via **plan ∩ role** (`GET /api/entitlements/me`).
- **Platform admin role** (`super`, `ops`, `compliance`, `billing`, `support`) gates the admin portal only.
- A user can be org `admin` **and** platform `ops` — the roles are independent.

### Authentication

The portal accepts either:

1. **Session** — `Authorization: Bearer <token>` after login/register
2. **API key** — `X-API-Key: <key>` where the key row includes `platform_admin_role`

Session users see **Admin portal** in the account menu when `platform_admin_role` is present on their profile.

---

## Platform roles and permissions

Defined in `backend/app/services/admin_portal.py`.

| Platform role | Organizations | Users | Feedback | Legal | Billing | Pilot | Audit | System |
|---|---|---|---|---|---|---|---|---|
| `super` | read/write | read/write | read/write | read/write | read/write | manage | read | ops |
| `ops` | read/write | read | read/write | — | — | manage | read | — |
| `compliance` | read | — | — | read/write | — | — | read | — |
| `billing` | read | — | — | — | read/write | — | read | — |
| `support` | read | read | read/write | — | — | — | read | — |

Permission strings (enforced per route): `orgs.read`, `orgs.write`, `users.read`, `users.write`, `feedback.read`, `feedback.write`, `legal.read`, `legal.write`, `billing.read`, `billing.write`, `pilot.manage`, `audit.read`, `system.ops`.

Only **`super`** can assign or revoke platform roles (`users.write`).

---

## UI sections

Route: `/admin?section=<id>`

| Section ID | Label | Visible when |
|---|---|---|
| `overview` | Work board | Always. Queue rows follow the caller's permissions |
| `orgs` | Organizations | `orgs.read` |
| `users` | Users | `users.read`. Filter: standing accounts |
| `feedback` | Feedback | `feedback.read`. Ack and Close |
| `legal` | Legal | `legal.read` |
| `billing` | Billing | `billing.read`. Issue an MSA invoice with `billing.write` |
| `audit` | Audit | `audit.read` |
| `labeling` | Labeling | `audit.read`. Queue, extracts, source checks. No accept |
| `commitments` | Commitments | `audit.read`. Unreviewed rows. No accept |
| `reports` | Reports | Index, coverage, filing-to-score, and auth events (`audit.read`); seat and agent use (`billing.read`); trust (`legal.read`) |
| `pilot-requests` | Pilot requests | `pilot.manage` |
| `system` | System | `system.ops` (super only). Job status, flags, test-tenant cleanup. Demo reset stays off this page |

Non-admins see an access-denied screen with a link back to Desk.

---

## API reference

Base path: `/api/admin/portal`

All endpoints require platform admin auth. Missing or invalid auth returns `401`; valid auth without platform role returns `403`.

### `GET /api/admin/portal/me`

Returns current platform role, flat permission list, and UI section map.

```json
{
  "platform_admin_role": "ops",
  "permissions": ["audit.read", "feedback.read", "feedback.write", "orgs.read", "orgs.write", "pilot.manage", "portal.access", "users.read"],
  "source": "session",
  "email": "ops@desk.example",
  "sections": [
    { "id": "overview", "label": "Overview" },
    { "id": "orgs", "label": "Organizations" }
  ]
}
```

### `GET /api/admin/portal/orgs`

Lists all org snapshots (plan, seats, account type) plus `members` (the logins on each seat), `deletable`, and `delete_block`. Requires `orgs.read`. A recorded `owner_email` with no matching member has not taken a seat.

### `DELETE /api/admin/portal/orgs/{org_id}`

Deletes an empty organisation, its pilot checklist, org API keys, and outstanding invites. Requires `orgs.write`. Standing desks (`demo`, `retail`, `onestop-demo`, `citealpha-team`, and any org marked `protected`) return 400. An organisation that still has a seat holder returns 409. A pilot request that named the desk is left in place.

### `POST /api/admin/portal/orgs/{org_id}/owner-invite`

Emails the address stored as `owner_email` a one-time link to join that desk as admin. Requires `pilot.manage`. The seat is taken when they accept. No recorded email returns 400. An email that already has a login returns 409. Use this to send the link again after an approved request, including a desk that was approved before the invite was sent. Approving a pilot request sends the same invite. The seat stays until the user is deleted.

### `GET /api/admin/portal/users`

Lists registered users (no password fields), including `protected`. Requires `users.read`.

### `DELETE /api/admin/portal/users/{user_id}`

Deletes the login, ends its sessions, and frees the seat. Requires `users.write` (super). A standing team account, and the account the caller is signed in with, return 400.

### `PATCH /api/admin/portal/users/{user_id}/platform-role`

Assign or revoke platform admin role. Requires `users.write` (**super only**).

```json
{ "platform_admin_role": "compliance" }
```

Revoke:

```json
{ "platform_admin_role": null }
```

Valid values: `super`, `ops`, `compliance`, `billing`, `support`, or `null`.

### `GET /api/admin/portal/feedback`

All partner feedback across orgs. Optional `?status=open`. Requires `feedback.read`.

### `PATCH /api/admin/portal/feedback/{item_id}`

Update feedback status (`open` | `ack` | `closed`). Requires `feedback.write`.

```json
{ "status": "ack" }
```

### `GET /api/admin/portal/legal`

Legal counsel snapshot (same shape as `legal_attest.snapshot()`). Requires `legal.read`.

### `POST /api/admin/portal/legal/attest`

Record counsel attestation. Requires `legal.write`.

```json
{
  "kind": "terms_privacy",
  "attested_by": "counsel@firm.com",
  "note": "Optional note"
}
```

Kinds: `terms_privacy` | `sebi_retail`.

### `GET /api/admin/portal/billing`

All invoices (cross-org). Requires `billing.read`.

### `GET /api/admin/portal/audit`

Aggregate counters: orgs, users, open feedback, reviews, pending extracts. Requires `audit.read`.

### Work board, queues, and reports

| Method | Path | Permission |
|---|---|---|
| GET | `/api/admin/portal/board` | Any platform role. Omits rows the role cannot open |
| GET | `/api/admin/portal/labeling` | `audit.read` |
| GET | `/api/admin/portal/commitments` | `audit.read` |
| GET | `/api/admin/portal/system` | `system.ops` |
| GET | `/api/admin/portal/reports` | Catalog for the caller |
| GET | `/api/admin/portal/reports/{id}` | See the table above. `audit-events?format=csv` downloads that page |
| POST | `/api/admin/portal/billing/invoices` | `billing.write`. Body `org_id`, `plan`, `seats`, optional `amount_inr`, `po_number`, `signer_email` |

The portal reads stored files. It does not recalculate a GCI, accept a label, or accept a commitment.

### `POST /api/admin/portal/pilot`

Provision a new pilot org. Requires `pilot.manage`.

```json
{ "name": "Acme Research Desk" }
```

---

## Bootstrap and operations

### Demo / local environment

Seed data includes a super-admin API key:

```
X-API-Key: intellens-admin
```

(`backend/app/data/seed.py` — `platform_admin_role: super`)

When `INTELLENS_API_KEY` is set (production), seeded platform-admin keys such as
`intellens-admin` are rejected everywhere; use `X-API-Key: $INTELLENS_API_KEY` instead
(it resolves as platform `super`).

### Grant platform access to a user

1. Register or identify the user (`GET /api/admin/portal/users` as super).
2. Assign role:

```bash
export API=http://localhost:8000

curl -X PATCH "$API/api/admin/portal/users/{USER_ID}/platform-role" \
  -H "X-API-Key: intellens-admin" \
  -H "Content-Type: application/json" \
  -d '{"platform_admin_role":"ops"}'
```

3. User signs in (or refreshes session). **Admin portal** appears in the account menu.
4. Open `/admin`.

### Revoke access

```bash
curl -X PATCH "$API/api/admin/portal/users/{USER_ID}/platform-role" \
  -H "X-API-Key: intellens-admin" \
  -H "Content-Type: application/json" \
  -d '{"platform_admin_role":null}'
```

### Production checklist

- [x] Rotate `intellens-admin` — setting `INTELLENS_API_KEY` disables seeded platform-admin keys.
- [ ] Grant `super` to at most 1–2 break-glass operator accounts (not shared mailboxes).
- [ ] Use least-privilege roles (`compliance`, `billing`, `support`) for day-to-day work.
- [ ] Legal attest changes are logged in `legal_attestations` (SQL) and seed `legal_attestations` (JSON fallback).
- [ ] Portal does not expose password hashes or raw API keys except org key mint on Desk.

See also: `docs/PRODUCTION_B2B_B2C.md`, `docs/INFRA_PRODUCTION.md`, `.env.production.example`.

---

## Security notes

- Platform permissions are **not** unioned with org entitlements — separate concern.
- Feedback and legal actions do **not** mutate GCI scores; they route to ops/legal workflows only.
- `POST /api/admin/reset-demo` requires platform `system.ops` (super). It wipes the JSON store and persisted tenant state (all customer orgs) — never run it on production; not exposed in UI.
- Do not grant `super` to customer org users; platform roles are for Ocotillo operators only.

---

## Development

| Artifact | Path |
|---|---|
| RBAC service | `backend/app/services/admin_portal.py` |
| Routes | `backend/app/api/routes.py` |
| Pydantic | `PlatformAdminRoleRequest` in `backend/app/models/schemas.py` |
| Session field | `platform_admin_role` on user; exposed in `_public_user()` |
| Frontend page | `frontend/src/pages/AdminPortalPage.tsx` |
| API client | `frontend/src/lib/api.ts` (`fetchAdminPortal*`) |
| Tests | `backend/tests/test_admin_portal.py` |

Run tests:

```bash
cd backend && pytest tests/test_admin_portal.py -q
```

KB summary: `docs/kb/15-admin-portal.md`
