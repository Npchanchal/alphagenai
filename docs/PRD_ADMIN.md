# PRD — Administration

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited  
**Status:** Implemented · **Date:** 2026-10-25  
**Owners:** `platform-engineer` (access and APIs) · `frontend-designer` (menu and screens)  
**Skills:** `citealpha-production` · `citealpha-expert-ux` · `citealpha-reuse-sources`  
**Related:** `docs/ADMIN_PORTAL.md` · `docs/PLAN_SUPER_ADMIN.md` · `docs/kb/15-admin-portal.md` · `docs/kb/09-i18n-auth-markets.md`

This document specifies the admin menu and the work each admin can do. It extends the portal and organisation settings that already ship. It does not add a second admin application.

---

## Prime requirement — a person who has one job to finish

An operator opens CiteAlpha to do one thing: invite a colleague, look up a desk, attest terms, or see whether a pilot is still inside its term. They already know the product. They should not have to remember a URL.

The admin bar sits under the public navigation, on every page, and only for someone who holds an organisation `owner` or `admin` seat, or a platform role. Everyone else sees the ordinary site. There is no empty “Admin” slot reminding them they lack a role.

The bar speaks in jobs, not in permission names. “People”, “Pilots”, “Billing”, “Trust”. The open item is marked, and the address remembers the place, so refresh and the back button bring them back to the same job. A control they cannot use is left off the menu. If they paste the address anyway, the page says, in one sentence, that this job belongs to another role, and it offers the place they can go. It does not render half a form.

An organisation owner who is also a platform operator sees two menus, Organisation then Platform, each with its own chip in plain words (“Organisation owner”, “Platform ops”). The two jobs stay separate. Approving a pilot does not publish a score. Appointing a seat does not change a GCI.

On a narrow screen the bar wraps or becomes a single menu the thumb can open. The role chip remains visible so a shared laptop does not leave someone guessing which hat they are wearing.

---

## 1. Summary

CiteAlpha has two independent admin layers.

| Layer | Who | Scope |
|---|---|---|
| **Platform** | `platform_admin_role` on the user or API key: `super`, `ops`, `compliance`, `billing`, `support` | Every organisation. Ocotillo operators only. |
| **Organisation** | Org seat role `owner` or `admin` | That one organisation. Customer desk leads. |

A signed-in admin sees a **second menu bar**, under the public navigation, and only that person sees it. The bar lists the jobs that role can perform. A Head of Research who is an analyst, a labeler, a reviewer, a viewer, a guest, or a retail account does not see the bar.

`super` is the full platform operator. An organisation `owner` is the full administrator of one desk. An organisation `admin` is the same desk with a shorter People menu: they cannot appoint or remove another admin.

Someone who holds both a platform role and an organisation seat sees both menus. The roles are not merged. Plan features and admin permissions stay separate: effective product access is still **plan ∩ role**.

---

## 2. Problem

Operators and desk leads already have the functions. They do not have one place to find them.

| Job today | Where it lives | Who can open it |
|---|---|---|
| Cross-tenant board, orgs, users, pilots, legal, billing, reports, system | `/admin?section=` | Platform role. Link sits in the account menu. |
| Seats, invites, revoke, design partner, one desk API key, SSO status | `/org/settings` | Org `owner` or `admin`. Link sits in the account menu. |
| Analyst API keys, delivery destinations, export house style | CiteAlpha Analyst settings | Org `owner` or `admin`, and only when the plan includes Analyst. |
| Invoices for this desk | `/billing` | The signed-in org. |
| Pilot checklist | `GET/PATCH /api/orgs/{id}/pilot-checklist` | The org. No admin screen. |
| Organisation sign-in (issuer, client id, email domain) | `PUT /api/orgs/{id}/oidc` | Org `owner` or `admin`. No form. |
| This desk’s auth events | `GET /api/audit` | The org. No admin screen. |

A viewer who is handed `/admin` or `/org/settings` must get a denial, not a partial console. A platform `support` user must not see System. An organisation `admin` must not see a control that appoints another admin.

---

## 3. Users

