# Plan — Super admin: workflows, board, reports

**Status:** implemented 2026-10-24 · **Owner:** `platform-engineer` · skill `citealpha-production`
**Surface:** `/admin` for `platform_admin_role: super` (and the narrower roles where a permission already exists).
**Rules:** `reuse-before-add`, `source-once`, `index-integrity`, `public-copy-voice`. Nothing here writes a GCI or accepts a commitment.

This plan is the operator console. It is not a second Analyst, and it does not bring back Disclosure Explorer boards.

---

## 0. What super already has

`/admin` and `/api/admin/portal/*` (`admin_portal.py`, `AdminPortalPage.tsx`).

| Section | What a super can do today |
|---|---|
| Overview | Lists the caller's permission strings |
| Organizations | List desks and seat holders; provision a pilot; resend the owner invite; delete an empty org |
| Users | List logins; assign `super` / `ops` / `compliance` / `billing` / `support`; delete a login and free the seat |
| Feedback | List partner feedback; acknowledge an open item |
| Pilot requests | Approve (30 / 45 / 60 days), reject, delete the request |
| Legal | Counsel snapshot; record `terms_privacy` or `sebi_retail` |
| Billing | Read the invoice table |
| Audit | Eight counters (orgs, users, feedback, pilots, reviews, pending extracts) |
| System | A note that `POST /api/admin/reset-demo` stays off the UI |

Server-side permissions already exist and stay the gate. Org seat admin on Desk is unchanged.

---

## 1. What is not in the portal

These owners already exist. The portal does not show them, so a super still shells in or opens Desk as one org.

### Workflows

| Workflow | Owner today | Gap |
|---|---|---|
| Feedback through to closed | `PATCH /api/admin/portal/feedback/{id}` accepts `closed` | UI only offers Ack |
| Test-tenant cleanup | `POST /api/admin/portal/cleanup-test-tenants` (`system.ops`, dry-run default) | No button. Dry-run result is invisible |
| Labeling queue across desks | `GET /api/labeling/queue?org_id=` for a platform admin | Desk queue is one org. Portal has no queue |
| Daily guidance review | `jobs/guidance_review.py` | No last market, last run, or rows left unscored |
| India / US coverage roll | `india_coverage.coverage_progress`, `us_coverage.coverage_progress`, `GET /api/ops/coverage-progress` (API key) | Not on `/admin` |
| Source verification | `jobs/verify_sources.py`, Trust `source_verification` | Failures enqueue labeling; portal does not list them |
| Commitment review | `api/analyst_routes.py` review actions | Unreviewed count is not on the board. Accept stays on the analyst route |
| Analyst monitors | `services/agent/monitors.py` `status()` | Per-org feed only. No cross-tenant last run |
| MSA invoice | `billing.create_msa_invoice`, `billing.sign_msa` | `billing.write` is granted and unused. Portal is read-only |
| Auth events | `audit_log.list_audit` (one org) | Portal audit is counters, not the event list |

`POST /api/admin/reset-demo` stays off the UI in every phase.

### Board

Overview is a permission list. There is no single board of work waiting on an operator: pending pilots, open feedback, pending extracts, source-verify failures, unreviewed commitments, labeling items, a coverage roll in flight.

Disclosure Explorer Boards (`/sights/boards`) were retired on 2026-10-17. Watchlists live on Filing Search. Do not rebuild that page.

### Reports

| Report | Data already on disk | Gap |
|---|---|---|
| Index health | `gci_score_cache.load_cache`, `score_policy` tiers | No count of published rows, tier mix, or `pending_guidance_cite` |
| Coverage | `coverage_status.json` | Scoreboard is `python -m app.jobs.guidance_coverage` |
| Filing-to-score | `score_pipeline.jsonl`, `services/score_sla.py` | Shown on `/methodology`, not to the operator |
| Seat and agent use | org snapshots, `run_store`, monitor `status()` | No per-desk runs, monitors, or seats-used report |
| Trust (internal) | `GET /api/admin/portal/trust` | No section. Counsel and SSO fields stay off the public API |
| Auth audit export | `audit_log.list_audit` | No cross-tenant list or download |

### Other

| Item | Owner | Gap |
|---|---|---|
| Feature flags | `feature_flags.flags_dict` | Env-only. Super cannot see which jobs are on |
| Protected accounts | `protected_users.json` | Enforced on delete. Not listed as a class of their own beyond the user row |

---

## 2. Decisions

| # | Decision | Consequence |
|---|---|---|
| D1 | Extend `admin_portal.py` and `AdminPortalPage.tsx` | No `admin_v2`, no new ops service |
| D2 | Read stores. Do not recompute a published GCI and do not refetch a filing | `load_cache`, `coverage_status.json`, `score_pipeline.jsonl`, commitment store, labeling queue |
| D3 | The portal does not accept a label, a commitment, or a score | Links and counts only. Mutations stay on Desk, Analyst review, and the guidance-review job |
| D4 | `reset-demo` is never a button | Cleanup of `e2e-*` / `@ocotillo.test` is the only destructive control, dry-run first |
| D5 | Copy on `/admin` may name the job. It does not name env flags | "Guidance review last ran …" rather than `INTELLENS_GUIDANCE_REVIEW` |

