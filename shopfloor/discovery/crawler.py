"""Independent discovery: we crawl POS/accounting marketplaces; vendors never submit themselves.

`MarketplaceSource` is the seam for real crawlers (Square App Marketplace, Toast Partner
Connect, QuickBooks App Store). Structured listings pass straight through; free-text ones
are normalized by an LLM into a `Tool`.
"""

import json
import re
from pathlib import Path
from typing import Iterable, Protocol

from shopfloor.config import get_settings
from shopfloor.llm import LLM, LLMError
from shopfloor.models import ConnectorKind, Job, Tool

SEED = Path(__file__).with_name("seed_listings.json")

EXTRACT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "name": {"type": "string"},
        "vendor": {"type": "string"},
        "job": {"type": "string", "enum": [j.value for j in Job]},
        "price_usd_month": {"type": "number"},
        "integrations": {"type": "array", "items": {"type": "string", "enum": [c.value for c in ConnectorKind]}},
        "summary": {"type": "string"},
    },
    "required": ["name", "vendor", "job", "price_usd_month", "integrations", "summary"],
}


class MarketplaceSource(Protocol):
    name: str

    def listings(self) -> Iterable[dict]: ...


class SeedFileSource:
    name = "seed"

    def __init__(self, path: Path = SEED):
        self.path = path

    def listings(self) -> Iterable[dict]:
        return json.loads(self.path.read_text())


def discover(sources: Iterable[MarketplaceSource], llm: LLM) -> list[Tool]:
    tools: list[Tool] = []
    for src in sources:
        for listing in src.listings():
            try:
                tools.append(normalize(listing, llm))
            except (LLMError, ValueError) as e:  # one bad listing must not stop the crawl
                print(f"[discovery] skipped listing {listing.get('id')}: {e}")
    return tools


def normalize(listing: dict, llm: LLM) -> Tool:
    if listing.get("raw_text"):
        res = llm.chat(
            [
                {"role": "system", "content": "[task:extract-listing] Extract a structured profile of this AI tool "
                 "from a marketplace listing. Use job=other if it fits none. Price is monthly USD."},
                {"role": "user", "content": listing["raw_text"]},
            ],
            model=get_settings().model_fast,
            schema=EXTRACT_SCHEMA,
            schema_name="tool_listing",
        )
        listing = {**listing, **(res.data or {})}
        listing["name"] = listing.get("name") or listing["raw_text"].split(" ")[0]
    slug = listing.get("id") or re.sub(r"\W+", "-", listing["name"].lower())
    return Tool(
        id=slug,
        name=listing["name"],
        vendor=listing.get("vendor", ""),
        job=Job(listing.get("job") or "other"),
        price_usd_month=float(listing.get("price_usd_month") or 0),
        source=listing.get("source", "unknown"),
        integrations=[ConnectorKind(c) for c in listing.get("integrations", []) if c in ConnectorKind._value2member_map_],
        summary=listing.get("summary", ""),
        behavior=listing.get("behavior", listing.get("summary", "")),
    )
