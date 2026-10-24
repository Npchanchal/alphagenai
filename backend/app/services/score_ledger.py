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
from dataclasses import asdict, dataclass
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

    def key(self) -> tuple:
        return (self.company_id, self.as_of, self.algorithm_id, self.dataset_version)

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)


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
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row.to_json(), separators=(",", ":"), ensure_ascii=False) + "\n")
    return True


def append_many(rows: Iterable[LedgerRow]) -> int:
    n = 0
    for r in rows:
        if append(r):
            n += 1
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
        if prev is not None and prior == c.gci_score and prior_tier == c.confidence_tier:
            continue
        # First-time unpublished names stay off the ledger; a published level
        # that is withdrawn (gci → None) is logged.
        if c.gci_score is None and (prev is None or prior is None):
            continue
        out.append(
            LedgerRow(
                company_id=c.id,
                as_of=today,
                algorithm_id=c.algorithm_id or "gci_scoring_v4",
                dataset_version=version,
                gci=c.gci_score,
                prior_gci=prior,
                confidence_tier=c.confidence_tier,
                reason=reason,
                note=note,
                by=by,
            )
        )
    return out
