# PRD — Plans and evaluation

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited  
**Status:** Implemented · **Date:** 2026-10-25  
**Routes:** `/products`, `/pilot` · `/package` redirects to `/products#plans`  
**Owners:** `ProductsPage.tsx`, `PilotRequestPage.tsx`, `entitlements.py`, `orgs.py`  
**Related:** [PRD_FILING_SEARCH.md](PRD_FILING_SEARCH.md) · [PRD_ADMIN.md](../PRD_ADMIN.md)

---

## Prime requirement — a buyer who can see the boundary before they write

A Head of Research opening Plans is deciding whether to ask for an evaluation. They need to see, without a call, what they can already read and what stays on a seat. They also need to leave without thinking they have been shown a rate card that the order form will contradict. The rupee amount lives on the order form. This page says that, once, and then talks about the work.

### What they can do this afternoon

The evaluation block comes before the plan grid, at `#plans`. It says four things in sentences, not in a feature grid of internal names:

- Dossiers and the Public Snapshot are open, with the guided band and the reported figure on one row.
- Filing Search before an evaluation is eight searches, on companies that already have a published GCI, and this browser keeps the count.
- Cite-only chat, the workbench, monitors, private notes, and the API open with a seat.
- A Coverage Monitor on that seat quotes a new filing. It does not change the score. Payment does not change a score or the date the score moves.

“Request an evaluation” goes to the form. Name, work email, firm. One button. A missing firm is marked and not submitted. After a successful send, the page says the request was received and that someone will reply. It does not say the desk is active, and it does not sign them in.

### The plans, as jobs

Pilot is a complimentary evaluation. The term, 30, 45, or 60 days, is set when the request is approved. Desk, Enterprise API, and One-Stop are the later plans, described by the jobs they open: the screener and the dossier, Filing Search, the workbench, CiteAlpha Analyst, holdings, the worksheet. Retail is not offered. The page does not show a card form.

The price line says the amount is on the order form, and that paying it does not move a GCI. When a pilot term ends, the page’s promise still holds: the screener remains, and the seat’s extra rooms close. The person’s role is unchanged. What changed is the term.

A viewer and an analyst on the same plan do not see different marketing. They discover the difference when they open a room: the viewer can search filings, the analyst can also ask a cited question and run a note. The plans page does not need to teach the whole ladder. The matrix later in this document is for the people who build and approve seats. The public page speaks in jobs.

On a phone the evaluation block is first, the plans stack, and the request button stays a button, not a footnote.

## 3. Users

| Persona | Job |
|---|---|
| Head of Research | Read the evaluation scope and send the request |
| Platform billing | Move a desk from pilot to Desk, Enterprise, or One-Stop. That is an admin action, not this page |
| Guest | Use the screener, dossiers within the cap, the snapshot, and the reading room |

## 3.1 Role requirements

The public page speaks in jobs, as the walkthrough says. The matrix below is for whoever approves a seat, so the jobs on the page and the doors in the product stay the same list.

The plans page states the seat ladder. It does not assign a seat. Assignment stays on the organisation menu in [`docs/PRD_ADMIN.md`](../PRD_ADMIN.md): the owner appoints and removes `admin`; an admin changes `viewer`, `analyst`, `labeler`, and `reviewer`; nobody assigns `owner` from that menu. Register creates the owner. A pilot approval invites the recorded address as `admin`.

Effective access is plan ∩ role. The page’s evaluation copy must match this matrix. A feature marked “—” is absent for that role even when the plan includes it.

| Feature | Guest | viewer, member | labeler | analyst | reviewer | admin, owner | Plans that include it |
|---|---|---|---|---|---|---|---|
| `tracker` — screener, dossier read, snapshot | Yes. 15 dossier opens | Yes | Yes | Yes | Yes | Yes | Every plan, including an ended pilot |
| Reading room — eight searches on a published GCI | Yes. This is a limit, not a feature flag | — (they have full search) | — | — | — | — | Callers without `research` |
| `research` — full Filing Search | — | Yes | Yes | Yes | Yes | Yes | Pilot, Desk, Enterprise, One-Stop, and retail if present |
| `research_chat`, `sights_ask` | — | — | — | Yes | Yes | Yes | Pilot, Desk, Enterprise, One-Stop |
| `read_api` | — | Yes | Yes | Yes | Yes | Yes | Pilot and above, and retail if present |
| `feedback` | — | Yes | Yes | Yes | Yes | Yes | Pilot and above |
| `desk` — open the workbench and read the queue | — | — | Yes | Yes | Yes | Yes | Pilot and above |
| `desk_write` — accept a guidance row, ingest, import facts | — | — | — | Yes | Yes | Yes | Pilot and above |
| `analyst_agent` — skills, monitors, projects, uploads | — | — | — | Yes | Yes | Yes | Pilot and above |
| Analyst keys, destinations, house-style write | — | — | — | — | — | Yes, and the plan must include `analyst_agent` | Pilot and above |
| `labeling` | — | — | Yes | — | Yes | Yes | Desk, Enterprise, One-Stop. Pilot only when `labeling_granted` |
| Commitment accept and close | — | — | — | — | Yes, with `labeling` | Yes, with `labeling` | Same as `labeling`. The role must be reviewer, admin, or owner |
| `wordmap`, `analytics_experimental`, `ic_export` | — | — | — | Yes | Yes | Yes | Pilot and above for word map, experimental analytics, and IC export |
| `alerts`, `vernacular` | — | — | — | Yes | Yes | Yes | Desk, Enterprise, One-Stop |
| Facts import | — | — | — | Yes | Yes | Yes | The route requires `desk_write`, which Pilot and above give to analyst, reviewer, admin, and owner. The separate `import` flag is on Desk and above and is not that route’s gate |
| `holdings`, `ninja` | — | — | — | Yes | Yes | Yes | Open approved pilot, Desk, Enterprise, One-Stop. Removed together when the pilot term ends |
| `em_export`, `sso` | — | — | — | — | — | Yes | Enterprise and One-Stop |
| `badge` | — | — | — | Yes | Yes | Yes | Enterprise and One-Stop |
| `labeling_priority` | — | — | — | — | — | Yes | One-Stop |

