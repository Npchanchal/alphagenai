"""Index list refresh: parsers and the never-shrink rule, offline."""

import json

from app.jobs import refresh_index_lists as job

WIKI_HSI = """
<table class="wikitable sortable" id="constituents"><tbody>
<tr><th>Ticker</th><th>Name</th><th>Sub-index</th></tr>
<tr><td>SEHK: 5</td><td>HSBC Holdings plc</td><td>Finance</td></tr>
<tr><td>SEHK: 700</td><td>Tencent Holdings Limited [zh]</td><td>Commerce</td></tr>
</tbody></table>
"""


def test_wiki_table_rows_and_hk_tickers():
    rows = job.parse_wiki_constituents(WIKI_HSI, "Ticker", "Name", "Sub-index")
    out = [job.world_row("HK", "HSI", r) for r in rows]
    assert [(r["ticker"], r["name"], r["exchange"]) for r in out] == [
        ("0005", "HSBC Holdings plc", "HKEX"),
        ("0700", "Tencent Holdings Limited", "HKEX"),
    ]


def test_china_and_eurozone_venues():
    assert job.world_row("CN", "CSI300", {"ticker": "SZSE: 000001", "name": "Ping An Bank"})["exchange"] == "SZSE"
    sap = job.world_row("EU", "DAX", {"ticker": "SAP.DE", "name": "SAP"})
    assert (sap["ticker"], sap["exchange"]) == ("SAP", "XETRA")
    pair = job._disambiguate(
        [
            job.world_row("EU", "STOXX50", {"ticker": "SAN.MC", "name": "Banco Santander"}),
            job.world_row("EU", "STOXX50", {"ticker": "SAN.PA", "name": "Sanofi"}),
        ]
    )
    assert [r["ticker"] for r in pair] == ["SAN.MC", "SAN.PA"]
    assert all("venue_suffix" not in r for r in pair)


def test_nikkei_and_b3_parsers():
    csv = 'Date of Data,Code,Company Name,Nikkei Industrial Classification,Sector,Weight\r\n"2026/09/30","7203","TOYOTA MOTOR CORP.","Automotive","Capital Goods","1.0%"\r\n'
    assert job.parse_nikkei225_csv(csv) == [{"ticker": "7203", "name": "TOYOTA MOTOR CORP.", "sector": "Automotive"}]
    b3 = json.dumps({"results": [{"cod": "PETR4", "asset": "PETROBRAS"}, {"cod": "", "asset": "x"}]})
    assert [r["ticker"] for r in job.parse_b3_portfolio(b3)] == ["PETR4"]


def test_short_source_never_overwrites_a_market(tmp_path, monkeypatch):
    monkeypatch.setattr(job, "LISTINGS", tmp_path)
    report = job.refresh_world(["HK"], fetch=lambda url: WIKI_HSI)
    assert "not written" in report["HSI"]
    assert not (tmp_path / "hk_equity.json").exists()