| Persona | Role | Menu they see | Job to be done |
|---|---|---|---|
| Engineering lead | Platform `super` | Full Platform menu | Break-glass: roles, empty-org removal, system status, test-tenant cleanup |
| Customer success | Platform `ops` | Work, Tenants (no platform-role assign), no System, no Billing write | Pilots, feedback, owner invites |
| Counsel | Platform `compliance` | Trust, plus organisation read | Attest terms and the retail gate |
| Finance | Platform `billing` | Commercial, organisation read, audit read | MSA invoices |
| Support | Platform `support` | Work (feedback), Tenants read, Users read, audit read | Look up a desk and close feedback |
| Desk owner | Org `owner` | Full Organisation menu | Seats, admins, keys, sign-in, billing, delivery |
| Desk admin | Org `admin` | Organisation menu without appoint-admin | Invites and day-to-day access |
| Analyst, reviewer, labeler, viewer | Seat role only | No admin bar | Use the product. Ask an owner when a seat or key is needed. |
| Guest or retail | No shared desk | No admin bar | Personal use. Retail has no shared seats. |

Platform roles are for Ocotillo staff. Do not grant `super` to a customer login. The Users screen says so before the role is saved.

---

## 4. Decisions

| # | Decision |
|---|---|
| D1 | Keep the two layers. An org `admin` does not unlock `/admin`. A platform role does not become a seat on every desk. |
| D2 | One admin bar in the site header. Two menus when the person holds both layers. Items the caller cannot open are omitted, not disabled. |
| D3 | Extend `AdminPortalPage.tsx`, `OrgSettingsPage.tsx`, `OrgAdminPanel.tsx`, and `AnalystSettings.tsx`. Extend `admin_portal.py`, `orgs.py`, and `services/agent/org_keys.py`. No new portal, no `admin_v2`. |
| D4 | The server is the gate. Hiding a menu item is presentation. A direct URL without the permission returns 403 and an empty body. |
| D5 | Organisation screens read and write only `user.org_id`. Platform screens are the only cross-tenant views. |
| D6 | This menu does not publish or move a GCI, accept a label, accept a commitment, or offer demo reset. |
| D7 | The seat ladder stays `viewer` · `analyst` · `labeler` · `reviewer` · `admin` · `owner`. No custom roles. |
| D8 | The owner appoints and removes `admin`. An admin changes only `viewer`, `analyst`, `labeler`, and `reviewer`. Nobody assigns `owner` from either menu. Register creates the owner. A pilot approval invites the recorded address as `admin`. |
| D9 | Standing team accounts (`*.team@citealpha.com` on `citealpha-team`) cannot be revoked or re-roled by an org admin. Platform delete of a standing login stays refused. |
| D10 | Customer-facing labels follow public-copy voice. Platform labels may name the job (“Guidance review last ran …”) and do not name environment flags. |
| D11 | Two key stores stay, with two labels on the Access menu. Desk keys (`orgs.mint_api_key`) and Analyst keys (`org_keys`) are different credentials. Do not add a third. |

---

## 5. What this menu is not

- A second GCI Screener, Workbench, Filing Search, or CiteAlpha Analyst. Those stay in the public nav. The admin bar links to them when an admin needs the product; it does not copy their panels.
- A place to accept labels or commitments. The platform Labeling and Commitments items are queues and counts. The reviewer still accepts on the Workbench and on the analyst review route.
- Disclosure Explorer boards, Sights search, Sights ask, or export. Those routes stay redirected.
- Retail checkout. Counsel attest can open the retail gate later. The billing item issues an MSA invoice for an existing organisation.
- Self-serve plan changes. Moving a desk from Pilot to Desk, Enterprise, or One-Stop is a platform billing action.
- A button for `POST /api/admin/reset-demo`.
- Environment-flag editing. System shows the current flag state in plain language. Changing a flag remains an environment change.

---

## 6. Menu bar

### 6.1 Placement

The public nav is unchanged for every visitor: GCI Screener, Research, Workspace, Pricing, Learn, and the account menu.

When the session is an organisation `owner`, an organisation `admin`, or any platform role, the shell renders an **admin bar** directly under that nav, on every page. It is a single horizontal bar, keyboard-operable, with the same paper/ink chrome as the public nav.

The account menu keeps a text link to the same home (`Organisation settings`, `Admin portal`) so a deep link still exists. The bar is the primary way in.

### 6.2 Who sees it

| Session | Admin bar |
|---|---|
| Logged out, guest, retail, viewer, analyst, labeler, reviewer | Absent. No empty “Admin” slot. |
| Org `owner` or `admin` only | **Organisation** menu |
| Platform role only | **Platform** menu, items for that role’s permissions |
| Both | **Organisation**, then **Platform** |