An approved pilot whose term has ended keeps the role and drops to `tracker`. Chat, the workbench, Analyst, holdings, and the API close. The screener, the dossier cap’s public read, and the snapshot remain.

A platform `super` who belongs to an organisation also receives the Desk plan’s features on the server. That union does not include `em_export`, `sso`, or `badge` unless the organisation’s own plan already has them. A super with no organisation remains a guest on the server. Platform `ops`, `compliance`, `billing`, and `support` follow their seat. Moving a desk from Pilot to Desk, Enterprise, or One-Stop is a platform billing action, not a control on `/products`.

Retail stays closed until counsel attests. The retail feature set, if the plan is later opened, is `tracker`, `research`, and `read_api` only.

**CM-R1.** The evaluation block names only what a caller without `research` can do, plus what stays on a seat.  
**CM-R2.** Guest entitlements are `features: ["tracker"]`, dossier cap 15, chat limit 0, search limit 8.  
**CM-R3.** A viewer on a pilot has `research` and `read_api`, and does not have `research_chat`, `desk`, or `analyst_agent`.  
**CM-R4.** An analyst on Desk has holdings and the workbench write, and does not have `labeling` or `em_export`.  
**CM-R5.** A reviewer on Desk has `labeling`. A reviewer on a pilot has `labeling` only when `labeling_granted` is set.  
**CM-R6.** Paying an invoice does not add a feature by itself and does not change a published GCI.

## 4. Decisions

| # | Decision |
|---|---|
| D1 | Plans on the page are Pilot (complimentary, term set on approval), Desk, Enterprise API, and One-Stop. Retail checkout stays closed until counsel attests. |
| D2 | The evaluation block states four facts: dossiers and the snapshot with both figures on one row; eight filing searches on companies with a published GCI, counted in this browser; chat, the workbench, monitors, private notes, and the API stay on a seat; a Coverage Monitor on a seat quotes a new filing and does not change the score. |
| D3 | The price line says the rupee amount is on the order form, and that payment does not change a score or the date it updates. |
| D4 | Guest features stay `["tracker"]`. The reading-room allowance is a limit, not a new feature flag. |
| D5 | SKU names on the page are Score, Cite, Radar, Ledger, and Data, plus the seats that include Holdings and Financial Ninja. They are jobs on the same record, not separate scores. |
| D6 | Approving a pilot invites the recorded address. The public form does not create the organisation by itself. |

## 5. What this page is not

- A shopping cart or a card checkout.
- A credit meter the reader tops up.
- A promise of a public dollar or rupee price.
- The admin billing screen.

## 6. Behaviour

1. `#plans` shows the evaluation scope, then the plan grid.
2. Each plan lists the jobs it opens. It does not list a recommendation product.
3. “Request an evaluation” goes to `/pilot` or the homepage form. Required fields are name, work email, and firm.
4. After submit, the page confirms the request was received. It does not say the desk is active.
5. A seat’s entitlements come from `GET /api/entitlements/me`.
6. When a pilot term ends, the desk closes and the screener remains.

## 7. Stories

**CM-1.** Given a visitor opens `/products#plans`, when the page loads, then the evaluation block is visible and it names eight searches, the seat boundary, and the order-form price.

**CM-2.** Given a guest reads entitlements, when the payload returns, then features are only `tracker` and chat limit is 0.

**CM-3.** Given the form is missing a firm, when the visitor submits, then the request is not sent.

**CM-4.** Given a research seat, when Filing Search loads, then the reading-room cap is not applied.

**CM-5.** Given a viewer and an analyst on the same pilot, when each reads `/api/entitlements/me`, then the viewer’s features include `research` and exclude `research_chat`, `desk`, and `analyst_agent`, and the analyst’s features include those three.

**CM-6.** Given an approved pilot term has ended, when a reviewer reads entitlements, then the role is still reviewer and the features are `["tracker"]`.

## 8. Index integrity

Commercial state does not enter the scorer. The page says payment does not change a number. That sentence matches the product rule: a covered company cannot buy, edit, or delay its score.

## 9. Test plan

- `evaluation-scope` is present on the plans page.
- Guest entitlements test.
- Public-copy hygiene, including the ban on recommendation language.
- Pilot request rejects an incomplete body.

## 10. Files

`frontend/src/pages/ProductsPage.tsx` · `frontend/src/pages/PilotRequestPage.tsx` · `backend/app/services/entitlements.py` · `backend/app/services/orgs.py` · `docs/kb/13-commercial.md`
