"""Discovery: turn any public product or marketplace page into a catalog *candidate*.

Paste a URL (a vendor pricing page, a Square/QuickBooks/Xero app-store listing). We fetch it, strip it to text,
and an LLM extracts a structured listing against a strict JSON schema. Candidates are shown in Browse labeled
"auto-extracted, unverified" and are never recommended until a human verifies them (16-week plan: scheduled
marketplace crawls + change detection feed this same path).
"""

import re
from html import unescape

import httpx

from shopfloor.config import get_settings
from shopfloor.llm import LLM
from shopfloor.models import Job, Plan, Pricing, Tool, now

EXTRACT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "name": {"type": "string"},
        "vendor": {"type": "string"},
        "is_ai_tool_for_small_business": {"type": "boolean"},
        "job": {"type": "string", "enum": [j.value for j in Job] + ["other"]},
        "summary": {"type": "string"},
        "plans": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                  "properties": {"name": {"type": "string"}, "usd_month": {"type": "number"}, "notes": {"type": "string"}},
                  "required": ["name", "usd_month", "notes"]}},
        "quote_only": {"type": "boolean"},
        "trial": {"type": "string"},
        "integrations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["name", "vendor", "is_ai_tool_for_small_business", "job", "summary", "plans", "quote_only", "trial", "integrations"],
}


class DiscoveryError(ValueError):
    pass


def page_text(url: str, limit: int = 12000) -> str:
    if not re.match(r"^https://[\w.-]+\.[a-z]{2,}(/|$)", url):
        raise DiscoveryError("Use a public https:// URL")
    try:
        r = httpx.get(url, timeout=15, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0 (compatible; ShopFloorDiscovery/0.2)"})
    except httpx.HTTPError as e:
        raise DiscoveryError(f"Couldn't fetch the page: {e}") from e
    if r.status_code >= 400:
        raise DiscoveryError(f"The site returned HTTP {r.status_code} (some review sites block automated access)")
    html = re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", " ", r.text)
    text = unescape(re.sub(r"<[^>]+>", " ", html))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def extract(url: str, text: str, llm: LLM) -> Tool:
    res = llm.chat(
        [{"role": "system", "content": "[task:extract-listing] Extract a structured listing of the software product "
          "described on this web page. Only use facts stated on the page; if a price is not stated, return no plans "
          "and quote_only=true. Prices are monthly USD. job=other if it is not one of the listed jobs."},
         {"role": "user", "content": f"URL: {url}\n\nPAGE TEXT:\n{text}"}],
        model=get_settings().model_fast, schema=EXTRACT_SCHEMA, schema_name="listing", max_tokens=1200,
    )
    d = res.data or {}
    if not d.get("name"):
        raise DiscoveryError("Couldn't find a product on that page")
    job = d.get("job")
    slug = "cand-" + re.sub(r"\W+", "-", d["name"].lower()).strip("-")[:40]
    return Tool(
        id=slug, name=d["name"], vendor=d.get("vendor", ""), kind="candidate",
        jobs=[Job(job)] if job in Job._value2member_map_ else [],
        summary=d.get("summary", ""), website=url,
        pricing=Pricing(url=url, evidence="llm_extracted", unit="flat",
                        plans=[Plan(name=p["name"], usd_month=p["usd_month"], notes=p.get("notes", "")) for p in d.get("plans", [])],
                        quote_only=bool(d.get("quote_only")), trial=d.get("trial", ""),
                        notes="Auto-extracted from the page by an LLM; not yet verified by a person."),
        works_with=[i.lower().replace(" ", "_") for i in d.get("integrations", [])][:12],
        engage={"signup_url": url, "cta": "Visit page"},
        evidence_gap="Auto-discovered candidate: no reviews collected yet.",
        retrieved=now().date().isoformat(),
        capabilities={"is_ai_tool": d.get("is_ai_tool_for_small_business")},
    )
