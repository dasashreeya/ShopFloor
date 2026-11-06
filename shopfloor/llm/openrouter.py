"""Thin OpenRouter Chat Completions client.

Endpoint, headers and usage fields follow https://openrouter.ai/docs (verified 2026-11):
POST {base}/chat/completions, `Authorization: Bearer <key>`, optional `HTTP-Referer` and
`X-OpenRouter-Title` attribution headers; `usage.cost` is returned on every response.
"""

import json
import random
import time

import httpx

from shopfloor.config import Settings
from shopfloor.llm.base import LLMError, LLMResult, Usage

RETRYABLE = {408, 429, 500, 502, 503, 524, 529}


class OpenRouterClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None):
        if not settings.openrouter_api_key:
            raise LLMError("OPENROUTER_API_KEY is not set (or use SHOPFLOOR_LLM_MODE=fake)")
        self.settings = settings
        self._http = httpx.Client(
            base_url=settings.openrouter_base_url,
            timeout=settings.openrouter_timeout_s,
            transport=transport,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": settings.openrouter_site_url,
                "X-OpenRouter-Title": settings.openrouter_app_title,
            },
        )

    def chat(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 800,
        schema: dict | None = None,
        schema_name: str = "result",
    ) -> LLMResult:
        body: dict = {
            "model": model or self.settings.model_fast,
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
        }
        if schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": schema},
            }

        payload, latency = self._post_with_retry(body)
        try:
            choice = payload["choices"][0]
            text = choice["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError(f"Malformed OpenRouter response: {payload!r:.300}") from e
        if schema is not None and choice.get("finish_reason") == "length":
            # Reasoning models spend part of max_tokens thinking; truncated JSON is useless.
            raise LLMError(f"{body['model']} hit max_tokens={max_tokens} before finishing JSON "
                           "(reasoning tokens count toward the limit); raise max_tokens")

        u = payload.get("usage") or {}
        result = LLMResult(
            text=text,
            model=payload.get("model", body["model"]),
            latency_s=latency,
            usage=Usage(
                prompt_tokens=u.get("prompt_tokens", 0),
                completion_tokens=u.get("completion_tokens", 0),
                cost_usd=float(u.get("cost") or 0.0),
            ),
            raw=payload,
        )
        if schema is not None:
            result.data = parse_json(text)
        return result

    def _post_with_retry(self, body: dict) -> tuple[dict, float]:
        attempts = self.settings.openrouter_max_retries + 1
        for attempt in range(attempts):
            start = time.perf_counter()
            try:
                resp = self._http.post("/chat/completions", json=body)
            except httpx.TransportError as e:
                if attempt == attempts - 1:
                    raise LLMError(f"OpenRouter unreachable: {e}") from e
                self._sleep(attempt)
                continue
            latency = time.perf_counter() - start
            if resp.status_code == 200:
                return resp.json(), latency
            if resp.status_code in RETRYABLE and attempt < attempts - 1:
                self._sleep(attempt, resp.headers.get("retry-after"))
                continue
            raise LLMError(_error_message(resp), status=resp.status_code)
        raise LLMError("unreachable")  # pragma: no cover

    @staticmethod
    def _sleep(attempt: int, retry_after: str | None = None) -> None:
        if retry_after and retry_after.isdigit():
            time.sleep(min(float(retry_after), 30))
        else:
            time.sleep(min(2**attempt, 16) * (0.5 + random.random() / 2))


def _error_message(resp: httpx.Response) -> str:
    try:
        err = resp.json().get("error", {})
        return f"OpenRouter {resp.status_code}: {err.get('message', resp.text[:300])}"
    except ValueError:
        return f"OpenRouter {resp.status_code}: {resp.text[:300]}"


def parse_json(text: str):
    """Parse model JSON, tolerating ```json fences some providers add."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        t = t.rsplit("```", 1)[0]
    try:
        return json.loads(t)
    except json.JSONDecodeError as e:
        raise LLMError(f"Model did not return valid JSON: {text[:200]!r}") from e
