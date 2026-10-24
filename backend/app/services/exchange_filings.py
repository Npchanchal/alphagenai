"""BSE/NSE filing ingest — PDF/HTML text into the document store.

Does not invent quotes or scores. Fetches allowlisted exchange URLs (and an
issuer's own IR host for that issuer only), extracts text, and upserts
documents. Quotes stay on the filing; we store text for bind and extract only.
Do not republish full PDFs (IR redistribution, R3-35).

Discovery: NSE corporate announcements by symbol (con-call, presentation,
results filings). BSE's announcement API is behind bot protection and is not
used; BSE-only names need another discovery source.
"""

from __future__ import annotations

import io
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Set
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from app.data import doc_store

ALLOWLIST_HOSTS: Set[str] = {
    "www.bseindia.com",
    "bseindia.com",
    "www.nseindia.com",
    "nseindia.com",
    "nsearchives.nseindia.com",
    "archives.nseindia.com",
}

# Issuer IR domains, allowed only for the issuer they belong to. A domain shared
# by several listed group companies (jsw.in; bajajfinserv.in beyond Bajaj
# Finance) is not added for the others: a document there could be any of them.
ISSUER_HOSTS: Dict[str, str] = {
    "adanienterprises.com": "adanient",
    "adaniports.com": "adani_ports",
    "airtel.in": "bhartiartl",
    "apollohospitals.com": "apollohosp",
    "asianpaints.com": "asianpaints",
    "axis.bank.in": "axisbank",
    "bajajauto.com": "bajaj_auto",
    "bajajfinserv.in": "bajajfinance",
    "bel-india.in": "bel",
    "britannia.co.in": "britannia",
    "cipla.com": "cipla",
    "coalindia.in": "coalindia",
    "divislabs.com": "divislab",
    "drreddys.com": "drreddy",
    "eicher.in": "eichermot",
    "eternal.com": "eternal",
    "goindigo.in": "indigo",
    "grasim.com": "grasim",
    "hcltech.com": "hcltech",
    "hdfcbank.com": "hdfcbank",
    "hdfclife.com": "hdfclife",
    "heromotocorp.com": "hero_motocorp",
    "hindalco.com": "hindalco",
    "hul.co.in": "hindunilvr",
    "icicibank.com": "icicibank",
    "indusind.com": "indusindbk",
    "infosys.com": "infy",
    "itcportal.com": "itc",
    "jfs.in": "jiofin",
    "kotak.com": "kotakbank",
    "larsentoubro.com": "lt",
    "mahindra.com": "m_m",
    "marutisuzuki.com": "maruti",
    "maxhealthcare.in": "maxhealth",
    "nestle.in": "nestleind",
    "ntpc.co.in": "ntpc",
    "ongcindia.com": "ongc",
    "powergrid.in": "powergrid",
    "ril.com": "reliance",
    "sbi.co.in": "sbin",
    "sbilife.co.in": "sbilife",
    "shriramfinance.in": "shriramfin",
    "sunpharma.com": "sunpharma",
    "tataconsumer.com": "tataconsum",
    "tatamotors.com": "tatamotors",
    "tatasteel.com": "tatasteel",
    "tcs.com": "tcs",
    "techmahindra.com": "techm",
    "titancompany.in": "titan",
    "trent-tata.com": "trent",
    "wipro.com": "wipro",
}

BOT_UA = "CiteAlphaBot/1.0 (filings; citealpha.com)"
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126 Safari/537.36"
)

NSE_ANNOUNCEMENTS = (
    "https://www.nseindia.com/api/corporate-announcements"
    "?index=equities&symbol={symbol}&from_date={start}&to_date={end}"
)
NSE_ANNUAL_REPORTS = "https://www.nseindia.com/api/annual-reports?index=equities&symbol={symbol}"

# Sensex / Nifty names that already have a distinct promise labeled.
PROMISE_COHORT = (
    "adani_ports",
    "adanient",
    "apollohosp",
    "axisbank",
    "bajaj_auto",
    "bajajfinance",
    "bel",
    "britannia",
    "cipla",
    "coalindia",
    "eternal",
    "hcltech",
    "hdfclife",
    "hindalco",
    "indigo",
    "indusindbk",
    "infy",
    "jiofin",
    "maxhealth",
    "ongc",
    "reliance",
    "sbilife",
    "shriramfin",
    "tataconsum",
    "tcs",
    "titan",
    "trent",
)

