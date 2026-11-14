"""Append-only ledger of every published GCI level (rule `index-integrity`).

One JSON row per line in ``backend/app/data/score_ledger.jsonl``. A row is keyed by
``(company_id, as_of, algorithm_id, dataset_version)``; the same key never carries
two different values — a correction is a *new* row (later ``as_of`` or next
``dataset_version`` the same day) with a reason.

Reasons: ``methodology`` · ``data_correction`` · ``new_filing`` · ``flag_change`` ·
``display_fix`` · ``snapshot`` (routine job run, no change).
"""

from __future__ import annotations

import json
import os
import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from app.data.store_lock import locked

LEDGER_PATH = Path(__file__).resolve().parents[1] / "data" / "score_ledger.jsonl"

REASONS = (
    "methodology",
    "data_correction",
    "new_filing",
    "flag_change",
    "display_fix",
    "snapshot",
)


@dataclass(frozen=True)
class LedgerRow:
    company_id: str
    as_of: str
    algorithm_id: str
    dataset_version: str
    gci: Optional[float]
    prior_gci: Optional[float]
    confidence_tier: Optional[str]
    reason: str
    note: str
    by: str
    #: Content address of the calculation snapshot (inputs + method) behind this level.
    snapshot_id: Optional[str] = None
    snapshot: Optional[Dict[str, Any]] = field(default=None, repr=False, compare=False, hash=False)

    def key(self) -> tuple:
        return (self.company_id, self.as_of, self.algorithm_id, self.dataset_version)

    def to_json(self) -> Dict[str, Any]:
        out = asdict(self)
        out.pop("snapshot", None)
        if out.get("snapshot_id") is None:
            out.pop("snapshot_id", None)
        return out


def _path() -> Path:
    override = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    if not override:
        return LEDGER_PATH
    dest = Path(override) / "score_ledger.jsonl"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists() and LEDGER_PATH.exists():
        dest.write_bytes(LEDGER_PATH.read_bytes())
    return dest


def read_all() -> List[Dict[str, Any]]:
    p = _path()
    if not p.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def rows_for(company_id: str) -> List[Dict[str, Any]]:
    return [r for r in read_all() if r.get("company_id") == company_id]


def latest_for(company_id: str) -> Optional[Dict[str, Any]]:
    rows = rows_for(company_id)
    return rows[-1] if rows else None


def levels_as_of(cutoff: str) -> Dict[str, Dict[str, Any]]:
    """Last ledger row per company dated on or before ``cutoff`` (YYYY-MM-DD). A withdrawal row has ``gci`` None."""
    latest: Dict[str, Dict[str, Any]] = {}
    for row in read_all():
        if str(row.get("as_of") or "") <= cutoff:
            latest[str(row.get("company_id"))] = row
    return latest


@locked
def append(row: LedgerRow) -> bool:
    """Append ``row``. Returns False when an identical row already exists.

    Raises ``ValueError`` when the same key already carries a different ``gci``
    (append-only: never overwrite a published level).
    """
    if row.reason not in REASONS:
        raise ValueError(f"unknown ledger reason: {row.reason}")
    for existing in read_all():
        existing_key = (
            existing.get("company_id"),
            existing.get("as_of"),
            existing.get("algorithm_id"),
            existing.get("dataset_version"),
        )
        if existing_key == row.key():
            if existing.get("gci") == row.gci:
                return False
            raise ValueError(
                f"ledger key {row.key()} already holds gci={existing.get('gci')}; "
                f"refusing to overwrite with {row.gci}"
            )
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    if row.snapshot is not None and row.snapshot_id:
        _write_snapshot(row.snapshot_id, row.snapshot)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row.to_json(), separators=(",", ":"), ensure_ascii=False) + "\n")
    return True


# ── Calculation snapshots (content-addressed inputs behind each level) ───────

SNAPSHOT_SCHEMA = "calc_snapshot_v1"
SNAPSHOT_DIR = LEDGER_PATH.parent / "calc_snapshots"


