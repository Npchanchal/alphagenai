# PRD — Disclosure Explorer

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited  
**Status:** Implemented · **Date:** 2026-10-25  
**Route:** `/sights`  
**Owners:** `services/sights.py`, Sights pages  
**Related:** [PRD_FILING_SEARCH.md](PRD_FILING_SEARCH.md) · [PRD_ANALYST.md](PRD_ANALYST.md)

---

## Prime requirement — one topic, several companies, every cell opens

A desk comparing revenue guidance across a sector should be able to start from the topic, not from a search box that duplicates Filing Search. Disclosure Explorer is that comparison. The reader picks a theme or a grid, reads a cell, and opens the filing that supports it. Browse is open to anyone. Asking a question inside Explorer is a seat.

### The hub

The hub lists the live rooms in language a PM uses: Delivery Themes, Street Context, Field Evidence, Compare Grid, Deep Dive, Fundamentals. It does not list retired tools as if they were still rooms. Search, a saved board, an agent, and export live on Filing Search and CiteAlpha Analyst. An old bookmark to those Explorer addresses forwards there, without a lecture about what moved.

### A cell has to be openable

A theme uses the same outcome words as the dossier: met, missed, dropped, pending. A grid cell that states a figure has a citation on it. Opening the citation shows the stored passage, not a summary that cannot be checked. A deep dive starts from a topic the reader typed. A blank topic is stopped with a sentence asking for the topic, before any paragraph is written. A paragraph that cannot be tied to a filing is not shown.

Street context is public filings and licensed consensus, labeled as such. It does not pretend to host a broker’s PDF. Field evidence is the hand-labeled record. It reads like a research file, not like a marketplace. Fundamentals are the strip the dossier already uses for that company. A missing actual is left missing.

### Ask, for the seat that has it

Ask sits where a reader who has been browsing would look for it. A viewer sees the themes and, on ask, a short explanation that cite-only questions stay on an analyst seat. An analyst gets the box. The answer is cited or it says it cannot answer. The same empty-topic refusal applies to them.

On a phone the hub is a list, the grid scrolls inside itself with the company names held, and a cell opens as a sheet the reader can dismiss back to the grid without losing their place.

## 3. Users

| Persona | Job |
|---|---|
| Analyst | Open a theme or a grid and follow a cell to its filing |
| Seat with cite-only ask | Ask inside Explorer where that surface is still enabled |
| Visitor | Browse themes, street context, field evidence, the grid, deep dive, and fundamentals. Retired tools redirect |

## 3.1 Role requirements

Browsing the grid is open, as the walkthrough says. Asking is the step that changes with the seat. Old bookmarks forward everyone, and the page they land on then speaks for itself.

Browse is public. Cite-only ask is `sights_ask`, which analyst, reviewer, admin, and owner have on Pilot, Desk, Enterprise, and One-Stop. Viewer, member, labeler, guest, and a signed-out visitor do not.

| Action | Signed out, guest, viewer, labeler | analyst, reviewer, admin, owner |
|---|---|---|
| Open the hub, a theme, street context, field evidence, the grid, a deep dive, and fundamentals | Allowed | Allowed |
| Ask inside Explorer | Gate, and `POST /api/sights/ask` returns 403 | Allowed on Pilot and above |
| Open `/sights/search`, `/sights/ask`, `/sights/boards`, `/sights/agents`, or `/sights/export` | Redirect for every role. Search and ask land on Filing Search. Agents and export land on CiteAlpha Analyst | Same redirects. The destination then applies its own role rules |
| Call a retired Sights agent or export API | 410 with `moved_to`, for every role | Same |

A deep dive that states a fact still needs a stored citation. The role does not relax that. An empty topic is refused for an analyst the same way it is refused for a guest.

**SI-R1.** A viewer browses the grid and receives 403 on ask.  
**SI-R2.** An analyst on a pilot can ask. A labeler on that pilot cannot.  
**SI-R3.** Retired routes redirect before any role check on the old tool. The new page applies its gate.

## 4. Decisions

| # | Decision |
|---|---|
| D1 | Remaining surfaces: hub, Delivery Themes, Street Context, Field Evidence, Compare Grid, Deep Dive, Fundamentals, settings links. |
| D2 | `/sights/search` redirects to Filing Search with all companies. `/sights/ask` redirects to chat. `/sights/boards` redirects to the watchlist. `/sights/agents` and `/sights/export` redirect to `/analyst`. |
| D3 | Matching API routes either return `superseded_by` or `410` with `moved_to`. |
| D4 | Themes use delivery labels (met, missed, dropped, pending). They do not use a sentiment score. |
| D5 | Street context is public filings and licensed consensus. It does not host broker PDFs. Field evidence is the hand-labeled record. It is not an expert-call marketplace. |
| D6 | No competitor names in the interface or the SEO titles. |

## 5. What Explorer is not

- A second Filing Search.
- A replacement for a global market-data terminal.
- A recommendation engine.

## 6. Behaviour

1. The hub lists the live surfaces and does not list the retired ones as tools.
2. A theme, grid cell, or deep-dive paragraph that states a fact has a citation the reader can open.
3. An empty deep-dive topic is refused rather than answered from nothing.
4. Fundamentals show the strip for a company already on the dossier path. They do not invent actuals.
5. Settings point at trust, methodology, and the commercial page.

## 7. Stories

**SI-1.** Given a reader opens `/sights/search`, when the router finishes, then the URL is Filing Search.

**SI-2.** Given a grid cell states a guidance figure, when the reader opens the citation, then the stored filing contains that passage.

**SI-3.** Given a deep dive is started with a blank topic, when the API responds, then `refused` is true.

**SI-4.** Given a viewer posts to `/api/sights/ask`, when the API answers, then the status is 403 and no answer is stored.

**SI-5.** Given an analyst and a guest open the same grid cell, when both pages render, then the citation and the filing passage match.

## 8. Index integrity

Explorer reads the delivery record and the document store. It does not publish a GCI.

## 9. Test plan

`backend/tests/test_sights.py` for deep dive, fundamentals, and the 410 moves. Playwright covers the redirects.

## 10. Files

`backend/app/services/sights.py` · `frontend/src` Sights pages · `docs/kb/14-sights.md`
