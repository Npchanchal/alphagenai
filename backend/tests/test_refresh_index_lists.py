"""Index list refresh: parsers and the never-shrink rule, offline."""

import json

import pytest

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


NSE_EQUITY = (
    "SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE\n"
    "HEGAM,HEG Limited,EQ,05-JAN-1995,10,1,INE545A01024,2\n"
    "20MICRONS,20 Microns Limited,EQ,06-OCT-2008,5,1,INE144J01027,5\n"
)


def test_nse_equity_rows_and_renamed_symbol_keeps_its_id():
    rows = job.parse_nse_equity_csv(NSE_EQUITY)
    assert rows[0] == {"symbol": "HEGAM", "name": "HEG Limited", "series": "EQ", "isin": "INE545A01024"}
    previous = [
        {"symbol": "HEG", "isin": "INE545A01024"},
        {"symbol": "20MICRONS", "isin": "INE144J01027"},
    ]
    assert job.carry_id_symbols(rows, previous) == 1
    assert rows[0]["id_symbol"] == "HEG" and "id_symbol" not in rows[1]
    again = job.parse_nse_equity_csv(NSE_EQUITY.replace("HEGAM", "HEGNEW"))
    job.carry_id_symbols(again, rows)
    assert again[0]["id_symbol"] == "HEG"


def test_short_nse_lists_are_not_written(tmp_path, monkeypatch):
    monkeypatch.setattr(job, "LISTINGS", tmp_path)
    with pytest.raises(RuntimeError, match="short"):
        job.refresh_nse_equity(NSE_EQUITY)
    assert not (tmp_path / "nse_equity.json").exists()
    short = "Company Name,Industry,Symbol,Series,ISIN Code\nHDFC Bank,Financial Services,HDFCBANK,EQ,INE040A01034\n"
    with pytest.raises(RuntimeError, match="NIFTY50"):
        job.refresh_nse_indexes(fetch=lambda url: short)
    assert not (tmp_path / "nse_indexes.json").exists()


def test_amfi_periods_roll_at_half_year():
    assert job.amfi_periods("2026-11-11") == ["30Jun2026", "31Dec2025"]
    assert job.amfi_periods("2027-01-05") == ["31Dec2026", "30Jun2026"]


def _amfi_book(rows):
    import io

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["Average Market Capitalization of listed companies during the six months ended 30 June 2026"])
    ws.append([
        "Sr. No.", "Company name", "ISIN", "BSE Symbol", "BSE 6 month Avg Total Market Cap in (Rs. Crs.)",
        "NSE Symbol", "NSE 6 month Avg Total Market Cap (Rs. Crs.)", "MSEI Symbol",
        "MSEI 6 month Avg Total Market Cap in (Rs Crs.)", "Average of All Exchanges (Rs. Cr.)",
        "Categorization as per SEBI Circular dated Oct 6, 2017",
    ])
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_amfi_rows_and_short_file_refused(tmp_path, monkeypatch):
    book = _amfi_book([
        [1, "Reliance Industries Ltd", "INE002A01018", "RELIANCE", 10.0, "RELIANCE", 10.0, "-", None, 10.0, "Large Cap"],
        [2, "BSE Only Ltd", "INE999Z01011", "BSEONLY", 1.5, "-", None, "-", None, 1.5, "Small Cap"],
    ])
    rows = job.parse_amfi_xlsx(book)
    assert rows[1] == {
        "rank": 2, "name": "BSE Only Ltd", "isin": "INE999Z01011", "bse_symbol": "BSEONLY",
        "nse_symbol": None, "avg_mcap_cr": 1.5, "category": "Small Cap",
    }
    monkeypatch.setattr(job, "LISTINGS", tmp_path)
    with pytest.raises(RuntimeError, match="short"):
        job.refresh_amfi(book, period="30Jun2026")
    assert not (tmp_path / "amfi_mcap.json").exists()


def test_amfi_falls_back_to_the_previous_half_year(tmp_path, monkeypatch):
    from urllib.error import HTTPError

    monkeypatch.setattr(job, "LISTINGS", tmp_path)
    tried = []

    def fetch(url):
        tried.append(url)
        raise HTTPError(url, 404, "Not Found", {}, None)

    with pytest.raises(RuntimeError, match="not found"):
        job.refresh_amfi(fetch=fetch)
    assert len(tried) == 2 and all("portal.amfiindia.com" in u for u in tried)
