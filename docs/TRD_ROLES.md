# TRD — Implementing the four seats and the accept split

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited
**Status:** final for the next development cycle · **Date:** 28 Oct 2026
**Specifies:** [BRD_ROLES.md](BRD_ROLES.md) · [PRD_ROLES.md](PRD_ROLES.md)
**Also implements:** the 25 Oct 2026 terminal pass (PRD section 7) and the 28 Oct 2026 public-page corrections (PRD section 4). Source files `docs/prd/PRD_TERMINAL.md` and `docs/PLAN_ROLE_UX.md` stay as the dated record. This TRD is the build document.
**Execute with:** `citealpha-production` for seats · `citealpha-expert-ux` for the public pages and the terminal pass · `index-integrity` before any accept-path change ships

Extend `entitlements.py` and `session_auth.py`. Do not add a second authorisation service, a new admin app, or a new export pipeline. Plan ∩ role stays the rule. No published GCI moves in steps 1–4 or 6–8. Step 5 only changes who may call the existing review route.

---

## 1. Build order

Ship in this order. Each step is releasable on its own, except step 6 and step 9 when they edit `EvidenceTable.tsx` or `HomePage.tsx`: those two edits land together, so a reader never sees a year view sitting on a misleading change.

| Step | Ships | Risk if skipped |
|---|---|---|
| 1 | Feature sets for `pm`, `data`, `oversight`, `ir` | Later UI would show buttons the server rejects, or the reverse |
| 2 | Invite allow-list and plain-language menu | Owners cannot appoint the seats |
| 3 | IR company allow-list on the user row | An IR seat could pack any company |
| 4 | `org_audit` on the audit route; analyst removed from it | Oversight has no trail, or every analyst still sees it |
| 5 | Accept restricted to reviewer, admin, owner | The new seats are pointless if analyst can still publish |
| 6 | Public-page truth (PRD section 4) | Seats land on pages that still misread |
| 7 | First-screen landings and Analyst grouping | Seats can do the job but open on the wrong room |
| 8 | Holdings “since last visit”, developers field table, board-pack link | The landing exists and the job is still a click away |
| 9 | Terminal pass (PRD section 7): year view, docked source, compact density, pills on the URL, palette, short frame | The analyst still cannot read one metric across years or keep the filing beside the table |

## 2. Step 1 — Entitlements

**File:** `backend/app/services/entitlements.py`, `ROLE_FEATURES`.

Add four keys. Do not give them `desk_write`, `labeling`, or `analyst_agent`.

```text
pm:         tracker, research, read_api, feedback, holdings, alerts
data:       tracker, research, read_api, feedback, em_export
oversight:  tracker, research, read_api, feedback, org_audit
ir:         tracker, research, read_api, feedback, pack_export
```

`org_audit` and `pack_export` are new feature names. They are not added to `PLAN_FEATURES`. They are role features, so a plan that already includes `tracker` does not need a new plan row. `holdings`, `alerts`, and `em_export` already exist on the Desk, Enterprise, and One-Stop plans. Intersection means:

- `pm` on Pilot has no holdings, because Pilot’s feature set has none.
- `data` on Pilot has no `em_export`.
- `ir` pack export does not require `em_export`.

`admin` and `owner` already receive `orgs.ALL_FEATURES`. Add `org_audit` and `pack_export` to that union by including them in `ALL_FEATURES` only if a plan does not already carry them. Cleaner: `_role_features` for admin/owner returns `orgs.ALL_FEATURES | {"org_audit", "pack_export"}`. Do not put those two names on the Pilot plan, or every admin on Pilot would be fine (they should have them) and a viewer would not (correct).

**Tests:** `backend/tests/test_entitlements_access.py`

- `pm` ∩ desk includes `holdings` and excludes `desk_write`.
- `data` ∩ enterprise includes `em_export` and excludes `desk_write`.
- `data` ∩ pilot excludes `em_export`.
- `oversight` includes `org_audit` and excludes `desk_write`.
- `ir` includes `pack_export` and excludes `desk_write`.
- Unknown role still falls through to viewer.

## 3. Step 2 — Appointing the seat

