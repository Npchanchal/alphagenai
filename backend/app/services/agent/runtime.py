"""CiteAlpha Analyst runtime: Skill → read-only tools → claims → verifier → output.

Every sentence in an output is a claim with numbered citations. The verifier
removes anything unsupported; the disproof pass searches for evidence against the
read; the Evidence Receipt lists every source with a quote hash so a compliance
reviewer can audit any line. No step writes to the GCI or the Commitment Record.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from app.services.agent import skills as skill_specs
from app.services.agent import tools
from app.services.agent.verifier import verify_claims, verify_text

ENGINE = "citealpha-analyst-v1"
DISCLAIMER = "Factual summary of company disclosures with sources. Not investment advice."

_LABEL_WORD = {"exceeded": "beat", "met": "met", "missed": "missed", "dropped": "guidance withdrawn"}
_PERIOD_KEY = re.compile(r"(\d{2,4})")


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _period_sort(p: str) -> str:
    m = _PERIOD_KEY.findall(p or "")
    return m[-1].rjust(4, "0") + (p or "") if m else (p or "")


class _Context:
    """Per-run tool cache and citation registry (one tool call per input, per run)."""

    def __init__(
        self,
        company_id: str,
        include_unreviewed: bool,
        org_id: Optional[str] = None,
        project: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.company_id = company_id
        self.include_unreviewed = include_unreviewed
        self.org_id = org_id
        self.project = project
        self._cache: Dict[tuple, Dict[str, Any]] = {}
        self.citations: List[Dict[str, Any]] = []
        self._keys: Dict[tuple, int] = {}
        self.tool_calls: List[Dict[str, Any]] = []

    def tool(self, name: str, **kwargs: Any) -> Dict[str, Any]:
        return self.tool_for(self.company_id, name, **kwargs)

    def tool_for(self, company_id: str, name: str, **kwargs: Any) -> Dict[str, Any]:
        key = (company_id, name, tuple(sorted(kwargs.items())))
        if key not in self._cache:
            fn = tools.REGISTRY[name]
            res = fn(company_id, **kwargs)
            self._cache[key] = res
            self.tool_calls.append(
                {"tool": name, "company_id": company_id, "args": kwargs, "evidence": len(res["evidence"])}
            )
        return self._cache[key]

    def uploads(self, query: str = "", limit: int = 0) -> List[Dict[str, Any]]:
        if not (self.org_id and self.project):
            return []
        return self.tool(
            "project_uploads", org_id=self.org_id, project_id=self.project["project_id"], query=query, limit=limit
        )["evidence"]

    def cite(self, ev: Dict[str, Any]) -> int:
        key = (ev.get("source_url"), " ".join(str(ev.get("quote") or "").split()))
        if key in self._keys:
            return self._keys[key]
        n = len(self.citations) + 1
        self.citations.append({**ev, "n": n})
        self._keys[key] = n
        return n


Builder = Callable[[_Context, Dict[str, Any]], Dict[str, Any]]


def _claim(text: str, cites: List[int], kind: str = "record", row: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """``row``: the same fact as table cells (for exports); never adds a figure the text lacks."""
    out: Dict[str, Any] = {"text": text, "cites": [c for c in cites if c], "kind": kind}
    if row:
        out["row"] = row
    return out


def _delivery_record(ctx: _Context, args: Dict[str, Any]) -> Dict[str, Any]:
    res = ctx.tool("guidance_record")
    ev = res["evidence"]
    rows = res["data"]["rows"]
    if not rows:
        return {"claims": [], "empty": "No closed guidance periods with both the guidance and the result filing cited."}
    by_metric: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_metric[r["metric_name"]].append(r)
    claims = []
    for metric, mrows in by_metric.items():
        cites = []
        for r in mrows:
            cites.append(ctx.cite(ev[r["guidance_ev"]]))
            if r["actual_ev"] is not None:
                cites.append(ctx.cite(ev[r["actual_ev"]]))
        scored = [r for r in mrows if r["label"] != "dropped"]
        kept = sum(1 for r in scored if r["label"] in ("met", "exceeded"))
        missed = sorted((r["period"] for r in scored if r["label"] == "missed"), key=_period_sort)
        dropped = sorted((r["period"] for r in mrows if r["label"] == "dropped"), key=_period_sort)
        text = f"{metric}: met or beat guidance in {kept} of {len(scored)} closed periods"
        if missed:
            text += f"; missed {', '.join(missed)}"
        if dropped:
            text += f"; withdrew guidance for {', '.join(dropped)}"
        claims.append(_claim(text + ".", cites, "computed"))
    latest = sorted(rows, key=lambda r: _period_sort(r["period"]), reverse=True)[:6]
    for r in latest:
        cites = [ctx.cite(ev[r["guidance_ev"]])]
        if r["actual_ev"] is not None:
            cites.append(ctx.cite(ev[r["actual_ev"]]))
        word = _LABEL_WORD.get(r["label"], r["label"])
        if r["label"] == "dropped":
            text = f"{r['period']} {r['metric_name']}: guided {r['guided']}; {word}."
        else:
            text = f"{r['period']} {r['metric_name']}: guided {r['guided']}, reported {r['actual']} ({word})."
        row = {"Period": r["period"], "Metric": r["metric_name"], "Guided": r["guided"],
               "Reported": r["actual"] if r["label"] != "dropped" else "—", "Result": word}
        claims.append(_claim(text, cites, row=row))
    return {"claims": claims}


def _open_guidance(ctx: _Context, args: Dict[str, Any]) -> Dict[str, Any]:
    res = ctx.tool("open_guidance")
    ev = res["evidence"]
    claims = [
        _claim(f"{r['period']} {r['metric_name']}: guided {r['guided']}.", [ctx.cite(ev[r["guidance_ev"]])])
        for r in res["data"]["rows"]
    ]
    return {"claims": claims, "empty": None if claims else "No open guidance with a cited source for the coming periods."}


def _commitments(ctx: _Context) -> Dict[str, Any]:
    return ctx.tool("commitments", include_unreviewed=ctx.include_unreviewed)


def _tag(row: Dict[str, Any]) -> str:
    return " (unreviewed)" if row.get("review_status") != "accepted" else ""


def _commitments_open(ctx: _Context, args: Dict[str, Any]) -> Dict[str, Any]:
    res = _commitments(ctx)
    ev = res["evidence"]
    today = _today()
    claims = []
    open_rows = [r for r in res["data"]["rows"] if r.get("state") == "open"]
    for r in open_rows:
        overdue = (r.get("due_date") or "9999") < today
        text = f"{r['subject']} — due {r['due_period']}"
        if overdue:
            text += " (past due; no result filing on record)"
        claims.append(_claim(text + _tag(r) + ".", [ctx.cite(ev[r["ev"]])]))
    summary = res["data"]["summary"]
    if summary.get("due"):
        all_cites = [ctx.cite(ev[r["ev"]]) for r in res["data"]["rows"] if r.get("review_status") == "accepted"]
        claims.insert(0, _claim(summary["sentence"], all_cites, "computed"))
    return {"claims": claims, "empty": None if claims else "No reviewed commitments on record yet."}


def _commitments_closed(ctx: _Context, args: Dict[str, Any]) -> Dict[str, Any]:
    res = _commitments(ctx)
    ev = res["evidence"]
    claims = []
    for r in res["data"]["rows"]:
        if r.get("state") == "open":
            continue
        cites = [ctx.cite(ev[r["ev"]])]
        if r.get("proof_ev") is not None:
            cites.append(ctx.cite(ev[r["proof_ev"]]))
        claims.append(_claim(f"{r['subject']} — {r['state_label']} (due {r['due_period']}){_tag(r)}.", cites))
    return {"claims": claims, "empty": None if claims else "No commitments closed yet."}


def _filing_quotes(ctx: _Context, args: Dict[str, Any]) -> Dict[str, Any]:
    claims = []
    seen: set[str] = set()
    for q in args.get("queries") or []:
        for e in ctx.tool("filing_search", query=q, limit=2)["evidence"]:
            if e["quote"] in seen:
                continue
            seen.add(e["quote"])
            claims.append(_claim(f"“{e['quote']}” — {e.get('title') or 'filing'}, {e.get('date') or 'undated'}",
                                 [ctx.cite(e)], "quoted"))
    return {"claims": claims, "empty": None if claims else "No matching passages in indexed filings."}


def _peers(ctx: _Context, args: Dict[str, Any]) -> Dict[str, Any]:
    res = ctx.tool("peers")
    ev = res["evidence"]
    claims = [
        _claim(f"{r['name']}: GCI {tools._num(r['gci'])} ({r.get('tier') or 'provisional'}).", [ctx.cite(ev[r["ev"]])])
        for r in res["data"]["rows"]
    ]
    return {"claims": claims, "empty": None if claims else f"No scored peers in {res['data']['sector']} yet."}


def _questions(ctx: _Context, args: Dict[str, Any]) -> Dict[str, Any]:
    claims = []
    gr = ctx.tool("guidance_record")
    ev = gr["evidence"]
    for r in sorted(gr["data"]["rows"], key=lambda r: _period_sort(r["period"]), reverse=True):
        g = ctx.cite(ev[r["guidance_ev"]])
        a = ctx.cite(ev[r["actual_ev"]]) if r["actual_ev"] is not None else None
        if r["label"] == "missed":
            claims.append(_claim(
                f"{r['metric_name']} for {r['period']} came in at {r['actual']} against guidance of {r['guided']}. "
                "What drove the gap, and does current guidance rest on the same assumption?", [g, a]))
        elif r["label"] == "dropped":
            claims.append(_claim(
                f"Guidance on {r['metric_name']} for {r['period']} was withdrawn. "
                "What replaced it, and when will the company guide on it again?", [g]))
    cm = _commitments(ctx)
    cev = cm["evidence"]
    today = _today()
    for r in cm["data"]["rows"]:
        c = ctx.cite(cev[r["ev"]])
        if r.get("state") == "open" and (r.get("due_date") or "9999") < today:
            claims.append(_claim(f"{r['subject']} was due {r['due_period']}. Has it been completed, and if not, what is the new date?", [c]))
        elif r.get("state") == "quietly_dropped":
            claims.append(_claim(f"{r['subject']} has not been mentioned in recent disclosures. Is it still planned?", [c]))
        elif r.get("state") in ("missed", "partially_delivered"):
            claims.append(_claim(f"{r['subject']} was {r['state_label'].lower()}. What is the plan to close the gap?", [c]))
    og = ctx.tool("open_guidance")
    for r in og["data"]["rows"][:3]:
        claims.append(_claim(
            f"Current guidance for {r['metric_name']} ({r['period']}) is {r['guided']}. Does it still hold?",
            [ctx.cite(og["evidence"][r["guidance_ev"]])]))
    claims = claims[: int(args.get("limit") or 10)]
    return {"claims": claims, "empty": None if claims else "No missed, withdrawn or overdue items on the cited record to question."}


def _recent_filings(ctx: _Context, args: Dict[str, Any]) -> Dict[str, Any]:
    res = ctx.tool("recent_filings", limit=int(args.get("limit") or 5))
    claims = [
        _claim(f"“{e['quote']}” — {e.get('title') or 'filing'}, {e.get('date') or 'undated'}", [ctx.cite(e)], "quoted")
        for e in res["evidence"]
    ]
    return {"claims": claims, "empty": None if claims else "No filings with a forward-looking passage on record."}


def _peer_grid(ctx: _Context, args: Dict[str, Any]) -> Dict[str, Any]:
    peers = ctx.tool("peers", limit=int(args.get("limit") or 6))["data"]["rows"]
    focus = [{"company_id": ctx.company_id}] if ctx.tool("profile")["data"]["published"] else []
    claims = []
    for p in focus + peers:
        res = ctx.tool_for(p["company_id"], "guidance_record")
        rows, ev = res["data"]["rows"], res["evidence"]
        scored = [r for r in rows if r["label"] != "dropped"]
        if not scored:
            continue
        kept = sum(1 for r in scored if r["label"] in ("met", "exceeded"))
        cites = []
        for r in rows:
            cites.append(ctx.cite(ev[r["guidance_ev"]]))
            if r["actual_ev"] is not None:
                cites.append(ctx.cite(ev[r["actual_ev"]]))
        metrics = sorted({r["metric_name"] for r in scored})
        text = f"{res['data']['name']}: met or beat guidance in {kept} of {len(scored)} closed periods ({', '.join(metrics)})"
        dropped = sum(1 for r in rows if r["label"] == "dropped")
        if dropped:
            text += f"; withdrew guidance {dropped} time{'s' if dropped > 1 else ''}"
        row = {"Company": res["data"]["name"], "Met or beat": kept, "Closed periods": len(scored),
               "Guidance withdrawn": dropped, "Metrics": ", ".join(metrics)}
        claims.append(_claim(text + ".", cites, "computed", row=row))
    return {"claims": claims, "empty": None if claims else "No sector peers with cited, closed guidance periods yet."}


_NO_PROJECT = "Run this Skill inside a Project with uploaded files."
_HAS_FIGURE = re.compile(r"\d")

DILIGENCE_CHECKLIST: List[tuple] = [
    ("Audited financial statements", ("balance sheet", "profit and loss", "audited", "cash flow statement")),
    ("Debt schedule", ("debt schedule", "borrowing", "term loan", "repayment schedule")),
    ("Related-party transactions", ("related party", "related-party")),
    ("Shareholding / cap table", ("shareholding", "cap table", "shareholder")),
    ("Customer contracts and concentration", ("customer contract", "top customers", "concentration", "master service agreement")),
    ("Litigation and contingent liabilities", ("litigation", "legal proceedings", "contingent liabilit")),
    ("Capex plan", ("capex", "capital expenditure")),
    ("Credit rating", ("credit rating", "rating rationale")),
    ("Statutory and tax compliance", ("gst", "income tax", "statutory dues", "tax demand")),
]

DRIVER_TERMS = (
    "revenue", "sales", "volume", "realisation", "realization", "price", "margin", "ebitda", "pat",
    "capex", "utilisation", "utilization", "capacity", "order", "inflow", "debt", "working capital",
    "growth", "cost", "headcount", "store", "branch", "aum", "nim", "loan", "deposit", "asp", "arpu",
)


def _diligence_claims(ctx: _Context, args: Dict[str, Any]) -> Dict[str, Any]:
    if not ctx.project:
        return {"claims": [], "empty": _NO_PROJECT}
    from app.services.commitment_extract import _FORWARD

    picked = [e for e in ctx.uploads() if _HAS_FIGURE.search(e["quote"]) or _FORWARD.search(e["quote"])]
    picked = [e for e in picked if len(e["quote"]) >= 25][: int(args.get("limit") or 8)]
    claims, missing = [], []
    for e in picked:
        claims.append(_claim(f"Your file says: “{e['quote']}” ({e['title'].split(' — ')[0]})", [ctx.cite(e)], "quoted"))
        query = " ".join(e["quote"].split()[:14])
        hits = ctx.tool("filing_search", query=query, limit=1)["evidence"]
        if hits:
            h = hits[0]
            claims.append(_claim(
                f"Closest public filing: “{h['quote']}” — {h.get('title') or 'filing'}, {h.get('date') or 'undated'}",
                [ctx.cite(h)], "quoted"))
        else:
            missing.append(f"No public filing passage matched “{query}…”")
    return {"claims": claims, "missing": missing,
            "empty": None if claims else "No figures or forward-looking statements found in the uploaded files."}


def _diligence_gaps(ctx: _Context, args: Dict[str, Any]) -> Dict[str, Any]:
    if not ctx.project:
        return {"claims": [], "empty": _NO_PROJECT}
    rows = ctx.uploads()
    claims, missing = [], []
    for label, terms in DILIGENCE_CHECKLIST:
        hit = next((e for e in rows if any(t in e["quote"].lower() for t in terms)), None)
        if hit:
            claims.append(_claim(f"{label}: covered in {hit['title'].split(' — ')[0]}.", [ctx.cite(hit)], "record"))
        else:
            missing.append(f"{label}: not found in the uploaded files")
    return {"claims": claims, "missing": missing, "empty": None if claims else "None of the checklist items appear in the uploads."}


def _model_drivers(ctx: _Context, args: Dict[str, Any]) -> Dict[str, Any]:
    if not ctx.project:
        return {"claims": [], "empty": _NO_PROJECT}
    from datetime import date, timedelta

    days = int(args.get("lookback_days") or 7)
    since = (date.fromisoformat(_today()) - timedelta(days=days)).isoformat()
    drivers = []
    seen: set[str] = set()
    for e in ctx.uploads():
        if e.get("file_kind") not in ("xlsx", "csv"):
            continue
        label = e["quote"].split(" | ")[0].strip()
        key = label.lower()
        if 2 < len(label) <= 60 and key not in seen and any(t in key for t in DRIVER_TERMS):
            seen.add(key)
            drivers.append((label, e))
    drivers = drivers[: int(args.get("limit") or 10)]
    claims, missing = [], []
    for label, e in drivers:
        claims.append(_claim(f"Model driver: {label} ({e['title'].split(' — ')[0]}).", [ctx.cite(e)], "record"))
        hits = ctx.tool("filing_search", query=label, limit=1)["evidence"]
        if not hits:
            missing.append(f"{label}: no filing passage on this driver")
            continue
        h = hits[0]
        fresh = str(h.get("date") or "") >= since
        when = f"filed in the last {days} days" if fresh else f"no new filing in the last {days} days"
        claims.append(_claim(
            f"Latest filing on {label} ({when}): “{h['quote']}” — {h.get('title') or 'filing'}, {h.get('date') or 'undated'}",
            [ctx.cite(h)], "quoted"))
    return {"claims": claims, "missing": missing,
            "empty": None if claims else "No model drivers found — upload the model as XLSX or CSV with driver names in the first column."}


def _language_shift(ctx: _Context, args: Dict[str, Any]) -> Dict[str, Any]:
    res = ctx.tool("language_shift", limit=int(args.get("limit") or 6))
    ev, data = res["evidence"], res["data"]
    if not data.get("previous"):
        return {"claims": [], "empty": "Fewer than two dated filings on record, so there is no earlier call to compare with."}
    claims = []
    for r in data["rows"]:
        p = ev[r["previous_ev"]]
        if r["change"] == "not_repeated":
            claims.append(_claim(
                f"{r['topic']}: said on {p.get('date')} (“{p['quote']}”); not repeated in the most recent filings we hold.",
                [ctx.cite(p)], "quoted"))
        else:
            latest = ev[r["latest_ev"]]
            claims.append(_claim(
                f"{r['topic']}: on {p.get('date')} management said “{p['quote']}”; on {latest.get('date')} it said “{latest['quote']}”.",
                [ctx.cite(p), ctx.cite(latest)], "quoted"))
    return {"claims": claims,
            "empty": None if claims else "No change in the figures management gave on revenue, margin, capex, debt, orders, volume, demand, pricing or capacity since the previous filing date."}


def _quote_line(e: Dict[str, Any]) -> str:
    if e.get("kind") == "upload":
        return f"Your file says: “{e['quote']}” ({e['title'].split(' — ')[0]})"
    return f"“{e['quote']}” — {e.get('title') or 'filing'}, {e.get('date') or 'undated'}"


def _event_tool(ctx: _Context, terms: List[str], limit: int, figures: bool = False, kinds: tuple = ()) -> List[Dict[str, Any]]:
    in_project = bool(ctx.org_id and ctx.project)
    return ctx.tool(
        "event_passages", terms=tuple(terms), limit=limit, figures=figures, kinds=kinds,
        org_id=ctx.org_id if in_project else None,
        project_id=ctx.project["project_id"] if in_project else None,
    )["evidence"]


def _passages(ctx: _Context, args: Dict[str, Any]) -> Dict[str, Any]:
    ev = _event_tool(ctx, list(args.get("terms") or []), int(args.get("limit") or 5),
                     bool(args.get("figures")), tuple(args.get("kinds") or ()))
    claims = [_claim(_quote_line(e), [ctx.cite(e)], "quoted") for e in ev]
    return {"claims": claims, "empty": None if claims else (args.get("empty") or "No passage on this in the filings we hold.")}


def _linked_commitments(ctx: _Context, args: Dict[str, Any]) -> Dict[str, Any]:
    res = _commitments(ctx)
    ev = res["evidence"]
    types = set(args.get("types") or [])
    terms = tuple(t.lower() for t in args.get("terms") or [])
    claims = []
    for r in res["data"]["rows"]:
        blob = f"{r.get('subject') or ''} {r.get('quote') or ''}".lower()
        if (types and r.get("type") in types) or (terms and any(t in blob for t in terms)):
            claims.append(_claim(f"{r['subject']} — {r['state_label']}, due {r['due_period']}{_tag(r)}.",
                                 [ctx.cite(ev[r["ev"]])], "record"))
    return {"claims": claims, "empty": None if claims else "No commitments on record that this event touches."}


DEBATE_TOPICS: Dict[str, List[str]] = {
    "Demand": ["demand"],
    "Margin": ["margin", "ebitda"],
    "Capex": ["capex", "capital expenditure"],
    "Debt and liquidity": ["debt", "leverage", "liquidity", "borrowing"],
    "Capacity and plants": ["capacity", "plant", "facility", "commissioning"],
    "Regulation and compliance": ["compliance", "inspection", "observation", "approval", "order"],
}
VOICES = (("company", "Company"), ("agency", "Rating agency"), ("regulator", "Regulator"))


def _voice(e: Dict[str, Any]) -> str:
    low = str(e.get("quote") or "").lower()
    if e.get("event_kind") == "credit_rating" or any(t in low for t in tools.AGENCY_TERMS):
        return "agency"
    if e.get("event_kind") == "usfda" or any(t in low for t in tools.REGULATOR_TERMS):
        return "regulator"
    return "company"


def _debate_map(ctx: _Context, args: Dict[str, Any]) -> Dict[str, Any]:
    topics = args.get("topics") or DEBATE_TOPICS
    claims, missing = [], []
    for topic, terms in topics.items():
        found: Dict[str, Dict[str, Any]] = {}
        for e in _event_tool(ctx, list(terms), 12):
            found.setdefault(_voice(e), e)
        if not found:
            continue
        for key, label in VOICES:
            if key in found:
                claims.append(_claim(f"{topic} — {label}: {_quote_line(found[key])}", [ctx.cite(found[key])], "quoted"))
        if len(found) == 1:
            only = dict(VOICES)[next(iter(found))].lower()
            missing.append(f"{topic}: only the {only} view is on record")
    return {"claims": claims, "missing": missing,
            "empty": None if claims else "No statements on these topics in the filings we hold."}


def _trigger_section(ctx: _Context, trigger: Dict[str, Any]) -> Dict[str, Any]:
    res = ctx.tool("document_passages", doc_id=str(trigger.get("doc_id") or ""), limit=5)
    claims = [
        _claim(f"“{e['quote']}”", [ctx.cite(e)], "quoted") for e in res["evidence"]
    ]
    title = trigger.get("title") or "new filing"
    return {
        "id": "trigger",
        "title": f"What the new filing says ({title}, {trigger.get('date') or 'undated'})",
        "claims": claims,
        "empty": "The new filing has no forward-looking passage we could quote.",
    }


BUILDERS: Dict[str, Builder] = {
    "delivery_record": _delivery_record,
    "open_guidance": _open_guidance,
    "commitments_open": _commitments_open,
    "commitments_closed": _commitments_closed,
    "filing_quotes": _filing_quotes,
    "peers": _peers,
    "questions": _questions,
    "recent_filings": _recent_filings,
    "peer_grid": _peer_grid,
    "diligence_claims": _diligence_claims,
    "diligence_gaps": _diligence_gaps,
    "model_drivers": _model_drivers,
    "language_shift": _language_shift,
    "passages": _passages,
    "linked_commitments": _linked_commitments,
    "debate_map": _debate_map,
}
assert set(BUILDERS) == skill_specs.KNOWN_BUILDERS


def _disproof(ctx: _Context, queries: List[str]) -> Dict[str, Any]:
    claims = []
    seen: set[str] = set()
    for q in queries:
        for e in ctx.tool("filing_search", query=q, limit=2)["evidence"]:
            if e["quote"] in seen:
                continue
            seen.add(e["quote"])
            claims.append(_claim(f"“{e['quote']}” — {e.get('title') or 'filing'}, {e.get('date') or 'undated'}",
                                 [ctx.cite(e)], "quoted"))
    return {"claims": claims, "queries": queries}


def _llm_summary(ctx: _Context, name: str, focus: Optional[List[str]] = None) -> Dict[str, Any]:
    from app.services import llm_client

    listing = "\n".join(
        f"[{c['n']}] {c.get('title')} ({c.get('date') or 'undated'}): {c.get('quote')}" for c in ctx.citations[:30]
    )
    if focus:
        listing += "\n\nAnalyst focus (topics to prioritise; not a source, never cite it):\n" + "\n".join(
            f"- {f}" for f in focus[:20])
    raw = llm_client.chat_completion(
        [
            {"role": "system", "content": (
                "Write 3 to 5 plain sentences summarising the company's delivery record from the numbered sources only. "
                "End every sentence with the source numbers it relies on, like [2] or [1][4]. Copy numbers exactly as "
                "they appear in the sources. No opinions, no recommendations, no forecasts.")},
            {"role": "user", "content": f"Company: {name}\nSources:\n{listing}"},
        ],
        max_tokens=600,
        wait=False,
        reasoning="low",
    )
    checked = verify_text(raw, ctx.citations)
    return {"claims": checked["kept"], "removed": checked["removed"], "model": llm_client.llm_chat_model()}


def _renumber(sections: List[Dict[str, Any]], citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    order: Dict[int, int] = {}
    for s in sections:
        for c in s["claims"]:
            for n in c["cites"]:
                order.setdefault(n, len(order) + 1)
    by_old = {c["n"]: c for c in citations}
    for s in sections:
        for c in s["claims"]:
            c["cites"] = sorted({order[n] for n in c["cites"]})
            c["text"] = re.sub(r"\s*\[\d+\]", "", c["text"]).strip()
    return [{**by_old[old], "n": new} for old, new in sorted(order.items(), key=lambda kv: kv[1])]


def _render_markdown(out: Dict[str, Any]) -> str:
    lines = [f"# {out['skill']['title']}: {out['company_name']}", "",
             f"Data as of {out['as_of']}. {DISCLAIMER}", ""]
    if out.get("headline"):
        lines += [out["headline"], ""]
    for s in out["sections"]:
        if not s["claims"]:
            continue
        lines.append(f"## {s['title']}")
        lines += [f"- {c['text']} " + "".join(f"[{n}]" for n in c["cites"]) for c in s["claims"]]
        lines.append("")
    if out["not_found"]:
        lines.append("## What we could not find")
        lines += [f"- {s}" for s in out["not_found"]]
        lines.append("")
    lines.append("## Sources")
    for c in out["citations"]:
        lines.append(f"{c['n']}. {c.get('title') or 'Source'} — {c.get('date') or 'undated'} — {c.get('source_url')}")
        lines.append(f"   > {c.get('quote')}")
    return "\n".join(lines)


def run_skill(
    skill_id: str,
    company_id: str,
    *,
    include_unreviewed: bool = False,
    use_llm: Optional[bool] = None,
    trigger: Optional[Dict[str, Any]] = None,
    org_id: Optional[str] = None,
    project: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """``trigger``: the new filing that caused a Monitor run (``doc_id``, ``title``, ``date``...).

    ``project``: a Project record of ``org_id``; its uploads become citable and its
    memory is passed to the optional model summary as focus, never as a source.
    """
    spec = skill_specs.get_skill(skill_id)
    ctx = _Context(company_id, include_unreviewed, org_id=org_id, project=project)
    prof = ctx.tool("profile")["data"]

    headline_claims = []
    if prof["published"]:
        n = ctx.cite(ctx.tool("profile")["evidence"][0])
        headline_claims.append(_claim(
            f"{prof['name']}: GCI {tools._num(prof['gci_score'])} ({prof['confidence_tier'] or 'provisional'}), "
            f"data as of {prof['as_of'] or 'n/a'}.", [n]))

    raw_sections = []
    if trigger:
        raw_sections.append(_trigger_section(ctx, trigger))
    extra_not_found: List[str] = []
    for sec in spec["sections"]:
        built = BUILDERS[sec["builder"]](ctx, sec.get("args") or {})
        raw_sections.append({"id": sec["id"], "title": sec["title"], "claims": built["claims"], "empty": built.get("empty")})
        extra_not_found += [f"{sec['title']}: {m}" for m in built.get("missing") or []]

    disproof_q = (spec.get("disproof") or {}).get("queries") or []
    disproof = _disproof(ctx, disproof_q) if disproof_q else None

    summary_section = None
    llm_info: Dict[str, Any] = {"used": False}
    if use_llm is None:
        from app.services.feature_flags import analyst_llm_enabled
        from app.services.llm_client import llm_configured

        use_llm = analyst_llm_enabled() and llm_configured()
    if use_llm and ctx.citations:
        try:
            focus = [m["text"] for m in (project or {}).get("memory") or []]
            s = _llm_summary(ctx, prof["name"], focus)
            summary_section = {"id": "summary", "title": "Summary", "claims": s["claims"], "empty": None}
            llm_info = {"used": True, "model": s["model"], "removed": len(s["removed"])}
        except Exception as exc:  # summary is optional; the cited sections stand alone
            llm_info = {"used": False, "error": type(exc).__name__}

    all_sections = ([summary_section] if summary_section else []) + raw_sections
    if headline_claims:
        all_sections.insert(0, {"id": "headline", "title": "Headline", "claims": headline_claims, "empty": None})
    if disproof is not None:
        all_sections.append({
            "id": "counter_evidence",
            "title": "Evidence that may cut against this read",
            "claims": disproof["claims"],
            "empty": "Searched indexed filings for delays, revisions and adverse orders; nothing found." if not disproof["claims"] else None,
        })

    kept_total, removed = 0, []
    for s in all_sections:
        checked = verify_claims(s["claims"], ctx.citations)
        s["claims"] = checked["kept"]
        kept_total += len(checked["kept"])
        removed += [{**r, "section": s["id"]} for r in checked["removed"]]

    citations = _renumber(all_sections, ctx.citations)
    headline = None
    if all_sections and all_sections[0]["id"] == "headline":
        h = all_sections.pop(0)
        if h["claims"]:
            c = h["claims"][0]
            headline = f"{c['text']} " + "".join(f"[{n}]" for n in c["cites"])
    not_found = [f"{s['title']}: {s['empty']}" for s in all_sections if not s["claims"] and s.get("empty")]
    not_found += extra_not_found

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    run_id = "run_" + uuid.uuid4().hex[:12]
    out: Dict[str, Any] = {
        "run_id": run_id,
        "engine": ENGINE,
        "skill": {k: spec.get(k) for k in ("id", "version", "title", "description")},
        "company_id": prof["company_id"],
        "company_name": prof["name"],
        "ticker": prof["ticker"],
        "as_of": _today(),
        "generated_at": generated_at,
        "headline": headline,
        "sections": all_sections,
        "not_found": not_found,
        "citations": citations,
        "refused": kept_total == 0,
        "verifier": {"kept": kept_total, "removed": len(removed), "removed_claims": removed},
        "llm": llm_info,
        "includes_unreviewed": include_unreviewed,
        "trigger": trigger,
        "project": {"project_id": project["project_id"], "name": project["name"],
                    "memory_items": len(project.get("memory") or [])} if project else None,
        "disclaimer": DISCLAIMER,
    }
    out["evidence_receipt"] = {
        "run_id": run_id,
        "skill_id": spec["id"],
        "skill_version": spec["version"],
        "engine": ENGINE,
        "model": llm_info.get("model"),
        "generated_at": generated_at,
        "trigger_doc_id": (trigger or {}).get("doc_id"),
        "project_id": (project or {}).get("project_id"),
        "tool_calls": ctx.tool_calls,
        "sources": [
            {
                "n": c["n"],
                "kind": c.get("kind"),
                "title": c.get("title"),
                "source_url": c.get("source_url"),
                "date": c.get("date"),
                "doc_id": c.get("doc_id"),
                "quote_sha256": hashlib.sha256(str(c.get("quote") or "").encode("utf-8")).hexdigest(),
            }
            for c in citations
        ],
    }
    out["markdown"] = _render_markdown(out)
    return out
