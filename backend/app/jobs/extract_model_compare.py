"""Compare extraction models on identical stored filing pieces (WS5 model choice).

Documents come from the store (``GET /api/documents`` saved as ``{company_id}.json``);
nothing is fetched from an exchange. Pieces are cut with ``disclosures.read_chunks``,
read through ``disclosures.llm_extract`` and every item is checked with
``disclosures._check_item`` — the production path end to end.

  python -m app.jobs.extract_model_compare sample --docs DIR --out RUN
  python -m app.jobs.extract_model_compare run --out RUN --model gemini:gemini-3.8-flash \
      --model bedrock:openai.gpt-oss-120b-1:0
  python -m app.jobs.extract_model_compare report --out RUN --baseline gemini:gemini-3.8-flash

Answers are cached per model in ``RUN/answers/``; a rerun reads only missing pieces.
Gemini uses ``GEMINI_API_KEY`` from the environment; Bedrock uses the AWS profile or role.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.data.metric_catalog import metrics_for_market
from app.services import disclosures, llm_client

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
SINCE = "2024-01-01"
PICKS = (("concall", "transcript"), ("presentation", "results", "guidance", "ir_guidance"))
OUTLOOK = re.compile(r"\b(outlook|guidance|we expect|we aim|target)\b", re.I)

#: USD per 1M tokens (input, output) at standard, and the Flex/Batch discount. List prices, Nov 2026.
PRICES: Dict[str, Tuple[float, float]] = {
    "gemini-3.8-flash": (0.75, 3.75),
    "openai.gpt-oss-120b-1:0": (0.1545, 0.618),
    "openai.gpt-oss-20b-1:0": (0.0721, 0.309),
    "apac.amazon.nova-lite-v1:0": (0.071, 0.28),
    "global.amazon.nova-2-lite-v1:0": (0.35, 2.95),
    "in.anthropic.claude-haiku-4-5-20251001-v1:0": (1.10, 5.50),
    "deepseek.v3.2": (0.74, 2.22),
}
FLEX_DISCOUNT = 0.5


def _piece(company_id: str, doc: Dict[str, Any], chunk: str, n: int) -> Dict[str, Any]:
    return {
        "id": f"{company_id}:{str(doc.get('doc_id'))[:8]}:{n}",
        "company_id": company_id,
        "company_name": company_id,
        "doc_type": doc.get("doc_type"),
        "date": str(doc.get("date"))[:10],
        "url": doc.get("url"),
        "text": chunk,
    }


def sample(docs_dir: Path, *, annual_reports: int = 5) -> List[Dict[str, Any]]:
    """Per company: the opening piece of the newest call and of the newest deck or result
    since 2024; plus an outlook piece from a few annual reports."""
    pieces: List[Dict[str, Any]] = []
    reports = 0
    for path in sorted(docs_dir.glob("*.json")):
        company_id = path.stem
        docs = [d for d in json.loads(path.read_text()).get("documents") or [] if str(d.get("date")) >= SINCE]
        docs.sort(key=lambda d: str(d.get("date")), reverse=True)
        for kinds in PICKS:
            doc = next((d for d in docs if d.get("doc_type") in kinds and d.get("text")), None)
            if doc is None:
                continue
            chunks = [c for c in disclosures.read_chunks(str(doc["text"])) if disclosures._worth_reading(c)]
            if chunks:
                pieces.append(_piece(company_id, doc, chunks[0], 0))
        report = next((d for d in docs if d.get("doc_type") == "annual_report" and d.get("text")), None)
        if report is not None and reports < annual_reports:
            chunks = disclosures.read_chunks(str(report["text"]))
            hit = next((i for i, c in enumerate(chunks) if disclosures._worth_reading(c) and len(OUTLOOK.findall(c)) >= 3), None)
            if hit is not None:
                pieces.append(_piece(company_id, report, chunks[hit], hit))
                reports += 1
    return pieces


def _use(spec: str) -> str:
    provider, model = spec.split(":", 1)
    os.environ["INTELLENS_LLM_MODEL"] = model
    if provider == "bedrock":
        os.environ["INTELLENS_LLM_PROVIDER"] = "bedrock"
    else:
        os.environ.pop("INTELLENS_LLM_PROVIDER", None)
        os.environ["INTELLENS_LLM_BASE_URL"] = GEMINI_BASE if provider == "gemini" else "https://api.openai.com/v1"
    return model


def _slug(spec: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", spec)


def run_model(spec: str, pieces: List[Dict[str, Any]], out: Path, *, workers: int = 4) -> Dict[str, Any]:
    _use(spec)
    path = out / "answers" / f"{_slug(spec)}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    answers: Dict[str, Any] = json.loads(path.read_text()) if path.exists() else {}
    todo = [p for p in pieces if "found" not in (answers.get(p["id"]) or {})]

    def read(p: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        started = time.time()
        try:
            found = disclosures.llm_extract(p["text"], company_name=p["company_name"], market_id="IN", doc_date=p["date"])
            return p["id"], {"found": found, "seconds": round(time.time() - started, 1), "usage": llm_client.last_usage()}
        except Exception as exc:  # noqa: BLE001 — recorded per piece
            return p["id"], {"error": str(exc)[:300], "seconds": round(time.time() - started, 1)}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for pid, answer in pool.map(read, todo):
            answers[pid] = answer
    path.write_text(json.dumps(answers, indent=1))
    return answers


def checked_items(found: Dict[str, Any], text: str, allowed: set) -> Tuple[set, Dict[str, int]]:
    """Accepted items as comparable keys, and drop counts by reason."""
    keys: set = set()
    dropped: Dict[str, int] = {}
    for kind, items in (("guidance", found.get("guidance") or []), ("result", found.get("results") or [])):
        for item in items:
            row, why = disclosures._check_item(kind, item, text, "IN", None, allowed)
            if row is None:
                dropped[str(why)] = dropped.get(str(why), 0) + 1
                continue
            keys.add((kind, row["metric"], row["period"], round(row["low"], 4), round(row["high"], 4)))
    return keys, dropped


def _cost(model: str, tokens_in: int, tokens_out: int) -> Optional[float]:
    price = PRICES.get(model)
    return None if price is None else (tokens_in * price[0] + tokens_out * price[1]) / 1e6


def report(pieces: List[Dict[str, Any]], answers_by_spec: Dict[str, Dict[str, Any]], baseline: str) -> List[Dict[str, Any]]:
    allowed = {m["id"] for m in metrics_for_market("IN")}
    texts = {p["id"]: p["text"] for p in pieces}
    accepted: Dict[str, Dict[str, set]] = {}
    rows = []
    for spec, answers in answers_by_spec.items():
        accepted[spec] = {}
        drops: Dict[str, int] = {}
        ok = errors = tin = tout = 0
        seconds: List[float] = []
        for pid in texts:
            answer = answers.get(pid) or {}
            if "found" not in answer:
                errors += 1 if "error" in answer else 0
                continue
            ok += 1
            keys, dropped = checked_items(answer["found"], texts[pid], allowed)
            accepted[spec][pid] = keys
            for why, n in dropped.items():
                drops[why] = drops.get(why, 0) + n
            tin += int((answer.get("usage") or {}).get("input") or 0)
            tout += int((answer.get("usage") or {}).get("output") or 0)
            seconds.append(float(answer.get("seconds") or 0))
        model = spec.split(":", 1)[1]
        cost = _cost(model, tin, tout)
        rows.append(
            {
                "model": spec,
                "pieces_read": ok,
                "errors": errors,
                "guidance": sum(1 for ks in accepted[spec].values() for k in ks if k[0] == "guidance"),
                "results": sum(1 for ks in accepted[spec].values() for k in ks if k[0] == "result"),
                "dropped": drops,
                "median_seconds": sorted(seconds)[len(seconds) // 2] if seconds else None,
                "tokens_in_per_piece": round(tin / ok) if ok else None,
                "tokens_out_per_piece": round(tout / ok) if ok else None,
                "usd_per_1000_pieces": round(cost / ok * 1000, 2) if cost is not None and ok else None,
                "usd_per_1000_pieces_flex": round(cost / ok * 1000 * FLEX_DISCOUNT, 2) if cost is not None and ok else None,
            }
        )
    base = accepted.get(baseline) or {}
    for row in rows:
        mine = accepted[row["model"]]
        shared = [pid for pid in mine if pid in base]
        base_items = sum(len(base[pid]) for pid in shared)
        hits = sum(len(base[pid] & mine[pid]) for pid in shared)
        row["recall_vs_baseline"] = round(hits / base_items, 3) if base_items else None
        row["items_not_in_baseline"] = sum(len(mine[pid] - base[pid]) for pid in shared)
    return rows


def main(argv: Optional[Iterable[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("step", choices=("sample", "run", "report"))
    ap.add_argument("--docs", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", action="append", default=[])
    ap.add_argument("--baseline", default="gemini:gemini-3.8-flash")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(list(argv) if argv is not None else None)
    pieces_path = args.out / "pieces.json"
    if args.step == "sample":
        args.out.mkdir(parents=True, exist_ok=True)
        pieces = sample(args.docs)
        pieces_path.write_text(json.dumps(pieces, indent=1))
        print(json.dumps({"pieces": len(pieces), "chars": sum(len(p["text"]) for p in pieces)}))
        return 0
    pieces = json.loads(pieces_path.read_text())
    if args.step == "run":
        for spec in args.model:
            answers = run_model(spec, pieces, args.out, workers=args.workers)
            failed = sum(1 for a in answers.values() if "error" in a)
            print(json.dumps({"model": spec, "answers": len(answers), "errors": failed}))
        return 0
    answers_by_spec = {}
    for spec in args.model or [args.baseline]:
        path = args.out / "answers" / f"{_slug(spec)}.json"
        if path.exists():
            answers_by_spec[spec] = json.loads(path.read_text())
    print(json.dumps(report(pieces, answers_by_spec, args.baseline), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