**Files:** `backend/app/services/session_auth.py` (`_DESK_ASSIGNABLE`, `seat_role_for_actor`, the known-role set near line 42), `frontend/src/components/OrgAdminPanel.tsx`.

Add `pm`, `data`, `oversight`, `ir` to `_DESK_ASSIGNABLE` and to the role set the session layer already recognises. Keep the rule that only an owner may appoint `admin`. Nobody appoints `owner` from this menu.

`member` and `partner` keep mapping to `viewer`.

The invite `<select>` currently prints the raw id. Map id → label in the component:

| id | label |
|---|---|
| viewer | Viewer |
| pm | Portfolio |
| data | Data |
| ir | Investor relations |
| oversight | Oversight |
| analyst | Analyst |
| labeler | Labeler |
| reviewer | Reviewer |
| admin | Admin |

Show the one-sentence description from PRD section 1 under the select. Strings live in `en.json`.

**Tests:** extend the seat-role tests that cover `seat_role_for_actor`. An admin appointing `pm` succeeds. An admin appointing `admin` is 403. An unknown id is 400.

## 4. Step 3 — IR allow-list

**Store:** a `company_scope` list on the user row the auth store already writes (`auth_db` / Postgres user columns). Empty list is the default. Do not add a new table for a single list of company ids.

**API:** the existing member-update route used by organisation settings gains an optional `company_scope` field, accepted only when the target role is `ir`, and only from an owner or admin of that org. Ids that are not companies return 400. A scope on any other role is stored as empty and ignored.

**Enforcement:** the board-pack export (the existing `board_scorecard` export in `services/agent/exports.py`, called from the dossier link) checks `pack_export` and, for role `ir`, `company_id in company_scope`. Owner, admin, analyst, and reviewer keep today’s export right without a list. IR outside the list is 403 with `detail` the sentence in PRD section 5.

**UI:** `OrgMembersPanel` shows the company search only on an `ir` row.

**Tests:** scope save, empty scope export 403, in-scope 200, other-role scope ignored.

## 5. Step 4 — Audit feature

**File:** `backend/app/api/routes.py`, `GET /api/audit`.

Replace the role tuple `owner, admin, reviewer, analyst` with `require_feature("org_audit")` plus the existing org match. Grant `org_audit` to `oversight`, `reviewer`, `admin`, and `owner` in `ROLE_FEATURES` (reviewer already listed; add the feature to that set). Remove it from `analyst`.

Org settings audit section (`OrgSettingsPage.tsx`, `section=audit`) renders for anyone with `org_audit`. Invites, billing, destinations, and style stay behind owner/admin as they are now. Oversight opening those sections gets the existing denial.

**Tests:** analyst `GET /api/audit` is 403. Oversight of the same org is 200. Oversight of another org is 403.

## 6. Step 5 — Who may accept

**File:** `backend/app/api/routes.py`, `POST /api/review`.

Today the route is `require_feature("desk_write")`, which `analyst` holds, and the reviewer recorded is `auth.get("org")` (the org id, not the person).

Change:

- `action=accept` requires role in `reviewer`, `admin`, `owner`. Anyone else, including `analyst` with `desk_write`, gets 403 and the repository is not called.
- `edit` and `reject` on a row that is already in the published set use the same role check. An analyst may still run extract into the pending queue (`desk_write` on the extract routes). They may not move a pending row to accepted.
- The reviewer string stored on the row is the actor’s user id or email, not the org id. The audit event uses the same actor.

This is the change `index-steward` reviews. It does not by itself recompute a GCI. The next real accept still follows the score-ledger and changelog protocol if a number moves.

**Tests:** analyst accept 403 and the stored score unchanged. Reviewer accept 200 and the audit actor is that user. Labeler, pm, data, ir, oversight, viewer all 403.

## 7. Step 6 — Public pages

PRD section 4. No new routes. Where a row below names `HomePage.tsx` or `EvidenceTable.tsx`, ship it in the same change as step 9.

