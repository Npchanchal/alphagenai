# BRD — Seats for the desks that buy CiteAlpha

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited
**Status:** final for the next development cycle · **Date:** 28 Oct 2026
**Companions:** [PRD_ROLES.md](PRD_ROLES.md) (what the person sees) · [TRD_ROLES.md](TRD_ROLES.md) (how it is built)
**Carries, in full for this cycle:** the 25 Oct 2026 terminal decisions in [prd/PRD_TERMINAL.md](prd/PRD_TERMINAL.md) and the 28 Oct 2026 role walk in [PLAN_ROLE_UX.md](PLAN_ROLE_UX.md). Those files stay the dated sources. This BRD is the business document that can be read without them.
**Still describes what ships today, and is not rewritten here:** the per-surface PRDs in `docs/prd/` and [PRD_ADMIN.md](PRD_ADMIN.md).

---

## 1. Business question

CiteAlpha sells one product to several jobs: a head of research, a portfolio manager, an analyst, a reviewer, an investor-relations officer, a quant, a journalist, and the customer’s own compliance reader. Today those jobs share eight organisation seats (`guest`, `viewer` / `member`, `labeler`, `analyst`, `reviewer`, `admin`, `owner`) plus five platform operator roles.

The question for this cycle is whether any job needs its **own seat**, meaning a different set of permissions, or only a different first screen on a seat that already exists.

