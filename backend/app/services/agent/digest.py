"""Weekly CiteAlpha Analyst digest per organisation.

Covers the companies the org monitors (single companies, owners' watchlists and
Project lists): new filings in the window, Skill runs saved, and reviewed
commitments falling due in the next 30 days or already past due, and guidance
changes (raised, cut, dropped or withdrawn) not sent before. Each line names its
filing, run or source, with a link. Sent at most once every seven days per org, from
the refresh loop; nothing is sent when there is nothing new.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

_PACKAGED = Path(__file__).resolve().parents[2] / "data" / "analyst_digest.json"
_LOCK = threading.Lock()
WINDOW_DAYS = 7
DUE_AHEAD_DAYS = 30
MAX_EMAILS = 10
MAX_SEEN_CHANGES = 2000


def _path() -> Path:
    env = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    return Path(env) / "analyst_digest.json" if env else _PACKAGED


def _load() -> Dict[str, Any]:
    p = _path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"orgs": {}}


def _save(data: Dict[str, Any]) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def get_settings(org_id: str) -> Dict[str, Any]:
    s = _load()["orgs"].get(org_id) or {}
    return {"enabled": bool(s.get("enabled")), "emails": list(s.get("emails") or []),
            "last_sent_at": s.get("last_sent_at")}


def set_settings(org_id: str, *, enabled: bool, emails: List[str]) -> Dict[str, Any]:
    clean = sorted({e.strip().lower() for e in emails if e and e.strip()})
    bad = [e for e in clean if "@" not in e or " " in e]
    if bad:
        raise ValueError(f"Invalid email address: {bad[0]}")
    if len(clean) > MAX_EMAILS:
        raise ValueError(f"At most {MAX_EMAILS} recipients")
    with _LOCK:
        data = _load()
        cur = data["orgs"].setdefault(org_id, {})
        cur.update(enabled=enabled, emails=clean)
        _save(data)
    return get_settings(org_id)


def covered_companies(org_id: str) -> List[str]:
    from app.services.agent import monitors

    out: List[str] = []
    for m in monitors.list_monitors(org_id):
        for c in monitors.companies_for(m):
            if c not in out:
                out.append(c)
    return out


def _company_name(company_id: str) -> str:
    from app.data.seed import list_companies

    return next((c.get("name") for c in list_companies() if c["id"] == company_id), company_id)


def change_key(item: Dict[str, Any]) -> str:
    return "|".join(str(item.get(k) or "") for k in ("company_id", "kind", "metric", "period"))


def guidance_changes(companies: List[str], seen: List[str]) -> List[Dict[str, Any]]:
    from app.services.portfolio import radar_feed

    wanted, skip = set(companies), set(seen)
    out = []
    for item in radar_feed(limit=500).get("items", []):
        if item.get("company_id") in wanted and change_key(item) not in skip:
            out.append({"key": change_key(item), "company_id": item["company_id"],
                        "company_name": _company_name(item["company_id"]), "message": item.get("message"),
                        "severity": item.get("severity"), "source_url": item.get("source_url")})
    return out


def build_digest(org_id: str, *, today: Optional[date] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    from app.data import doc_store
    from app.services import commitment_store, mailer
    from app.services.agent import run_store
    from app.services.agent.tools import is_company_filing

    today = today or datetime.now(timezone.utc).date()
    since = (today - timedelta(days=WINDOW_DAYS)).isoformat()
    ahead = (today + timedelta(days=DUE_AHEAD_DAYS)).isoformat()
    base = (base_url or mailer.public_base_url()).rstrip("/")
    companies = covered_companies(org_id)

    filings = []
    for cid in companies:
        for d in doc_store.list_documents(company_id=cid):
            if is_company_filing(d) and str(d.get("date") or "") >= since:
                filings.append({"company_id": cid, "company_name": _company_name(cid), "title": d.get("title"),
                                "date": d.get("date"), "url": d.get("url")})
    filings.sort(key=lambda f: str(f["date"]), reverse=True)

    runs = [r for r in run_store.list_runs(org_id, limit=200) if str(r.get("generated_at") or "")[:10] >= since]
    for r in runs:
        r["link"] = f"{base}/analyst?run={r['run_id']}"

    due = []
    for cid in companies:
        view = commitment_store.company_view(cid, include_unreviewed=False, as_of=today.isoformat())
        for c in view["commitments"]:
            if c.get("state") != "open" or not c.get("due_date"):
                continue
            if c["due_date"] <= ahead:
                due.append({"company_id": cid, "company_name": _company_name(cid), "subject": c.get("subject"),
                            "due_period": c.get("due_period"), "due_date": c["due_date"],
                            "past_due": c["due_date"] < today.isoformat(), "source_url": c.get("source_url")})
    due.sort(key=lambda c: c["due_date"])

    seen = (_load()["orgs"].get(org_id) or {}).get("seen_changes") or []
    changes = guidance_changes(companies, seen)

    return {"org_id": org_id, "from": since, "to": today.isoformat(), "companies": companies,
            "filings": filings[:40], "runs": runs[:40], "due": due[:40], "changes": changes[:40],
            "empty": not (filings or runs or due or changes)}


def render_text(d: Dict[str, Any]) -> str:
    lines = [f"CiteAlpha Analyst weekly digest, {d['from']} to {d['to']}",
             f"Companies covered by your Monitors: {len(d['companies'])}", ""]
    if d["filings"]:
        lines.append("New filings")
        lines += [f"- {f['company_name']}: {f['title']} ({f['date']}) {f.get('url') or ''}".rstrip() for f in d["filings"]]
        lines.append("")
    if d["runs"]:
        lines.append("Skill runs saved")
        lines += [f"- {r['skill_title']}: {r['company_name']} ({str(r['generated_at'])[:10]}"
                  f"{', after ' + r['trigger']['title'] if r.get('trigger') and r['trigger'].get('title') else ''}) {r['link']}"
                  for r in d["runs"]]
        lines.append("")
    if d.get("changes"):
        lines.append("Guidance changes")
        lines += [f"- {c['company_name']}: {c['message']} {c.get('source_url') or ''}".rstrip() for c in d["changes"]]
        lines.append("")
    if d["due"]:
        lines.append("Commitments falling due (reviewed only)")
        lines += [f"- {c['company_name']}: {c['subject']}, due {c['due_period']}"
                  f"{' (past due; no result filing on record)' if c['past_due'] else ''} {c.get('source_url') or ''}".rstrip()
                  for c in d["due"]]
        lines.append("")
    if d["empty"]:
        lines += ["Nothing new this week for the companies you monitor.", ""]
    lines.append("Factual summary of company disclosures with sources. Not investment advice.")
    return "\n".join(lines)


def _due_for_send(settings: Dict[str, Any], now: datetime) -> bool:
    last = settings.get("last_sent_at")
    if not last:
        return True
    try:
        then = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
    except ValueError:
        return True
    return now - then >= timedelta(days=WINDOW_DAYS)


def send_due_digests(*, now: Optional[datetime] = None, force: bool = False, deliver: bool = True) -> Dict[str, Any]:
    from app.services import mailer
    from app.services.agent import delivery

    now = now or datetime.now(timezone.utc)
    sent, skipped = [], []
    for org_id, s in list(_load()["orgs"].items()):
        if not s.get("enabled") or not (s.get("emails") or delivery.has_subscribers(org_id, "digest.weekly")):
            continue
        if not force and not _due_for_send(s, now):
            continue
        d = build_digest(org_id, today=now.date())
        if d["empty"]:
            skipped.append(org_id)
        elif deliver:
            text = render_text(d)
            for to in s.get("emails") or []:
                try:
                    mailer.send_mail(to=to, subject=f"CiteAlpha Analyst weekly digest — {d['to']}", body=text)
                except Exception as exc:  # one bad address must not stop the batch
                    log.warning("digest_email_failed org=%s err=%s", org_id, exc)
            try:
                delivery.deliver(org_id, "digest.weekly", d, text)
            except Exception as exc:
                log.warning("digest_push_failed org=%s err=%s", org_id, exc)
            sent.append(org_id)
        with _LOCK:
            data = _load()
            cur = data["orgs"].setdefault(org_id, {})
            cur["last_sent_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            if deliver and not d["empty"]:
                seen = list(cur.get("seen_changes") or []) + [c["key"] for c in d["changes"]]
                cur["seen_changes"] = seen[-MAX_SEEN_CHANGES:]
            _save(data)
    return {"sent": sent, "skipped_empty": skipped}
