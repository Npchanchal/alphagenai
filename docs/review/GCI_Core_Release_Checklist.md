# GCI Core — release checklist and policies (non-code items)

**Owner:** Index steward · **Date:** 10 Nov 2026 · **Applies to:** any GCI Core ruleset (`v2.4`, `delivery`, `v2.5-proposal`) before a level is published.

Gate numbers follow PRD §19. `GET /api/v1/index/core/{id}/readiness` (`validation_gates.core_release_gates`) checks every gate:

| Gate | Checked by | Pass rule |
|---|---|---|
| G-01 Methodology approved | code + [methodology sign-off](#methodology) | `CORE_ENGINE_APPROVED = True`, set the same day as the ledger snapshot and changelog row |
| G-02 Engine validated | code | Two runs give the same input digest and level; golden tests §24.1–§24.10 pass |
| G-03 Data coverage adequate | code | At least 60% of numeric figures compute (O-02); tier `established` or `deep` |
| G-04 Reviewer workflow complete | code | No row awaiting review, promise citation or quote check |
| G-05 … G-08 | a person, below | An admin records each one: `POST /api/v1/index/release-signoffs {"gate_id": "G-06", "note": "…"}` |

A publication request (`POST /api/v1/index/core/{id}/publication-requests`) freezes the calculation as a snapshot. A second `labeling` seat decides. Approval writes the ledger only when every gate has passed; otherwise the request is recorded as `blocked` with the open gates. Every request, decision and sign-off is on the audit log.

## Methodology

Part of **G-01**. Covers GAP-26, GAP-27, GAP-30. Reduced to fit the team's size.

- [ ] **Methodology owner plus one independent reviewer** (not a three-committee structure yet). Both sign the methodology version, the default ruleset (`CORE_DEFAULT_RULESET`), and every change to a Core constant. The record is the methodology changelog row.
- [ ] **Pre-registered research.** Before a calibration (composite weights, growth floor, companion constants), write down the dataset version, the rows in and out, the parameter grid, any random seeds, and the decision rule. Results that were not pre-registered are labelled exploratory and change no constant.
- [ ] **Index readiness.** An index product (licensed levels, benchmark use) is a separate launch with its own gate: established tier for every constituent, a published methodology, a correction policy, and a named calculation agent. Until then the Public Snapshot is research, not a benchmark.
- [ ] **Issuer firewall (GAP-25).** Issuers get read access to their own dossier and evidence and raise corrections through the same evidence process as anyone else: a filing link and a quote. No paid service changes a level, a tier or a review outcome. Sales and IR relationships stay out of the review queue.

## Security

Gate **G-05**. Covers SEC-03, SEC-06.

- [ ] Backups scheduled and a restore tested on a copy (go-live checklist row B8); restore time recorded. The ledger and `calc_snapshots/` are included.
- [ ] Encryption at rest for the data volume and in transit at the load balancer (go-live section C).
- [ ] Secrets in the secrets manager, rotated; API keys appear only as hashes in logs (`_actor_label`).
- [ ] Dependency and container scan clean of high-severity findings; an external penetration test before the first paying index licence.
- [ ] Audit log: publication, sign-off, label-accept and seat-change events are never trimmed; other events keep the last 1,000–2,000. Export the file daily to durable storage before an index launch.
- [ ] Certification (SOC 2 or ISO 27001) is scheduled when a licensee requires it; not a launch blocker for pilots.

## Legal

Gate **G-06**. Covers GAP-23, GAP-24, D-13, D-14, D-27.

- [ ] Written opinion on the words used externally for the index and its outputs: "index", "score", "rating", "ranking", "grade". Until it is in hand, public copy keeps the current GCI wording and adds no new ranked surface.
- [ ] Opinion on whether a ranked list of issuers, or a numeric level per issuer, is research or a rating under the SEBI (Research Analysts) and (Credit Rating Agencies) Regulations. Retail Buy/Hold/Sell stays out.
- [ ] Terms, privacy and disclaimer approved (go-live row E1; attest with `kind=terms_privacy`).
- [ ] Wording for the delivery ruleset and the companion indexes approved before either appears outside the Workbench.
- [ ] **Data rights register** per market: source (NSE, BSE, issuer IR, EDGAR, other exchanges), licence or terms of use, whether quoting a sentence is allowed, whether bulk redistribution is allowed, renewal date. Quotes shown publicly stay within the most restrictive terms for that market. Bulk endpoints (`/api/v1/index/core/bulk`, frozen level files) are licensed per customer and name the markets included. A market without a register row stays `shadow` or `diagnostic_only`.

## API docs

Gate **G-07**.

- [ ] Every Core route in `docs/kb/05-api-map.md` and the OpenAPI schema, with field meanings: `algorithm_id`, `ruleset`, `family_id`, `vintage_id`, `record_state`, `coverage`, `uncertainty`, reason codes.
- [ ] A worked example per ruleset (locked, delivery, proposal) using a published company.

## Support

Gate **G-08**.

- [ ] A named contact and a response time for data-correction requests, published with the methodology.
- [ ] Corrections follow the evidence process: a filing link and a quote, reviewed by a second person, written to the ledger as `data_correction` with a changelog row the same day.

## What the code already enforces

| Item | Where |
|---|---|
| Two-person publication | `score_ledger.decide_publication` refuses the requester as approver |
| Append-only ledger, content-addressed snapshots, replay | `score_ledger.append`, `snapshot_payload`, `replay_snapshot` |
| Audit events: review, export, seat change, recalculation, ledger write, publication, sign-off | `data/audit_log.py` |
| Re-runs cannot add revisions | `gci_scoring._vintages` |
| Route change at the same level writes a snapshot row | `score_ledger._routes_changed` |
| Same-day conflicting statements | `disclosures.statement_precedence`; review queue item |
| Withdrawal, reinstatement, deadline extension, basis switch, thin history | `guidance_profile.guidance_diagnostics` |
