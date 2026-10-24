# CiteAlpha Analyst — compliance sign-off: Skill templates and export layouts

Record of the compliance review of every CiteAlpha Analyst Skill template and export layout.
`backend/tests/test_analyst_compliance_signoff.py` fails when a Skill version or the export layout
version changes without a new row here, so nothing ships unreviewed.

Export layout version: **1.1** (Excel, PowerPoint, PDF memo, Markdown; default layout and desk house style)

## Review basis

Checked against `docs/kb/12-compliance.md`, `docs/customer/COMPLIANCE.md` and rule `public-copy-voice`:

1. No Buy / Hold / Sell, target price, rating of the stock, "signal", "outperform" or tip wording in Skill copy or fixed export copy (automated: `SKILL_COPY_BANNED`).
2. Every output sentence cites a filed source; unsupported sentences are removed by the verifier and counted in the Evidence Receipt.
3. Every export, in the default layout and in a house style, carries the disclaimer ("Factual summary of company disclosures with sources. Not investment advice."), "Data as of", the run id and the Evidence Receipt (automated).
4. Quotes are stored spans of 400 characters or less; whole documents are never redistributed (R3-35).
5. A house style changes presentation only (colours, font, logo, firm name, footer, classification, PowerPoint master); it cannot remove citations, source footers, the disclaimer or the receipt (automated).
6. No unpublished GCI appears in any Skill output, export, API or MCP response; `tools.profile` returns no number unless the score is published.
7. Each Skill states what would disprove its output (`disproof`) and an empty section says what is not on record rather than inferring.
8. Credit-rating, USFDA and offer-document Skills quote the agency, regulator or company in their own filed words; CiteAlpha adds no view.

## Skills reviewed

| Skill | Version | Reviewed | Notes |
|---|---|---|---|
| `board_scorecard` | 1.0.0 | 2026-10-17 | "Questions a board should ask" are governance questions, not investment advice |
| `company_note` | 1.0.0 | 2026-10-24 | Delivery record, open commitments, and filing quotes. The sector is the one already stored on the company. No second map, no unpublished score. |
| `company_ramp` | 1.0.0 | 2026-10-17 | |
| `concall_questions` | 1.1.0 | 2026-10-17 | Adds "What changed since the last call" (figures changed / not repeated, both quotes cited) |
| `corporate_action_brief` | 1.0.0 | 2026-10-17 | Open offer, delisting and scheme terms as filed; no view on acceptance |
| `coverage_monitor` | 1.0.0 | 2026-10-17 | |
| `debate_map` | 1.0.0 | 2026-10-17 | Voices are company / rating agency / regulator only; missing voices stated as "on record" |
| `diligence_room` | 1.0.0 | 2026-10-17 | Project-only; uploads are cited without a public link |
| `drhp_reader` | 1.0.0 | 2026-10-17 | Risks are those the company states, quoted |
| `peer_delivery_grid` | 1.0.0 | 2026-10-17 | Published GCI only, with tier |
| `rating_tracker` | 1.0.0 | 2026-10-17 | Credit-rating actions by agencies, not a rating of the stock |
| `results_prep` | 1.1.0 | 2026-10-17 | Adds "What changed since the last call" |
| `sector_note` | 1.0.0 | 2026-10-24 | Delivery inside the stored sector, beside this company's record. Published delivery only. |
| `thematic_note` | 1.0.0 | 2026-10-24 | Peers, commitments, and filing quotes under the sector already stored on the company. |
| `usfda_watch` | 1.0.0 | 2026-10-17 | Inspection outcomes as the company disclosed them |
| `weekly_driver_review` | 1.0.0 | 2026-10-17 | Project-only |

## Sign-off

- Automated gate: `test_analyst_compliance_signoff.py`, `test_analyst_agent.py::test_skill_copy_is_factual` — passing on 2026-10-17. Company, thematic, and sector notes checked against the same basis on 2026-10-24.
- Agent review (compliance-reviewer checklist): 2026-10-17. The three notes above, 2026-10-24.
- Human approver: _pending — name, role, date_. Counsel status stays pending until counsel attests; this record is not a counsel attestation.
