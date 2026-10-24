"""Deliver CiteAlpha Analyst events to an org's webhooks, Slack and Microsoft Teams (A6).

Events: ``monitor.run`` (a Monitor ran a Skill on a new filing) and ``digest.weekly``.
Webhook bodies are signed: ``X-CiteAlpha-Signature: sha256=<hex HMAC of "<timestamp>.<body>">``
with the destination's secret, and ``X-CiteAlpha-Timestamp``. URLs must be HTTPS;
generic webhooks may not resolve to private or loopback addresses, and redirects
are not followed. A failed delivery is logged and never loses the saved run.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
import os
import secrets
import socket
import threading
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

log = logging.getLogger(__name__)

KINDS = ("webhook", "slack", "teams")
EVENTS = ("monitor.run", "digest.weekly")
MAX_DESTINATIONS_PER_ORG = 10
LOG_KEEP = 50
SLACK_HOSTS = ("hooks.slack.com",)
TEAMS_SUFFIXES = (".webhook.office.com", ".logic.azure.com", ".powerplatform.com")

_PACKAGED = Path(__file__).resolve().parents[2] / "data" / "analyst_destinations.json"
_LOCK = threading.Lock()

Poster = Callable[[str, bytes, Dict[str, str]], int]


def _path() -> Path:
    env = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    return Path(env) / "analyst_destinations.json" if env else _PACKAGED


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> Dict[str, Any]:
    p = _path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"destinations": [], "log": []}


def _save(data: Dict[str, Any]) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def _private_host(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return True
    for info in infos:
        addr = ipaddress.ip_address(info[4][0])
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_multicast:
            return True
    return False


def validate_url(kind: str, url: str) -> None:
    u = urlparse(url or "")
    host = (u.hostname or "").lower()
    if u.scheme != "https" or not host:
        raise ValueError("Destination URL must start with https://")
    if kind == "slack" and host not in SLACK_HOSTS:
        raise ValueError("Slack destinations must be a hooks.slack.com incoming-webhook URL")
    if kind == "teams" and not host.endswith(TEAMS_SUFFIXES):
        raise ValueError("Teams destinations must be a Teams or Power Automate workflow webhook URL")
    if kind == "webhook" and _private_host(host):
        raise ValueError("Webhook host must resolve to a public address")


def _mask(url: str) -> str:
    u = urlparse(url)
    return f"{u.scheme}://{u.hostname}/…{url[-6:]}"


def _public(d: Dict[str, Any]) -> Dict[str, Any]:
    return {"destination_id": d["destination_id"], "kind": d["kind"], "label": d.get("label"),
            "url": _mask(d["url"]), "events": d["events"], "created_at": d["created_at"],
            "last_status": d.get("last_status"), "last_delivered_at": d.get("last_delivered_at")}


def list_destinations(org_id: str) -> List[Dict[str, Any]]:
    return [_public(d) for d in _load()["destinations"] if d["org_id"] == org_id]


def delivery_log(org_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    return [e for e in reversed(_load()["log"]) if e["org_id"] == org_id][:limit]


def add_destination(org_id: str, *, kind: str, url: str, events: List[str], label: str, created_by: str) -> Dict[str, Any]:
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}")
    events = [e for e in dict.fromkeys(events or list(EVENTS))]
    if any(e not in EVENTS for e in events):
        raise ValueError(f"events must be from {', '.join(EVENTS)}")
    validate_url(kind, url)
    with _LOCK:
        data = _load()
        if sum(1 for d in data["destinations"] if d["org_id"] == org_id) >= MAX_DESTINATIONS_PER_ORG:
            raise OverflowError(f"destination limit reached ({MAX_DESTINATIONS_PER_ORG} per organisation)")
        dest = {"destination_id": "dst_" + uuid.uuid4().hex[:12], "org_id": org_id, "kind": kind, "url": url,
                "events": events, "label": (label or kind).strip()[:80], "created_by": created_by,
                "created_at": _now(), "secret": "whsec_" + secrets.token_urlsafe(24) if kind == "webhook" else None}
        data["destinations"].append(dest)
        _save(data)
    out = _public(dest)
    if dest["secret"]:
        out["secret"] = dest["secret"]
    return out


def delete_destination(org_id: str, destination_id: str) -> bool:
    with _LOCK:
        data = _load()
        keep = [d for d in data["destinations"] if not (d["org_id"] == org_id and d["destination_id"] == destination_id)]
        if len(keep) == len(data["destinations"]):
            return False
        data["destinations"] = keep
        _save(data)
        return True


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):  # noqa: ANN002
        return None


def _post(url: str, body: bytes, headers: Dict[str, str]) -> int:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=8) as resp:
            return int(resp.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


def sign(secret: str, timestamp: str, body: bytes) -> str:
    mac = hmac.new(secret.encode("utf-8"), f"{timestamp}.".encode("utf-8") + body, hashlib.sha256)
    return "sha256=" + mac.hexdigest()


def _request(dest: Dict[str, Any], event: str, payload: Dict[str, Any], text: str) -> tuple:
    headers = {"Content-Type": "application/json", "User-Agent": "CiteAlpha-Webhooks/1"}
    if dest["kind"] == "slack":
        body = json.dumps({"text": text}).encode("utf-8")
    elif dest["kind"] == "teams":
        body = json.dumps({"text": text.replace("\n", "<br>")}).encode("utf-8")
    else:
        body = json.dumps({"event": event, "delivered_at": _now(), "data": payload}, ensure_ascii=False).encode("utf-8")
        ts = str(int(time.time()))
        headers.update({"X-CiteAlpha-Event": event, "X-CiteAlpha-Timestamp": ts,
                        "X-CiteAlpha-Signature": sign(dest["secret"] or "", ts, body)})
    return body, headers


def _send_one(dest: Dict[str, Any], event: str, payload: Dict[str, Any], text: str, poster: Poster) -> Dict[str, Any]:
    body, headers = _request(dest, event, payload, text)
    status, error = 0, None
    for attempt in range(2):
        try:
            if dest["kind"] == "webhook" and _private_host(urlparse(dest["url"]).hostname or ""):
                raise ValueError("host resolves to a private address")
            status = poster(dest["url"], body, headers)
            error = None
            if status < 500:
                break
        except Exception as exc:  # network failure; retry once
            error = type(exc).__name__
    return {"destination_id": dest["destination_id"], "kind": dest["kind"], "event": event,
            "status": status, "ok": 200 <= status < 300, "error": error, "at": _now()}


def deliver(org_id: str, event: str, payload: Dict[str, Any], text: str, *, poster: Optional[Poster] = None,
            only: Optional[str] = None) -> List[Dict[str, Any]]:
    poster = poster or _post
    dests = [d for d in _load()["destinations"]
             if d["org_id"] == org_id and (only == d["destination_id"] if only else event in d["events"])]
    results = [_send_one(d, event, payload, text, poster) for d in dests]
    if results:
        with _LOCK:
            data = _load()
            by_id = {r["destination_id"]: r for r in results}
            for d in data["destinations"]:
                if d["destination_id"] in by_id:
                    r = by_id[d["destination_id"]]
                    d["last_status"] = r["status"] or r["error"]
                    d["last_delivered_at"] = r["at"]
            data["log"] = (data["log"] + [{**r, "org_id": org_id} for r in results])[-LOG_KEEP * 20:]
            _save(data)
    return results


def has_subscribers(org_id: str, event: str) -> bool:
    return any(d["org_id"] == org_id and event in d["events"] for d in _load()["destinations"])


def run_payload(out: Dict[str, Any], base_url: str) -> Dict[str, Any]:
    link = f"{base_url.rstrip('/')}/analyst?run={out['run_id']}"
    return {
        "run_id": out["run_id"], "skill": out["skill"], "company_id": out["company_id"],
        "company_name": out["company_name"], "generated_at": out["generated_at"], "as_of": out["as_of"],
        "trigger": out.get("trigger"), "headline": out.get("headline"),
        "sections": [{"title": s["title"], "claims": s["claims"]} for s in out["sections"] if s["claims"]],
        "not_found": out.get("not_found"),
        "citations": [{k: c.get(k) for k in ("n", "kind", "title", "date", "quote", "source_url", "permalink")}
                      for c in out["citations"] if c.get("kind") != "upload"],
        "link": link,
        "exports": {f: f"{base_url.rstrip('/')}/api/analyst/runs/{out['run_id']}/export?format={f}"
                    for f in ("xlsx", "pptx", "pdf", "md")},
        "disclaimer": out.get("disclaimer"),
    }