CATEGORY_CUES = (
    "result",
    "earnings",
    "transcript",
    "concall",
    "investor presentation",
    "press release",
    "financial",
    "outcome",
)

_LAST_FETCH = 0.0
_COUNTS: Dict[str, int] = {}
_BOT_REFUSED: Set[str] = set()
_FETCH_DAY = ""


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: List[str] = []

    def handle_data(self, data: str) -> None:
        t = (data or "").strip()
        if t:
            self._chunks.append(t)

    def text(self) -> str:
        return "\n".join(self._chunks)


def fetch_interval_sec() -> float:
    return float(os.environ.get("INTELLENS_FILING_FETCH_INTERVAL_SEC", "1.5"))


def daily_fetch_cap() -> int:
    return int(os.environ.get("INTELLENS_FILING_FETCH_DAILY_CAP", "200"))


def daily_discovery_cap() -> int:
    return int(os.environ.get("INTELLENS_FILING_DISCOVERY_DAILY_CAP", "500"))


def browser_fallback_enabled() -> bool:
    return os.environ.get("INTELLENS_FILING_BROWSER_UA_FALLBACK", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _matches(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def is_exchange_host(url: str) -> bool:
    host = _host(url)
    return bool(host) and any(_matches(host, h) for h in ALLOWLIST_HOSTS)


def host_allowed(url: str, company_id: Optional[str] = None) -> bool:
    host = _host(url)
    if not host:
        return False
    if is_exchange_host(url):
        return True
    if company_id:
        return any(_matches(host, d) and cid == company_id for d, cid in ISSUER_HOSTS.items())
    return False


class DailyCapReached(RuntimeError):
    pass


def _budget_path() -> Optional[str]:
    root = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    return os.path.join(root, "filing_fetch_budget.json") if root else None


def _load_budget(today: str) -> None:
    """Daily counts are shared by every process that uses the same data dir."""
    global _FETCH_DAY
    path = _budget_path()
    if not path or not os.path.exists(path):
        return
    try:
        with open(path, encoding="utf-8") as fh:
            saved = json.load(fh)
    except (OSError, ValueError):
        return
    if saved.get("day") == today:
        _FETCH_DAY = today
        for bucket, n in (saved.get("counts") or {}).items():
            _COUNTS[bucket] = max(_COUNTS.get(bucket, 0), int(n))


def _save_budget() -> None:
    path = _budget_path()
    if not path:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"day": _FETCH_DAY, "counts": _COUNTS}, fh)
    os.replace(tmp, path)


def _rate_limit(bucket: str = "fetch") -> None:
    global _LAST_FETCH, _FETCH_DAY
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if _FETCH_DAY != today:
        _FETCH_DAY = today
        _COUNTS.clear()
    _load_budget(today)
    cap = daily_discovery_cap() if bucket == "discovery" else daily_fetch_cap()
    if _COUNTS.get(bucket, 0) >= cap:
        raise DailyCapReached(f"daily {bucket} cap reached ({cap})")
    wait = fetch_interval_sec() - (time.time() - _LAST_FETCH)
    if wait > 0:
        time.sleep(wait)
    _LAST_FETCH = time.time()
    _COUNTS[bucket] = _COUNTS.get(bucket, 0) + 1
    _save_budget()


def budget_remaining(bucket: str = "fetch") -> int:
    global _FETCH_DAY
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if _FETCH_DAY != today:
        _FETCH_DAY = today
        _COUNTS.clear()
    _load_budget(today)
    cap = daily_discovery_cap() if bucket == "discovery" else daily_fetch_cap()
    return max(0, cap - _COUNTS.get(bucket, 0))


def reset_rate_limit() -> None:
    global _LAST_FETCH, _FETCH_DAY
    _LAST_FETCH = 0.0
    _COUNTS.clear()
    _BOT_REFUSED.clear()
    _FETCH_DAY = ""
    path = _budget_path()
    if path and os.path.exists(path):
        os.remove(path)