The bar shows a role chip in plain words: “Organisation owner”, “Organisation admin”, “Platform super”, “Platform ops”, and the same pattern for compliance, billing, and support. A dual-role user sees both chips.

### 6.3 Behaviour

- Each top-level word opens a menu of groups. Each group is a label plus items. Selecting an item navigates; it does not open a third flyout.
- The open item is marked. The query string is the source of truth, so refresh and back keep the place.
- Organisation home: `/org/settings?section=<id>`
- Platform home: `/admin?section=<id>` (reports add `&report=<id>`)
- On a narrow viewport the bar collapses to one control labelled **Admin**, then the same groups. The public nav’s own menu is separate.
- A section the role cannot open is missing from the menu. Pasting its URL shows a short denial and a link back to the first section they can open. No counts, names, or rows from the forbidden section.

### 6.4 Organisation menu

Visible to org `owner` and org `admin`. Owner-only items are marked.

| Group | Item | Section id | Owner | Admin |
|---|---|---|---|---|
| Overview | Summary | `overview` | yes | yes |
| People | Members | `members` | yes, including appoint admin | yes, working seats only |
| People | Invites | `invites` | yes | yes |
| People | Design partners | `partners` | yes | yes |
| Access | Sign-in | `signin` | yes | yes |
| Access | API keys | `keys` | yes | yes |
| Delivery | Destinations | `destinations` | yes, plan has Analyst | yes, plan has Analyst |
| Delivery | Export style | `style` | yes, plan has Analyst | yes, plan has Analyst |
| Commercial | Billing | `billing` | yes | yes |
| Commercial | Pilot checklist | `pilot` | yes, while the org is a pilot | yes, while the org is a pilot |
| Activity | Audit | `audit` | yes | yes |

Delivery items are omitted when the plan does not include `analyst_agent`. The rest of the Organisation menu still shows. Pilot checklist is omitted when the org is not on the Pilot plan.

### 6.5 Platform menu

Items follow the permission already enforced in `admin_portal.py`. `GET /api/admin/portal/me` remains the list the bar renders. The groups below are presentation over that list.

| Group | Item | Section | Permission |
|---|---|---|---|
| Work | Board | `overview` | any platform role |
| Work | Feedback | `feedback` | `feedback.read` |
| Work | Pilot requests | `pilot-requests` | `pilot.manage` |
| Tenants | Organisations | `orgs` | `orgs.read` |
| Tenants | Users | `users` | `users.read` |
| Index | Labeling queue | `labeling` | `audit.read` |
| Index | Commitments | `commitments` | `audit.read` |
| Index | Index health | `reports` + `report=index` | `audit.read` |
| Index | Coverage | `reports` + `report=coverage` | `audit.read` |
| Index | Filing to score | `reports` + `report=sla` | `audit.read` |
| Commercial | Invoices | `billing` | `billing.read` |
| Commercial | Seat and agent use | `reports` + `report=usage` | `billing.read` |
| Trust | Legal | `legal` | `legal.read` |
| Trust | Trust snapshot | `reports` + `report=trust` | `legal.read` |
| Trust | Audit counters | `audit` | `audit.read` |
| Trust | Auth events | `reports` + `report=audit-events` | `audit.read` |
| System | Jobs and cleanup | `system` | `system.ops` |

Permission by role (unchanged):

| | Orgs | Users | Feedback | Legal | Billing | Pilot | Audit | System |
|---|---|---|---|---|---|---|---|---|
| `super` | read/write | read/write | read/write | read/write | read/write | manage | read | ops |
| `ops` | read/write | read | read/write | — | — | manage | read | — |
| `compliance` | read | — | — | read/write | — | — | read | — |
| `billing` | read | — | — | — | read/write | — | read | — |
| `support` | read | read | read/write | — | — | — | read | — |

Only `super` has `users.write` (assign platform role, delete a login). Only `super` has `system.ops`.

---

## 7. Organisation screens

Each screen is one section of `/org/settings`. Copy is for a desk lead: plan name, seats, and dates. No internal ids in labels. Org id may appear once, in small type, on Summary.

### 7.1 Summary

**Job.** See whose desk this is and whether a seat is free.

**Shows.** Organisation name, plan, seats used and seats purchased, the caller’s role, and the account type. Links into Members, API keys, and Billing.

**Data.** `GET /api/orgs/me`. Already on the page; the menu makes it the first item.

