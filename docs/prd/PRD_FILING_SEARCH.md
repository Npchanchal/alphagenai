# PRD — Filing Search

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited  
**Status:** Implemented · **Date:** 2026-10-25  
**Route:** `/research`  
**Owners:** `ResearchPage.tsx`, `research_svc.search_documents`, `session_auth.consume_reading_search`  
**Related:** [PRD_ANALYST.md](PRD_ANALYST.md) · [PRD_COMMERCIAL.md](PRD_COMMERCIAL.md)

---

## Prime requirement — looking up a filing the way a person looks one up

Someone arrives with a question already in mind. “What did Infosys say about revenue growth?” They need a box, a company, and passages they can open. They should know, before they type, whether this visit is the open reading room or the full search their seat paid for. The page tells them in the kicker, not in an error after they have written the query.

### The reading room

A visitor, a guest, and a desk whose evaluation has ended land in the reading room. The kicker says “Published scores · eight searches”. The lede says the search covers companies with a published GCI, that this browser keeps the eight, and that cite-only answers, the company snapshot, and the watchlist open with an evaluation.

The company control lists only those published names, as “INFY — Infosys Ltd.” There is no “all companies” option, because an empty search of the whole archive is the seat. Infosys is selected when it is in the list. If the reader clears the company, the page puts the first published name back rather than firing a search that will be refused.

The allowance is a sentence they can read: “7 of 8 filing searches left on companies with a published GCI.” The words sit above the button, with a text link to request an evaluation. At zero the button is quiet and disabled, and the sentence says the eight are used. The ninth attempt, if they reach the API another way, comes back as a clear limit, and the count stays at eight. Clearing the site’s storage does not reset it. This browser is the cookie, explained in human words.

Results are passages. Each row has a title a person can say, the company, the date, and a snippet. “Open source” shows the stored passage highlighted and keeps the original filing link. A title that was stored as a metric id is shown as the period and the metric name.

Chat, the company snapshot, news, and the watchlist are present as tabs so the reader can see what an evaluation adds. Opening one explains that those stay on a seat, with a way to request the evaluation or to sign in. The search they already ran stays put. The page does not dump them onto a login wall and lose the query.

### The seat

A viewer, an analyst, or anyone whose plan includes research sees a different lede: one company or all covered companies, synonyms for Indian filings, citations, a snapshot, saved searches, and a watchlist. “All covered companies” is a real option. The search is not counted.

Cite-only chat is a further step. A viewer can search and cannot ask. The chat tab, for them, explains that answers stay with an analyst seat, in one sentence, and does not show a box that will fail. An analyst sees the box. They type a question, they wait with the button disabled so they do not send it twice, and the answer comes back with numbered citations. A citation opens the passage. If nothing in the store supports an answer, the page says so and does not invent one.

The company snapshot on its own tab repeats the published score and the tier. It does not draw a price. News is the stored items for that company. The watchlist is the reader’s list. Saving a monitor on it requires them to be signed in. An API key with no person behind it is asked to sign in, in those words.

### Failure in plain language

A company with no published score, if someone asks for it directly, is answered with: the reading room searches companies with a published GCI, and they should pick one from the list. A search with no hits says nothing matched, and it leaves the query in the box so they can widen it. Synonym expansion, when it happens, is shown as a line they can read (“also searched for …”), not as a silent change to their words.

On a phone the company control, the query, and the allowance sit in one column. Results are cards, not a table that runs off the edge.

## 3. Users

| Persona | Access |
|---|---|
| Visitor, no session | Reading room |
| Signed-in guest | Reading room, counted on the guest account |
| Pilot, Desk, Enterprise, or any seat whose plan ∩ role includes `research` | Full Filing Search |
| Platform super | Full Filing Search |

Chat requires `research_chat`. The reading room does not include it.

## 3.1 Role requirements

The reading room and the full search are two different welcomes, described above. This table is who receives which welcome. A refusal is a sentence on the page, and the same rule on the API, so a hidden button is not the only thing stopping a ninth search.

A caller without `research` is in the reading room, whether or not the query sends `reading_room=true`. That is the signed-out visitor, the guest, and a seat whose plan no longer includes `research` (an approved pilot whose term has ended).

| Action | Signed out, guest, ended pilot | viewer, member | labeler | analyst | reviewer | admin, owner |
|---|---|---|---|---|---|---|
| Search one company that has a published GCI | Allowed, eight per browser or per account | Allowed, not counted | Allowed, not counted | Allowed, not counted | Allowed, not counted | Allowed, not counted |
| Search with no company, or a company with no published GCI | 403 `reading_room_scope` | Allowed | Allowed | Allowed | Allowed | Allowed |
| Ninth search | 403 `reading_room_cap`. The count stays at 8 | Not counted | Not counted | Not counted | Not counted | Not counted |
| Cite-only chat | Gate. `research_chat` is absent. The API returns 403 | Gate and 403 | Gate and 403 | Allowed on Pilot, Desk, Enterprise, and One-Stop | Allowed on those plans | Allowed on those plans |
| Company snapshot, news, and watchlist tabs | Gate. These tabs require `research` | Allowed | Allowed | Allowed | Allowed | Allowed |

A watchlist monitor requires a signed-in user. An API key with no user receives 422 and no monitor is stored.

A platform `super` is treated as having `research`, including cite-only chat, because the Desk feature set includes both. Platform `ops`, `compliance`, `billing`, and `support` follow their seat. A support user with no organisation is a guest and stays in the reading room.

