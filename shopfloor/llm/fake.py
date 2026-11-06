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
    return {"job": "other", "pricing_usd_month": 0, "integrations": [], "summary": user[:120]}


def _card_copy(user: str) -> dict:
    return {"headline": ""}  # empty -> caller keeps its template


_ANSWERS = {
    "tool-attempt": _tool_attempt,
    "lab-judge": _judge,
    "extract-listing": _extract,
    "card-copy": _card_copy,
    "shadow-draft": lambda u: {"text": f"(offline draft) would respond to {u[:80]}"},
}
