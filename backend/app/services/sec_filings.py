"""US results releases from SEC EDGAR (8-K Item 2.02, Exhibit 99).

One submissions call per company lists its 8-Ks; each results 8-K's index page
names the exhibits. Exhibit 99.1 is the press release; a second Exhibit 99 is
kept when it is CFO commentary or a results supplement. Text is stored as an
accepted filing so the same quote checks as India apply. No audio, no
transcription, no third-party transcript sites.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.data import doc_store

SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
SUBMISSIONS_PAGE = "https://data.sec.gov/submissions/{name}"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/"
INDEX_PAGE = ARCHIVE + "{acc}-index.htm"
SEC_HOSTS = ("www.sec.gov", "sec.gov", "data.sec.gov")
#: SEC asks automated clients for no more than ten requests a second.
MIN_INTERVAL_SEC = 0.15
TEXT_LIMIT = 150000
MAX_EXHIBITS_PER_FILING = 2

_LAST = 0.0


def user_agent() -> str:
    """SEC requires a name and contact address in the User-Agent."""
    return os.environ.get("INTELLENS_SEC_USER_AGENT", "").strip() or "CiteAlpha filings research ops@citealpha.com"


def is_sec_host(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in SEC_HOSTS


def _get(url: str, accept: str = "*/*") -> bytes:
    global _LAST
    if not is_sec_host(url):
        raise ValueError(f"Not an SEC host: {url}")
    wait = MIN_INTERVAL_SEC - (time.time() - _LAST)
    if wait > 0:
        time.sleep(wait)
    _LAST = time.time()
    req = Request(url, headers={"User-Agent": user_agent(), "Accept": accept, "Accept-Encoding": "identity"})
    with urlopen(req, timeout=45) as resp:  # noqa: S310 — SEC hosts only
        return resp.read()


def _results_rows(block: Dict[str, Any], since: str) -> List[Dict[str, Any]]:
    out = []
    forms = block.get("form") or []
    for i, form in enumerate(forms):
        if form not in ("8-K", "8-K/A"):
            continue
        items = str((block.get("items") or [""] * len(forms))[i] or "")
        filed = str(block["filingDate"][i])
        if "2.02" not in items or filed < since:
            continue
        out.append(
            {
                "accession": block["accessionNumber"][i],
                "date": filed,
                "form": form,
                "report_date": (block.get("reportDate") or [""] * len(forms))[i],
            }
        )
    return out


def submissions(cik: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if payload is not None:
        return payload
    raw = _get(SUBMISSIONS.format(cik=str(cik).zfill(10)), accept="application/json")
    return json.loads(raw.decode("utf-8"))


def results_filings(
    cik: str,
    *,
    since: str,
    payload: Optional[Dict[str, Any]] = None,
    pages: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Results 8-Ks filed on or after ``since``, newest first, plus the fiscal year end (MMDD)."""
    sub = submissions(cik, payload)
    recent = (sub.get("filings") or {}).get("recent") or {}
    rows = _results_rows(recent, since)
    dates = recent.get("filingDate") or []
    if dates and min(dates) > since:
        for page in (sub.get("filings") or {}).get("files") or []:
            if str(page.get("filingTo") or "") < since:
                continue
            name = str(page.get("name") or "")
            block = (pages or {}).get(name)
            if block is None and pages is None:
                block = json.loads(_get(SUBMISSIONS_PAGE.format(name=name), accept="application/json").decode("utf-8"))
            rows += _results_rows(block or {}, since)
    seen = set()
    unique = []
    for r in sorted(rows, key=lambda r: r["date"], reverse=True):
        if r["accession"] in seen:
            continue
        seen.add(r["accession"])
        unique.append(r)
    return {
        "fiscal_year_end": str(sub.get("fiscalYearEnd") or "") or None,
        "name": sub.get("name"),
        "filings": unique,
    }


