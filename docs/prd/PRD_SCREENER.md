# PRD — GCI Screener

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited  
**Status:** Implemented · **Date:** 2026-10-25  
**Route:** `/tracker`  
**Owners:** `HomePage.tsx`, `repository.list_company_summaries`  
**Related:** [PRD_DOSSIER.md](PRD_DOSSIER.md) · [PRD_SNAPSHOT.md](PRD_SNAPSHOT.md)

---

## Prime requirement — a list someone can scan before the open

An analyst opens the GCI Screener the way they open a coverage sheet on a Tuesday morning. They want to see who has a delivery record, how solid that record is, and which name to open next. They should be able to do that without an account. Signing in is what they do after a name is worth a note, not before they can see the list.

### What one row has to answer

The row is a company a person can recognise: name, ticker, sector. Then the GCI, large enough to scan, with the confidence tier in words beside it (`provisional`, `established`, `deep`). Then a short record: how many closed results were met, exceeded, or missed, and the date of the last filing. A change versus last week, month, quarter, or year appears only when that series can be cited. Otherwise the cell is an em dash, and the dash is quiet. It is not a zero, and it is not a hint that the score fell.

A company with no published score stays on the list, because coverage is wider than the scored set. The score cell is empty, or it carries one sentence of why (“Not yet scored”). The row sorts after the scored names. It is never given a rank, and it is never filled with 0 so that the column lines up.

### How the page behaves in the hand

The kicker says the screener covers Indian listed companies. The default index is the one the desk already uses. Search narrows the companies already loaded. Typing a name uses the existing company search and attaches a GCI only when one is published.

Selecting a row opens the dossier. That is the primary action. Alerts, when they appear, are changes in the delivery record, written as a metric a person says and as guided versus reported. They are not price alerts.

The page carries the ordinary disclaimer in the footer: factual research, no recommendation. There is no Buy, Hold, or Sell column, no price, and no star that implies a call.

On a phone the company and the score stay on screen. The rest of the row scrolls sideways inside the table, with the company column held still if the table is wide. Loading is a single line. An empty index says no companies matched, and it leaves the filter visible so the reader can clear it.

A guest and an owner see the same number for the same company. The screener is the working list. The public rank, when there are enough deep names to deserve one, lives on the Public Snapshot.

## 3. Users

| Persona | Job |
|---|---|
| Buy-side analyst | Scan scored names, then open the evidence |
| Sell-side associate | See which names in a sector have a delivery record |
| Guest | Read the list without an evaluation. Chat, the workbench, and the API stay closed |

## 3.1 Role requirements

Anyone who can open the site can scan the list. The table records that, and it records the one thing no row may do: pretend an unscored name has a rank.

Reading the screener is the guest feature `tracker`. Every seat has it, including after a pilot term ends.

| Action | Signed out, guest | viewer, member | labeler | analyst | reviewer | admin, owner |
|---|---|---|---|---|---|---|
| Open `/tracker`, sort, filter, and search the loaded list | Allowed | Allowed | Allowed | Allowed | Allowed | Allowed |
| See a published GCI, its tier, and a citeable change | Allowed | Allowed | Allowed | Allowed | Allowed | Allowed |
| Open the dossier from a row | Allowed, then the dossier cap | Allowed | Allowed | Allowed | Allowed | Allowed |
| Accept, edit, or reject a guidance row | Refused. No control on this page | Refused | Refused | Refused | Refused | Refused |

No role may treat the list as a public rank of provisional names. That rank is the Public Snapshot, and only for established and deep names.

The delivery-alert list that the screener already shows is part of this public read. The `alerts` feature (analyst, reviewer, admin, and owner, and only on Desk, Enterprise, and One-Stop) is the Radar seat. It does not grant a second score, and it does not hide a row from a guest.

**SC-R1.** A viewer and a guest receive the same row for the same company.  
**SC-R2.** No role receives a Buy, Hold, or Sell control.  
**SC-R3.** A direct call that would accept a label from this route is not provided. Acceptance remains `desk_write` on the workbench.

## 4. Decisions

| # | Decision |
|---|---|
| D1 | Default market is India. The index control uses the existing listings. The screener does not add a second company list. |
| D2 | `gci_score` is null unless `publishable_score` allows it (`hand_labeled` or `extracted_verified`). |
| D3 | Every published number shows its confidence tier beside it. |
| D4 | A change chip (week, month, quarter, year) renders only when `series_kind` is `citeable_pit`. Otherwise the cell is an em dash. |
| D5 | Quality is visible on the row. Sample data is called sample data, not a demo flag name. |
| D6 | Guest entitlements are exactly `features: ["tracker"]`, with a dossier-open cap of 15 and a chat limit of 0. |

## 5. What the screener is not

- A recommendation screen. No Buy, Hold, or Sell column.
- A price board.
- The Public Snapshot. The snapshot is the public rank of established and deep names. The screener is the working list, including unscored coverage.
- A place to accept a label. Acceptance stays on the Analyst Workbench.

## 6. Behaviour

1. The table loads from `GET /api/companies` with the selected market and index, paged.
2. Columns a reader needs on one screen: name and ticker, sector, GCI, tier or coverage sentence, and the citeable change when it exists.
3. Sort may put published scores first. Sort is not a public rank of provisional names.
4. Search narrows the loaded list. Entity search (`GET /api/companies/search`) is the typeahead over listings and attaches a GCI only when one is published.
5. A row links to `/companies/{id}`.
6. Alerts, when shown, are changes in the delivery record. They are not price alerts.
7. The page carries the standard disclaimer: factual research, no recommendation.

## 7. Stories

**SC-1.** Given a company has no published GCI, when it appears on the screener, then the score cell is empty or a coverage sentence, and the row is not given a rank.

**SC-2.** Given Infosys is published at 76.5 with tier deep, when the screener lists it, then the number and the tier match the dossier.

**SC-3.** Given the point-in-time series is not citeable, when the row renders a change, then the change is an em dash.

**SC-4.** Given a guest session, when entitlements load, then features are only `tracker` and the screener still opens.

**SC-5.** Given a viewer and a guest request the same company on the screener, when both responses return, then `gci_score` and `confidence_tier` match.

## 8. Index integrity

The list reads the same score the dossier publishes (`audited_company_gci` / score cache). A screener change that moves a published number follows the score ledger and the public changelog on the same day.

## 9. Test plan

- `tests/test_score_consistency.py`: list score equals dossier score.
- Guest entitlements test: features equal `["tracker"]`.
- No synthetic horizon fields on the public payload.

## 10. Files

`frontend/src/pages/HomePage.tsx` · `backend/app/services/repository.py` (`list_company_summaries`) · `backend/app/services/score_policy.py` · `GET /api/companies`
