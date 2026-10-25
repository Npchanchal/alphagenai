# PRD — Public Snapshot

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited  
**Status:** Implemented · **Date:** 2026-10-25  
**Route:** `/rankings`  
**Owners:** `RankingsPage.tsx`, rankings API  
**Related:** [PRD_SCREENER.md](PRD_SCREENER.md) · [PRD_INDEX_RECORD.md](PRD_INDEX_RECORD.md)

---

## Prime requirement — a page a journalist can quote

The Public Snapshot is the page someone cites when they are not logged in and they need to be careful. A journalist, a PM, or a client who was sent the link should understand, in the headline, whether they are looking at a rank or at a delivery record. Those are different claims. The page has to choose the honest one and say which it chose.

### When the list is still short

Until at least 20 companies are established or deep, this is a record, not a league table. The heading says so, in words a reader can repeat: this is the delivery record, and a rank will wait until more companies are there. Columns are the company, the tier, how many results were met, exceeded, or missed, and the last filing. Rows are not numbered 1, 2, 3. There is no “Top” and no “Lowest”. Sort by the depth of the record if a sort is offered. A provisional score does not appear as a rank even later, when ranked mode is on.

Each row links to the dossier. The page shows the date the snapshot was taken. An empty payload says the record is empty. It does not fill the table with sample companies to make the page look finished.

### When a rank is earned

When the snapshot is in ranked mode and at least 20 names qualify, a rank is fair. Each row then shows the place, the GCI, the tier, and the link. The heading changes to match. A reader who arrives from an old bookmark still sees the heading that matches the table in front of them, not a rank title over an unranked list.

Sector cuts, if they are shown, are the same published companies grouped. They do not invent a second score.

The page is the same for a guest and for the owner of a desk. No login wall, no blurred rows, no prompt before the first company. On a phone the company and the record counts stay readable. The disclaimer sits where a quote would see it: factual research, no recommendation.

## 3. Users

| Persona | Job |
|---|---|
| Journalist or PM | Cite a public page that is not a recommendation |
| Analyst | Jump from a ranked or recorded name into the dossier |
| Guest | Read it with no login |

## 3.1 Role requirements

There is no signed-in version of this page. If a rank is too strong a claim for a guest, it is too strong a claim for the owner as well.

The snapshot is public. Ranked mode and record mode are properties of the universe, not of the seat.

| Action | Signed out, guest, viewer, labeler, analyst, reviewer, admin, owner |
|---|---|
| Open `/rankings` and read the record or the rank | Allowed. No login wall |
| See a rank for a provisional company, or a rank when fewer than 20 names qualify | Refused for every role |
| Recompute or override a level from this page | Refused. No role has a write control here |

A seat does not receive a rank, a tier, or a delivery count that a guest does not.

**SN-R1.** The payload is identical for a guest and for an owner.  
**SN-R2.** Record mode at fewer than 20 rankable names applies to every role, including platform `super`.

## 4. Decisions

| # | Decision |
|---|---|
| D1 | Rankable tiers are `established` and `deep` only (`score_policy.RANKABLE_TIERS`). |
| D2 | Ranked mode requires the snapshot mode to be `ranked` and the universe to be at least 20 names. Below that, the page uses record mode. |
| D3 | Record mode columns are the delivery counts and the last filing, not a position. |
| D4 | The page shows data as of the snapshot date. |
| D5 | No leaderboard of companies below the confidence threshold. |

## 5. What the snapshot is not

- The working screener. Unscored listings belong on `/tracker`.
- A performance league table against share prices.
- A buy list.

## 6. Behaviour

1. The page loads the public rankings payload and reads `mode` and `universe_n`.
2. When record mode applies, the heading explains that this is the delivery record, and the table does not number the rows as a rank.
3. When ranked mode applies, each row shows the GCI, the tier, and a link to the dossier.
4. An empty payload says the record is empty. It does not fill sample companies.
5. Sector grouping, if present, is a cut of the same published set.

## 7. Stories

**SN-1.** Given fewer than 20 rankable names, when the snapshot loads, then `rankings-record-table` is shown and no row is numbered as a rank.

**SN-2.** Given a provisional score, when the snapshot is in ranked mode, then that company is absent from the rank.

**SN-3.** Given a visitor with no session, when they open `/rankings`, then the page renders without a login wall.

**SN-4.** Given an owner and a guest request the snapshot on the same day, when both payloads return, then `mode`, `universe_n`, and the company rows match.

## 8. Index integrity

The snapshot reads published rows. It does not recompute them. A methodology change that alters who is rankable is a changelog entry the same day.

## 9. Test plan

- Page test id `gci-rankings-page`.
- Record-mode fixture shows `rankings-record-table` and no rank column.
- A provisional company is excluded from a ranked payload.

## 10. Files

`frontend/src/pages/RankingsPage.tsx` · `backend/app/services/score_policy.py` · rankings route behind `frontend/src/lib/api.ts`
