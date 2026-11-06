"""Replay estimators: what would this tool have done on the business's own last N days?

Rule: numbers come from deterministic math over real events + explicit, published
assumptions (low/mid/high). LLMs never compute the money; they only phrase it.
Every assumption here is a prior that the outcome loop (outcomes/calibration.py) corrects.
"""

from dataclasses import dataclass, field
from statistics import mean
from typing import Callable

from shopfloor.models import Event, Job

MONTH = 30.0


@dataclass
class Estimate:
    opportunity: dict[str, float]
    low: float
    mid: float
    high: float
    assumptions: dict[str, float] = field(default_factory=dict)
    facts: dict[str, float | str] = field(default_factory=dict)  # numbers the card copy may quote


def _per_month(n: float, window_days: int) -> float:
    return n * MONTH / window_days


def _avg_ticket(events: list[Event]) -> float:
    totals = [e.attrs["total"] for e in events if e.kind == "order"]
    return mean(totals) if totals else 25.0


def missed_calls(events: list[Event], window_days: int, accuracy: float) -> Estimate:
    missed = [e for e in events if e.kind == "call" and e.attrs.get("missed")]
    rush = sum(1 for e in missed if e.attrs.get("rush"))
    callers = len({e.attrs.get("caller") for e in missed})
    ticket = _avg_ticket(events)
    recovery = {"low": 0.15, "mid": 0.25, "high": 0.35}  # share of texted-back callers who order
    monthly_callers = _per_month(callers, window_days)
    vals = {k: monthly_callers * r * accuracy * ticket for k, r in recovery.items()}
    orders = monthly_callers * recovery["mid"] * accuracy
    return Estimate(
        opportunity={"missed_calls": len(missed), "rush_missed_calls": rush, "unique_callers": callers},
        low=vals["low"], mid=vals["mid"], high=vals["high"],
        assumptions={"recovery_rate_mid": recovery["mid"], "avg_ticket_usd": round(ticket, 2)},
        facts={"missed": len(missed), "rush": rush, "orders_per_month": round(orders), "avg_ticket": round(ticket, 2)},
    )


def review_replies(events: list[Event], window_days: int, accuracy: float) -> Estimate:
    unreplied = [e for e in events if e.kind == "review" and not e.attrs.get("replied")]
    negative = sum(1 for e in unreplied if e.attrs.get("stars", 5) <= 2)
    per_reply = {"low": 4.0, "mid": 12.0, "high": 25.0}  # retained/won revenue per replied review
    monthly = _per_month(len(unreplied), window_days)
    vals = {k: monthly * v * accuracy for k, v in per_reply.items()}
    return Estimate(
        opportunity={"unreplied_reviews": len(unreplied), "unreplied_negative": negative},
        low=vals["low"], mid=vals["mid"], high=vals["high"],
        assumptions={"value_per_reply_mid": per_reply["mid"]},
        facts={"unreplied": len(unreplied), "negative": negative},
    )


def invoice_chasing(events: list[Event], window_days: int, accuracy: float) -> Estimate:
    late = [e for e in events if e.kind == "invoice" and e.attrs.get("days_late", 0) > 0]
    late_usd = sum(e.attrs["amount"] for e in late)
    writeoff_cut = {"low": 0.02, "mid": 0.04, "high": 0.07}  # share of late $ no longer written off
    owner_time = _per_month(len(late), window_days) * 3 * (10 / 60) * 30  # 3 reminders x 10 min x $30/h
    vals = {k: _per_month(late_usd, window_days) * c * accuracy + owner_time * accuracy for k, c in writeoff_cut.items()}
    return Estimate(
        opportunity={"late_invoices": len(late), "late_usd": round(late_usd, 2)},
        low=vals["low"], mid=vals["mid"], high=vals["high"],
        assumptions={"writeoff_reduction_mid": writeoff_cut["mid"], "owner_rate_usd_h": 30},
        facts={"late": len(late), "late_usd": round(late_usd)},
    )


def email_triage(events: list[Event], window_days: int, accuracy: float) -> Estimate:
    emails = [e for e in events if e.kind == "email"]
    catering = sum(1 for e in emails if e.attrs.get("category") == "catering")
    minutes_saved = _per_month(len(emails), window_days) * 1.5
    time_value = minutes_saved / 60 * 30
    lead_uplift = {"low": 0.02, "mid": 0.05, "high": 0.10}  # extra catering wins from faster replies
    vals = {k: (time_value + _per_month(catering, window_days) * u * 400) * accuracy for k, u in lead_uplift.items()}
    return Estimate(
        opportunity={"emails": len(emails), "catering_emails": catering},
        low=vals["low"], mid=vals["mid"], high=vals["high"],
        assumptions={"catering_uplift_mid": lead_uplift["mid"], "catering_ticket_usd": 400},
        facts={"emails": len(emails), "catering": catering},
    )


ESTIMATORS: dict[Job, Callable[[list[Event], int, float], Estimate]] = {
    Job.MISSED_CALLS: missed_calls,
    Job.REVIEW_REPLIES: review_replies,
    Job.INVOICE_CHASING: invoice_chasing,
    Job.EMAIL_TRIAGE: email_triage,
}
