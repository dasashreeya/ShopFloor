"""The researched catalog (tools.json) and the sourced assumptions/research notes (research.json)."""

import json
from functools import lru_cache
from pathlib import Path

from shopfloor.models import Tool

HERE = Path(__file__).parent


@lru_cache
def research() -> dict:
    return json.loads((HERE / "research.json").read_text(encoding="utf-8"))


@lru_cache
def _raw_catalog() -> dict:
    return json.loads((HERE / "tools.json").read_text(encoding="utf-8"))


def catalog_tools() -> list[Tool]:
    raw = _raw_catalog()
    retrieved = raw["_meta"]["retrieved"]
    return [Tool(**{"retrieved": retrieved, **t}) for t in raw["tools"]]


def catalog_meta() -> dict:
    return _raw_catalog()["_meta"]


def assumption(key: str) -> dict:
    return research()["assumptions"][key]


def industry_group(industry: str) -> str:
    return research()["industry_groups"].get(industry, "other")