**Empty.** A guest or a retail account never reaches this bar. A signed-in user with no `org_id` who pastes the URL sees the existing explanation and a link to Account. They do not see member controls.

### 7.2 Members

**Job.** See who holds a seat, change a working role, and free a seat.

**Shows.** Name or email, role, active or revoked, verified or not. Seats used update after each change.

**Actions.**

| Action | Owner | Admin | Rule |
|---|---|---|---|
| Change role among viewer, analyst, labeler, reviewer | yes | yes | `POST /api/orgs/{id}/members/{user_id}/role` |
| Appoint or remove `admin` | yes | no | The select does not list `admin` for an admin caller |
| Revoke | yes, except owner and standing accounts | yes, except owner, admin, and standing accounts | `POST /api/orgs/{id}/revoke`. Revoke frees the seat. |
| Assign `owner` | no | no | Not in the select |

**Errors.** No seats left on invite (handled on Invites). Protected account returns the existing 400, shown as “This account is kept for the CiteAlpha team.” Another org’s user id returns 403.

### 7.3 Invites

**Job.** Give a colleague a seat.

**Actions.** Email plus role, then Send. Roles offered match Members: owner may invite `admin`; admin may invite the four working roles. Seat is consumed when the invite is accepted, not when it is sent. The screen states seats available before send.

**Mail.** Use the existing invite mail. In local development the screen may show the dev link. In production it shows only that the message was queued or that mail failed.

**Outstanding invites.** The current store issues a one-time token and does not keep a list safe to display. This screen does not list raw tokens. The caller can send again to the same address. A later list is in scope only if it shows email, role, and expiry, and never the token.

**Design partners** are the next item, not a role in this select.

### 7.4 Design partners

**Job.** Invite a design partner as viewer with feedback, 60-day token.

**Actions.** Email plus Invite. Same route as today: `POST /api/orgs/{id}/partner-invite`. Available to owner and admin.

### 7.5 Sign-in

**Job.** Record how this organisation signs in with its identity provider, and see whether production SSO is ready.

**Form.** Issuer, client id, email domain. Save calls `PUT /api/orgs/{id}/oidc`. Owner and admin. The client secret is not collected here; production OIDC remains the ops follow-up already documented. The form stores only the three fields the route accepts.

**Status.** The existing SSO readiness panel (enabled, configured, production-ready, checklist) stays on this item. IdP redirect stays `https://citealpha.com/api/auth/sso/callback`, with a link to Trust.

**Empty.** Fields blank means password sign-in only. Say that in one sentence.

### 7.6 API keys

Two blocks on one screen. Each names what the key is for.

**Analyst keys.** List, create, revoke via `/api/analyst/keys`. Label, role (`analyst` or `viewer`), created time, and a revoked state. The secret is shown once. Stored value is a hash. Cap is the existing per-org limit. Owner and admin. Reuse `AnalystSettings` key UI; do not build a second client.

**Desk key.** Mint via `POST /api/orgs/{id}/api-keys` (`orgs.mint_api_key`). Shown once. This is the organisation `X-API-Key` for desk write paths. The screen says it is not the Analyst key.

If the plan lacks `analyst_agent`, the Analyst block is omitted and the desk key remains.

### 7.7 Destinations

**Job.** Where Analyst deliveries go: feed, email, Slack, Teams, webhook. Events and a test send.

**Actions.** The existing destination list, add, delete, and test (`/api/analyst/destinations`). Owner and admin. Reuse the Analyst settings panel.

**Omitted when** the plan has no `analyst_agent`. A pasted URL shows the plan-access explanation, not an empty form that 403s on submit.

### 7.8 Export style

**Job.** House colours, font, logo, and PowerPoint template for exports.

**Rules.** The disclaimer, data date, source footers, and Evidence Receipt stay. The screen says so. Reset and clear-asset stay as they are. Owner and admin. Same plan gate as Destinations.

### 7.9 Billing

**Job.** See this organisation’s invoices and, when an invoice is waiting, record the signature.

**Shows.** Invoices for `user.org_id` only. Another desk’s invoice id returns 404, as today. Link text can still open `/billing` if that page remains the form; the menu item is the way the admin finds it. Do not list other organisations’ invoices.

**Not on this screen.** Creating an MSA invoice. That is platform Commercial.

### 7.10 Pilot checklist

**Job.** Mark the onboarding steps for this pilot.

**Shows.** `GET /api/orgs/{id}/pilot-checklist`. Check and notes call `PATCH`. Owner and admin. Hidden once the plan is not Pilot.

