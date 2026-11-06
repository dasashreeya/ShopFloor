import json

import httpx
import pytest

from shopfloor.config import Settings
from shopfloor.llm import LLMError, OpenRouterClient
from shopfloor.llm.openrouter import parse_json


def ok(content: str, cost=0.0012):
    return httpx.Response(200, json={
        "id": "gen-1", "model": "anthropic/claude-haiku-5.5",
        "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "cost": cost},
    })


def client(handler, **kw):
    s = Settings(openrouter_api_key="sk-test", openrouter_max_retries=2, **kw)
    return OpenRouterClient(s, transport=httpx.MockTransport(handler))


def test_request_shape_and_usage(monkeypatch):
    seen = {}

    def handler(req: httpx.Request):
        seen["url"] = str(req.url)
        seen["headers"] = req.headers
        seen["body"] = json.loads(req.content)
        return ok('{"answer": 4}')

    res = client(handler).chat([{"role": "user", "content": "2+2"}], model="m/x",
                               schema={"type": "object"}, schema_name="math")
    assert seen["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert seen["headers"]["authorization"] == "Bearer sk-test"
    assert seen["headers"]["x-openrouter-title"] == "ShopFloor"
    assert seen["body"]["model"] == "m/x"
    assert seen["body"]["response_format"]["type"] == "json_schema"
    assert seen["body"]["response_format"]["json_schema"]["name"] == "math"
    assert res.data == {"answer": 4}
    assert res.usage.cost_usd == pytest.approx(0.0012)
    assert res.usage.prompt_tokens == 10


def test_retries_on_429(monkeypatch):
    monkeypatch.setattr("shopfloor.llm.openrouter.time.sleep", lambda s: None)
    calls = iter([httpx.Response(429, json={"error": {"code": 429, "message": "slow down"}}), ok("hi")])
    assert client(lambda req: next(calls)).chat([{"role": "user", "content": "x"}]).text == "hi"


def test_non_retryable_error_surfaces_message():
    def handler(req):
        return httpx.Response(401, json={"error": {"code": 401, "message": "Missing Authentication header"}})

    with pytest.raises(LLMError, match="401: Missing Authentication header") as ei:
        client(handler).chat([{"role": "user", "content": "x"}])
    assert ei.value.status == 401


def test_missing_key_is_explicit():
    with pytest.raises(LLMError, match="OPENROUTER_API_KEY"):
        OpenRouterClient(Settings(openrouter_api_key=""))


def test_truncated_json_is_reported_clearly():
    def handler(req):
        r = ok('{"ok": tr')
        body = json.loads(r.content)
        body["choices"][0]["finish_reason"] = "length"
        return httpx.Response(200, json=body)

    with pytest.raises(LLMError, match="hit max_tokens"):
        client(handler).chat([{"role": "user", "content": "x"}], schema={"type": "object"})


def test_parse_json_tolerates_fences():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(LLMError):
        parse_json("not json")