| Item | Owner | Done when |
|---|---|---|
| One published-count sentence on screener, snapshot, and reading room | `HomePage.tsx`, `RankingsPage.tsx`, `ResearchPage.tsx` | The three pages name the same count for “published GCI” |
| Guest screener opens on India; title follows the index; markets other than India leave the public control | `HomePage.tsx` | `/tracker` with a cleared preference is an India index |
| “Not scored” chip in the tier cell; score cell is one coverage sentence; sample data is called sample data | `HomePage.tsx`, `TierBadge.tsx`, `en.json` | No “Demo”, no pipeline stage in the score cell |
| Growth-rate change labeled as a change in the rate; guest page returns to six panels | `CompanyDetailPage.tsx` | Infosys does not show a −26.2% that reads as revenue |
| Promise-after-result flag | `EvidenceTable.tsx` | The FY25 operating-margin row is flagged; 76.5 unchanged |
| Snapshot heading matches the table; cite sentence includes the tier | `RankingsPage.tsx` | Provisional rows are called provisional in the heading and in the copied sentence |
| Drop the expert chip; reading-room list matches the published set or says why it does not | `ResearchPage.tsx` | The chip is gone |
| Explorer hub lede, “Open a surface”, and homepage cards | sights hub, `LandingPage.tsx`, `en.json` | Search, boards, and agents are not offered as Explorer rooms |

Sort is unchanged. Do not implement closed-results-then-GCI unless the owner confirms the proposal recorded in the BRD.

Copy hygiene: extend `backend/tests/test_public_copy_hygiene.py` if a banned string was the thing removed. Do not add a new banned-term test that forbids the word “reviewer”.

## 8. Step 7 — Landing and Analyst groups

**Landing.** After a session is established, if the location is `/` or the post-login default, send:

| role | path |
|---|---|
| pm | `/holdings` |
| data | `/developers` |
| ir | `/companies/{id}` when `company_scope` has one id; `/tracker?scope=ir` when it has several or none |
| oversight | `/org/settings?section=audit` |
| analyst | `/analyst` |
| reviewer | `/desk?tab=review` |
| labeler | `/desk?tab=labeling` |
| viewer, guest | `/tracker` |
| owner, admin | `/tracker` |

Implement the redirect in the existing auth landing (`frontend/src/lib/auth.tsx` or the post-login path in `App.tsx`). A bookmarked route is not overridden: the redirect runs only when they signed in from the login page or from `/`.

**Analyst groups.** `AnalystPage.tsx` groups the skills it already loads. Grouping is presentation. Skill ids and the runtime stay in `backend/app/skills/` and `services/agent/`.

| Group | Skill ids |
|---|---|
| This print | `results_prep`, `concall_questions`, `coverage_monitor` |
| Learn a name | `company_ramp`, `company_note` |
| Board, credit, and events | `board_scorecard`, `peer_delivery_grid`, `corporate_action_brief`, `drhp_reader`, `usfda_watch`, `rating_tracker`, `debate_map`, plus the project-only skills behind the existing project gate |

A skill id the page does not recognise falls into the third group, so a new skill file does not disappear.

## 9. Step 8 — The job on the landing

**Holdings.** `HoldingsPage.tsx` and `services/holdings.py`. “Since you last opened this” reads the document store and published outcomes for identifiers in the saved file. It writes nothing to the score. Persist the last-open timestamp on the org holdings record that already exists.

**Developers.** `DevelopersPage.tsx`. The field table is static copy plus one sample row drawn from the existing published export, not a new schema service. The download button calls the export route that already checks `em_export`.

**Board pack.** `CompanyDetailPage.tsx` shows the text link when the seat has `pack_export` or `ic_export` and, for `ir`, the company is in scope. The link calls the existing export. It does not add a pack builder.

## 10. Step 9 — Terminal pass

PRD section 7. Extend the owners below. Do not add a component, a context, a route, or an endpoint that the list forbids.

**Year view.** `EvidenceTable.tsx` and `CompanyDetailPage.tsx`. A toggle on the evidence panel: “By year” first, “By row” one control away. Group `outcomes` already on `GET /api/companies/{id}/gci` by `metricDisplayName()`. Columns are periods on that company, newest first. Cell text is guided band, reported figure, outcome word. Pending stays pending. A missing year is an em dash. The track column is closed-year outcome words, oldest to newest. No new `/api/v1/companies/{ticker}/guidance-history`.

