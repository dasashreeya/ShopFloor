from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0  # OpenRouter returns usage.cost (credits == USD) on every response


@dataclass
class LLMResult:
    text: str
    model: str
    latency_s: float
    usage: Usage = field(default_factory=Usage)
    data: Any = None  # parsed JSON when a schema was requested
    raw: dict | None = None


class LLMError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class LLM(Protocol):
    def chat(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 800,
        schema: dict | None = None,
        schema_name: str = "result",
    ) -> LLMResult: ...
