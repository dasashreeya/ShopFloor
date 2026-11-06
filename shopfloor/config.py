from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_site_url: str = "https://github.com/dasashreeya/ShopFloor"
    openrouter_app_title: str = "ShopFloor"
    openrouter_timeout_s: float = 60.0
    openrouter_max_retries: int = 3

    model_fast: str = Field("anthropic/claude-haiku-5.5", alias="SHOPFLOOR_MODEL_FAST")
    model_smart: str = Field("anthropic/claude-sonnet-5.5", alias="SHOPFLOOR_MODEL_SMART")
    model_judge: str = Field("google/gemini-3.8-flash", alias="SHOPFLOOR_MODEL_JUDGE")

    llm_mode: Literal["auto", "openrouter", "fake"] = Field("auto", alias="SHOPFLOOR_LLM_MODE")
    db_path: str = Field("data/shopfloor.db", alias="SHOPFLOOR_DB_PATH")

    @property
    def use_fake_llm(self) -> bool:
        if self.llm_mode == "fake":
            return True
        if self.llm_mode == "openrouter":
            return False
        return not self.openrouter_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
