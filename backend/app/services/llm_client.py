"""OpenAI-compatible LLM + embeddings client (urllib only — no SDK required).

Uses OPENAI_API_KEY or INTELLENS_LLM_API_KEY. When unset, callers fall back locally.
"""

from __future__ import annotations

import json
import math
import os
import re
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from typing import Any, Dict, List, Optional, Sequence


def llm_base_url() -> str:
    return (
        os.environ.get("INTELLENS_LLM_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or "https://api.openai.com/v1"
    ).rstrip("/")


def is_gemini() -> bool:
    return "generativelanguage.googleapis.com" in llm_base_url()


# Gemini 3.x counts hidden reasoning against max_tokens; ~1.1k-5k tokens on a 12k-char chunk.
GEMINI_THINKING_HEADROOM = 8192


def llm_api_key() -> Optional[str]:
    key = (
        os.environ.get("INTELLENS_LLM_API_KEY")
        or (os.environ.get("GEMINI_API_KEY") if is_gemini() else None)
        or os.environ.get("OPENAI_API_KEY")
        or ""
    ).strip()
    return key or None


def llm_chat_model() -> str:
    return os.environ.get("INTELLENS_LLM_MODEL") or "gpt-4o-mini"


def embed_model() -> str:
    return os.environ.get("INTELLENS_EMBED_MODEL") or "text-embedding-3-small"


def llm_configured() -> bool:
    return llm_api_key() is not None


class LLMRateLimited(RuntimeError):
    pass


_RATE_LOCK = threading.Lock()
_CALL_TIMES: "deque[float]" = deque()


def llm_rate_per_min() -> int:
    """Calls per rolling minute across the process; 0 disables the limit."""
    return int(os.environ.get("INTELLENS_LLM_RATE_PER_MIN", "4"))


def _acquire_slot(*, wait: bool, clock=time.monotonic, sleep=time.sleep) -> None:
    """Background jobs wait for a slot; a user-facing call fails fast and falls back."""
    limit = llm_rate_per_min()
    if limit <= 0:
        return
    while True:
        with _RATE_LOCK:
            now = clock()
            while _CALL_TIMES and now - _CALL_TIMES[0] >= 60.0:
                _CALL_TIMES.popleft()
            if len(_CALL_TIMES) < limit:
                _CALL_TIMES.append(now)
                return
            delay = 60.0 - (now - _CALL_TIMES[0])
        if not wait:
            raise LLMRateLimited(f"LLM rate limit {limit}/min reached")
        sleep(max(delay, 0.05))


def reset_rate_limit() -> None:
    with _RATE_LOCK:
        _CALL_TIMES.clear()


def _post_json(
    path: str, payload: Dict[str, Any], *, timeout: float = 45.0, wait: bool = True
) -> Dict[str, Any]:
    key = llm_api_key()
    if not key:
        raise RuntimeError("LLM API key not configured")
    _acquire_slot(wait=wait)
    url = f"{llm_base_url()}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": "CiteAlpha-GCI/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:500]
        raise RuntimeError(f"LLM HTTP {e.code}: {body}") from e


def chat_completion(
    messages: Sequence[Dict[str, str]],
    *,
    temperature: float = 0.0,
    max_tokens: int = 1200,
    wait: bool = True,
    reasoning: Optional[str] = None,
    timeout: float = 45.0,
    service_tier: Optional[str] = None,
) -> str:
    """``max_tokens`` budgets the answer; Gemini's hidden reasoning gets its own headroom."""
    payload: Dict[str, Any] = {
        "model": llm_chat_model(),
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": list(messages),
    }
    if is_gemini():
        if reasoning:
            payload["reasoning_effort"] = reasoning
        if reasoning not in ("none", "minimal", "low"):
            payload["max_tokens"] = max_tokens + GEMINI_THINKING_HEADROOM
        if service_tier:
            payload["service_tier"] = service_tier
    doc = _post_json("/chat/completions", payload, timeout=timeout, wait=wait)
    choices = doc.get("choices") or []
    if not choices:
        raise RuntimeError("LLM returned no choices")
    if choices[0].get("finish_reason") == "length":
        raise RuntimeError("LLM answer cut off at max_tokens")
    content = (choices[0].get("message") or {}).get("content") or ""
    return str(content).strip()


def search_model() -> str:
    if os.environ.get("INTELLENS_LLM_SEARCH_MODEL"):
        return os.environ["INTELLENS_LLM_SEARCH_MODEL"]
    return llm_chat_model() if is_gemini() else "gpt-4.1-mini"


_URL_IN_TEXT = re.compile(r"https?://[^\s<>()\"'\]]+")
_GEMINI_REDIRECT = "vertexaisearch.cloud.google.com/grounding-api-redirect/"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


def _resolve_redirect(url: str, timeout: float = 20.0) -> str:
    """Gemini cites a Google redirect; the allowlist needs the real address."""
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        opener.open(urllib.request.Request(url, method="HEAD"), timeout=timeout)
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
            return str(e.headers["Location"])
    except (urllib.error.URLError, OSError):
        pass
    return ""


def _gemini_search(prompt: str, timeout: float) -> Dict[str, Any]:
    key = llm_api_key()
    if not key:
        raise RuntimeError("LLM API key not configured")
    root = re.sub(r"/openai$", "", llm_base_url())
    _acquire_slot(wait=True)
    req = urllib.request.Request(
        f"{root}/models/{search_model()}:generateContent",
        data=json.dumps(
            {"contents": [{"parts": [{"text": prompt}]}], "tools": [{"google_search": {}}]}
        ).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:500]
        raise RuntimeError(f"LLM HTTP {e.code}: {body}") from e


def web_search_links(prompt: str, *, timeout: float = 120.0) -> List[Dict[str, str]]:
    """Ask the model to search the web; return the links it cited or wrote.

    The links are leads only. The caller fetches each through its own allowlist
    and never takes a number or quote from this response.
    """
    links: List[Dict[str, str]] = []
    seen = set()

    def add(url: str, title: str = "") -> None:
        url = url.rstrip(".,;:")
        if _GEMINI_REDIRECT in url:
            url = _resolve_redirect(url)
        if url and url not in seen:
            seen.add(url)
            links.append({"url": url, "title": title})

    if is_gemini():
        doc = _gemini_search(prompt, timeout)
        for cand in doc.get("candidates") or []:
            for part in (cand.get("content") or {}).get("parts") or []:
                for url in _URL_IN_TEXT.findall(str(part.get("text") or "")):
                    add(url)
            for chunk in (cand.get("groundingMetadata") or {}).get("groundingChunks") or []:
                web = chunk.get("web") or {}
                if web.get("uri"):
                    add(str(web["uri"]), str(web.get("title") or ""))
        return links

    tool = os.environ.get("INTELLENS_LLM_SEARCH_TOOL") or "web_search"
    doc = _post_json(
        "/responses",
        {"model": search_model(), "tools": [{"type": tool}], "input": prompt},
        timeout=timeout,
    )
    for item in doc.get("output") or []:
        if item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            for ann in part.get("annotations") or []:
                if ann.get("type") == "url_citation" and ann.get("url"):
                    add(str(ann["url"]), str(ann.get("title") or ""))
            for url in _URL_IN_TEXT.findall(str(part.get("text") or "")):
                add(url)
    return links


def embed_texts(texts: Sequence[str]) -> List[List[float]]:
    if not texts:
        return []
    # OpenAI embeds API accepts batch
    doc = _post_json(
        "/embeddings",
        {"model": embed_model(), "input": list(texts)},
        timeout=60.0,
        wait=False,
    )
    data = sorted(doc.get("data") or [], key=lambda r: int(r.get("index", 0)))
    return [list(r.get("embedding") or []) for r in data]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(y * y for y in b)) or 1e-9
    return float(dot / (na * nb))


