"""Deterministic offline LLM so the whole product runs without a key (tests, demos, CI).

It answers by *task tag*: callers put `[task:<name>]` in the system prompt.
"""

import re

from shopfloor.llm.base import LLMResult, Usage


class FakeLLM:
    def __init__(self):
        self.calls: list[dict] = []

    def chat(self, messages, *, model=None, temperature=0.2, max_tokens=800, schema=None, schema_name="result"):
        self.calls.append({"messages": messages, "model": model, "schema": schema})
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        task = (re.search(r"\[task:([\w-]+)\]", system) or [None, "generic"])[1]
        data = _ANSWERS.get(task, lambda u: {"text": "ok"})(user)
        text = data.get("text", "") if isinstance(data, dict) else str(data)
        return LLMResult(
            text=text,
            model=f"fake/{model or 'default'}",
            latency_s=0.05,
            usage=Usage(prompt_tokens=len(str(messages)) // 4, completion_tokens=40, cost_usd=0.0001),
            data=data if schema is not None else None,
        )


def _tool_attempt(user: str) -> dict:
    return {"text": "Sorry we missed your call! Reply with your order and we'll have it ready for pickup."}


def _judge(user: str) -> dict:
    # Fails tasks whose golden output explicitly says the tool must decline.
    passed = "MUST_DECLINE" not in user
    return {"pass": passed, "reason": "matches rubric" if passed else "should have declined"}


def _extract(user: str) -> dict:
    url = user.splitlines()[0].removeprefix("URL: ").strip() if user else ""
    host = url.split("/")[2] if "//" in url else "example"
    return {"name": f"{host} (offline extraction)", "vendor": host, "is_ai_tool_for_small_business": True,
            "job": "missed_calls", "summary": "Offline mode: set OPENROUTER_API_KEY for a real extraction.",
            "plans": [], "quote_only": True, "trial": "", "integrations": []}


def _try(user: str) -> dict:
    return {"text": "(offline demo reply) Thank you for taking the time to share this. We'd like to make it right; "
                    "please call or email us so the owner can follow up personally."}


_ANSWERS = {
    "tool-attempt": _tool_attempt,
    "lab-judge": _judge,
    "extract-listing": _extract,
    "try-tool": _try,
}
