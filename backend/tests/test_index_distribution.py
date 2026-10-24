"""W9.2 parquet + checksum, W9.6 weekly ledger digest."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.jobs import publish_index_files as pub
from app.main import app
from app.services.ledger_digest import score_moves, send_weekly

client = TestClient(app)


def test_publish_writes_parquet_checksum_and_optional_s3(tmp_path, monkeypatch):
    monkeypatch.setattr(pub, "INDEX_DIR", tmp_path)
    monkeypatch.delenv("INTELLENS_DATA_DIR", raising=False)
    uploaded: dict = {}

    def _fake_upload(paths):
        uploaded["names"] = [p.name for p in paths]
        return {"status": "uploaded", "bucket": "test-bucket", "keys": uploaded["names"]}

    monkeypatch.setenv("INTELLENS_INDEX_S3_BUCKET", "test-bucket")
    monkeypatch.setattr(pub, "upload_to_s3", _fake_upload)
    meta = pub.publish(as_of="20260929")
    csv_path = tmp_path / "gci_levels_20260929.csv"
    parquet_path = tmp_path / "gci_levels_20260929.parquet"
    assert csv_path.is_file()
    assert parquet_path.read_bytes()[:4] == b"PAR1"
    assert parquet_path.read_bytes()[-4:] == b"PAR1"
    assert meta["sha256"]
    assert meta["parquet_sha256"]
    assert meta["s3"]["status"] == "uploaded"
    assert "gci_levels_20260929.parquet" in uploaded["names"]
    listed = pub.list_files()
    assert listed[-1]["parquet_sha256"] == meta["parquet_sha256"]


def test_index_file_download_and_digest_preview():
    files = client.get("/api/v1/index/files").json()["files"]
    name = files[-1]["name"]
    got = client.get(f"/api/v1/index/files/{name}")
    assert got.status_code == 200
    assert "company_id" in got.text.splitlines()[0]
    missing = client.get("/api/v1/index/files/gci_levels_19990101.csv")
    assert missing.status_code == 404
    digest = client.get("/api/v1/index/digest")
    assert digest.status_code == 200
    body = digest.json()
    assert "move_count" in body
    assert "CiteAlpha GCI" in body["body"]
    assert "recipients" not in body


def test_score_moves_skip_unchanged_snapshots():
    rows = [
        {
            "company_id": "infy",
            "as_of": "2026-09-01",
            "gci": 76.5,
            "prior_gci": 88.2,
            "reason": "methodology",
            "confidence_tier": "provisional",
        },
        {
            "company_id": "infy",
            "as_of": "2026-09-28",
            "gci": 76.5,
            "prior_gci": 76.5,
            "reason": "snapshot",
            "confidence_tier": "provisional",
        },
        {
            "company_id": "cipla",
            "as_of": "2026-09-28",
            "gci": 65.5,
            "prior_gci": 85.2,
            "reason": "methodology",
            "confidence_tier": "provisional",
        },
    ]
    rows.append(
        {
            "company_id": "tcs",
            "as_of": "2026-09-28",
            "gci": 100.0,
            "prior_gci": 100.0,
            "reason": "methodology",
            "confidence_tier": "provisional",
        }
    )
    rows.append(
        {
            "company_id": "trent",
            "as_of": "2026-09-28",
            "gci": None,
            "prior_gci": 89.9,
            "reason": "methodology",
            "confidence_tier": None,
        }
    )
    moves = score_moves(rows, since="2026-09-20")
    assert [m["company_id"] for m in moves] == ["cipla", "trent"]


def test_weekly_digest_sends_when_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("INTELLENS_LEDGER_DIGEST_TO", "licensee@example.com")
    sent = {}

    def _mail(*, to, subject, body):
        sent["to"] = to
        sent["subject"] = subject
        sent["body"] = body
        return {"status": "stubbed", "to": to}

    monkeypatch.setattr("app.services.mailer.send_mail", _mail)
    from datetime import date, timedelta

    rows = [
        {
            "company_id": "infy",
            "as_of": (date.today() - timedelta(days=2)).isoformat(),
            "gci": 76.5,
            "prior_gci": 88.2,
            "reason": "methodology",
            "confidence_tier": "provisional",
        }
    ]
    first = send_weekly(force=True, rows=rows)
    assert first["status"] == "sent"
    assert sent["to"] == "licensee@example.com"
    assert "76.5" in sent["body"]
    second = send_weekly(force=False, rows=rows)
    assert second["status"] == "already_sent"
    assert Path(tmp_path / "ledger_digest_stamp.json").is_file()
