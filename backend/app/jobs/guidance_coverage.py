"""How much of an index has cited explicit guidance in CiteAlpha's data (plan A0).

    python -m app.jobs.guidance_coverage [--index NIFTY50] [--json]

This is a lower bound on how many companies guide: it counts what has been
labelled and cited, not every statement a company has made.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict


def _cited(outcome: Any) -> bool:
    quote = getattr(outcome, "guidance_quote", None) or (outcome.get("guidance_quote") if isinstance(outcome, dict) else None)
    url = getattr(outcome, "guidance_source_url", None) or (
        outcome.get("guidance_source_url") if isinstance(outcome, dict) else None
    )
    return bool(quote and url)


def _matched(outcome: Any) -> bool:
    if not _cited(outcome):
        return False
    if isinstance(outcome, dict):
        actual, span, url = outcome.get("actual_value"), outcome.get("quote_span"), outcome.get("source_url")
    else:
        actual, span, url = outcome.actual_value, outcome.quote_span, outcome.source_url
    return actual is not None and bool(span) and bool(url)


def classify_member(
    *,
    company_id: str,
    in_dataset: bool,
    outcomes: Any = (),
    data_quality: str = "",
    gci_score: Any = None,
    confidence_tier: Any = None,
    accepted_commitments: int = 0,
) -> Dict[str, Any]:
    """One index member. A commitment is not guidance. A promise without an actual is not matched."""
    cited = [o for o in outcomes or [] if _cited(o)]
    matched = [o for o in cited if _matched(o)]
    quality = (data_quality or "").lower()
    published = quality == "hand_labeled" and gci_score is not None
    provisional_only = quality == "extracted_verified" and bool(matched) and not published
    below = bool(matched) and confidence_tier not in ("established", "deep")
    return {
        "company_id": company_id,
        "in_dataset": in_dataset,
        "data_quality": data_quality or None,
        "cited_guidance_rows": len(cited),
        "cited_guidance_metrics": len(
            {
                (o.get("metric") if isinstance(o, dict) else o.metric)
                for o in cited
            }
        ),
        "matched_actual_rows": len(matched),
        "published_gci": published,
        "provisional_only": provisional_only,
        "below_established": below,
        "accepted_commitments": accepted_commitments,
    }


def rollup(index_id: str, rows: list) -> Dict[str, Any]:
    with_guidance = [r["company_id"] for r in rows if r.get("cited_guidance_rows")]
    with_matched = [r["company_id"] for r in rows if r.get("matched_actual_rows")]
    provisional = [r["company_id"] for r in rows if r.get("provisional_only")]
    below = [r["company_id"] for r in rows if r.get("below_established")]
    with_commitments = sum(1 for r in rows if r.get("accepted_commitments"))
    return {
        "index": index_id,
        "members": len(rows),
        "with_cited_guidance": len(with_guidance),
        "with_matched_actual": len(with_matched),
        "with_published_gci": sum(1 for r in rows if r.get("published_gci")),
        "with_accepted_commitments": with_commitments,
        "provisional_only": len(provisional),
        "with_any_delivery_record": sum(
            1 for r in rows if r.get("cited_guidance_rows") or r.get("accepted_commitments")
        ),
        "without_cited_guidance": [r["company_id"] for r in rows if not r.get("cited_guidance_rows")],
        "provisional_only_ids": provisional,
        "matched_below_established": below,
        "rows": rows,
    }


def measure(index_id: str = "NIFTY50") -> Dict[str, Any]:
    from app.data.india_listings import india_index_members
    from app.services import commitment_store, repository

    rows = []
    for m in india_index_members(index_id):
        cid = m["id"]
        try:
            d = repository.get_company_gci(cid)
        except Exception:
            rows.append(classify_member(company_id=cid, in_dataset=False))
            continue
        rows.append(
            classify_member(
                company_id=cid,
                in_dataset=True,
                outcomes=d.outcomes,
                data_quality=d.data_quality or "",
                gci_score=d.gci_score,
                confidence_tier=getattr(d, "confidence_tier", None),
                accepted_commitments=len(commitment_store.list_commitments(cid)),
            )
        )
    return rollup(index_id, rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="NIFTY50")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    res = measure(args.index)
    if args.json:
        print(json.dumps(res, indent=2))
        return
    print(
        f"{res['index']}: {res['members']} members · cited guidance {res['with_cited_guidance']} · "
        f"matched actual {res['with_matched_actual']} · published GCI {res['with_published_gci']} · "
        f"accepted commitments {res['with_accepted_commitments']} · "
        f"provisional-only {res['provisional_only']}"
    )
    print("Provisional only:", ", ".join(res["provisional_only_ids"]) or "none")
    print("Matched below established:", ", ".join(res["matched_below_established"]) or "none")
    print("No cited guidance:", ", ".join(res["without_cited_guidance"]) or "none")


if __name__ == "__main__":
    main()
