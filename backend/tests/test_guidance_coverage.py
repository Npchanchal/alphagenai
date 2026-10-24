"""Whitespace scoreboard: cited guidance, matched actuals, published GCI. No network."""

from types import SimpleNamespace

from app.jobs.guidance_coverage import classify_member, rollup


def test_matched_requires_actual_citation_and_commitment_is_not_guidance():
    promise = SimpleNamespace(
        guidance_quote="We expect revenue growth of 10% to 12%.",
        guidance_source_url="https://example.test/promise",
        actual_value=None,
        quote_span=None,
        source_url=None,
        metric="revenue_growth_pct",
    )
    closed = SimpleNamespace(
        guidance_quote="We expect revenue growth of 10% to 12%.",
        guidance_source_url="https://example.test/promise",
        actual_value=11.0,
        quote_span="Revenue growth was 11.0%.",
        source_url="https://example.test/actual",
        metric="revenue_growth_pct",
    )
    open_only = classify_member(
        company_id="open_co",
        in_dataset=True,
        outcomes=[promise],
        data_quality="extracted_verified",
        gci_score=70,
        confidence_tier="provisional",
        accepted_commitments=2,
    )
    assert open_only["cited_guidance_rows"] == 1
    assert open_only["matched_actual_rows"] == 0
    assert open_only["provisional_only"] is False
    assert open_only["accepted_commitments"] == 2

    matched = classify_member(
        company_id="matched_co",
        in_dataset=True,
        outcomes=[closed],
        data_quality="extracted_verified",
        gci_score=70,
        confidence_tier="provisional",
        accepted_commitments=0,
    )
    assert matched["matched_actual_rows"] == 1
    assert matched["provisional_only"] is True
    assert matched["published_gci"] is False
    assert matched["below_established"] is True

    published = classify_member(
        company_id="pub_co",
        in_dataset=True,
        outcomes=[closed],
        data_quality="hand_labeled",
        gci_score=80,
        confidence_tier="established",
        accepted_commitments=0,
    )
    assert published["published_gci"] is True
    assert published["provisional_only"] is False
    assert published["below_established"] is False

    summary = rollup("SENSEX", [open_only, matched, published])
    assert summary["with_cited_guidance"] == 3
    assert summary["with_matched_actual"] == 2
    assert summary["with_published_gci"] == 1
    assert summary["provisional_only"] == 1
    assert summary["with_accepted_commitments"] == 1
    assert summary["provisional_only_ids"] == ["matched_co"]
    assert "open_co" not in summary["matched_below_established"]