**Dock.** `SourceViewer.tsx` and `SourceViewerContext.tsx`. The existing `openSource()` becomes a dock beside the table, about 60/40, instead of a centered dialog. Promise links call it too. Highlight uses `span_start` / `span_end`. Escape closes. “Open original” and the `/c/{citationId}` copy stay. Callers on Filing Search, the revision trail, and Disclosure Explorer are not given a second viewer. No page rectangle. No fetch of NSE, BSE, EDGAR, or the issuer.

**Density.** `HomePage.tsx`, `CompanyDetailPage.tsx`, `styles.css`, and the existing account `density` preference. Compact is the default. Comfortable applies when the account says so. Numbers: IBM Plex Sans, `tabular-nums`, right-aligned. Tickers and fiscal periods: IBM Plex Mono. Do not add JetBrains Mono or Roboto Mono. Target: at least 25 screener rows on 1920×1080 without scrolling the window.

**Pills.** `HomePage.tsx`. Replace the checkbox with two pills, “Scored only (n)” and “All (n)”, counts from the loaded list. Persist `scored=1` or `scored=0` on the URL. Default is scored only on every India index, including NSE All and BSE All. The unused `screener.filter.all` string in `en.json` is the one to use. The long unscored essay leaves once the pills state the count. The disclaimer line stays.

**Chip.** `TierBadge.tsx`. “Not scored” where the tier cell is empty. Existing tier colours. No emoji. Deep stays.

**Palette and frame.** `NavMenu.tsx` and `App.tsx`. Cmd+K / Ctrl+K, and `/` when focus is outside a field. Company hits go through `GET /api/companies/search` (`searchCompanies` in `api.ts`). Tool hits are the nav routes that already exist. Recent company ids live in `localStorage` and are not a watchlist. Marketing routes keep the current header. Working routes (`/tracker`, `/companies`, `/research`, `/analyst`, `/rankings`, `/desk`, `/sights`, `/ninja`, `/holdings`) render the short frame: mark, palette hint, account, and Sign in when signed out. No `/console` routes. No second host.

**Tests.** Dossier evidence (year row, pending cell, track), screener URL round-trip, source viewer dock and Escape, palette search, public-copy check. `tests/test_score_consistency.py` still runs and is expected to stay green, because this step does not touch the scorer.

**Do not add:** `GuidancePivotMatrix`, a second citation context, a second palette library if a short list will do, `/console` routes, or a guidance-history endpoint.

## 11. Data and migration

- Existing users keep their role. No mass rewrite.
- `member` rows stay valid and keep resolving as viewer.
- `company_scope` defaults to `[]`.
- No score ledger row is written by the migration.
- Sessions issued before the deploy keep working. The next entitlements read picks up the new feature set.

## 12. Tests to run before merge

- `pytest backend/tests/test_entitlements_access.py backend/tests/test_production_auth.py` and the seat-role tests touched in step 2.
- A new test module `backend/tests/test_role_seats.py` for the accept 403 matrix and the IR scope 403.
- `backend/tests/test_public_copy_hygiene.py` after step 6.
- Frontend tests already on the dossier evidence table, the screener filter, and the source viewer, updated for the year toggle, the `scored` query, and the dock. `tests/test_score_consistency.py` still runs after step 9.
- `cd frontend && npm run build`.
- Playwright, if a spec already covers the invite select or the screener: update the option labels and the India default. Do not add a new suite for its own sake.

## 13. Rollback

Feature sets and the accept check are the only server behavior changes that can lock someone out.

- Rollback of step 5 restores analyst accept. Do that only with the index steward, and write a changelog entry if any accept happened under the new rule and is being reversed.
- Rollback of steps 1–4 returns unknown roles to the viewer feature set (`_role_features` falls back to viewer). Anyone already stored as `pm` would suddenly look like a viewer until the code returns. Prefer a forward fix.
- Steps 6, 8, and 9 are presentation. Revert the commit. Step 6 and step 9 revert together when they share a file.

## 14. Explicit non-work

- No new FastAPI router package.
- No change to `gci_scoring.py`, tier thresholds, or the score cache in this TRD.
- No platform-role edit in `admin_portal.py` beyond leaving those roles without the new product features.
- No `app.` host, no `/console` prefix, no guidance-history endpoint, and no second source viewer. The short frame in step 9 is the working header.