Retail, if the plan exists, intersects to `research` without `research_chat`: full search, no chat.

**FS-R1.** The server enforces the room. Omitting `reading_room`, or editing page storage, does not reset the eight.  
**FS-R2.** A viewer searches every covered company and is refused on chat.  
**FS-R3.** An analyst on a pilot searches and chats. A labeler on the same pilot searches and is refused on chat.  
**FS-R4.** A research-seat API key may omit `company_id` and is not counted. The demo key is that seat.

## 4. Decisions

| # | Decision |
|---|---|
| D1 | The server is the gate. Hiding a tab is presentation. A caller without `research` is held to the reading-room rules even when `reading_room` is omitted. |
| D2 | A reading-room company is one whose score-cache `gci_score` is a number (`published_gci`). Hand-labeled rows without a number, including Apollo Hospitals on the local set, are out. |
| D3 | The company list for the room is `GET /api/companies?scored=true`, not the default Sensex page. |
| D4 | The allowance is 8. A signed-in user is counted on `preferences.reading_searches`. A visitor is counted on the HttpOnly cookie `citealpha_reading` (30 days, SameSite lax). The ninth search returns 403 `reading_room_cap` and does not increment past 8. |
| D5 | `GET /api/research/reading-room` reports the count and does not increment it. The page shows the remaining count before the search. |
| D6 | A research seat is not counted and may omit `company_id`. The demo API key is a research seat. |
| D7 | India IR synonyms stay the `expand=true` option. Chat still refuses an answer that has no citation. |
| D8 | Saved searches and the watchlist remain preference fields. They are not a second store. |

## 5. What Filing Search is not

- CiteAlpha Analyst. Skills, monitors, and exports live at `/analyst`.
- Disclosure Explorer. Themes, grid, and deep dive stay at `/sights`. Retired Sights search, ask, and boards redirect here.
- A way to change a GCI.
- A news product. The news tab is stored items for a seat, not a wire.

## 6. Behaviour

### 6.1 Reading room

1. While entitlements are loading, the page waits. When the session lacks `research` and is not platform super, reading room is on.
2. The kicker and lede say the search covers companies with a published GCI, that this browser keeps eight searches, and that chat, the snapshot, and the watchlist open with an evaluation.
3. The company control lists published names only. There is no “all companies” option. Infosys is the default when it is in the list. An empty selection is replaced by the first published name.
4. The allowance line is `{remaining} of {cap}` plus a link to `/pilot`. At zero remaining the search button is disabled.
5. Search calls `GET /api/research/search` with `company_id` and `reading_room=true`. The response `reading_room.remaining` replaces the displayed count.
6. Tabs chat, desk, news, and watch render `PlanAccessGate` (`research-access-gate`) instead of their bodies.
7. A direct search with no company, or with a company that has no published GCI, returns 403 `reading_room_scope`.

### 6.2 Research seat

1. The lede describes one company or all covered companies, synonyms, citations, the snapshot, saved searches, and the watchlist.
2. The company control includes “all covered companies” (`scope=all`).
3. Chat posts to `/api/research/chat` and requires `research_chat`. Answers use numbered citations. Opening a citation shows the stored passage highlighted.
4. The desk snapshot, news, and watchlist load only on those tabs.
5. Period-on-period changes appear only when the series can be cited.

## 7. Stories

**FS-1.** Given no session, when the visitor opens Filing Search, then the list is the published-score companies and the allowance reads 8 of 8.

**FS-2.** Given that visitor searches Infosys, when the response returns, then filings are listed and the allowance is 7 of 8.

**FS-3.** Given the same browser sends a ninth search, when the API answers, then the status is 403 `reading_room_cap`.

**FS-4.** Given a new browser, when it searches Cipla, then the search is allowed. Cipla is a published score even when it is outside the Sensex default list.

**FS-5.** Given a caller with `research`, when they search with no company id, then the status is 200 and the body has no `reading_room` count.

**FS-6.** Given a visitor opens the AI Chat tab, when the tab renders, then the evaluation gate is shown and chat is not called.

**FS-7.** Given a viewer on a pilot opens the chat tab, when the tab renders, then the chat gate is shown and `POST /api/research/chat` returns 403.

**FS-8.** Given an analyst and a labeler on the same pilot, when each asks a cited question, then the analyst receives a cited answer and the labeler receives 403.

## 8. Index integrity

Search does not score. Passages are stored documents. A title that contains a metric id is displayed with `publicDocTitle`.

## 9. Test plan

`backend/tests/test_reading_room.py`

- Recent filings are accepted sources.
- `scored=true` includes Infosys and Cipla and excludes Apollo Hospitals.
- An anonymous search with no company is `reading_room_scope`.
- Eight anonymous searches then a ninth is `reading_room_cap`. A second client still has an allowance.
- A guest bearer is capped at eight.
- `X-API-Key: intellens-demo` searches without a company and without a count.

`test_sights.py`: synonym expansion across companies runs with the research-seat key.

Browser: reading-room lede, both company names, a search that decrements the allowance, chat tab gated.

## 10. Files

`frontend/src/pages/ResearchPage.tsx` · `frontend/src/lib/api.ts` (`fetchReadingRoom`, `fetchCompanies({ scored })`) · `backend/app/api/routes.py` · `backend/app/services/session_auth.py` · `backend/app/data/gci_score_cache.py` (`published_gci`) · `backend/app/services/repository.py` (`list_published_companies`)
