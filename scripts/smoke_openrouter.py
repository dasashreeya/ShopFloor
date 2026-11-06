"""One cheap live call to confirm the key, model slugs and JSON-schema mode work.

    uv run python scripts/smoke_openrouter.py
"""

from shopfloor.config import get_settings
from shopfloor.llm import OpenRouterClient

s = get_settings()
c = OpenRouterClient(s)
for model in (s.model_fast, s.model_judge):
    r = c.chat(
        [{"role": "user", "content": "Return ok=true."}],
        model=model, max_tokens=500,
        schema={"type": "object", "additionalProperties": False,
                "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
    )
    print(f"{model}: data={r.data} latency={r.latency_s:.2f}s cost=${r.usage.cost_usd:.6f}")