### 7.11 Audit

**Job.** See recent auth and admin actions on this desk.

**Shows.** `GET /api/audit` for this `org_id` only. Newest first. The same columns the platform auth-events report uses, limited to this org: time, actor, action. No passwords, tokens, or key secrets. `?org=` naming another desk stays rejected.

---

## 8. Platform screens

These sections already exist on `/admin`. The menu groups them. Behaviour below is the requirement the grouped menu must keep. Detail and request bodies stay in `docs/ADMIN_PORTAL.md`.

### 8.1 Board

Counts of work the caller can open, each linking to its item: pilot requests waiting, feedback still open, extracts waiting, labeling items, unreviewed commitments, source-check failures, coverage roll (System permission only). A support user does not receive the coverage row.

### 8.2 Feedback

Cross-tenant partner feedback. Filter by open. Acknowledge and close. Status `open` | `ack` | `closed`. Does not change a GCI.

### 8.3 Pilot requests

Approve for 30, 45, or 60 days, reject, or delete the request row. Approve opens the desk and emails `owner_email` an invite as organisation `admin`. Resend lives on Organisations.

### 8.4 Organisations

Every desk: plan, seats, account type, members, whether the recorded owner has taken a seat. Provision a pilot. Resend the owner invite. Delete an empty organisation. Standing desks (`demo`, `retail`, `onestop-demo`, `citealpha-team`, and any org marked protected) stay. A desk that still has a seat holder returns 409. `ops` can write; `compliance`, `billing`, and `support` are read-only, so write controls are absent for them.

### 8.5 Users

Logins without password fields. Filter for standing accounts. `super` assigns `super` | `ops` | `compliance` | `billing` | `support` or clears the platform role, and can delete a login that is not standing and not themselves. Other roles with `users.read` see the table without those controls. The assign control warns that platform roles are for Ocotillo operators.

### 8.6 Labeling queue and Commitments

Cross-tenant rows: company, kind, organisation, age. No Accept. The row tells the operator to open the Workbench or the analyst review path. Reads stored queues. Does not recompute a score.

### 8.7 Reports

One report per menu item. Each table shows the as-of time of the file it read.

| Report | Contents | Must |
|---|---|---|
| Index health | Published company count, tier counts, rows held as `pending_guidance_cite` | Read `gci_score_cache`. Do not recalculate. Do not rank a company below `established`. |
| Coverage | India and US counts by coverage status | Read `coverage_status.json`. Do not call NSE, BSE, or EDGAR. |
| Filing to score | Median from the score pipeline | When the file is empty, say that no filings are in the window. |
| Seat and agent use | Per org: plan, seats used, monitor count, skill runs in 7 days | Omit another org’s uploads and memory. |
| Trust snapshot | Counsel and SSO fields already on the trust payload | This report is the only place those fields render. They stay off public pages and public APIs. |
| Auth events | Newest 200 across orgs, plus CSV of that page | Omit passwords, tokens, and API key secrets. |

### 8.8 Invoices

All MSA invoices. `billing.write` can create an invoice for an existing org: plan, seats, optional amount, PO number, signer email. Signature recording uses the existing sign path when the signer email is supplied. No retail checkout on this screen.

### 8.9 Legal

Counsel snapshot. Record `terms_privacy` or `sebi_retail` with the counsel email and an optional note. This is the operator path. The legacy `POST /api/legal/attest` with the admin API key stays.

### 8.10 Audit counters

The eight counters (orgs, users, open feedback, reviews, pending extracts, and the rest of the current payload). The event list is Auth events, not this item.

### 8.11 System

`super` only.

- Guidance review: last market and last completed date. Read only.
- Monitors: organisations with a monitor, last trigger. Read only.
- Coverage roll status. Read only.
- Flags in plain labels: India coverage roll, guidance review, analyst monitors, event filings, Sights grid, Sights deep dive. Read only.
- Test-tenant cleanup: dry-run first, show who would be removed, second confirm to apply. Approved pilot orgs and CiteAlpha accounts stay. `e2e-*` and `@ocotillo.test` are the cleanup set.

Demo reset is not on this screen.

---

## 9. Denial, dual role, and direct links