---

## 3. Phases

### SA0 — Work board

Replace the Overview permission dump with a board. Keep the permission list under it.

Rows, each a link to the section that can act:

| Row | Read from | Shown when |
|---|---|---|
| Pilot requests waiting | `pilot_request.list_requests` | `pilot.manage` |
| Feedback still open | `feedback.list_feedback` | `feedback.read` |
| Extracts waiting | `get_data()["pending_extracts"]` | `audit.read` |
| Labeling items | labeling queue, all orgs | `audit.read` |
| Commitments unreviewed | `commitment_store` | `audit.read` |
| Coverage roll | `india_coverage.coverage_progress` and `us_coverage.coverage_progress` | `system.ops` |

`GET /api/admin/portal/board` returns those counts. The page does not call `/api/ops/coverage-progress` (that route stays API-key). Tests: a support actor does not receive the coverage row; counts match the stores.

### SA1 — Finish the workflows that already have an API

| Item | Change | Permission |
|---|---|---|
| Close feedback | Button next to Ack, status `closed` | `feedback.write` |
| Cleanup | System section: dry-run, show `users_removed` / `orgs_removed`, second confirm to apply | `system.ops` |
| Labeling | New section lists queue rows across orgs (company, kind, org, age). No accept button. Link copy tells the reviewer to open Desk | `audit.read` |
| Invoices | Billing section: create an MSA invoice for an existing org (`create_msa_invoice`). Record a signature only through the existing `sign_msa` path if the signer email is supplied. No retail checkout | `billing.write` |
| Guidance review | System section shows last market and last completed date from the job's existing status file. Read only | `system.ops` |
| Monitors | System section shows `monitors.status()` totals (orgs with a monitor, last trigger). Read only | `system.ops` |

Tests extend `test_admin_portal.py`. An ops actor gets 403 on cleanup and on invoice create.

### SA2 — Reports

`GET /api/admin/portal/reports/{id}` with `audit.read`, except billing usage which needs `billing.read`.

| id | Contents | Must not |
|---|---|---|
| `index` | Published company count, tier counts, rows excluded as `pending_guidance_cite` | Recalculate a score. Rank a company below `established` |
| `coverage` | Counts by `coverage_status` for India and US, from `coverage_status.json` | Call NSE, BSE, or EDGAR |
| `sla` | Filing-to-score median from `score_sla` | Invent a median when the pipeline file is empty — show "no filings in the window" |
| `usage` | Per org: plan, seats used, monitor count, skill runs in the last 7 days | Include another org's upload text or memory |
| `trust` | Existing `/api/admin/portal/trust` body, rendered | Put counsel status on any public page |
| `audit-events` | `audit_log.list_audit` across orgs, newest 200, CSV download of that page | Log passwords, tokens, or API key secrets |

UI: a Reports section. Each report is a table plus the as-of time of the file it read.

### SA3 — Flags and protected accounts

| Item | Change |
|---|---|
| Flags | System section lists `flags_dict()` values in plain labels (India coverage roll, guidance review, analyst monitors, event filings, sights grid, sights deep dive). Read only. Changing a flag stays an environment change |
| Protected | Users table already shows `protected`. Add a filter "Standing accounts" so super can see them without scanning |

No phase adds a scheduler, a new document fetcher, or a write into `hand_labeled.py`.

---

## 4. Out of scope

- Sights search, ask, boards, agents, export. They stay redirected.
- Analyst Skills, exports, and destinations. Those are `/analyst`. A super reads counts only.
- Buyer-universe, estimate-forecast, and pitch workflows from the SuperAnalyst benchmark. `docs/PLAN_CITEALPHA_ANALYST.md` §2.2 already marks them out of scope. The thirteen Skills in `backend/app/skills/` are the shipped set.
- Office add-in, Postgres, and the ten-company commitment review. Those leftovers stay on the Analyst plan.
- A button for `reset-demo`.
- Publishing or moving a GCI from this portal.

---

## 5. Exit

- Super opens `/admin` and sees the board with live counts, not only permission names.
- Feedback can be closed, an MSA invoice can be created, and test-tenant cleanup shows a dry-run before it deletes.
- The six reports render from stored files and match those files in tests.
- `tests/test_admin_portal.py` covers each new route for super, for a role that lacks the permission, and for a user with no platform role (403).
- `docs/ADMIN_PORTAL.md` and `docs/kb/15-admin-portal.md` list the new sections in the same change as the routes.

---

## 6. Progress log

| Date | Note |
|---|---|
| 2026-10-24 | Plan written from the live portal. No code in this change. |
| 2026-10-24 | SA0–SA3 in `admin_portal.py` and `AdminPortalPage.tsx`. Board, labeling, commitments, six reports, MSA invoice, cleanup preview, flags, standing-account filter. |