def extract_pdf_text(payload: bytes, *, limit: int = 80000) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(payload))
    parts: List[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
        if sum(len(p) for p in parts) >= limit:
            break
    text = re.sub(r"[ \t]+", " ", "\n".join(parts)).strip()
    return text[:limit]


# The management discussion carries its title as a running header, usually on
# alternate pages; the table of contents names it once.
MDA_HEADERS = ("management discussion", "management's discussion")
# "guidance" is left out: in an annual report it is mostly shareholder help text.
OUTLOOK_PAGE_CUES = (
    "outlook",
    "going forward",
    "we expect",
    "we aim",
    "we target",
    "capital expenditure",
    "capex",
)
ANNUAL_REPORT_LIMIT = 300000


def outlook_pages(pages: List[str], *, gap: int = 3, min_headers: int = 3) -> List[int]:
    """Indexes of the management-discussion span plus outlook pages elsewhere."""
    lows = [p.lower() for p in pages]
    headed = [i for i, t in enumerate(lows) if any(h in t for h in MDA_HEADERS)]
    keep: Set[int] = set()
    run: List[int] = []
    for i in headed + [None]:
        if i is not None and run and i - run[-1] <= gap:
            run.append(i)
            continue
        if len(run) >= min_headers:
            keep.update(range(run[0], run[-1] + 1))
        run = [i] if i is not None else []
    keep.update(i for i, t in enumerate(lows) if any(c in t for c in OUTLOOK_PAGE_CUES))
    return sorted(keep)


def extract_annual_report_text(payload: bytes, *, limit: int = ANNUAL_REPORT_LIMIT) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(payload))
    pages = [p.extract_text() or "" for p in reader.pages]
    text = "\n".join(pages[i] for i in outlook_pages(pages))
    return re.sub(r"[ \t]+", " ", text).strip()[:limit]


def extract_html_text(payload: bytes, *, limit: int = 80000) -> str:
    parser = _TextExtractor()
    parser.feed(payload.decode("utf-8", errors="ignore"))
    return parser.text()[:limit]


def _open(url: str, user_agent: str, accept: str = "*/*", timeout: float = 30) -> bytes:
    headers = {"User-Agent": user_agent, "Accept": accept}
    if is_exchange_host(url):
        host = _host(url)
        headers["Referer"] = (
            "https://www.bseindia.com/" if "bseindia" in host else "https://www.nseindia.com/"
        )
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — allowlist gated
        return resp.read()


def fetch_bytes(
    url: str,
    company_id: Optional[str] = None,
    *,
    bucket: str = "fetch",
    accept: str = "*/*",
) -> bytes:
    """Identify as CiteAlphaBot first; exchanges that refuse bots get a browser UA."""
    if not host_allowed(url, company_id):
        raise ValueError(f"Host not allowlisted: {_host(url)}")
    _rate_limit(bucket)
    exchange = is_exchange_host(url)
    host = _host(url)
    if exchange and host in _BOT_REFUSED and browser_fallback_enabled():
        return _open(url, BROWSER_UA, accept)
    try:
        # NSE stalls bot requests rather than refusing them; keep that wait short.
        return _open(url, BOT_UA, accept, timeout=8 if exchange else 30)
    except (HTTPError, URLError, OSError) as exc:
        refused = not isinstance(exc, HTTPError) or exc.code in (401, 403)
        if not (refused and exchange and browser_fallback_enabled()):
            raise
    _BOT_REFUSED.add(host)
    time.sleep(fetch_interval_sec())
    return _open(url, BROWSER_UA, accept)


def text_from_payload(payload: bytes, url: str, category: str = "filing") -> str:
    if payload.lstrip()[:5] == b"%PDF-":
        if category == "annual_report":
            return extract_annual_report_text(payload)
        return extract_pdf_text(payload)
    return extract_html_text(payload)


# Issuers often file a one-page letter giving the weblink to the transcript on
# their own site. PDF text wraps that link across lines.
COVER_LETTER_MAX_CHARS = 4000
_URL_PIECE = re.compile(r"^[\w\-./%~?=&+:#]+$")


