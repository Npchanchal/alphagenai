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


def test_openai_usage_recorded(monkeypatch):
    monkeypatch.setenv("INTELLENS_LLM_BASE_URL", "https://api.openai.com/v1")
    _capture_post(monkeypatch, {"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 9, "completion_tokens": 2}})
    llm_client.chat_completion([{"role": "user", "content": "x"}])
    assert llm_client.last_usage() == {"input": 9, "output": 2}


class FakeBedrock:
    def __init__(self, reply=None, error=None):
        self.sent = []
        self.reply = reply
        self.error = error

    def converse(self, **request):
        self.sent.append(request)
        if self.error:
            raise self.error
        return self.reply


def _bedrock(monkeypatch, **kw):
    monkeypatch.setenv("INTELLENS_LLM_PROVIDER", "bedrock")
    monkeypatch.setenv("INTELLENS_LLM_MODEL", "openai.gpt-oss-120b-1:0")
    fake = FakeBedrock(**kw)
    monkeypatch.setattr(llm_client, "_bedrock", lambda timeout: fake)
    monkeypatch.setattr(llm_client, "_post_json", lambda *a, **k: pytest.fail("HTTP path used under bedrock"))
    return fake


def _converse_reply(content, stop="end_turn"):
    return {"output": {"message": {"content": content}}, "stopReason": stop, "usage": {"inputTokens": 50, "outputTokens": 7}}


def test_bedrock_converse_request_and_answer(monkeypatch):
    fake = _bedrock(monkeypatch, reply=_converse_reply([{"reasoningContent": {"reasoningText": {"text": "hmm"}}}, {"text": " ok "}]))
    assert llm_client.llm_configured() and not llm_client.is_gemini()
    out = llm_client.chat_completion(
        [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}], max_tokens=300, reasoning="low", service_tier="flex"
    )
    assert out == "ok"
    req = fake.sent[0]
    assert req["system"] == [{"text": "s"}]
    assert req["messages"] == [{"role": "user", "content": [{"text": "u"}]}]
    assert req["inferenceConfig"]["maxTokens"] == 300
    assert req["additionalModelRequestFields"] == {"reasoning_effort": "low"}
    assert req["serviceTier"] == {"type": "flex"}
    assert llm_client.last_usage() == {"input": 50, "output": 7}


def test_bedrock_cut_off_and_throttle_read_like_http(monkeypatch):
    from botocore.exceptions import ClientError

    _bedrock(monkeypatch, reply=_converse_reply([{"text": "[{"}], stop="max_tokens"))
    with pytest.raises(RuntimeError, match="cut off"):
        llm_client.chat_completion([{"role": "user", "content": "x"}])
    throttled = ClientError({"Error": {"Code": "ThrottlingException", "Message": "slow down"}}, "Converse")
    _bedrock(monkeypatch, error=throttled)
    with pytest.raises(RuntimeError, match="LLM HTTP 429"):
        llm_client.chat_completion([{"role": "user", "content": "x"}])


def test_bedrock_has_no_web_search(monkeypatch):
    _bedrock(monkeypatch)
    assert llm_client.web_search_links("infosys investor relations") == []


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
