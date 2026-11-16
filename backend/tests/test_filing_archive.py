"""Stored filings copied to the per-exchange S3 buckets, and the platform-admin archive browser."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.data import doc_store
from app.main import app
from app.services import filing_archive

client = TestClient(app)
ADMIN = {"X-API-Key": "intellens-admin"}
PDF = b"%PDF-1.4 results for the quarter"


class FakeS3:
    def __init__(self) -> None:
        self.objects: dict = {}

    def put_object(self, *, Bucket, Key, Body, ContentType, Metadata):  # noqa: N803 — boto3 names
        assert all(v.isascii() for v in Metadata.values())
        self.objects[(Bucket, Key)] = {"body": Body, "type": ContentType, "meta": Metadata}

    def get_object(self, *, Bucket, Key):  # noqa: N803
        body = self.objects[(Bucket, Key)]["body"]

        class _Stream:
            def read(self_inner):
                return body

        return {"Body": _Stream()}


@pytest.fixture(autouse=True)
def _store(tmp_path, monkeypatch):
    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    for ex in ("NSE", "BSE", "INTL"):
        monkeypatch.setenv(f"INTELLENS_FILING_S3_{ex}", f"test-filings-{ex.lower()}")
    doc_store._DOCS = {"documents": [], "versions": []}
    doc_store._TEXT_CACHE.clear()
    filing_archive.reset_ledger()
    yield tmp_path
    doc_store._DOCS = None
    doc_store._TEXT_CACHE.clear()
    filing_archive.reset_ledger()


def _seed() -> dict:
    nse = doc_store.upsert_document(
        company_id="infy", doc_type="concall", title="Q2 FY26 earnings call — Café",
        text="Management guided revenue growth of 3 to 5 percent in constant currency. " * 100,
        url="https://nsearchives.nseindia.com/corporate/INFY_q2.pdf", date="2025-10-17",
        raw_bytes=PDF, review_status="accepted",
    )
    bse = doc_store.upsert_document(
        company_id="infy", doc_type="results", title="Outcome of board meeting",
        text="Revenue for the quarter rose 8.6 percent year on year.",
        url="https://www.bseindia.com/xml-data/corpfiling/AttachLive/infy.pdf", date="2025-10-16",
    )
    us = doc_store.upsert_document(
        company_id="us_aapl", doc_type="results_release", title="Apple 8-K exhibit 99.1",
        text="Apple reported quarterly revenue of 94.9 billion dollars.",
        url="https://www.sec.gov/Archives/edgar/data/320193/ex99.htm", date="2025-10-30",
    )
    seeded = doc_store.upsert_document(
        company_id="infy", doc_type="guidance", title="FY26 revenue", text="seeded outcome text"
    )
    return {"nse": nse, "bse": bse, "us": us, "seeded": seeded}


def test_routes_each_filing_to_its_exchange_bucket(monkeypatch):
    docs = _seed()
    assert filing_archive.exchange_for(docs["nse"]) == "nse"
    assert filing_archive.exchange_for(docs["bse"]) == "bse"
    assert filing_archive.exchange_for(docs["us"]) == "intl"
    issuer = {"company_id": "infy", "url": "https://www.infosys.com/investors/q2.pdf"}
    assert filing_archive.exchange_for(issuer) == "nse"
    monkeypatch.setattr(filing_archive, "_company", lambda cid: ("IN", "Smallcap", "SML", "BSE"))
    assert filing_archive.exchange_for({"company_id": "bse_543210", "url": "https://issuer.example/ar.pdf"}) == "bse"


def test_seeded_outcome_text_and_sample_concalls_stay_out():
    docs = _seed()
    assert not filing_archive.archivable(docs["seeded"])
    assert not filing_archive.archivable({"doc_type": "transcript", "source": "sample_transcript"})
    assert not filing_archive.archivable(
        {"doc_type": "filing", "source": "ir_catalog", "url": "https://www.tcs.com/investor-relations"}
    )
    assert {d["doc_id"] for d in filing_archive.pending()} == {
        docs["nse"]["doc_id"], docs["bse"]["doc_id"], docs["us"]["doc_id"]
    }


def test_upload_writes_text_and_original_once():
    docs = _seed()
    s3 = FakeS3()
    report = filing_archive.archive_pending(client=s3)
    assert report["status"] == "ok" and report["uploaded"] == 3 and report["failed"] == 0

    nse_entry = filing_archive.archived(docs["nse"]["doc_id"])
    assert nse_entry["bucket"] == "test-filings-nse"
    assert nse_entry["text_key"].startswith("text/infy/concall/2025-10-17_")
    assert nse_entry["raw_key"].endswith(".pdf")
    text_obj = s3.objects[("test-filings-nse", nse_entry["text_key"])]
    assert text_obj["body"].decode() == docs["nse"]["text"]
    assert text_obj["meta"]["doc-id"] == docs["nse"]["doc_id"]
    assert s3.objects[("test-filings-nse", nse_entry["raw_key"])]["body"] == PDF
    assert filing_archive.archived(docs["bse"]["doc_id"])["bucket"] == "test-filings-bse"
    assert filing_archive.archived(docs["us"]["doc_id"])["bucket"] == "test-filings-intl"

    again = filing_archive.archive_pending(client=FakeS3())
    assert again["uploaded"] == 0

    filing_archive.reset_ledger()
    assert filing_archive.archived(docs["nse"]["doc_id"]) is not None


def test_archive_is_off_without_buckets(monkeypatch):
    for ex in ("NSE", "BSE", "INTL"):
        monkeypatch.delenv(f"INTELLENS_FILING_S3_{ex}")
    _seed()
    assert filing_archive.archive_pending(client=FakeS3())["status"] == "off"


def test_status_includes_pending_and_coverage(monkeypatch):
    _seed()
    monkeypatch.setattr(
        filing_archive,
        "_coverage_snapshot",
        lambda: {
            "cohort": "all",
            "cohort_size": 10,
            "lookback_reached": 3,
            "lookback_remaining": 7,
            "discovery_since": "2019-01-01",
            "extract_enabled": False,
        },
    )
    st = filing_archive.status()
    assert st["pending"] >= 1
    assert st["cron_interval_sec"] >= 300
    assert st["coverage"]["cohort"] == "all"
    assert st["coverage"]["lookback_reached"] == 3


def test_browse_filters_and_counts():
    docs = _seed()
    filing_archive.archive_pending(client=FakeS3(), limit=1)
    out = filing_archive.browse()
    assert out["total"] == 3
    assert [d["doc_id"] for d in out["documents"]][0] == docs["us"]["doc_id"]
    assert out["facets"]["exchange"] == {"nse": 1, "bse": 1, "intl": 1}
    assert out["facets"]["in_s3"] == {"yes": 1, "no": 2}

    nse_only = filing_archive.browse(exchange="nse")
    assert [d["doc_id"] for d in nse_only["documents"]] == [docs["nse"]["doc_id"]]
    assert nse_only["documents"][0]["s3_text"] is None or nse_only["documents"][0]["s3_text"].startswith("s3://")

    words = filing_archive.browse(q="constant currency")
    assert [d["doc_id"] for d in words["documents"]] == [docs["nse"]["doc_id"]]
    dated = filing_archive.browse(date_from="2025-10-17", date_to="2025-10-20")
    assert [d["doc_id"] for d in dated["documents"]] == [docs["nse"]["doc_id"]]


def test_original_comes_from_s3_when_the_volume_copy_is_gone(_store):
    docs = _seed()
    s3 = FakeS3()
    filing_archive.archive_pending(client=s3)
    (_store / "doc_raw" / docs["nse"]["raw_sha256"]).unlink()
    data, ctype, name = filing_archive.original_file(docs["nse"]["doc_id"], client_factory=lambda: s3)
    assert data == PDF and ctype == "application/pdf" and name.endswith(".pdf")
    assert filing_archive.original_file(docs["bse"]["doc_id"]) is None


def test_admin_routes_need_a_platform_role():
    docs = _seed()
    assert client.get("/api/admin/portal/filings").status_code == 401
    assert client.get("/api/admin/portal/filings", headers={"X-API-Key": "intellens-demo"}).status_code == 403

    listed = client.get("/api/admin/portal/filings", params={"exchange": "nse"}, headers=ADMIN)
    assert listed.status_code == 200
    assert listed.json()["documents"][0]["doc_id"] == docs["nse"]["doc_id"]

    one = client.get(f"/api/admin/portal/filings/{docs['nse']['doc_id']}", headers=ADMIN).json()
    assert one["text"] == docs["nse"]["text"] and one["exchange"] == "nse"

    raw = client.get(f"/api/admin/portal/filings/{docs['nse']['doc_id']}/original", headers=ADMIN)
    assert raw.status_code == 200 and raw.content == PDF
    assert raw.headers["content-type"] == "application/pdf"
    assert client.get(f"/api/admin/portal/filings/{docs['bse']['doc_id']}/original", headers=ADMIN).status_code == 404

    me = client.get("/api/admin/portal/me", headers=ADMIN).json()
    assert "filings" in {s["id"] for s in me["sections"]}