def linked_filing_urls(text: str, company_id: str, *, exclude: str = "", max_pieces: int = 6) -> List[str]:
    """PDF links in a short cover letter, on hosts allowed for this issuer."""
    if len(re.sub(r"\s+", " ", text).strip()) > COVER_LETTER_MAX_CHARS:
        return []
    tokens = text.split()
    found: List[str] = []
    for i, tok in enumerate(tokens):
        if not tok.lower().startswith(("http://", "https://")):
            continue
        url = ""
        for piece in tokens[i : i + max_pieces]:
            if url and (piece.lower().startswith(("http://", "https://")) or not _URL_PIECE.match(piece)):
                break
            url += piece
            bare = url.rstrip(".,;)")
            if bare.lower().endswith(".pdf"):
                if bare != exclude and bare not in found and host_allowed(bare, company_id):
                    found.append(bare)
                break
    return found


def ingest_url(
    company_id: str,
    url: str,
    *,
    title: Optional[str] = None,
    date: Optional[str] = None,
    category: str = "filing",
    review_status: str = "accepted",
    dry_run: bool = False,
    text: Optional[str] = None,
    undated: bool = False,
    persist: bool = True,
) -> Dict[str, Any]:
    """Ingest one filing. ``text`` skips the network (tests / fixtures).

    ``undated`` stores an empty date instead of today: a guidance row from it then
    has no ``guidance_as_of`` and stays out of the score until a reviewer dates it.
    """
    if not url and not text:
        raise ValueError("url or text required")
    if url and not host_allowed(url, company_id) and text is None:
        raise ValueError(f"Host not allowlisted: {urlparse(url).hostname}")
    body = text
    if body is None:
        payload = fetch_bytes(url, company_id)
        body = text_from_payload(payload, url, category)
    cleaned = re.sub(r"\s+", " ", (body or "")).strip()
    if len(cleaned) < 40:
        return {"ok": False, "reason": "insufficient_text", "url": url, "company_id": company_id}
    linked = linked_filing_urls(body or "", company_id, exclude=url)
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "company_id": company_id,
            "url": url,
            "chars": len(cleaned),
            "linked_urls": linked,
        }
    doc = doc_store.upsert_document(
        company_id=company_id,
        doc_type=category,
        title=title or f"Exchange filing {urlparse(url).path.rsplit('/', 1)[-1]}",
        text=cleaned,
        url=url or None,
        date=date or ("" if undated else datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        source="exchange_filing",
        review_status=review_status,
        persist=persist,
    )
    return {
        "ok": True,
        "company_id": company_id,
        "url": url,
        "doc_id": doc.get("doc_id"),
        "action": "upserted",
        "chars": len(cleaned),
        "linked_urls": linked,
    }


def _outcome_urls(company_id: str) -> List[str]:
    from app.data.seed import get_data

    seen: Set[str] = set()
    urls: List[str] = []
    for row in (get_data().get("outcomes") or {}).get(company_id) or []:
        for key in ("source_url", "guidance_source_url"):
            url = str(row.get(key) or "").strip()
            if url and url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


_KIND_RULES = (
    ("concall", ("con. call", "concall", "earnings call", "transcript", "analyst")),
    ("presentation", ("investor presentation", "presentation")),
    ("results", ("financial result", "result updates", "outcome of board meeting")),
    ("press_release", ("press release",)),
    ("annual_report", ("annual report",)),
)
_KIND_RANK = {
    "concall": 3,
    "presentation": 1,
    "results": 2,
    "press_release": 4,
    "agm": 3,
    "annual_report": 5,
}

_AGM_RE = re.compile(r"\bagm\b|annual general meeting")
# AGM notices and voting results carry no outlook; the meeting record does.
_AGM_RECORD_CUES = ("transcript", "proceedings", "speech")
# A letter giving members the weblink to the report is not the report.
_WEBLINK_CUES = ("weblink", "web-link", "web link", "letter sent to")

# Doc types where management states forward guidance; a lookback needs one.
GUIDANCE_DOC_TYPES = ("concall", "presentation", "agm", "annual_report")


def classify_announcement(desc: str, text: str = "") -> Optional[str]:
    blob = f"{desc} {text}".lower()
    if _AGM_RE.search(blob):
        if any(c in blob for c in _AGM_RECORD_CUES):
            return "agm"
        blob = _AGM_RE.sub(" ", blob)
    if "annual report" in blob and any(c in blob for c in _WEBLINK_CUES):
        return None
    for kind, cues in _KIND_RULES:
        if any(c in blob for c in cues):
            return kind
    return None


def _announcement_rank(kind: str, text: str) -> int:
    if kind == "concall" and "transcript" in text.lower():
        return 0
    return _KIND_RANK.get(kind, 9)


def nse_symbol_for(company_id: str) -> Optional[str]:
    from app.data.india_listings import india_equity_universe

    for row in india_equity_universe():
        if row["id"] == company_id:
            if "NSE_ALL" in (row.get("index_ids") or []) and row.get("ticker"):
                return str(row["ticker"]).upper()
            return None
    return None


def _ann_date(raw: str) -> Optional[str]:
    for fmt in ("%d-%b-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            continue
    return None


def discovery_months() -> int:
    return int(os.environ.get("INTELLENS_FILING_DISCOVERY_MONTHS", "24"))


def discovery_max_docs() -> int:
    return int(os.environ.get("INTELLENS_FILING_DISCOVERY_MAX_DOCS", "6"))


def discovery_since() -> str:
    """First filing date the walk reads (ISO). A promise made in 2022 closes in FY23 or later."""
    raw = os.environ.get("INTELLENS_FILING_DISCOVERY_SINCE", "").strip()
    try:
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return "2022-01-01"


def discovery_docs_per_year() -> int:
    return int(os.environ.get("INTELLENS_FILING_DISCOVERY_DOCS_PER_YEAR", "6"))


def _india_fy(iso_date: Optional[str]) -> int:
    """Indian fiscal year a filing date falls in (Apr–Mar); 0 when undated."""
    try:
        d = datetime.strptime(str(iso_date or "")[:10], "%Y-%m-%d")
    except ValueError:
        return 0
    return d.year + 1 if d.month >= 4 else d.year


def _best_per_year(picked: List[Dict[str, Any]], per_year: int) -> List[Dict[str, Any]]:
    by_year: Dict[int, List[Dict[str, Any]]] = {}
    for row in picked:
        by_year.setdefault(_india_fy(row.get("date")), []).append(row)
    out: List[Dict[str, Any]] = []
    for year in sorted(by_year, reverse=True):
        out.extend(by_year[year][:per_year])
    return out


def discover_nse_filings(
    company_id: str,
    *,
    months: Optional[int] = None,
    max_docs: Optional[int] = None,
    payload: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Guidance-bearing NSE announcements (PDF links) for one company, best first.

    Default: every filing since :func:`discovery_since`, the best few per fiscal
    year, so a 2022 promise and the result that closed it are both read.
    ``months`` / ``max_docs`` keep the older rolling window and flat cap.
    ``payload`` is the NSE JSON list (tests); otherwise one live API call.
    """
    flat = months is not None or max_docs is not None
    max_docs = discovery_max_docs() if max_docs is None else max_docs
    if payload is None:
        symbol = nse_symbol_for(company_id)
        if not symbol:
            return []
        end = datetime.now(timezone.utc)
        if months is not None:
            start = end - timedelta(days=int(months * 30.5))
        else:
            start = datetime.strptime(discovery_since(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        url = NSE_ANNOUNCEMENTS.format(
            symbol=quote(symbol, safe=""),
            start=start.strftime("%d-%m-%Y"),
            end=end.strftime("%d-%m-%Y"),
        )
        raw = fetch_bytes(url, company_id, bucket="discovery", accept="application/json")
        payload = json.loads(raw.decode("utf-8", errors="ignore") or "[]")
    picked: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for ann in payload if isinstance(payload, list) else []:
        link = str(ann.get("attchmntFile") or "").strip()
        if not link.lower().endswith(".pdf") or link in seen or not is_exchange_host(link):
            continue
        desc = str(ann.get("desc") or "")
        text = str(ann.get("attchmntText") or "")
        kind = classify_announcement(desc, text)
        if not kind:
            continue
        seen.add(link)
        picked.append(
            {
                "url": link,
                "category": kind,
                "title": (text or desc)[:200],
                "date": _ann_date(str(ann.get("an_dt") or ann.get("sort_date") or "")),
                "rank": _announcement_rank(kind, text),
            }
        )
    picked.sort(key=lambda r: (r["rank"], -(int((r["date"] or "0").replace("-", "")))))
    top = picked[:max_docs] if flat else _best_per_year(picked, discovery_docs_per_year())
    # Transcripts fill the cap every quarter; the yearly AGM record would never make it.
    for kind in ("agm", "annual_report"):
        latest = next((r for r in picked if r["category"] == kind), None)
        if latest and latest not in top:
            top.append(latest)
    return top


def discover_nse_annual_reports(
    company_id: str,
    *,
    years: int = 2,
    payload: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Latest annual-report PDFs from NSE's annual-report list (older years are ZIPs; skipped)."""
    if payload is None:
        symbol = nse_symbol_for(company_id)
        if not symbol:
            return []
        url = NSE_ANNUAL_REPORTS.format(symbol=quote(symbol, safe=""))
        raw = fetch_bytes(url, company_id, bucket="discovery", accept="application/json")
        payload = json.loads(raw.decode("utf-8", errors="ignore") or "{}")
    rows = payload.get("data") if isinstance(payload, dict) else payload
    picked: List[Dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        link = str(row.get("fileName") or "").strip()
        if not link.lower().endswith(".pdf") or not is_exchange_host(link):
            continue
        fy = f"FY {row.get('fromYr')}-{str(row.get('toYr') or '')[-2:]}"
        picked.append(
            {
                "url": link,
                "category": "annual_report",
                "title": f"Annual Report {fy}",
                "date": _ann_date(str(row.get("broadcast_dttm") or "").title()),
                "rank": _KIND_RANK["annual_report"],
                "to_year": str(row.get("toYr") or ""),
            }
        )
    picked.sort(key=lambda r: r["to_year"], reverse=True)
    return picked[:years]


# Web search finds where a filing sits (a transcript only on the issuer's site,
# a BSE-only scrip). It is a lead: each link is fetched through the allowlist and
# goes through the same extract and quote bind as an NSE filing.
_WEB_LEDGER: Optional[Dict[str, Any]] = None


def web_search_enabled() -> bool:
    return os.environ.get("INTELLENS_WEB_SEARCH_DISCOVERY", "").strip().lower() in ("1", "true", "yes")


def web_search_daily_cap() -> int:
    return int(os.environ.get("INTELLENS_WEB_SEARCH_DAILY_CAP", "60"))


def web_search_refresh_days() -> int:
    return int(os.environ.get("INTELLENS_WEB_SEARCH_REFRESH_DAYS", "30"))


def _web_ledger_path() -> Optional[str]:
    root = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    return os.path.join(root, "web_search_ledger.json") if root else None


def _web_ledger() -> Dict[str, Any]:
    global _WEB_LEDGER
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if _WEB_LEDGER is None:
        _WEB_LEDGER = {"day": today, "used": 0, "last": {}}
        path = _web_ledger_path()
        if path and os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    _WEB_LEDGER.update(json.load(fh))
            except (OSError, json.JSONDecodeError):
                pass
    if _WEB_LEDGER.get("day") != today:
        _WEB_LEDGER["day"] = today
        _WEB_LEDGER["used"] = 0
    return _WEB_LEDGER


def _save_web_ledger() -> None:
    path = _web_ledger_path()
    if not path or _WEB_LEDGER is None:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(_WEB_LEDGER, fh)
    os.replace(tmp, path)


def reset_web_search() -> None:
    global _WEB_LEDGER
    _WEB_LEDGER = None


def _web_search_due(company_id: str) -> bool:
    ledger = _web_ledger()
    if int(ledger["used"]) >= web_search_daily_cap():
        return False
    last = (ledger.get("last") or {}).get(company_id)
    if not last:
        return True
    try:
        age = datetime.now(timezone.utc) - datetime.strptime(last, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    return age.days >= web_search_refresh_days()


def _strip_tracking(url: str) -> str:
    parts = urlparse(url)
    if not parts.query:
        return url
    kept = [q for q in parts.query.split("&") if q and not q.lower().startswith("utm_")]
    return parts._replace(query="&".join(kept)).geturl()


def _listing_row(company_id: str) -> Optional[Dict[str, Any]]:
    from app.data.india_listings import india_equity_universe

    return next((r for r in india_equity_universe() if r["id"] == company_id), None)


def web_search_prompt(company_id: str) -> Optional[str]:
    row = _listing_row(company_id)
    if row is None:
        return None
    sites = ["nseindia.com", "bseindia.com"] + [d for d, cid in ISSUER_HOSTS.items() if cid == company_id]
    return (
        f"Find documents in which the management of {row['name']} "
        f"(India, ticker {row.get('ticker') or company_id}) gave forward guidance in the last "
        f"{discovery_months()} months: earnings call transcripts, investor presentations, "
        "annual reports, AGM transcripts or proceedings. "
        f"Only documents hosted on {', '.join(sites)}. "
        "Give the direct document URL (PDF where available), one per line, with the document "
        "title and date. Do not summarise the guidance."
    )


def discover_via_web_search(
    company_id: str,
    *,
    max_docs: int = 8,
    search: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """Leads from a web-search model, kept only on hosts allowed for this issuer."""
    if search is None:
        if not web_search_enabled() or not _web_search_due(company_id):
            return []
        from app.services import llm_client

        if not llm_client.llm_configured():
            return []
        search = llm_client.web_search_links
    prompt = web_search_prompt(company_id)
    if not prompt:
        return []
    ledger = _web_ledger()
    ledger["used"] = int(ledger["used"]) + 1
    _save_web_ledger()
    links = search(prompt)
    ledger.setdefault("last", {})[company_id] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    _save_web_ledger()
    picked: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for link in links:
        url = _strip_tracking(str(link.get("url") or ""))
        if not url or url in seen or not host_allowed(url, company_id):
            continue
        title = str(link.get("title") or "")
        words = re.sub(r"[-_/.%]+", " ", f"{title} {urlparse(url).path}")
        kind = classify_announcement(words)
        if kind is None and not urlparse(url).path.lower().endswith(".pdf"):
            continue
        seen.add(url)
        picked.append(
            {
                "url": url,
                "category": kind or "filing",
                "title": (title or urlparse(url).path.rsplit("/", 1)[-1])[:200],
                "date": None,
                "rank": _KIND_RANK.get(kind or "", 9),
                "found_by": "web_search",
            }
        )
    picked.sort(key=lambda r: r["rank"])
    return picked[:max_docs]


def _stored_texts() -> Dict[str, str]:
    """URL key → stored text, every company. Long documents keep only a preview inline; they map to ""."""
    return {
        doc_store.url_key(d["url"]): "" if d.get("text_file") else str(d.get("text") or "")
        for d in doc_store.list_documents(include_rejected=True, hydrate=False)
        if d.get("url")
    }


def ingest_company_urls(
    company_id: str,
    *,
    dry_run: bool = False,
    live: bool = False,
    fixture_text: Optional[str] = None,
    discover: bool = False,
    discovery_payload: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    urls = _outcome_urls(company_id)
    results: List[Dict[str, Any]] = []
    if fixture_text:
        results.append(
            ingest_url(
                company_id,
                urls[0] if urls else "https://www.bseindia.com/xml-data/corpfiling/fixture.pdf",
                title="Fixture filing",
                category="concall",
                dry_run=dry_run,
                text=fixture_text,
            )
        )
        return {"company_id": company_id, "results": results, "urls": urls}
    if not live and discovery_payload is None:
        return {
            "company_id": company_id,
            "results": [],
            "urls": urls,
            "skipped": "offline — pass live=true or fixture_text",
        }
    targets: List[Dict[str, Any]] = [{"url": u, "category": "filing"} for u in urls] if live else []
    discovered: List[Dict[str, Any]] = []
    if discover or discovery_payload is not None:
        try:
            discovered = discover_nse_filings(company_id, payload=discovery_payload)
            if discovery_payload is None:
                have = {d["url"] for d in discovered}
                discovered += [
                    r for r in discover_nse_annual_reports(company_id) if r["url"] not in have
                ]
        except DailyCapReached:
            results.append({"ok": False, "reason": "discovery_cap"})
        except Exception as exc:  # noqa: BLE001 — discovery must not stop the cohort
            results.append({"ok": False, "reason": f"discovery_{type(exc).__name__}"})
        if discovery_payload is None:
            try:
                have = {d["url"] for d in discovered}
                discovered += [r for r in discover_via_web_search(company_id) if r["url"] not in have]
            except Exception as exc:  # noqa: BLE001 — a search lead must not stop the cohort
                results.append({"ok": False, "reason": f"web_search_{type(exc).__name__}"})
            try:
                from app.services.ir_discovery import discover_from_issuer_site

                have = {d["url"] for d in discovered}
                discovered += [r for r in discover_from_issuer_site(company_id) if r["url"] not in have]
            except Exception as exc:  # noqa: BLE001 — the site walk must not stop the cohort
                results.append({"ok": False, "reason": f"ir_crawl_{type(exc).__name__}"})
        targets.extend(discovered)
    stored = _stored_texts()
    queued = {doc_store.url_key(t["url"]) for t in targets}
    try:
        _ingest_targets(company_id, targets, stored, queued, results, dry_run)
    finally:
        # One index write per company: the index holds every filing, so a write per filing is costly.
        if any(r.get("action") == "upserted" for r in results):
            doc_store.save()
    return {
        "company_id": company_id,
        "results": results,
        "urls": urls,
        "discovered": len(discovered),
    }


def _ingest_targets(
    company_id: str,
    targets: List[Dict[str, Any]],
    stored: Dict[str, str],
    queued: set,
    results: List[Dict[str, Any]],
    dry_run: bool,
) -> None:
    def follow(target: Dict[str, Any], linked: List[str]) -> None:
        if target.get("linked_from"):
            return
        for link in linked:
            if doc_store.url_key(link) not in queued:
                queued.add(doc_store.url_key(link))
                targets.append({**target, "url": link, "linked_from": target["url"]})

    for target in targets:
        url = target["url"]
        key = doc_store.url_key(url)
        if key in stored:
            results.append({"ok": True, "url": url, "action": "already_stored"})
            follow(target, linked_filing_urls(stored[key], company_id, exclude=url))
            continue
        if not host_allowed(url, company_id):
            results.append({"ok": False, "url": url, "reason": "host_not_allowlisted"})
            continue
        try:
            out = ingest_url(
                company_id,
                url,
                title=target.get("title"),
                date=target.get("date"),
                category=target.get("category") or "filing",
                dry_run=dry_run,
                undated=target.get("found_by") in ("web_search", "ir_crawl"),
                persist=False,
            )
            if target.get("linked_from"):
                out["linked_from"] = target["linked_from"]
            if target.get("found_by"):
                out["found_by"] = target["found_by"]
            results.append(out)
            follow(target, out.get("linked_urls") or [])
        except DailyCapReached:
            results.append({"ok": False, "url": url, "reason": "fetch_cap"})
            break
        except Exception as exc:  # noqa: BLE001 — one URL must not stop the cohort
            results.append({"ok": False, "url": url, "reason": type(exc).__name__})


def ingest_promise_cohort(
    *,
    live: bool = False,
    dry_run: bool = False,
    limit: Optional[int] = None,
    fixture_text: Optional[str] = None,
    discover: bool = False,
) -> Dict[str, Any]:
    ids = list(PROMISE_COHORT)
    if limit is not None and limit > 0:
        ids = ids[:limit]
    companies: List[Dict[str, Any]] = []
    ingested = 0
    for cid in ids:
        report = ingest_company_urls(
            cid, live=live, dry_run=dry_run, fixture_text=fixture_text, discover=discover
        )
        companies.append(report)
        ingested += sum(
            1 for r in report.get("results") or [] if r.get("ok") and r.get("action") == "upserted"
        )
    return {
        "ok": True,
        "cohort": "promise_distinct",
        "companies": len(ids),
        "ingested": ingested,
        "live": live,
        "dry_run": dry_run,
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "results": companies,
        "note": "Stores filing text for bind/extract. Does not invent a GCI number.",
    }
