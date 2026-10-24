"""Process-wide LLM rate limit (INTELLENS_LLM_RATE_PER_MIN)."""

import pytest

from app.services import llm_client


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    monkeypatch.setenv("INTELLENS_LLM_RATE_PER_MIN", "4")
    llm_client.reset_rate_limit()
    yield FakeClock()
    llm_client.reset_rate_limit()


def _acquire(clock, wait=True):
    llm_client._acquire_slot(wait=wait, clock=clock, sleep=clock.sleep)


def test_four_calls_pass_then_fifth_waits_for_oldest_to_age_out(clock):
    for _ in range(4):
        _acquire(clock)
        clock.now += 5
    assert clock.slept == []
    _acquire(clock)
    assert clock.slept == [pytest.approx(40.0)]


def test_interactive_call_fails_fast_when_full(clock):
    for _ in range(4):
        _acquire(clock)
    with pytest.raises(llm_client.LLMRateLimited):
        _acquire(clock, wait=False)
    assert clock.slept == []


def test_window_frees_after_a_minute(clock):
    for _ in range(4):
        _acquire(clock)
    clock.now += 60
    _acquire(clock, wait=False)
    assert clock.slept == []


def test_zero_disables_limit(clock, monkeypatch):
    monkeypatch.setenv("INTELLENS_LLM_RATE_PER_MIN", "0")
    for _ in range(50):
        _acquire(clock, wait=False)


def test_post_json_counts_against_limit(clock, monkeypatch):
    monkeypatch.setenv("INTELLENS_LLM_API_KEY", "k")
    for _ in range(4):
        llm_client._acquire_slot(wait=False)
    with pytest.raises(llm_client.LLMRateLimited):
        llm_client._post_json("/chat/completions", {}, wait=False)


def test_research_rewrite_falls_back_when_limited(clock, monkeypatch):
    monkeypatch.setenv("INTELLENS_LLM_API_KEY", "k")
    for _ in range(4):
        llm_client._acquire_slot(wait=False)
    with pytest.raises(llm_client.LLMRateLimited):
        llm_client.rewrite_cite_only_answer("q", ["snippet"])


def _capture_post(monkeypatch, reply):
    sent = []
    monkeypatch.setattr(llm_client, "_post_json", lambda path, payload, **kw: sent.append(payload) or reply)
    return sent


GEMINI = "https://generativelanguage.googleapis.com/v1beta/openai"


def test_gemini_gets_reasoning_headroom_unless_low(monkeypatch):
    monkeypatch.setenv("INTELLENS_LLM_BASE_URL", GEMINI)
    sent = _capture_post(monkeypatch, {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]})
    llm_client.chat_completion([{"role": "user", "content": "x"}], max_tokens=800)
    llm_client.chat_completion([{"role": "user", "content": "x"}], max_tokens=400, reasoning="low")
    assert sent[0]["max_tokens"] == 800 + llm_client.GEMINI_THINKING_HEADROOM
    assert sent[1]["max_tokens"] == 400 and sent[1]["reasoning_effort"] == "low"


def test_gemini_service_tier_sent_only_when_asked(monkeypatch):
    monkeypatch.setenv("INTELLENS_LLM_BASE_URL", GEMINI)
    sent = _capture_post(monkeypatch, {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]})
    llm_client.chat_completion([{"role": "user", "content": "x"}], reasoning="low", service_tier="flex")
    llm_client.chat_completion([{"role": "user", "content": "x"}], reasoning="low")
    assert sent[0]["service_tier"] == "flex" and "service_tier" not in sent[1]


def test_openai_payload_unchanged(monkeypatch):
    monkeypatch.setenv("INTELLENS_LLM_BASE_URL", "https://api.openai.com/v1")
    sent = _capture_post(monkeypatch, {"choices": [{"message": {"content": "ok"}}]})
    llm_client.chat_completion([{"role": "user", "content": "x"}], max_tokens=800, reasoning="low")
    assert sent[0]["max_tokens"] == 800 and "reasoning_effort" not in sent[0]


def test_cut_off_answer_raises(monkeypatch):
    _capture_post(monkeypatch, {"choices": [{"message": {"content": "[{\"metric\""}, "finish_reason": "length"}]})
    with pytest.raises(RuntimeError):
        llm_client.chat_completion([{"role": "user", "content": "x"}])


def test_extract_drops_unknown_metrics_and_keeps_the_rest(monkeypatch):
    reply = (
        '[{"metric": "capex_guidance", "guided_value": 26000, "quote_span": "capex of INR26,000 crore"},'
        ' {"metric": "psp_capacity_commissioned_mw", "guided_value": 1000, "quote_span": "1,000 MW"}]'
    )
    sent = _capture_post(monkeypatch, {"choices": [{"message": {"content": reply}, "finish_reason": "stop"}]})
    rows = llm_client.extract_guidance_via_llm("t", company_id="ntpc", period="FY26", source_ref="u")
    assert [r["metric"] for r in rows] == ["capex_guidance"]
    assert rows[0]["guided_value"] == 26000.0
    prompt = sent[0]["messages"][0]["content"]
    assert "capex_guidance [inr_cr]" in prompt and "{metric_ids}" not in prompt