| Case | Result |
|---|---|
| No session, or session without org admin and without platform role, opens `/admin` | Denial. Link to the product home. No portal payload. |
| Org analyst opens `/org/settings` | Summary may describe the org as read-only, matching today. No invite, revoke, key, or sign-in form. The admin bar is absent, so they arrived by URL or an old link. |
| Org admin opens `/admin` | Denial. Their Organisation menu is unaffected. |
| Platform `ops` opens `?section=system` or `?section=billing` | Denial for that section. Board still loads. |
| Platform `billing` calls a feedback route | 403. The menu never offered Feedback. |
| Dual-role user | Organisation actions send the session and touch one org. Platform actions use the platform role and can cross orgs. The chips make the layer obvious. |
| API key with `platform_admin_role` | Same platform menu as a session with that role, when the key is how the console is opened. Org seat admin still requires a user session. |

---

## 10. Compliance and index integrity

- No Buy, Hold, or Sell, and no recommendation language, on any admin screen.
- Partner feedback, legal attest, invoices, and cleanup do not write a score.
- Index health is a count of the published file. A tier below `established` is not a rank.
- Trust and counsel status render only on the platform Trust item.
- Export style cannot remove the disclaimer, the data date, or the source line.
- Customer strings on the Organisation menu avoid internal names: no env flags, no `intellens`, no “CSM”, no “AlphaHunter”, no “One-Stop” as a product label (One-Stop may appear only as the plan name already stored on the org). Prefer “Usage” and “Delivery” if a workbench metric is linked.
- The public nav and this bar do not mention a Trust Score.

---

## 11. Stories

### US-ADM-01 — Admin bar follows the person

**As a** signed-in user  
**I want** administration in a bar that appears only when I am an admin  
**So that** analysts never see operator controls, and I do not hunt through the account menu.

**Acceptance**

- Given I am a guest, a retail user, or a seat of viewer, analyst, labeler, or reviewer  
- When any page loads  
- Then the admin bar is absent, and `/admin` shows a denial  

- Given I am an organisation owner  
- When any page loads  
- Then the bar shows Organisation and the groups in §6.4, and it does not show Platform  

- Given I am platform ops  
- When any page loads  
- Then the bar shows Platform items for `orgs.read`, `orgs.write`, `users.read`, `feedback.*`, `pilot.manage`, and `audit.read`, and it does not show System, Legal, Invoices, or Trust snapshot  

### US-ADM-02 — Owner and admin are not the same seat

**As an** organisation admin  
**I want** to invite analysts and free their seats  
**So that** the desk stays full, while only the owner can appoint another admin.

**Acceptance**

- Given I am the owner  
- When I open Members  
- Then I can set a working seat to admin, and I cannot set anyone to owner  

- Given I am an admin  
- When I open Members  
- Then the role control lists viewer, analyst, labeler, and reviewer, and an admin row has no role control and no revoke  

- Given the member is a standing team account  
- When I revoke or change the role  
- Then the request is refused and the seat stays  

### US-ADM-03 — Keys and delivery stay on their owners

**As an** organisation owner  
**I want** Analyst keys, the desk key, destinations, and export style under Access and Delivery  
**So that** I manage credentials in one menu.

**Acceptance**

- Given the plan includes Analyst  
- When I open API keys  
- Then I see Analyst keys from `/api/analyst/keys` and a separate desk-key mint, and a new secret is shown once  

- Given I revoke an Analyst key  
- Then that key no longer authenticates, and keys of another org are unchanged  

- Given the plan does not include Analyst  
- Then Destinations and Export style are absent from the menu  

### US-ADM-04 — Sign-in fields that already have an API

**As an** organisation admin  
**I want** to save our issuer, client id, and email domain  
**So that** SSO setup is not a support ticket for those three fields.

**Acceptance**

- Given I am owner or admin  
- When I save Sign-in  
- Then `PUT /api/orgs/{id}/oidc` stores those fields on this org only  

- Given I am an analyst  
- When I call that route  
- Then the response is 403  

### US-ADM-05 — This desk’s billing and audit

**As an** organisation owner  
**I want** our invoices and our auth events  
**So that** I can answer procurement without seeing another firm.

**Acceptance**

- Given I open Billing  
- Then I see invoices for my `org_id` only  

- Given I open Audit  
- Then the rows are `GET /api/audit` for my org, with no secrets  

- Given I pass another org id  
- Then the response is 403 or 404, and the screen has no row from that org  

### US-ADM-06 — Super sees the full platform menu

**As a** platform super  
**I want** every platform group in §6.5  
**So that** board, tenants, index queues, invoices, legal, and system are one bar.