A seat is justified only when two people on the same plan must be denied each other’s actions. A job title that can share a permission set is a home view, not a new role. That split is the NIST role-engineering rule: permissions hang off roles, separation of duties is a constraint between roles, and extra roles that do not change a permission are an admin burden ([NIST RBAC](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=916402), [privilege versus complexity](https://doi.org/10.1145/3381991.3395597)).

## 2. Decision

**Yes. Four seats are added. Seven jobs stay on seats that already exist.**

| Job | Seat | Why |
|---|---|---|
| Portfolio manager | **New: `pm`** | Holdings today require the `analyst` seat, and `analyst` includes `desk_write`. A PM who can paste a book can also accept a figure onto the score path. |
| Quant / data buyer | **New: `data`** | Bulk file export (`em_export`) is on the Enterprise and One-Stop plans and is delivered only because `owner` and `admin` receive every plan feature. A quant should not have to be the organisation owner to take the file. |
| Customer oversight | **New: `oversight`** | The customer’s compliance reader needs the organisation’s own audit trail. Today that trail is open to every analyst (`GET /api/audit`), and the only people who can be denied write access are viewers, who cannot open the audit. Platform `compliance` is an Ocotillo operator and must stay that way. |
| Investor-relations officer | **New: `ir`** | An issuer must not be able to accept, edit, or reject a row that enters the published record. Giving them `analyst` would allow `POST /api/review`. The seat is useless without a company allow-list, so the allow-list ships with the seat. |
| Head of Research | `owner` or `admin` | They appoint seats and read coverage. A second admin seat would duplicate billing and invites. Coverage is a sentence on the screener, not a role. |
| Buy-side analyst, sell-side associate | `analyst` | Same permissions. The associate’s first screen is grouped skills. The analyst’s first screen is the dossier. |
| Reviewer | `reviewer` | Already the person who may accept. This cycle takes accept **off** the analyst seat so the split is real. |
| Labeler | `labeler` | Already read-only on the workbench, with the labeling queue. |
| Journalist, guest | `guest` | Public pages. No account required to quote a dossier. |
| Viewer | `viewer` | Unchanged. `member` remains an alias and stays off the invite menu. |

Platform roles (`super`, `ops`, `compliance`, `billing`, `support`) do not gain product features. An organisation `oversight` seat is not a platform `compliance` role, and neither one is a SEBI Research Analyst compliance officer.

## 3. Why the four seats pay for themselves

- **Least privilege on the score.** The published GCI moves only when a reviewer, an admin, or the owner accepts a row. A portfolio manager, a quant, an IR officer, and an oversight reader cannot call that route. That is the separation of duties the index needs: the person who uses the number is not the person who publishes it.
- **A pilot can be staffed honestly.** Today an owner who wants the PM to see the book must appoint them `analyst`. The invite list in `session_auth._DESK_ASSIGNABLE` is `viewer`, `analyst`, `labeler`, `reviewer`. After this cycle the owner can appoint the job the contract named.
- **IR is sellable only if it cannot touch the score.** About already says a covered company cannot buy, edit, or delay its score. The seat has to make that sentence true for a logged-in issuer.
- **Oversight is a read, not a licence.** SEBI’s Research Analyst regulations require a non-individual research entity to appoint a compliance officer ([regulation 26](https://www.sebi.gov.in/sebi_data/attachdocs/oct-2026/1792127227860.pdf), [FAQ 27](https://www.sebi.gov.in/sebi_data/faqfiles/jul-2025/1753269723942.pdf)). CiteAlpha is not that officer and this seat does not appoint one. It lets a customer who *is* a research entity give their own reader a trail of exports and accepts, with no path to the score.

## 4. What was rechecked

Signed-out production walk on 28 Oct 2026, then a code pass the same day.

| Check | Result |
|---|---|
| Homepage coverage | “2 of 30 Sensex companies scored”, “57 companies scored in total”, “10 companies have sample data”. Honest. |
| Screener | Document title says Sensex. This session’s first body was US · S&P 500, 503 unscored names. India Sensex then showed Axis Bank 90.7 (1 closed result) above Infosys 76.5 (5). Unscored cells use pipeline sentences. Quality filter still offers Demo. `scoredOnly` in `HomePage.tsx` still starts off. |
| Infosys dossier | Header sentence is right. Metric strip shows 3.1 and YoY −26.2% on a growth rate. Delivery chips include Unmapped 0 and Pending guidance cite 0. FY25 operating-margin promise date (28 Jul 2026) is after the result date (17 Apr 2025). |
| Public Snapshot | “n=0 citeable” and “provisional scores are excluded”, then six provisional rows. |
| Filing Search | Reading room is honest (eight searches). Company control listed Infosys and Cipla. A chip is named expert. |
| Disclosure Explorer | Lede still says search, boards, and agents. |
| API page | A list of `/api/v1` paths. No field dictionary, no sample file, no available-date. |
| Analyst gate | Names the jobs and does not show a skill list to a guest. |
| Who may accept a row | `POST /api/review` depends on `desk_write`. `analyst` has `desk_write`. The surface PRD says accepting a commitment is the reviewer. The route is wider than the PRD. |
| Who may export the file | `em_export` is on `enterprise` and `onestop` only. `analyst` is not in that feature. `owner` and `admin` receive every feature the plan has, so they are the only seats that can export. |
| Who may read the org audit | `GET /api/audit` allows `owner`, `admin`, `reviewer`, and `analyst`. |
| Invite menu | Raw role ids. `member` is mapped to `viewer` and is not assignable. An admin cannot appoint an admin. |

The terminal pass is not on the live page. It does not add a seat. Its confirmed choices, the alternatives that were declined, and how they sit next to the 28 Oct walk are in sections 8–11. They are part of this cycle.

## 5. Business rules

1. Effective access remains **plan ∩ role**. A new seat adds no feature the plan left out. A Pilot plan still has no holdings and no `em_export`. The `pm` and `data` seats exist so the appointment is right when the plan later includes those features. The page says the plan does not include the room yet.
2. One person, one organisation seat. Separation of duties is that single field: an IR seat cannot also be a reviewer.
3. `owner` and `admin` may still accept a row. Small desks have no separate reviewer on day one. The audit event names the person.
4. `ir` with an empty company allow-list can read the public screener and cannot export a pack. The owner names the companies.
5. No seat, new or old, writes a published GCI except through the existing accept path, the score ledger, and the public changelog.
6. Public copy does not call `oversight` a compliance officer, and does not call CiteAlpha a SEBI-registered research analyst.

## 6. Success

| # | Outcome | How we know |
|---|---|---|
| B1 | An owner can appoint Portfolio, Data, Investor relations, and Oversight without giving them accept | Invite accepts those four ids. `POST /api/review` with `action=accept` returns 403 for all four |
| B2 | An analyst can no longer accept a row onto the scored record | Same 403 for `analyst`. Reviewer, admin, and owner still 200, and the ledger records the reviewer |
| B3 | An IR seat exports a pack only for a company on its allow-list | In-scope 200, out-of-scope 403, empty list 403 with a sentence the owner can act on |
| B4 | A quant on Enterprise can download the existing export without being owner | `data` ∩ `em_export` succeeds. `data` on Pilot is told the plan does not include the file |
| B5 | A journalist still needs no seat to read the screener, the dossier, and the snapshot | Guest entitlements unchanged |
| B6 | The snapshot headline, the Infosys metric strip, and the screener’s first paint are safe to read aloud | Acceptance in the PRD |
| B7 | An analyst reads one metric across years, then the filing, without losing the table | Infosys constant-currency revenue is one row, newest year first. Both quotes open beside the table |
| B8 | The screener opens on names that already have a score, and an unscored name is one control away | “Scored only” is the default and survives a round-trip to a dossier |
| B9 | A signed-in reader types a ticker and lands on that company from any working page | The palette uses the company search that already exists |
| B10 | A guest still reads the screener with no account, and still stops at 15 dossier opens | Unchanged caps |

## 7. Out of scope

- A seat per job title (head of research, journalist, sell-side, credit).
- A team directory, an earnings calendar product, or a second admin application.
- Making CiteAlpha, or this seat, the compliance officer under the SEBI Research Analyst regulations.
- Retail checkout, Buy / Hold / Sell, or a rank of provisional names.
- Moving a published number as part of the seat work.
- A third vote on the terminal choices in section 10. They are restated so this document stands alone. They are not open again.

## 8. What each job is trying to do

Each job has one decision and a short clock. The first screen answers that decision. Specialist tools stay one labeled step away, on a route that already exists. That is the constraint from Nielsen Norman’s guide for complex applications and from progressive disclosure: the first screen holds what the person uses every week.

| Job | Clock | The decision | First screen |
|---|---|---|---|
| Head of Research | Morning meeting, about 10 minutes | Is coverage deep enough to brief, and what arrived overnight? | Screener, India, with one coverage sentence. Thin records do not read as the best record |
| Portfolio manager | Before the open, about 5 minutes | Did anything in the book change the delivery record? | Holdings, once a file exists: covered weight, named gaps, what changed |
| Buy-side analyst | Under 60 seconds to a sentence they can cite | What was guided, what was reported, where are the two filings? | Dossier evidence, one metric across years, source beside the table |
| Sell-side associate | The afternoon before a print | What is still open, and what do I ask on the call? | CiteAlpha Analyst, grouped as “this print” |
| IR officer | A board pack of about two pages | What did we guide, what did we report, what is still open? | That company’s dossier, then the existing board scorecard |
| Credit / compliance reader | A review sitting | Which commitment is open, who accepted the quote, when? | Workbench review for a reviewer. The audit, for oversight |
| Quant / data buyer | Before a backtest | What is the row, when did it become known, what is null and why? | API page: fields, a sample file, as-of and available date |
| Journalist | A filing deadline, a few minutes | Can I quote this number, and can a reader repeat it? | Snapshot or the dossier cite line: level, tier, as-of, two links |
| Guest | One minute on the homepage | Is this a real filing comparison? | Homepage worked example, then the screener |
| Reviewer | One quote | Does this figure match the filing? | Workbench, Review, company pinned |
| Org owner | Seat setup | Who can run a note, and when does the evaluation end? | Organisation settings |

The clocks come from how these jobs already work, not from a new product shape:

- A buy-side morning is a funnel. The analyst asks what changed, then protects time for the primary document. The note a PM reads keeps the filing, the management statement, and the analyst’s own figure apart.
- A head of research owns coverage: who is covered, what is stale, and the record of notes. They do not re-screen the universe to learn the count.
- An IR board pack is short. Directors ask what was guided, what was reported, and where the outside view diverges. Two pages, then they ask for the rest.
- A journalist’s citation is an instruction to repeat the measurement: publisher, series, period, retrieval date, permalink. A projection is not printed as an outturn.
- A quant buyer starts from the dictionary: a point-in-time anchor, a null with a reason, and a sample file.

## 9. What production showed on 28 Oct 2026

Signed out, on https://citealpha.com. Counts are what the pages printed that day.

| Surface | What the reader got | Why it fails the job |
|---|---|---|
| `/` | Headline, Infosys / Apollo, four workflow links, “2 of 30 Sensex companies scored”, “57 companies scored in total”, “10 companies have sample data” | The first minute is sound. Cards below call the snapshot “by sector”, the workbench “Packages”, and Disclosure Explorer “Beta” and “boards”. |
| `/tracker` | Title says Sensex. This session’s first body was US · S&P 500, 503 unscored names, GCI cell “SEC results releases since Jan 2024 not yet read”. India Sensex then showed Axis Bank 90.7 (1 closed result) above Infosys 76.5 (5). Quality filter offers Hand-labeled and Demo. Twelve markets remain. “Scored only” starts off. | A head of research cannot trust the first screen. A PM scanning GCI sees the thinnest record at the top. |
| `/companies/infy` | Header is the right sentence: 76.5, provisional, data as of 23 Apr 2026, reviewed 29 Sept 2026, met or beat constant-currency revenue guidance in 4 of 5 years, missed FY24. | The metric strip then shows 3.1 and YoY −26.2% on a growth rate. Chips include Unmapped 0 and Pending guidance cite 0. Cells say “not citeable”. FY25 operating-margin promise date 28 Jul 2026 is after the result date 17 Apr 2025. The page is past six panels. The year-by-metric row and the docked source are not there. |
| `/rankings` | “n=0 citeable” and “provisional scores are excluded”, then six provisional rows (Infosys, HDFC Life, Adani Ports, Apollo Hospitals, Axis Bank, Cipla). Title says “Guidance Credibility Quarterly”. CSV and permalink exist. | A journalist cannot tell whether the table is quotable. |
| `/research` | Eight searches, Infosys selected, chat behind a seat. The company control listed Infosys and Cipla. A document chip is named expert. | “Published” here, on the snapshot, and on the homepage are three different sets. |
| `/sights` | Subnav has the live rooms. The lede still says search, boards, and agents. “Open a surface” lists three rooms. Compare Grid says “Same prompts across names”. | A PM comparing a sector has to translate the page. |
| `/analyst` | The gate names the jobs and does not show a skill list. | The seat, once inside, meets a flat catalogue. |
| `/developers` | A list of `/api/v1` paths. | No field dictionary, no sample, no available date. |
| `/workflows` | Four articles, same page for a guest and an owner. | A map. It is not the morning itself. |

Seat rooms were not signed into. Their shape is the shipped PRD for the workbench, Analyst, holdings, and Financial Ninja.

## 10. Terminal pass — confirmed 25 Oct 2026

A PM with Infosys open wants constant-currency revenue across FY22–FY26 in one glance, then the sentence in the filing, without losing the table. A coverage analyst wants the screener to open on names that already have a score. A signed-in seat wants to type INFY and land on that dossier.

The homepage, evaluation, blog, and plan page stay a public site. The screener, dossier, Filing Search, workbench, Disclosure Explorer, Holdings, and Financial Ninja are the working surface.

Nothing in this pass adds a score, a route, a filing client, or a second evidence table. Week, month, quarter, and year chips stay on the citeable point-in-time rule. These choices were confirmed on 25 Oct 2026. The lettered alternatives were declined and stay declined.

| # | Confirmed | Declined |
|---|---|---|
| Q1 | On the evidence panel, “By year” opens first and “By row” is one control away. The dossier stays within six panels. For Infosys, constant-currency revenue growth is one row. Columns run FY26 back to FY22. Each cell shows the guided band, the reported figure, and the outcome in words. A pending cell stays visible and is not drawn as met. A year with no row is an em dash. | By year as the only public view, with the cite-row table moved to the workbench. Pivot only on the workbench. |
| Q2 | The last column is the track: outcome words for that metric, oldest to newest among closed years. Example: Met · Met · Exceeded · Missed. Pending years are left out. No segment bar. No gap versus the guided midpoint. Score Δ is not this column. | A bar, or a numeric gap. |
| Q3 | A promise click and a result click keep the table on the left and open stored text on the right, about 60/40. The quote is highlighted from the character span already stored. Escape closes the pane. “Open original” and “Copy citation link” stay. The same `openSource()` call is the only entry, including Filing Search, the revision trail, and Disclosure Explorer. | A PDF highlight when the stored file is a PDF. A new extract that stores a page rectangle. The browser does not fetch NSE, BSE, EDGAR, or the issuer. |
| Q4 | Compact is the default on the screener and the dossier. On 1920×1080 the screener shows at least 25 rows without scrolling the window. Numbers use IBM Plex Sans, tabular figures, right-aligned. Tickers and fiscal periods use IBM Plex Mono. Comfortable remains in account settings and is applied when set. | JetBrains Mono and Roboto Mono. |
| Q5 | One disclaimer line stays at the foot of the screener and the dossier: factual research, no recommendation. The longer “N not yet scored” essay leaves once the pills state that count. The disclaimer is not hidden behind an info control. The one-sentence delivery record on the dossier stays. | Collapsing the disclaimer. |
| Q6 | From a working route, Cmd+K (Ctrl+K elsewhere) and `/` when focus is not in a field open a palette. It searches companies through the existing company search and lists the tools already in the nav. Choosing a company opens that dossier. Recent companies are the last few ids this browser opened. They are not a watchlist and they do not change a score. The palette does not search API keys. | Saved screens such as “margin misses”. A ticker box fixed in the header. |
| Q7 | Two frames on the same host. Marketing routes keep today’s header. Working routes use a short frame: mark, palette hint, account. A text link “CiteAlpha” returns home. A signed-out reader on a working route sees Sign in and is not sent to a login wall. No separate host and no `/console` prefix. Admin and organisation settings keep the admin bar. | A second application frame on another host. |
| Q8 | “Scored only” and “All”, with live counts for the index on screen, written on the URL (`scored=1` or `scored=0`) so a round-trip to a dossier restores the choice. Scored only is the default on every index that remains, including NSE All and BSE All. An empty scored list says no scored companies are in this index yet and leaves “All” visible. Unscored rows still sort after scored rows, with no rank and no fabricated score. | A default of the full unscored master. |
| Q9 | Tier words stay Provisional, Established, and Deep. An unscored row may carry a quiet “Not scored” chip. It is not a rank and not a fourth tier. Sample data stays on the quality badge. No emoji. `score_policy` and the Public Snapshot rank rule do not change. | Emoji status marks. Dropping Deep. |

What already ships, and this cycle does not rebuild: one evidence table rather than a stack of year cards; an in-app viewer on the result link (today a centered dialog, not a dock); character offsets as the citation geometry; the three confidence tiers; a scored-only checkbox that starts off and forgets itself; tabular digits that are still left-aligned and padded for a comfortable density; an account density preference that no research table reads; a dark console that is only the workbench ops tab; one header for marketing and research; company search without a palette; the SEBI line on the screener and the dossier; outcomes already returned on the company GCI payload, so the year view is a client arrangement of `outcomes[]` and not a new history API.

## 11. Where the 25 Oct choices and the 28 Oct walk meet

| Topic | 25 Oct | 28 Oct | This cycle |
|---|---|---|---|
| Which market opens | Scored only on every index, including the broad India masters | A guest opens on India. Markets other than India leave the public control. The title follows the index | Both. The public control lists India indexes only. Inside those, including NSE All and BSE All, scored only is the default and is on the URL |
| Sort | Sort stays as it is | A one-period 90.7 sorting above a five-year 76.5 misleads a head of research. Proposed sort: closed results, then GCI. That is not a rank | Sort stays as it is until the owner confirms the change. The proposal is recorded here and is not a requirement of this cycle |
| Coverage words | The long “N not yet scored” essay leaves once pills state the count. The disclaimer line stays | The kicker should be the homepage sentence (“2 of 30 Sensex companies scored”) | Pills carry scored versus all. The kicker carries the coverage sentence for the index on screen. The essay under the table goes. The disclaimer line stays |
| Unscored label | Chip says “Not scored” | The score cell says why, in one sentence, and does not use a pipeline stage or the word Demo | The chip says “Not scored”. The score cell carries one coverage sentence. Sample data is called sample data |
| Dossier length | Six panels. The year view is another arrangement of the evidence panel | Drop the extra trend, metric-change, and score-history panels. A change in a growth rate is labeled as a change in that rate | Both. The year toggle lives inside evidence. The −26.2% figure on Infosys is not shown as a revenue decline |
| Frame and landing | Short frame on working routes | Each seat lands on its job | The short frame is the chrome. Login sends each seat to the screen in section 8. A bookmark is not redirected |
| Who publishes | Not in the terminal pass | Analyst can accept today, because accept is `desk_write` | Accept is reviewer, admin, or owner. The four new seats cannot accept |

## 12. Owner

Product owns the seat list. `platform-engineer` implements entitlements. `frontend-designer` implements the first screens. `index-steward` reviews the accept-path change before it ships, because that change decides who may move a published input.
