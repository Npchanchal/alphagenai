# PRD — Holdings

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited  
**Status:** Implemented · **Date:** 2026-10-25  
**Route:** `/holdings`  
**Owners:** `services/holdings.py`, `HoldingsPage.tsx`  
**Related:** [PRD_DOSSIER.md](PRD_DOSSIER.md) · [PRD_COMMERCIAL.md](PRD_COMMERCIAL.md)

---

## Prime requirement — a book the PM can trust because the gaps are named

A portfolio manager pastes a holdings file to see one question: of the weight CiteAlpha can actually score, what is the delivery record. They will not trust a single blended number that quietly treats cash as if it had guidance. The page has to show the covered weight, the weighted GCI of that weight, and a gap list they can read down.

### Pasting the book

The page explains, in two sentences above the box, what to paste: an identifier, a weight, and a name, and whether the line is cash, debt, an indirect holding, or something else. Five hundred lines is the limit, stated before they paste a thousand. The button is “Look through”. While it runs, the button waits. The previous result stays visible until the new one is ready, so the page does not go blank.

The result leads with the weighted GCI and the share of the book that entered it. Under that, the gap list names every line left out, and why: no published score yet, cash, debt, an indirect holding, or an identifier CiteAlpha does not know. A line for Apollo, if Apollo has no published number, appears there by name. It is not given a provisional score to make the total neat.

Scheme values the desk typed (a date and a value) are shown as their own series, labeled as the desk’s figures. They are not drawn on the same axis as GCI.

### Coming back, and the closed door

The latest file is there on the next visit, for this organisation. Another desk’s file is simply not found. A guest, a viewer, or a labeler sees a short explanation of the look-through and a way to ask for a seat that includes it. The paste box is not shown to them.

The disclaimer under the figure says the number uses published scores only and is not a recommendation. On a phone the figure and the first gaps fit the width. The full gap list scrolls.

## 3. Users

| Persona | Job |
|---|---|
| PM or risk on an approved pilot, Desk, Enterprise, or One-Stop | Paste holdings, read the weighted published score and the gaps |
| Visitor or guest | Sees the seat gate |

## 3.1 Role requirements

The paste box, the covered weight, and the named gaps are for a PM whose seat includes holdings. Everyone else gets the explanation and no box. The table is that rule, including a pilot whose term has ended.

The feature is `holdings`. The role must be analyst, reviewer, admin, or owner. Viewer, member, labeler, and guest do not have it. The plan must be an open approved pilot, Desk, Enterprise, or One-Stop. `holdings` is removed when the pilot term ends, and it is absent on retail.

| Action | guest, viewer, labeler | analyst, reviewer, admin, owner |
|---|---|---|
| Open `/holdings` and read the saved file | Page gate. API 403 | Allowed while the plan above is open |
| Paste a book and read the weighted published GCI and the gap list | Refused. Nothing is written | Allowed. The file is stored for that organisation only |
| Read another organisation’s file | Refused | 404 |
| Give an unscored line or a cash line a weight in the total | Refused for every role that can open the page | Refused. The line stays in the gap list |

A platform `super` receives the Desk set, so Holdings opens for super while a Desk plan would have it. Super does not publish a GCI from the file.

**HO-R1.** A labeler and a viewer on Desk see the gate, and no file is written.  
**HO-R2.** An analyst on Desk can save a book. An analyst on an ended pilot cannot.  
**HO-R3.** Two organisations never read each other’s files.

## 4. Decisions

| # | Decision |
|---|---|
| D1 | The file is org-scoped under the holdings store. Another org cannot read it. |
| D2 | A line counts only when the identifier resolves to a company with a published GCI. |
| D3 | Residual kinds are cash, debt, indirect, and other. They are excluded from the weight. |
| D4 | The page accepts at most 500 lines. |
| D5 | Scheme history is values the desk typed (date, value). It is not a GCI series. |
| D6 | The feature flag is `holdings`. The page uses `PlanAccessGate`. |

## 5. What Holdings is not

- A fund-accounting system or an order-management system.
- A rank of the book against prices.
- A way to give an unscored holding a provisional number for the sake of a total.

## 6. Behaviour

1. The desk pastes lines of identifier, weight, residual kind, and name, plus optional scheme rows of date and value.
2. The report returns the weighted GCI of the covered weight, the covered weight itself, and the gap list.
3. The latest saved file reloads on the next visit.
4. The disclaimer states that the figure uses published scores only and is not a recommendation.

## 7. Stories

**HO-1.** Given a book that is half a scored company and half cash, when the look-through runs, then the weighted figure uses only the scored weight and cash appears in the gaps.

**HO-2.** Given a line whose identifier has no published GCI, when the report is built, then that line is named and omitted from the weight.

**HO-3.** Given a guest opens `/holdings`, when the page loads, then the gate is shown and no file is written.

**HO-4.** Given a viewer and an analyst on the same Desk plan, when each opens `/holdings`, then the viewer sees the gate and the analyst sees the saved book.

**HO-5.** Given an analyst whose pilot term has ended, when they post a book, then the API returns 403 and the previous file is unchanged.

## 8. Index integrity

Holdings reads `gci_score_cache` and the commitment record. It does not append the score ledger.

## 9. Test plan

`backend/tests` holdings cases: unscored and residual lines stay out; org isolation holds; no GCI write.

## 10. Files

`backend/app/services/holdings.py` · `frontend/src/pages/HoldingsPage.tsx`