_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
_HREF = re.compile(r'href="([^"]+)"', re.I)
_COMMENTARY = ("commentary", "supplement", "prepared remarks", "presentation", "outlook", "cfo")


def _clean(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).replace("&nbsp;", " ").strip()


def exhibits_from_index(html: str) -> List[Dict[str, str]]:
    """Exhibit 99 documents on a filing index page: [{type, description, url}]."""
    out = []
    for row in _ROW.findall(html or ""):
        cells = [_clean(c) for c in _CELL.findall(row)]
        hrefs = _HREF.findall(row)
        if len(cells) < 4 or not hrefs:
            continue
        kind = cells[3].upper()
        if not kind.startswith("EX-99"):
            continue
        href = hrefs[0]
        if href.startswith("/ix?doc="):
            href = href[len("/ix?doc=") :]
        url = href if href.startswith("http") else f"https://www.sec.gov{href}"
        if not url.lower().endswith((".htm", ".html", ".txt")):
            continue
        out.append({"type": kind, "description": cells[1], "url": url})
    return out


def pick_exhibits(exhibits: List[Dict[str, str]]) -> List[Dict[str, str]]:
    first = [e for e in exhibits if e["type"] in ("EX-99.1", "EX-99")]
    rest = [
        e
        for e in exhibits
        if e not in first and any(c in e["description"].lower() for c in _COMMENTARY)
    ]
    return (first[:1] + rest)[:MAX_EXHIBITS_PER_FILING] or exhibits[:1]


def exhibit_text(payload: bytes) -> str:
    from app.services.exchange_filings import extract_html_text

    return re.sub(r"\s+", " ", extract_html_text(payload, limit=TEXT_LIMIT)).strip()


def _stored_urls(company_id: str) -> set:
    return {
        doc_store.url_key(d["url"])
        for d in doc_store.list_documents(company_id=company_id, include_rejected=True, hydrate=False)
        if d.get("url")
    }


def ingest_company(
    company_id: str,
    cik: str,
    *,
    ticker: str = "",
    since: str = "2022-01-01",
    max_filings: Optional[int] = None,
    listing: Optional[Dict[str, Any]] = None,
    fetch: Optional[Callable[[str], bytes]] = None,
) -> Dict[str, Any]:
    """Store every results release filed since ``since``. Returns counts and the fiscal year end.

    ``listing`` / ``fetch`` replace the network in tests.
    """
    get = fetch or _get
    listing = listing if listing is not None else results_filings(cik, since=since)
    filings = listing["filings"][:max_filings] if max_filings else listing["filings"]
    stored = _stored_urls(company_id)
    added = already = failed = 0
    cik_int = str(int(str(cik)))
    for f in filings:
        acc = f["accession"]
        index_url = INDEX_PAGE.format(cik_int=cik_int, acc_nodash=acc.replace("-", ""), acc=acc)
        try:
            page = get(index_url).decode("utf-8", errors="ignore")
            picked = pick_exhibits(exhibits_from_index(page))
        except Exception:  # noqa: BLE001 — one filing must not stop the company
            failed += 1
            continue
        for ex in picked:
            if doc_store.url_key(ex["url"]) in stored:
                already += 1
                continue
            try:
                text = exhibit_text(get(ex["url"]))
            except Exception:  # noqa: BLE001
                failed += 1
                continue
            if len(text) < 200:
                continue
            doc_store.upsert_document(
                company_id=company_id,
                doc_type="results_release",
                title=f"{ticker or company_id.upper()} results release, {f['date']} ({ex['type']})",
                text=text,
                url=ex["url"],
                date=f["date"],
                source="sec_filing",
                review_status="accepted",
                persist=False,
            )
            stored.add(doc_store.url_key(ex["url"]))
            added += 1
    if added:
        doc_store.save()
    return {
        "company_id": company_id,
        "results_filings": len(filings),
        "added": added,
        "already_stored": already,
        "failed": failed,
        "fiscal_year_end": listing.get("fiscal_year_end"),
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
