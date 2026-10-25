# CiteAlpha product requirements

**Product:** CiteAlpha · **Legal entity:** Ocotillo Innovation Private Limited  
**Date:** 2026-10-25

Each file specifies one job a desk can do. The first requirement in every file is the person on the page: what they came to learn, what they see in one glance, the words on the screen, and what the page does when the record is missing, still loading, or closed to them. Administration is already specified in [`docs/PRD_ADMIN.md`](../PRD_ADMIN.md). These documents describe what ships. They do not open a second product for a job that already has an owner.

Write the requirements the way you would brief a designer who has sat with a Head of Research. Name the company, the figure, and the sentence on the screen. A role table is there so an engineer can enforce it. It comes after the person, because a correct 403 on a confusing page is still a failed page.

| Job | Route | PRD |
|---|---|---|
| Homepage | `/` | [PRD_HOMEPAGE.md](PRD_HOMEPAGE.md) |
| GCI Screener | `/tracker` | [PRD_SCREENER.md](PRD_SCREENER.md) |
| Company dossier | `/companies/:id` | [PRD_DOSSIER.md](PRD_DOSSIER.md) |
| Public Snapshot | `/rankings` | [PRD_SNAPSHOT.md](PRD_SNAPSHOT.md) |
| Filing Search | `/research` | [PRD_FILING_SEARCH.md](PRD_FILING_SEARCH.md) |
| CiteAlpha Analyst | `/analyst` | [PRD_ANALYST.md](PRD_ANALYST.md) |
| Analyst Workbench | `/desk` | [PRD_WORKBENCH.md](PRD_WORKBENCH.md) |
| Disclosure Explorer | `/sights` | [PRD_SIGHTS.md](PRD_SIGHTS.md) |
| Holdings | `/holdings` | [PRD_HOLDINGS.md](PRD_HOLDINGS.md) |
| Financial Ninja | `/ninja` | [PRD_NINJA.md](PRD_NINJA.md) |
| Workflows | `/workflows` | [PRD_WORKFLOWS.md](PRD_WORKFLOWS.md) |
| Plans and evaluation | `/products`, `/pilot` | [PRD_COMMERCIAL.md](PRD_COMMERCIAL.md) |
| Methodology, changelog, company, trust | `/methodology`, `/changelog`, `/about`, `/trust` | [PRD_INDEX_RECORD.md](PRD_INDEX_RECORD.md) |
| Administration | `/admin`, `/org/settings` | [PRD_ADMIN.md](../PRD_ADMIN.md) |

[PRD_TERMINAL.md](PRD_TERMINAL.md) is the confirmed pass over the screener, the dossier, the source viewer, and the header (25 October 2026). It extends the rows above. It does not replace them, and it is not a description of what already ships.

## Rules that apply to every PRD

- A published GCI is a number in the score cache. A row enters that number only when both the guidance quote and the later reported quote are on the cited filings.
- Confidence tiers are `provisional`, `established`, and `deep`. A public rank uses `established` and `deep` only.
- No surface issues Buy, Hold, or Sell. No surface sells sentiment as the score.
- Guests receive the feature `tracker` only. Other jobs stay behind plan ∩ role.
- A monitor, an upload, a worksheet, or a holdings file does not write a published GCI.
- Public copy uses the canonical names above. Metric ids stay out of the page.

## Seat model

Effective access is the intersection of the organisation’s plan and the seat’s role. A role never adds a feature the plan left out. `admin` and `owner` may use every feature that plan includes. A platform `super` who belongs to an organisation also receives the Desk plan’s features on the server. A super with no organisation remains a guest on the server. The page gate treats every super as open, so a super with no organisation still has to pass the API. Platform `ops`, `compliance`, `billing`, and `support` receive no extra product features. Their menus are specified in [`docs/PRD_ADMIN.md`](../PRD_ADMIN.md).

When an approved pilot term ends, that organisation’s features fall back to `tracker`. The seat role stays as it was. Retail is not sold. If a retail plan is present, its features are `tracker`, `research`, and `read_api` only.

| Role | May use, still limited by the plan |
|---|---|
| Guest, and anyone signed out | `tracker`. Fifteen dossier opens. Eight filing searches, and only on companies with a published GCI |
| `viewer`, `member` | `tracker`, `research`, `read_api`, `feedback` |
| `labeler` | The viewer set, plus `desk` (read the workbench) and `labeling` |
| `analyst` | Cite-only chat, Disclosure Explorer ask, CiteAlpha Analyst, workbench write, word map, holdings, Financial Ninja, alerts, vernacular, IC export, experimental analytics, and the badge. Not labeling |
| `reviewer` | The analyst set, plus `labeling`. Accepting or closing a commitment also requires this role |
| `admin`, `owner` | Every feature on the plan, including data-file export and SSO where the plan has them. Appointing seats is the admin document. Analyst keys, delivery destinations, and house style are this pair only |

`member` and `viewer` carry the same features. Each PRD below states which of these roles may perform each action on that route, and which refusal the server returns. Hiding a control is presentation. A direct call without the feature returns 403 and does not write.
