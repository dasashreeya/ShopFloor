from shopfloor.config import Settings, get_settings
from shopfloor.llm.base import LLM, LLMError, LLMResult, Usage
from shopfloor.llm.fake import FakeLLM
from shopfloor.llm.openrouter import OpenRouterClient


def get_llm(settings: Settings | None = None) -> LLM:
    settings = settings or get_settings()
    return FakeLLM() if settings.use_fake_llm else OpenRouterClient(settings)


__all__ = ["LLM", "LLMError", "LLMResult", "Usage", "FakeLLM", "OpenRouterClient", "get_llm"]
