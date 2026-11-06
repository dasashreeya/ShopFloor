"""Turn predictions into swipeable cards. Copy is template-first. An LLM may rephrase the
headline (the observation), never the body (the money sentence): a live run showed a model
keeping the right numbers but swapping value and cost. Headline rewrites that introduce a
number not in the original are rejected."""

import re

from shopfloor.config import get_settings
from shopfloor.llm import LLM, LLMError
from shopfloor.models import Card, Job, LabScore, Prediction, Tool
from shopfloor.replay.estimators import Estimate

TEMPLATES = {
    Job.MISSED_CALLS: ("You missed {missed} calls in the last 90 days, {rush} of them over the lunch rush.",
                       "{tool} would have recovered roughly {orders_per_month} orders a month: about +${value}/month against ${cost}/month."),
    Job.REVIEW_REPLIES: ("{unreplied} Google reviews never got a reply ({negative} of them negative).",
                         "{tool} would have answered them: worth about +${value}/month against ${cost}/month."),
    Job.INVOICE_CHASING: ("{late} invoices went late, ${late_usd} in total.",
                          "{tool} chases them for you: about +${value}/month against ${cost}/month."),
    Job.EMAIL_TRIAGE: ("{emails} emails hit your inbox, {catering} of them catering requests.",
                       "{tool} sorts them and answers catering fast: about +${value}/month against ${cost}/month."),
}

STATS = {
    Job.MISSED_CALLS: [("Missed during rush", "{rush} calls", False), ("Recoverable orders", "~{orders_per_month}/mo", True)],
    Job.REVIEW_REPLIES: [("Unreplied reviews", "{unreplied}", False), ("Negative, unanswered", "{negative}", True)],
    Job.INVOICE_CHASING: [("Late invoices", "{late}", False), ("Late balance", "${late_usd:,}", True)],
    Job.EMAIL_TRIAGE: [("Inbound emails", "{emails:,}", False), ("Catering requests", "{catering}", True)],
}

COPY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"headline": {"type": "string"}},
    "required": ["headline"],
}

NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _nums(text: str) -> set[str]:
    return {n.replace(",", "") for n in NUM.findall(text)}


def build_card(pred: Prediction, tool: Tool, est: Estimate, lab: LabScore | None, llm: LLM | None = None) -> Card:
    facts = {**est.facts, "tool": tool.name, "value": f"{pred.monthly_value_usd:,.0f}", "cost": f"{pred.monthly_cost_usd:,.0f}"}
    head_t, body_t = TEMPLATES.get(tool.job, ("{tool}", "About +${value}/month against ${cost}/month."))
    headline, body = head_t.format(**facts), body_t.format(**facts)
    if llm is not None:
        headline = _polish(llm, headline)
    return Card(
        business_id=pred.business_id, prediction_id=pred.id, tool_id=tool.id, tool_name=tool.name, job=tool.job,
        headline=headline, body=body,
        monthly_value_usd=round(pred.monthly_value_usd, 2), monthly_value_low=round(pred.monthly_value_low, 2),
        monthly_value_high=round(pred.monthly_value_high, 2), monthly_cost_usd=pred.monthly_cost_usd,
        lab_accuracy=lab.accuracy if lab else None,
        stats=[{"label": label, "value": value.format(**est.facts), "accent": accent}
               for label, value, accent in STATS.get(tool.job, [])],
    )


def _polish(llm: LLM, headline: str) -> str:
    try:
        res = llm.chat(
            [
                {"role": "system", "content": "[task:card-copy] Rewrite this one-sentence observation for a busy "
                 "restaurant owner: plain, concrete, no hype. Keep every number exactly; add no new numbers."},
                {"role": "user", "content": headline},
            ],
            model=get_settings().model_fast, schema=COPY_SCHEMA, schema_name="card", max_tokens=800,
        )
    except LLMError:
        return headline
    new_h = (res.data or {}).get("headline", "")
    if not new_h or not _nums(new_h) <= _nums(headline):
        return headline
    return new_h
