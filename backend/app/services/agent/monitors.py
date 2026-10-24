"""Event-triggered CiteAlpha Analyst Monitors.

A Monitor is an org's standing instruction: "when <company> files something new,
run <Skill> and send it to me". ``process_new_documents`` compares the document
store with the IDs it has already seen. The first call records the existing corpus
as a baseline and runs nothing, so a fresh deployment does not flood feeds with
old filings. Each later new filing:

1. queues commitment proposals (``unreviewed``; a reviewer must accept them),
2. runs every matching Monitor's Skill with a "What the new filing says" section,
3. saves the run to the org's history (the feed) and emails the Monitor owner.

Nothing here writes to the GCI or accepts a commitment.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger(__name__)

_PACKAGED = Path(__file__).resolve().parents[2] / "data" / "analyst_monitors.json"
_LOCK = threading.Lock()
MAX_MONITORS_PER_ORG = 25
AUTO_PROPOSER = "auto:commitment_extract"


class LimitError(ValueError):
    pass


def _path() -> Path:
    env = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    return Path(env) / "analyst_monitors.json" if env else _PACKAGED


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> Dict[str, Any]:
    p = _path()
    if not p.exists():
        return {"monitors": [], "seen_doc_ids": [], "baselined_at": None}
    return json.loads(p.read_text(encoding="utf-8"))


def _save(data: Dict[str, Any]) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def list_monitors(org_id: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = _load().get("monitors", [])
    return [m for m in rows if org_id is None or m.get("org_id") == org_id]


SCOPES = ("company", "watchlist", "project")


def _target(mon: Dict[str, Any]) -> tuple:
    scope = mon.get("scope") or "company"
    key = {"company": "company_id", "watchlist": "user_id", "project": "project_id"}[scope]
    return scope, mon.get(key)


def companies_for(mon: Dict[str, Any]) -> List[str]:
    """Companies a Monitor covers now: one company, the owner's watchlist, or a Project's list."""
    scope, target = _target(mon)
    if scope == "company":
        return [target] if target else []
    if scope == "watchlist":
        from app.services.session_auth import user_watchlist

        return user_watchlist(target)
    from app.services.agent import projects

    proj = projects.get_project(mon["org_id"], target)
    return list(proj["company_ids"]) if proj else []


def create_monitor(
    *,
    org_id: str,
    created_by: str,
    skill_id: str,
    company_id: Optional[str] = None,
    email: Optional[str] = None,
    scope: str = "company",
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    if scope not in SCOPES:
        raise ValueError(f"scope must be one of {', '.join(SCOPES)}")
    new = {"scope": scope, "company_id": company_id if scope == "company" else None,
           "user_id": user_id if scope == "watchlist" else None,
           "project_id": project_id if scope == "project" else None}
    if not _target(new)[1]:
        raise ValueError(f"{scope} monitor needs its target")
    with _LOCK:
        data = _load()
        mine = [m for m in data["monitors"] if m["org_id"] == org_id]
        for m in mine:
            if _target(m) == _target(new) and m["skill_id"] == skill_id:
                if email and m.get("email") != email:
                    m["email"] = email
                    _save(data)
                return m
        if len(mine) >= MAX_MONITORS_PER_ORG:
            raise LimitError(f"monitor limit reached ({MAX_MONITORS_PER_ORG} per organisation)")
        mon = {
            "monitor_id": "mon_" + uuid.uuid4().hex[:12],
            "org_id": org_id,
            "created_by": created_by,
            **new,
            "skill_id": skill_id,
            "email": email or None,
            "created_at": _now(),
            "last_run_id": None,
            "last_triggered_at": None,
        }
        data["monitors"].append(mon)
        _save(data)
        return mon


def delete_monitor(org_id: str, monitor_id: str) -> bool:
    with _LOCK:
        data = _load()
        before = len(data["monitors"])
        data["monitors"] = [
            m for m in data["monitors"] if not (m["org_id"] == org_id and m["monitor_id"] == monitor_id)
        ]
        if len(data["monitors"]) == before:
            return False
        _save(data)
        return True


def delete_project_monitors(org_id: str, project_id: str) -> int:
    with _LOCK:
        data = _load()
        keep = [m for m in data["monitors"]
                if not (m["org_id"] == org_id and m.get("scope") == "project" and m.get("project_id") == project_id)]
        dropped = len(data["monitors"]) - len(keep)
        if dropped:
            data["monitors"] = keep
            _save(data)
        return dropped


def _email_body(out: Dict[str, Any], link: str) -> str:
    lines = [
        f"{out['skill']['title']}: {out['company_name']}",
        f"Triggered by: {(out.get('trigger') or {}).get('title') or 'new filing'}",
        "",
    ]
    for s in out["sections"][:3]:
        if not s["claims"]:
            continue
        lines.append(s["title"])
        lines += [f"- {c['text']} " + "".join(f"[{n}]" for n in c["cites"]) for c in s["claims"][:4]]
        lines.append("")
    lines += [f"Full memo with sources: {link}", "", out["disclaimer"]]
    return "\n".join(lines)


def _deliver(mon: Dict[str, Any], out: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not mon.get("email"):
        return None
    from app.services import mailer

    link = f"{mailer.public_base_url()}/analyst?run={out['run_id']}"
    subject = f"CiteAlpha Analyst: new filing from {out['company_name']} — {out['skill']['title']}"
    try:
        return mailer.send_mail(to=mon["email"], subject=subject, body=_email_body(out, link))
    except Exception as exc:  # delivery failure must not lose the saved run
        log.warning("monitor_email_failed monitor=%s err=%s", mon["monitor_id"], exc)
        return {"sent": False, "error": type(exc).__name__}


def _push(mon: Dict[str, Any], out: Dict[str, Any]) -> None:
    from app.services import mailer
    from app.services.agent import delivery

    try:
        base = mailer.public_base_url()
        delivery.deliver(mon["org_id"], "monitor.run", delivery.run_payload(out, base),
                         _email_body(out, f"{base}/analyst?run={out['run_id']}"))
    except Exception as exc:  # connectors must not lose the saved run
        log.warning("monitor_push_failed monitor=%s err=%s", mon["monitor_id"], exc)


def _queue_commitments(doc: Dict[str, Any], use_llm: Optional[bool]) -> Dict[str, Any]:
    from app.services import commitment_store
    from app.services.commitment_extract import extract_from_document
    from app.services.commitment_monitor import CYCLE_DOC_TYPES

    if doc.get("doc_type") not in CYCLE_DOC_TYPES:
        return {"proposed": 0}
    ex = extract_from_document(doc, use_llm=use_llm)
    res = commitment_store.propose(ex["proposals"], proposed_by=AUTO_PROPOSER)
    return {"proposed": len(res["added"]), "engine": ex["engine"]}


def process_new_documents(
    *,
    limit: int = 50,
    use_llm: Optional[bool] = None,
    deliver: bool = True,
    runner: Optional[Callable[..., Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Process filings not seen before. First call only records the baseline."""
    from app.data import doc_store
    from app.services.agent import run_store
    from app.services.agent.runtime import run_skill
    from app.services.agent.tools import is_ingested_filing
    from app.services.research import ensure_doc_store_seeded

    runner = runner or run_skill
    ensure_doc_store_seeded()
    with _LOCK:
        data = _load()
        docs = doc_store.list_documents(include_rejected=False, hydrate=False)
        seen = set(data.get("seen_doc_ids") or [])
        if not data.get("baselined_at"):
            data["seen_doc_ids"] = sorted({d["doc_id"] for d in docs} | seen)
            data["baselined_at"] = _now()
            _save(data)
            return {"baselined": len(data["seen_doc_ids"]), "processed": 0, "runs": [], "pending": 0}
        unseen = [d for d in docs if d["doc_id"] not in seen]
        internal = {d["doc_id"] for d in unseen if not is_ingested_filing(d)}
        new = sorted((d for d in unseen if d["doc_id"] not in internal), key=lambda d: str(d.get("date") or ""))
        batch, pending = new[:limit], max(0, len(new) - limit)
        data["seen_doc_ids"] = sorted(seen | internal | {d["doc_id"] for d in batch})
        _save(data)
        monitors = list(data.get("monitors", []))

    events: List[Dict[str, Any]] = []
    runs: List[Dict[str, Any]] = []
    last: Dict[str, Dict[str, Any]] = {}
    for meta in batch:
        doc = doc_store.get_document(meta["doc_id"]) or meta
        ev: Dict[str, Any] = {"doc_id": doc["doc_id"], "company_id": doc.get("company_id"),
                              "doc_type": doc.get("doc_type"), "title": doc.get("title")}
        try:
            ev.update(_queue_commitments(doc, use_llm))
        except Exception as exc:
            ev["commitments_error"] = type(exc).__name__
        trigger = {k: doc.get(k) for k in ("doc_id", "title", "date", "doc_type", "url")}
        company = doc.get("company_id")
        for mon in monitors:
            try:
                if company not in companies_for(mon):
                    continue
                kwargs: Dict[str, Any] = {"trigger": trigger}
                if mon.get("scope") == "project":
                    from app.services.agent import projects

                    kwargs.update(org_id=mon["org_id"], project=projects.get_project(mon["org_id"], mon["project_id"]))
                out = runner(mon["skill_id"], company, **kwargs)
            except Exception as exc:
                log.warning("monitor_run_failed monitor=%s err=%s", mon["monitor_id"], exc)
                runs.append({"monitor_id": mon["monitor_id"], "error": type(exc).__name__})
                continue
            out["monitor_id"] = mon["monitor_id"]
            run_store.save_run(mon["org_id"], f"monitor:{mon['monitor_id']}", out)
            delivery = _deliver(mon, out) if deliver else None
            if deliver:
                _push(mon, out)
            runs.append({"monitor_id": mon["monitor_id"], "run_id": out["run_id"],
                         "org_id": mon["org_id"], "emailed": bool(delivery)})
            last[mon["monitor_id"]] = {"last_run_id": out["run_id"], "last_triggered_at": out["generated_at"]}
        events.append(ev)

    if last:
        with _LOCK:
            data = _load()
            for m in data.get("monitors", []):
                m.update(last.get(m["monitor_id"], {}))
            _save(data)
    return {"baselined": 0, "processed": len(batch), "pending": pending, "events": events, "runs": runs}


def status() -> Dict[str, Any]:
    data = _load()
    mons = data.get("monitors") or []
    orgs = {m.get("org_id") for m in mons if m.get("org_id")}
    triggers = [str(m.get("last_triggered_at")) for m in mons if m.get("last_triggered_at")]
    by_org: Dict[str, int] = {}
    for mon in mons:
        oid = str(mon.get("org_id") or "")
        if oid:
            by_org[oid] = by_org.get(oid, 0) + 1
    return {
        "baselined_at": data.get("baselined_at"),
        "seen_documents": len(data.get("seen_doc_ids") or []),
        "monitors": len(mons),
        "orgs": len(orgs),
        "last_triggered_at": max(triggers) if triggers else None,
        "by_org": by_org,
    }
