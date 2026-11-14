"""Long filing text lives in per-document files when a data dir is set."""

from __future__ import annotations

import json

import pytest

from app.data import doc_store


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("INTELLENS_DATA_DIR", str(tmp_path))
    doc_store._DOCS = {"documents": [], "versions": []}
    doc_store._TEXT_CACHE.clear()
    yield tmp_path
    doc_store._DOCS = None
    doc_store._TEXT_CACHE.clear()


def _long(tag: str) -> str:
    return (f"{tag} management guided revenue growth of 12 to 14 percent. " * 200).strip()


def test_long_text_is_stored_outside_documents_json(_data_dir):
    text = _long("Alpha")
    doc = doc_store.upsert_document(
        company_id="fix_a", doc_type="concall", title="t", text=text, source="exchange_filing"
    )
    assert doc["text"] == text
    meta = json.loads((_data_dir / "documents.json").read_text())["documents"][0]
    assert meta["text_file"] and len(meta["text"]) == doc_store.PREVIEW_CHARS
    assert (_data_dir / "doc_text" / meta["text_file"]).read_text() == text


def test_company_reads_full_text_corpus_reads_preview():
    text = _long("Beta")
    doc_store.upsert_document(company_id="fix_b", doc_type="concall", title="t", text=text)
    doc_store._TEXT_CACHE.clear()
    assert doc_store.list_documents(company_id="fix_b")[0]["text"] == text
    assert len(doc_store.list_documents()[0]["text"]) == doc_store.PREVIEW_CHARS
    doc_id = doc_store.list_documents()[0]["doc_id"]
    assert doc_store.get_document(doc_id)["text"] == text
    assert doc_store.set_review_status(doc_id, "accepted")["text"] == text


def test_inline_overlay_migrates_on_load(_data_dir):
    text = _long("Gamma")
    inline = {
        "documents": [
            {
                "doc_id": "d1",
                "company_id": "fix_c",
                "doc_type": "concall",
                "title": "t",
                "text": text,
                "content_hash": doc_store.content_hash(text),
                "review_status": "accepted",
            }
        ],
        "versions": [],
    }
    (_data_dir / "documents.json").write_text(json.dumps(inline))
    doc_store._DOCS = None
    assert doc_store.get_document("d1")["text"] == text
    saved = json.loads((_data_dir / "documents.json").read_text())["documents"][0]
    assert saved["text_file"] and len(saved["text"]) == doc_store.PREVIEW_CHARS


def test_short_text_stays_inline(_data_dir):
    doc_store.upsert_document(company_id="fix_d", doc_type="note", title="t", text="short note text")
    meta = json.loads((_data_dir / "documents.json").read_text())["documents"][0]
    assert "text_file" not in meta and meta["text"] == "short note text"


def test_lookups_follow_upserts_patches_and_a_replaced_store():
    url = "https://www.bseindia.com/xml-data/corpfiling/AttachLive/q4.pdf"
    assert doc_store.find_by_url(url) is None and doc_store.stored_preview(url) is None
    doc = doc_store.upsert_document(company_id="fix_e", doc_type="concall", title="t", text="cover letter", url=url)
    again = doc_store.upsert_document(company_id="fix_e", doc_type="concall", title="t", text="cover letter")
    assert again["doc_id"] == doc["doc_id"]
    assert doc_store.find_by_url("http://bseindia.com/xml-data/corpfiling/AttachLive/q4.pdf?utm_source=x")["doc_id"] == doc["doc_id"]
    assert doc_store.find_by_hash(doc["content_hash"])["doc_id"] == doc["doc_id"]
    assert doc_store.stored_preview(url) == "cover letter"
    long_url = "https://www.nseindia.com/long.pdf"
    doc_store.upsert_document(company_id="fix_e", doc_type="concall", title="t", text=_long("Delta"), url=long_url)
    assert doc_store.stored_preview(long_url) == ""
    moved = "https://www.bseindia.com/xml-data/corpfiling/AttachLive/moved.pdf"
    doc_store.patch_document(doc["doc_id"], url=moved)
    assert doc_store.find_by_url(moved)["doc_id"] == doc["doc_id"]
    doc_store._DOCS = {"documents": [], "versions": []}
    assert doc_store.find_by_url(moved) is None and doc_store.find_by_hash(doc["content_hash"]) is None