**Acceptance**

- Given I am super  
- When I open the Platform menu  
- Then each item in §6.5 is present and opens the existing section  

- Given I open Labeling or Commitments  
- Then I see rows and no control that accepts a label, a commitment, or a score  

- Given I open System  
- Then cleanup shows a dry-run before delete, and demo reset is absent  

### US-ADM-07 — A narrower operator sees less

**As** platform billing  
**I want** invoices and the usage report  
**So that** I can issue an MSA without access to feedback or system cleanup.

**Acceptance**

- Given my platform role is billing  
- When the bar renders  
- Then I see Organisations (read), Invoices, Seat and agent use, Audit counters, and Board rows my permissions allow  

- Given I request feedback, user role change, or cleanup  
- Then the response is 403  

### US-ADM-08 — Both hats, unmerged

**As a** user who is organisation owner and platform ops  
**I want** both menus  
**So that** I can invite my own desk and approve a pilot without one role granting the other.

**Acceptance**

- Given I hold both  
- Then the bar shows Organisation and Platform, with both chips  

- Given I am on Organisation Members  
- Then I cannot list another org’s members  

- Given I am on Platform Organisations  
- Then I can  

---

## 12. Delivery

### Phase A — Bar over what already renders

- Add the admin bar component to the shell. Drive platform items from `portal.sections` plus the report ids. Drive organisation items from role, plan, and `analyst_agent`.
- Point each item at the existing section or page. Re-home the Analyst key, destination, and house-style panels into Access and Delivery by reusing the components.
- Keep account-menu links.
- Tests: bar absent for an analyst; present for owner; ops menu has no System; direct `?section=system` as ops is a denial.

### Phase B — Organisation gaps that already have routes

- Sign-in form on `PUT /api/orgs/{id}/oidc`.
- Pilot checklist on the existing get/patch.
- Audit list on `GET /api/audit` scoped to the session org.
- Billing item shows this org’s invoices.
- Tests: admin cannot appoint admin; oidc rejected for analyst; audit ignores `?org=` for another desk.

### Phase C — Not in A or B

- A safe outstanding-invite list (email, role, expiry, no token), only if the token store can answer without revealing secrets.
- Anything in §5.

No phase adds a scheduler, a document fetcher, a score write, or a new key store.

---

## 13. Test plan

| Check | Where |
|---|---|
| Platform role matrix, 403 for a missing permission, 403 for no platform role | `backend/tests/test_admin_portal.py` |
| Owner vs admin seat changes, standing-account refusal | Existing org auth tests; extend for the menu’s role list |
| Analyst key revoke isolation | Connector / org key tests |
| Bar visibility and section denial | Playwright on `/`, `/org/settings`, `/admin` for analyst, owner, ops, and super |
| Public copy | Organisation menu strings go through `test_public_copy_hygiene.py` banned terms |
| Index | No new route in this PRD writes `hand_labeled` rows or the score ledger |

---

## 14. Files to extend

| Concern | Owner |
|---|---|
| Platform permissions and section list | `backend/app/services/admin_portal.py` |
| Seats, invites, desk key, OIDC | `backend/app/services/orgs.py`, `session_auth.py` |
| Analyst keys, destinations, house style | `backend/app/services/agent/org_keys.py`, `delivery`, house style; routes in `connector_routes.py` |
| Platform UI | `frontend/src/pages/AdminPortalPage.tsx` |
| Organisation UI | `frontend/src/pages/OrgSettingsPage.tsx`, `frontend/src/components/OrgAdminPanel.tsx` |
| Analyst panels to reuse | `frontend/src/pages/analyst/AnalystSettings.tsx` |
| Bar | New presentational component next to `NavMenu.tsx`, rendered from the shell only. Menu data comes from the APIs above. |
| Client | `frontend/src/lib/api.ts` |
| Operator runbook | `docs/ADMIN_PORTAL.md` when behaviour changes |
| Agent memory | `docs/kb/15-admin-portal.md` |

---

## 15. Success

- An analyst never sees the admin bar. An owner sees Organisation on every page. A super sees Platform. A dual-role user sees both.
- Every item in §6.4 and §6.5 opens a working screen, or is omitted when the permission or plan says so.
- Owner and admin differ only where §7.2 says so.
- No published GCI moves because someone used this menu.
- `docs/ADMIN_PORTAL.md` remains the operator runbook. This PRD remains the menu and role contract.