def _snapshot_dir() -> Path:
    override = os.environ.get("INTELLENS_DATA_DIR", "").strip()
    return Path(override) / "calc_snapshots" if override else SNAPSHOT_DIR


def _canonical(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def snapshot_payload(
    company_id: str,
    *,
    as_of: str,
    algorithm_id: str,
    dataset_version: str,
    gci: Optional[float],
    confidence_tier: Optional[str],
) -> Dict[str, Any]:
    """Everything needed to recompute ``gci``: the stored outcome rows, audit flags, method."""
    from app.data.seed import get_data
    from app.services.gci_scoring import ALGORITHM_REVISION, CORE_REVISION
    from app.services.guidance_flags import applied_audit_flags

    core = algorithm_id.startswith("gci_core")
    inputs: Dict[str, Any] = {
        "outcomes": list(get_data()["outcomes"].get(company_id, [])),
        "audit_flags": sorted(applied_audit_flags(company_id)),
    }
    if core:
        from app.jobs.validation_gates import core_inputs

        held = core_inputs(company_id, as_of=as_of)
        inputs["commitments"] = held["commitments"]
        inputs["issuance_times"] = held["issuance_times"]
        inputs["market"] = {k: held[k] for k in ("market_id", "regime", "fy_end_mmdd")}
    return {
        "schema": SNAPSHOT_SCHEMA,
        "company_id": company_id,
        "as_of": as_of,
        "algorithm_id": algorithm_id,
        "algorithm_revision": CORE_REVISION if core else ALGORITHM_REVISION,
        "dataset_version": dataset_version,
        "gci": gci,
        "confidence_tier": confidence_tier,
        "inputs": inputs,
    }


def snapshot_id_for(payload: Dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _write_snapshot(snapshot_id: str, payload: Dict[str, Any]) -> None:
    d = _snapshot_dir()
    d.mkdir(parents=True, exist_ok=True)
    dest = d / f"{snapshot_id.split(':', 1)[-1]}.json"
    if not dest.exists():
        dest.write_text(_canonical(payload), encoding="utf-8")


def read_snapshot(snapshot_id: str) -> Optional[Dict[str, Any]]:
    digest = snapshot_id.split(":", 1)[-1]
    if not digest or any(ch not in "0123456789abcdef" for ch in digest):
        return None
    for base in (_snapshot_dir(), SNAPSHOT_DIR):
        p = base / f"{digest}.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return None


def replay_snapshot(snapshot_id: str) -> Optional[Dict[str, Any]]:
    """Recompute a stored snapshot with the method it names; ``matches`` is the reproducibility check."""
    snap = read_snapshot(snapshot_id)
    if snap is None:
        return None
    return replay_payload(snap, snapshot_id)


def replay_payload(snap: Dict[str, Any], snapshot_id: Optional[str] = None) -> Dict[str, Any]:
    from app.data.seed import outcome_from_dict
    from app.services.gci_scoring import (
        ALGORITHM_REVISION,
        CORE_REVISION,
        compute_company_gci,
        compute_core_detail,
        core_ruleset_for,
    )

    snapshot_id = snapshot_id or snapshot_id_for(snap)
    rows = [outcome_from_dict(d) for d in snap["inputs"]["outcomes"]]
    flags = list(snap["inputs"].get("audit_flags") or [])
    algo = str(snap.get("algorithm_id") or "")
    if algo.startswith("gci_core"):
        replayed = compute_core_detail(
            rows,
            audit_flags=flags,
            commitments=snap["inputs"].get("commitments") or [],
            as_of=snap.get("as_of"),
            ruleset=core_ruleset_for(algo),
            company_id=snap.get("company_id"),
            issuance_times=snap["inputs"].get("issuance_times") or {},
            **(snap["inputs"].get("market") or {}),
        )["headline_gci"]
        current = CORE_REVISION
    else:
        replayed = compute_company_gci(rows, audit_flags=flags, version=algo.replace("gci_scoring_", ""))
        current = ALGORITHM_REVISION
    intact = snapshot_id_for(snap) == ("sha256:" + snapshot_id.split(":", 1)[-1])
    return {
        "snapshot_id": snapshot_id,
        "algorithm_id": algo,
        "algorithm_revision": snap.get("algorithm_revision"),
        "current_revision": current,
        "recorded_gci": snap.get("gci"),
        "replayed_gci": replayed,
        "content_intact": intact,
        "matches": intact and replayed == snap.get("gci"),
    }


def updates_since(since: str, *, limit: int = 500) -> List[Dict[str, Any]]:
    """Ledger rows dated after ``since`` (YYYY-MM-DD), oldest first — the licensee change feed."""
    rows = [r for r in read_all() if str(r.get("as_of") or "") > since]
    return rows[:limit]


def append_many(rows: Iterable[LedgerRow]) -> int:
    n = 0
    written: List[LedgerRow] = []
    for r in rows:
        if append(r):
            n += 1
            written.append(r)
    if written:
        from app.data import audit_log

        audit_log.record(
            "ledger_publish",
            actor=written[0].by,
            role="system",
            detail={
                "rows": n,
                "reasons": sorted({r.reason for r in written}),
                "companies": sorted({r.company_id for r in written})[:50],
            },
        )
    return n


RELEASE_BY = "job:methodology_release"
_RELEASE_CORRECTION_NOTE = (
    "Level restored. The methodology entry recorded this company as withdrawn because its score "
    "was read while the service was still loading filing citations. The published level was never withdrawn."
)


def correct_release_withdrawals(*, by: str = RELEASE_BY) -> int:
    """Append a data_correction where the release step logged a withdrawal the live score contradicts."""
    if not os.environ.get("INTELLENS_DATA_DIR", "").strip():
        return 0
    latest: Dict[str, Dict[str, Any]] = {}
    for r in read_all():
        latest[str(r.get("company_id"))] = r
    flagged = {cid for cid, r in latest.items() if r.get("by") == RELEASE_BY and r.get("gci") is None}
    if not flagged:
        return 0
    rows = [
        r
        for r in snapshot_rows(reason="data_correction", note=_RELEASE_CORRECTION_NOTE, by=by)
        if r.company_id in flagged and r.gci is not None
    ]
    return append_many(rows)


def record_methodology_release(*, by: str = RELEASE_BY) -> int:
    """Once per scorer revision: log every level the new method moved, as ``methodology``.

    Runs before the daily filing walks so a method change is not booked as ``new_filing``.
    Only on a data volume; packaged data is snapshotted by hand with ``snapshot_scores``.
    """
    from app.services.gci_scoring import ALGORITHM_REVISION

    if not os.environ.get("INTELLENS_DATA_DIR", "").strip():
        return 0
    marker = _path().parent / "methodology_release.txt"
    if marker.exists() and marker.read_text(encoding="utf-8").strip() == ALGORITHM_REVISION:
        return 0
    n = append_many(snapshot_rows(reason="methodology", note=ALGORITHM_REVISION, by=by))
    marker.write_text(ALGORITHM_REVISION + "\n", encoding="utf-8")
    return n


def dataset_version(now: Optional[datetime] = None) -> str:
    """Next ``YYYY-MM-DD.N`` for today — N is one above the highest already in the ledger."""
    d = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    highest = 0
    for r in read_all():
        v = str(r.get("dataset_version", ""))
        if v.startswith(d + "."):
            try:
                highest = max(highest, int(v.split(".", 1)[1]))
            except ValueError:
                continue
    return f"{d}.{highest + 1}"


def _route_map(outcome_dicts: Iterable[Dict[str, Any]]) -> Dict[tuple, tuple]:
    from app.services.score_policy import core_route

    return {
        (str(d.get("period")), str(d.get("metric")), str(d.get("scope")), str(d.get("reporting_basis"))): core_route(d)
        for d in outcome_dicts
    }


def _routes_changed(company_id: str, prev: Dict[str, Any]) -> bool:
    """RT-06: a row moved route (scored ↔ excluded) since the last snapshot, even at the same level."""
    from app.data.seed import get_data

    snap = read_snapshot(str(prev.get("snapshot_id") or "")) if prev.get("snapshot_id") else None
    if snap is None:
        return False
    before = _route_map(snap.get("inputs", {}).get("outcomes") or [])
    now = _route_map(get_data()["outcomes"].get(company_id, []))
    return before != now


def snapshot_rows(
    *,
    reason: str = "snapshot",
    note: str = "",
    by: str = "job:snapshot_scores",
    as_of: Optional[str] = None,
) -> List[LedgerRow]:
    """Build one row per scored company whose level differs from its last ledger row.

    Pure with respect to the ledger file until :func:`append_many` is called.
    """
    from app.services import repository

    today = as_of or datetime.now(timezone.utc).date().isoformat()
    # dataset_version follows the row's as_of date, not the wall clock.
    version = dataset_version(datetime.fromisoformat(today).replace(tzinfo=timezone.utc))
    out: List[LedgerRow] = []
    from app.services.score_policy import is_scoreable

    for c in repository.list_company_summaries():
        if not is_scoreable(c.data_quality):
            continue
        prev = latest_for(c.id)
        prior = prev.get("gci") if prev else None
        prior_tier = prev.get("confidence_tier") if prev else None
        if (
            prev is not None
            and prior == c.gci_score
            and prior_tier == c.confidence_tier
            and not _routes_changed(c.id, prev)
        ):
            continue
        # First-time unpublished names stay off the ledger; a published level
        # that is withdrawn (gci → None) is logged.
        if c.gci_score is None and (prev is None or prior is None):
            continue
        algo = c.algorithm_id or "gci_scoring_v4"
        snap = snapshot_payload(
            c.id,
            as_of=today,
            algorithm_id=algo,
            dataset_version=version,
            gci=c.gci_score,
            confidence_tier=c.confidence_tier,
        )
        out.append(
            LedgerRow(
                company_id=c.id,
                as_of=today,
                algorithm_id=algo,
                dataset_version=version,
                gci=c.gci_score,
                prior_gci=prior,
                confidence_tier=c.confidence_tier,
                reason=reason,
                note=note,
                by=by,
                snapshot_id=snapshot_id_for(snap),
                snapshot=snap,
            )
        )
    return out


# ── Publication requests (WF-07, DM-10) and release sign-offs ───────────────
# A Core level reaches the ledger only through a request that a second person
# approves after every release gate passes. Events live in the audit log.

PUBLICATION_REQUESTED = "publication_requested"
PUBLICATION_DECIDED = "publication_decided"
RELEASE_SIGNOFF = "release_signoff"


def _events(action: str) -> List[Dict[str, Any]]:
    from app.data import audit_log

    return audit_log.list_by_action(action)


def signed_off_gates() -> List[str]:
    return sorted({str((r.get("detail") or {}).get("gate_id")) for r in _events(RELEASE_SIGNOFF)})


def record_signoff(gate_id: str, *, by: str, role: str, note: str = "") -> Dict[str, Any]:
    from app.data import audit_log
    from app.jobs.validation_gates import CORE_MANUAL_GATES

    if gate_id not in {g[0] for g in CORE_MANUAL_GATES}:
        raise ValueError("unknown_gate")
    if not by:
        raise ValueError("missing_actor")
    return audit_log.record(RELEASE_SIGNOFF, actor=by, role=role, detail={"gate_id": gate_id, "note": note})


def publication_events(company_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Requests with their decision, oldest first."""
    decided = {str((r.get("detail") or {}).get("event_id")): r for r in _events(PUBLICATION_DECIDED)}
    out = []
    for r in _events(PUBLICATION_REQUESTED):
        d = dict(r.get("detail") or {})
        if company_id and d.get("company_id") != company_id:
            continue
        decision = decided.get(str(d.get("event_id")))
        out.append({
            **d,
            "requested_by": r.get("actor"),
            "requested_at": r.get("ts"),
            "status": (decision.get("detail") or {}).get("status") if decision else "awaiting_approval",
            "decided_by": decision.get("actor") if decision else None,
            "decided_at": decision.get("ts") if decision else None,
            "decision_note": (decision.get("detail") or {}).get("note") if decision else None,
        })
    return out


def request_publication(company_id: str, *, by: str, role: str, ruleset: Optional[str] = None) -> Dict[str, Any]:
    """Freeze the Core calculation as a snapshot and open a request. Publishes nothing."""
    from app.data import audit_log
    from app.jobs.validation_gates import core_inputs
    from app.services import gci_scoring as g

    if not by:
        raise ValueError("missing_actor")
    rs = ruleset or g.CORE_DEFAULT_RULESET
    today = datetime.now(timezone.utc).date().isoformat()
    kw = core_inputs(company_id, as_of=today)
    detail = g.compute_core_detail(kw.pop("outcomes"), ruleset=rs, **kw)
    algo = detail["algorithm_id"]
    snap = snapshot_payload(
        company_id,
        as_of=today,
        algorithm_id=algo,
        dataset_version="pending",
        gci=detail["headline_gci"],
        confidence_tier=detail["confidence_tier"],
    )
    sid = snapshot_id_for(snap)
    _write_snapshot(sid, snap)
    event = {
        "event_id": "pub_" + sid.split(":", 1)[-1][:16] + "_" + hashlib.sha256(f"{by}{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:6],
        "company_id": company_id,
        "algorithm_id": algo,
        "ruleset": rs,
        "as_of": today,
        "gci": detail["headline_gci"],
        "confidence_tier": detail["confidence_tier"],
        "snapshot_id": sid,
    }
    audit_log.record(PUBLICATION_REQUESTED, actor=by, role=role, detail=event)
    return {**event, "status": "awaiting_approval", "requested_by": by}


def decide_publication(event_id: str, *, approve: bool, by: str, role: str, note: str = "") -> Dict[str, Any]:
    """Second person approves or rejects. Approval appends the ledger row only when every gate passes."""
    from app.data import audit_log
    from app.jobs.validation_gates import core_release_gates

    event = next((e for e in publication_events() if e.get("event_id") == event_id), None)
    if event is None:
        raise KeyError("publication_event_not_found")
    if event["status"] != "awaiting_approval":
        raise ValueError("already_decided")
    if not by or by == event["requested_by"]:
        raise ValueError("second_person_required")
    status = "rejected"
    failed: List[str] = []
    if approve:
        gates = core_release_gates(event["company_id"], ruleset=event.get("ruleset"), signed_off=signed_off_gates())
        failed = list(gates["failed"])
        replay = replay_snapshot(event["snapshot_id"])
        # The approver signs the level that was requested; data that moved since needs a new request.
        if not (replay and replay["matches"]) or gates["level"] != event["gci"]:
            failed.append("STALE_REQUEST")
        status = "blocked" if failed else "approved"
    if status == "approved":
        from app.services.guidance_review import _append_changelog

        prev = latest_for(event["company_id"])
        snap = read_snapshot(event["snapshot_id"])
        row = LedgerRow(
            company_id=event["company_id"],
            as_of=event["as_of"],
            algorithm_id=event["algorithm_id"],
            dataset_version=dataset_version(datetime.fromisoformat(event["as_of"]).replace(tzinfo=timezone.utc)),
            gci=event["gci"],
            prior_gci=prev.get("gci") if prev else None,
            confidence_tier=event["confidence_tier"],
            reason="methodology",
            note=note or f"Published through request {event_id}",
            by=by,
            snapshot_id=event["snapshot_id"],
            snapshot=snap,
        )
        if append(row):
            _append_changelog(
                datetime.now(timezone.utc).date(),
                [row],
                lead=f"{event['algorithm_id']} level published through two-person approval ({event_id}).",
                reason="methodology",
            )
    audit_log.record(
        PUBLICATION_DECIDED,
        actor=by,
        role=role,
        detail={
            "event_id": event_id,
            "company_id": event["company_id"],
            "status": status,
            "note": note,
            "failed_gates": failed,
        },
    )
    return {**event, "status": status, "decided_by": by, "failed_gates": failed}
