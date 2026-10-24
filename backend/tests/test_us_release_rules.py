"""Rule reader for US results releases (8-K Ex 99.1): narrow, and silent when unsure."""

from __future__ import annotations

from app.services.us_release_rules import extract

NVDA_Q4 = (
    "NVIDIA Announces Financial Results for Fourth Quarter and Fiscal 2023. "
    "Outlook NVIDIA's outlook for the first quarter of fiscal 2024 is as follows: "
    "Revenue is expected to be $6.50 billion, plus or minus 2%. "
    "GAAP and non-GAAP gross margins are expected to be 64.1% and 66.5%, respectively, plus or minus 50 basis points."
)

NVDA_Q1 = (
    "NVIDIA (NASDAQ: NVDA) today reported revenue for the first quarter ended April 30, 2023, of $7.19 billion, "
    "down 13% from a year ago and up 19% from the previous quarter. "
)


def test_outlook_heading_gives_quarter_and_plus_minus():
    out = extract(NVDA_Q4, doc_date="2023-02-22", fy_end_mmdd="0131")
    assert out["guidance"] == [
        {
            "metric": "revenue_usd_mn",
            "period": "Q1 FY2024",
            "low": 6500.0,
            "high": 6500.0,
            "quote": "Revenue is expected to be $6.50 billion, plus or minus 2%.",
            "pm_pct": 2.0,
        }
    ]
    assert out["results"] == []


def test_reported_quarter_from_filing_date_and_fiscal_year_end():
    out = extract(NVDA_Q1, doc_date="2023-05-24", fy_end_mmdd="0131")
    assert [(r["metric"], r["period"], r["value"]) for r in out["results"]] == [
        ("revenue_usd_mn", "Q1 FY2024", 7190.0)
    ]
    assert out["guidance"] == []


def test_presentation_table_text_is_not_guidance():
    table = (
        "Metric Q3 Consolidated net sales (cc) Increase 3.25% to 4.25% Operating income (cc) Increase 3% to 6% "
        "Adjusted EPS $0.51 to $0.52 Fiscal Year 2025 Consolidated net sales Increase 4.8% to 5.1%."
    )
    assert extract(table, doc_date="2024-11-19", fy_end_mmdd="0131") == {"guidance": [], "results": []}


def test_prior_year_baseline_is_not_guidance():
    base = (
        "The Company's second quarter fiscal 2027 guidance is based on the following Q2 FY26 figures: "
        "adjusted EPS of $0.68."
    )
    assert extract(base, doc_date="2026-05-14", fy_end_mmdd="0131")["guidance"] == []


def test_eps_guidance_needs_period_in_the_sentence():
    with_period = "The company expects adjusted EPS for fiscal 2025 of $2.35 to $2.43."
    without = "The company expects adjusted EPS of $2.35 to $2.43."
    got = extract(with_period, doc_date="2024-05-16", fy_end_mmdd="0131")["guidance"]
    assert [(g["metric"], g["period"], g["low"], g["high"]) for g in got] == [
        ("eps_adjusted_usd", "FY2025", 2.35, 2.43)
    ]
    assert extract(without, doc_date="2024-05-16", fy_end_mmdd="0131")["guidance"] == []


def test_fiscal_year_before_quarter_is_a_quarter():
    s = "For the fiscal 2024 first quarter, Air Products' adjusted EPS guidance is $2.90 to $3.05."
    (g,) = extract(s, doc_date="2023-11-07", fy_end_mmdd="0930")["guidance"]
    assert (g["period"], g["low"], g["high"]) == ("Q1 FY2024", 2.9, 3.05)


def test_gaap_and_adjusted_in_one_sentence_bind_to_their_own_figures():
    g = ("Abbott issues full-year 2024 guidance for diluted EPS on a GAAP basis of $3.20 to $3.40 "
         "and full-year adjusted diluted EPS of $4.50 to $4.70.")
    a = "Full-year 2025 GAAP diluted EPS of $3.72 and adjusted diluted EPS of $5.15, which excludes specified items."
    got = extract(g, doc_date="2024-01-24", fy_end_mmdd="1231")["guidance"]
    assert sorted((x["metric"], x["low"], x["high"]) for x in got) == [
        ("eps_adjusted_usd", 4.5, 4.7), ("eps_diluted_usd", 3.2, 3.4)
    ]
    res = extract(a, doc_date="2026-01-22", fy_end_mmdd="1231")["results"]
    assert sorted((x["metric"], x["period"], x["value"]) for x in res) == [
        ("eps_adjusted_usd", "FY2025", 5.15), ("eps_diluted_usd", "FY2025", 3.72)
    ]


def test_comparison_year_is_not_the_reported_year():
    a = "GAAP diluted earnings per share were $10.77, compared to $10.71 in fiscal 2022."
    b = "GAAP diluted EPS for fiscal 2023 were $10.77 compared with $10.71 for fiscal 2022."
    assert extract(a, doc_date="2023-09-28", fy_end_mmdd="0831")["results"] == []
    (r,) = extract(b, doc_date="2023-09-28", fy_end_mmdd="0831")["results"]
    assert (r["metric"], r["period"], r["value"]) == ("eps_diluted_usd", "FY2023", 10.77)


def test_period_after_the_figure_is_the_next_heading():
    s = "EPS of $0.94, with adjusted EPS of $0.87 Full-year 2025 Key Takeaways : Adjusted EBITDA rose."
    assert extract(s, doc_date="2026-02-03", fy_end_mmdd="1231")["results"] == []


def test_bad_date_reads_nothing():
    assert extract(NVDA_Q1, doc_date="not-a-date", fy_end_mmdd="0131") == {"guidance": [], "results": []}