_GUIDANCE_JSON_HINT = """Extract quantified management guidance from the transcript.
Return ONLY a JSON array. Each object keys:
metric (one of: {metric_ids}; skip guidance that fits none),
guided_value (number in the metric's unit: pct = percent e.g. 12.5, inr_cr = INR crore e.g. 26000, mmt = million tonnes),
guided_low, guided_high, guided_text, quote_span,
speaker (CFO|CEO|Management), confidence (0.5-0.95).
If none found return []. No markdown fences."""


def _guidance_prompt() -> str:
    from app.data.metric_catalog import METRICS

    ids = ", ".join(f"{m['id']} [{m.get('unit')}]" for m in METRICS)
    return _GUIDANCE_JSON_HINT.replace("{metric_ids}", ids)


def extract_guidance_via_llm(
    text: str,
    *,
    company_id: str,
    period: str,
    source_ref: str,
    wait: bool = True,
) -> List[Dict[str, Any]]:
    """Call chat model; parse JSON array of statements. Raises on transport/parse failure."""
    excerpt = (text or "")[:12000]
    raw = chat_completion(
        [
            {"role": "system", "content": _guidance_prompt()},
            {
                "role": "user",
                "content": f"company_id={company_id} period={period}\n\n{excerpt}",
            },
        ],
        max_tokens=4096,
        wait=wait,
    )
    # Strip optional ```json fences
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    parsed = json.loads(cleaned)
    if not isinstance(parsed, list):
        raise RuntimeError("LLM extract did not return a JSON array")
    from app.data.metric_catalog import normalize_metric, normalize_statement_metrics

    out: List[Dict[str, Any]] = []
    for row in parsed:
        if not isinstance(row, dict) or not normalize_metric(row.get("metric")):
            continue
        mid = float(row.get("guided_value") or 0)
        low = row.get("guided_low")
        high = row.get("guided_high")
        low_f = float(low) if low is not None else mid
        high_f = float(high) if high is not None else mid
        quote = str(row.get("quote_span") or row.get("guided_text") or "")[:200]
        out.append(
            {
                "company_id": company_id,
                "period": period,
                "metric": str(row["metric"]),
                "guided_value": mid,
                "guided_low": low_f,
                "guided_high": high_f,
                "actual_value": None,
                "guided_text": str(row.get("guided_text") or quote)[:240],
                "confidence": float(row.get("confidence") or 0.75),
                "speaker": str(row.get("speaker") or "Management"),
                "thread_id": f"{company_id}-{row['metric']}",
                "dropped": False,
                "source_url": None,
                "source_ref": source_ref,
                "quote_span": quote,
                "as_of": None,
                "review_status": "pending",
                "needs_review": True,
                "extract_engine": "llm_v1",
            }
        )
    return normalize_statement_metrics(out)


def rewrite_cite_only_answer(
    question: str,
    snippets: Sequence[str],
    *,
    gci_note: str = "",
) -> str:
    """Optional LLM polish — must stay grounded in snippets (caller still refuses if empty)."""
    joined = " | ".join(snippets[:4])
    raw = chat_completion(
        [
            {
                "role": "system",
                "content": (
                    "You are CiteAlpha Research. Answer ONLY using the provided source snippets. "
                    "Do not invent numbers or filings. End with: Not investment advice."
                ),
            },
            {
                "role": "user",
                "content": f"Question: {question}\nContext:{gci_note}\nSnippets: {joined}",
            },
        ],
        max_tokens=400,
        wait=False,
        reasoning="low",
    )
    return raw
