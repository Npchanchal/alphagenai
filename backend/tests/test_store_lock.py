"""India and US walks share in-memory stores across threads; saves must not race writes."""

from __future__ import annotations

import threading

from app.data import doc_store
from app.data.india_listings import india_equity_universe
from app.data.seed import reset_data, save_data
from app.data.us_listings import us_equity_universe
from app.services.coverage import LISTED_ONLY, note_discovery, reset_coverage, stamp_coverage
from app.services.extract_pipeline import ensure_company_record


def test_two_walks_writing_at_once_do_not_corrupt_saves(tmp_path, monkeypatch):
    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    doc_store._DOCS = None
    reset_data()
    reset_coverage()
    india = [r["id"] for r in india_equity_universe()[:150]]
    us = [r["id"] for r in us_equity_universe()[:150]]
    errors = []

    def walk(ids, tag):
        try:
            for i, cid in enumerate(ids):
                ensure_company_record(cid)
                stamp_coverage(cid, LISTED_ONLY)
                note_discovery(cid, since="2022-01-01")
                doc_store.upsert_document(
                    company_id=cid, doc_type="results_release", title=f"{tag} {i}",
                    text=f"{tag} filing {cid} " * 40, url=f"https://example.com/{tag}/{cid}", date="2024-05-01",
                )
                if i % 10 == 0:
                    save_data()
        except Exception as exc:  # noqa: BLE001
            errors.append(repr(exc))

    threads = [threading.Thread(target=walk, args=(india, "in")), threading.Thread(target=walk, args=(us, "us"))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(120)
    assert errors == []
    assert len(doc_store.list_documents(hydrate=False)) >= len(india) + len(us)
    doc_store._DOCS = None
    reset_data()
