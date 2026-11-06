"""Swipe left = pass, up = 14-day shadow shift (live data, no actions), right = hire.
One button fires: revoke access, export data, cancel billing."""

from datetime import timedelta

from shopfloor.config import get_settings
from shopfloor.connectors.base import SCOPES
from shopfloor.llm import LLM, LLMError
from shopfloor.models import Card, Crew, Event, Hire, HireStatus, Job, SwipeDirection, Tool, now

SHADOW_DAYS = 14
REFERRAL_FEE_RATE = 0.20  # recurring share of the tool's subscription (business model)
JOB_EVENTS: dict[Job, list[str]] = {
    Job.MISSED_CALLS: ["call"],
    Job.REVIEW_REPLIES: ["review"],
    Job.INVOICE_CHASING: ["invoice"],
    Job.EMAIL_TRIAGE: ["email"],
}


class LifecycleError(ValueError):
    pass


def _scopes(tool: Tool, read_only: bool) -> list[str]:
    scopes = [f"{c.value}:{s}" for c in tool.integrations for s in SCOPES.get(c, [])]
    return [s for s in scopes if not read_only or any(w in s.lower() for w in ("read", "readonly"))]


def would_have_acted(tool: Tool, event: Event) -> bool:
    if event.kind not in JOB_EVENTS.get(tool.job, []):
        return False
    if tool.job == Job.MISSED_CALLS:
        return bool(event.attrs.get("missed"))
    if tool.job == Job.REVIEW_REPLIES:
        return not event.attrs.get("replied")
    if tool.job == Job.INVOICE_CHASING:
        return event.attrs.get("days_late", 0) > 0
    return True


def swipe(card: Card, direction: SwipeDirection, tool: Tool, recent: list[Event], llm: LLM | None = None) -> Hire | None:
    if card.decision is not None:
        raise LifecycleError(f"card {card.id} already decided: {card.decision}")
    card.decision = direction
    if direction == SwipeDirection.LEFT:
        return None
    if direction == SwipeDirection.UP:
        hire = Hire(business_id=card.business_id, tool_id=tool.id, prediction_id=card.prediction_id,
                    status=HireStatus.SHADOW, granted_scopes=_scopes(tool, read_only=True),
                    shadow_ends_at=now() + timedelta(days=SHADOW_DAYS))
        hire.shadow_log = shadow_log(tool, recent, llm)
        return hire
    return _activate(Hire(business_id=card.business_id, tool_id=tool.id, prediction_id=card.prediction_id,
                          status=HireStatus.HIRED), tool)


def promote(hire: Hire, tool: Tool) -> Hire:
    if hire.status != HireStatus.SHADOW:
        raise LifecycleError(f"only shadow hires can be promoted (status={hire.status})")
    return _activate(hire, tool)


def _activate(hire: Hire, tool: Tool) -> Hire:
    hire.status = HireStatus.HIRED
    hire.hired_at = now()
    hire.granted_scopes = _scopes(tool, read_only=False)
    hire.billing = {"plan_usd_month": tool.price_usd_month, "status": "active",
                    "referral_fee_usd_month": round(tool.price_usd_month * REFERRAL_FEE_RATE, 2)}
    return hire


def fire(hire: Hire) -> dict:
    """Revoke access, export data, cancel billing. Returns the export bundle handed to the owner."""
    if hire.status == HireStatus.FIRED:
        raise LifecycleError(f"hire {hire.id} already fired")
    revoked = list(hire.granted_scopes)
    # TODO(real integrations): call each provider's token-revocation endpoint here.
    hire.granted_scopes = []
    if hire.billing:
        hire.billing = {**hire.billing, "status": "cancelled"}  # TODO: cancel in billing provider
    hire.status = HireStatus.FIRED
    hire.fired_at = now()
    return {"revoked_scopes": revoked, "billing": hire.billing, "export": hire.model_dump(mode="json")}


def shadow_log(tool: Tool, events: list[Event], llm: LLM | None, drafts: int = 3) -> list[dict]:
    """Actions the tool *would* have taken. Nothing is sent. A few get LLM drafts for show-and-tell."""
    log = []
    for e in events:
        if not would_have_acted(tool, e):
            continue
        entry = {"ts": e.ts.isoformat(), "event": e.kind, "attrs": e.attrs, "action": f"{tool.name} would respond"}
        if llm is not None and len([x for x in log if "draft" in x]) < drafts:
            try:
                entry["draft"] = llm.chat(
                    [{"role": "system", "content": f"[task:shadow-draft] {tool.behavior}"},
                     {"role": "user", "content": f"{e.kind} event: {e.attrs}"}],
                    model=get_settings().model_fast, max_tokens=200,
                ).text
            except LLMError as err:
                entry["draft_error"] = str(err)
        log.append(entry)
    return log


def make_crew(business_id: str, hires: list[Hire], tools: dict[str, Tool]) -> Crew:
    routes: dict[str, list[str]] = {}
    for h in hires:
        for kind in JOB_EVENTS.get(tools[h.tool_id].job, []):
            routes.setdefault(kind, []).append(h.id)
    crew = Crew(business_id=business_id, hire_ids=[h.id for h in hires], routes=routes)
    for h in hires:
        h.crew_id = crew.id
    return crew


def route(crew: Crew, event: Event) -> list[str]:
    """The integration layer: which hired tools receive this event."""
    return crew.routes.get(event.kind, [])
